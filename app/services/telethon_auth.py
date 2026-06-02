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


def looks_like_sms_code(text: str) -> bool:
    cleaned = re.sub(r"\s+", "", text.strip())
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


async def _create_client(settings: Settings) -> TelegramClient:
    client = TelegramClient(
        StringSession(),
        settings.telegram_api_id,
        settings.telegram_api_hash,
        **_client_kwargs(settings),
    )
    await connect_telethon(client, settings)
    return client


async def start_login(telegram_id: int, phone: str, settings: Settings) -> CodeSent:
    normalized = normalize_phone(phone)
    if not is_plausible_phone(normalized):
        raise ValueError("Invalid phone number. Use format +79001234567")

    async with _lock(telegram_id):
        await cancel_login(telegram_id)
        client = await _create_client(settings)
        try:
            sent = await client.send_code_request(normalized)
        except PhoneNumberInvalidError as exc:
            await client.disconnect()
            raise ValueError("Invalid phone number. Use format +79001234567") from exc

        _pending[telegram_id] = PendingLogin(
            client=client,
            phone=normalized,
            phone_code_hash=sent.phone_code_hash,
        )
        logger.info("login_code_sent", telegram_id=telegram_id, phone=mask_phone(normalized))
        return CodeSent(phone=normalized, phone_code_hash=sent.phone_code_hash)


async def complete_login(
    telegram_id: int,
    code: str,
    settings: Settings,
    *,
    password: str | None = None,
) -> str:
    pending = _pending.get(telegram_id)
    if not pending:
        raise ValueError("Login session expired. Start again.")

    client = pending.client
    code = (code or "").strip().replace(" ", "")

    try:
        if password:
            await client.sign_in(password=password)
        elif code:
            # Use the same Telethon client + internal phone_code_hash from send_code_request
            await client.sign_in(code=code)
        else:
            raise ValueError("Enter the code from Telegram.")
    except SessionPasswordNeededError:
        if password:
            raise ValueError("Invalid 2FA password")
        raise ValueError("2FA_REQUIRED")
    except PhoneCodeInvalidError as exc:
        raise ValueError("Invalid code. Try again.") from exc
    except PhoneCodeExpiredError as exc:
        logger.warning("login_code_expired", telegram_id=telegram_id)
        await cancel_login(telegram_id)
        raise ValueError("Code expired. Request a new one.") from exc

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
