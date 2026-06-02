import asyncio
import re
from dataclasses import dataclass

from telethon import TelegramClient
from telethon.errors import (
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    SessionPasswordNeededError,
)
from telethon.sessions import StringSession
from telethon.utils import parse_phone as tg_parse_phone

from app.config import Settings
from app.services.telethon_client import _client_kwargs, connect_telethon
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CodeSent:
    phone: str
    phone_code_hash: str


@dataclass
class PendingLogin:
    client: TelegramClient
    phone: str
    phone_code_hash: str


_pending: dict[int, PendingLogin] = {}
_login_locks: dict[int, asyncio.Lock] = {}


def normalize_phone(raw: str) -> str:
    phone = raw.strip().replace(" ", "").replace("-", "")
    if phone.startswith("8") and len(phone) == 11:
        phone = "+7" + phone[1:]
    if not phone.startswith("+"):
        phone = f"+{phone}"
    return phone


def telethon_phone(raw: str) -> str:
    """Phone key must match Telethon's internal format after send_code_request."""
    normalized = normalize_phone(raw)
    return tg_parse_phone(normalized) or normalized


def normalize_code(raw: str) -> str:
    return "".join(ch for ch in raw if ch.isdigit())


def looks_like_sms_code(text: str) -> bool:
    cleaned = normalize_code(text)
    return cleaned.isdigit() and 4 <= len(cleaned) <= 6


def is_plausible_phone(text: str) -> bool:
    if looks_like_sms_code(text):
        return False
    digits = re.sub(r"\D", "", text)
    return len(digits) >= 10


def _lock(telegram_id: int) -> asyncio.Lock:
    if telegram_id not in _login_locks:
        _login_locks[telegram_id] = asyncio.Lock()
    return _login_locks[telegram_id]


async def _ensure_connected(client: TelegramClient, settings: Settings) -> None:
    if not client.is_connected():
        await connect_telethon(client, settings)


async def _create_client(settings: Settings) -> TelegramClient:
    client = TelegramClient(
        StringSession(),
        settings.telegram_api_id,
        settings.telegram_api_hash,
        **_client_kwargs(settings),
    )
    await connect_telethon(client, settings)
    return client


async def _send_code(client: TelegramClient, phone: str) -> CodeSent:
    sent = await client.send_code_request(phone)
    if not sent.phone_code_hash:
        raise ValueError("Telegram did not return a code hash. Try again.")
    telethon_phone = client._phone or phone
    return CodeSent(phone=telethon_phone, phone_code_hash=sent.phone_code_hash)


async def start_login(telegram_id: int, phone: str, settings: Settings) -> CodeSent:
    parsed = telethon_phone(phone)
    if not is_plausible_phone(parsed):
        raise ValueError("Invalid phone number. Use format +79001234567")

    async with _lock(telegram_id):
        await cancel_login(telegram_id)
        client = await _create_client(settings)
        try:
            result = await _send_code(client, parsed)
        except PhoneNumberInvalidError as exc:
            await client.disconnect()
            raise ValueError("Invalid phone number. Use format +79001234567") from exc

        _pending[telegram_id] = PendingLogin(
            client=client,
            phone=result.phone,
            phone_code_hash=result.phone_code_hash,
        )
        logger.info(
            "login_code_sent",
            telegram_id=telegram_id,
            phone=mask_phone(result.phone),
            hash_prefix=result.phone_code_hash[:8],
        )
        return result


async def resend_login_code(telegram_id: int, settings: Settings) -> CodeSent:
    pending = _pending.get(telegram_id)
    if not pending:
        raise ValueError("Login session expired. Share your phone again.")

    async with _lock(telegram_id):
        await _ensure_connected(pending.client, settings)
        try:
            result = await _send_code(pending.client, pending.phone)
        except PhoneCodeExpiredError:
            result = await _send_code(pending.client, pending.phone)

        pending.phone = result.phone
        pending.phone_code_hash = result.phone_code_hash
        logger.info("login_code_resent", telegram_id=telegram_id)
        return result


async def complete_login(
    telegram_id: int,
    code: str,
    settings: Settings,
    *,
    password: str | None = None,
) -> str:
    pending = _pending.get(telegram_id)
    if not pending:
        raise ValueError("Login session expired. Share your phone again.")

    async with _lock(telegram_id):
        client = pending.client
        await _ensure_connected(client, settings)

        try:
            if password:
                await client.sign_in(password=password)
            else:
                code_digits = normalize_code(code)
                if not code_digits:
                    raise ValueError("Enter the code from Telegram.")
                await client.sign_in(
                    pending.phone,
                    code_digits,
                    phone_code_hash=pending.phone_code_hash,
                )
        except SessionPasswordNeededError:
            if password:
                raise ValueError("Invalid 2FA password")
            raise ValueError("2FA_REQUIRED")
        except PhoneCodeInvalidError as exc:
            raise ValueError("Invalid code. Check digits and try again.") from exc
        except PhoneCodeExpiredError as exc:
            logger.warning("login_code_expired", telegram_id=telegram_id)
            try:
                fresh = await _send_code(client, pending.phone)
                pending.phone = fresh.phone
                pending.phone_code_hash = fresh.phone_code_hash
            except Exception:
                await cancel_login(telegram_id)
                raise ValueError("Code expired. Share your phone again.") from exc
            raise ValueError("Code expired. A new code was sent — enter the latest one.") from exc

        if not await client.is_user_authorized():
            raise ValueError("Authorization failed")

        session_string = client.session.save()
        _pending.pop(telegram_id, None)
        await client.disconnect()
        logger.info("login_completed", telegram_id=telegram_id)
        return session_string


def get_pending_phone(telegram_id: int) -> str | None:
    pending = _pending.get(telegram_id)
    return pending.phone if pending else None


async def cancel_login(telegram_id: int) -> None:
    pending = _pending.pop(telegram_id, None)
    if pending:
        await pending.client.disconnect()


def mask_phone(phone: str) -> str:
    if len(phone) < 6:
        return phone
    return f"{phone[:3]}***{phone[-2:]}"
