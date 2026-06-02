import asyncio
import re
from dataclasses import dataclass, field
from typing import Any

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
    phone: str = ""
    phone_code_hash: str = ""
    mode: str = "phone"
    qr_login: Any = field(default=None, repr=False)


_pending: dict[int, PendingLogin] = {}
_login_locks: dict[int, asyncio.Lock] = {}
_qr_tasks: dict[int, asyncio.Task] = {}


def normalize_phone(raw: str) -> str:
    phone = raw.strip().replace(" ", "").replace("-", "")
    if phone.startswith("8") and len(phone) == 11:
        phone = "+7" + phone[1:]
    if not phone.startswith("+"):
        phone = f"+{phone}"
    return phone


def telethon_phone(raw: str) -> str:
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


def cancel_qr_task(telegram_id: int) -> None:
    task = _qr_tasks.pop(telegram_id, None)
    if task and not task.done():
        task.cancel()


async def start_qr_login(telegram_id: int, settings: Settings) -> str:
    async with _lock(telegram_id):
        await cancel_login(telegram_id)
        client = await _create_client(settings)
        qr = await client.qr_login()
        _pending[telegram_id] = PendingLogin(client=client, mode="qr", qr_login=qr)
        logger.info("login_qr_started", telegram_id=telegram_id)
        return qr.url


async def wait_qr_login(telegram_id: int, timeout: float = 180) -> str:
    pending = _pending.get(telegram_id)
    if not pending or pending.mode != "qr" or not pending.qr_login:
        raise ValueError("QR login session expired. Open step 2 again.")

    async with _lock(telegram_id):
        try:
            await asyncio.wait_for(pending.qr_login.wait(), timeout=timeout)
        except SessionPasswordNeededError:
            raise ValueError("2FA_REQUIRED")
        except asyncio.TimeoutError as exc:
            raise ValueError("QR login timed out. Refresh QR and try again.") from exc

        if not await pending.client.is_user_authorized():
            raise ValueError("QR authorization failed")

        session_string = pending.client.session.save()
        _pending.pop(telegram_id, None)
        await pending.client.disconnect()
        logger.info("login_qr_completed", telegram_id=telegram_id)
        return session_string


async def refresh_qr_login(telegram_id: int, settings: Settings) -> str:
    cancel_qr_task(telegram_id)
    return await start_qr_login(telegram_id, settings)


async def start_login(telegram_id: int, phone: str, settings: Settings) -> CodeSent:
    cancel_qr_task(telegram_id)
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
            mode="phone",
        )
        logger.info(
            "login_code_sent",
            telegram_id=telegram_id,
            phone=mask_phone(result.phone),
            hash_prefix=result.phone_code_hash[:8],
            connected=client.is_connected(),
        )
        return result


async def resend_login_code(telegram_id: int, settings: Settings) -> CodeSent:
    pending = _pending.get(telegram_id)
    if not pending or pending.mode != "phone":
        raise ValueError("Login session expired. Open step 2 again.")

    async with _lock(telegram_id):
        if not pending.client.is_connected():
            await connect_telethon(pending.client, settings)
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
        raise ValueError("Login session expired. Open step 2 again.")

    async with _lock(telegram_id):
        client = pending.client

        if password:
            if not client.is_connected():
                await connect_telethon(client, settings)
            try:
                await client.sign_in(password=password)
            except SessionPasswordNeededError:
                raise ValueError("Invalid 2FA password")
        elif pending.mode != "phone":
            raise ValueError("Login session expired. Open step 2 again.")
        else:
            code_digits = normalize_code(code)
            if not code_digits:
                raise ValueError("Enter the code from Telegram.")

            if not client.is_connected():
                logger.warning(
                    "login_disconnected_before_sign_in",
                    telegram_id=telegram_id,
                )
                await connect_telethon(client, settings)
                fresh = await _send_code(client, pending.phone)
                pending.phone = fresh.phone
                pending.phone_code_hash = fresh.phone_code_hash
                raise ValueError(
                    "Connection was reset. A new code was sent — enter the latest digits."
                )

            live_hash = client._phone_code_hash.get(pending.phone) or pending.phone_code_hash
            logger.info(
                "sign_in_attempt",
                telegram_id=telegram_id,
                phone=mask_phone(pending.phone),
                hash_prefix=(live_hash or "")[:8],
                connected=client.is_connected(),
            )

            try:
                await client.sign_in(
                    pending.phone,
                    code_digits,
                    phone_code_hash=live_hash,
                )
            except SessionPasswordNeededError:
                raise ValueError("2FA_REQUIRED")
            except PhoneCodeInvalidError as exc:
                raise ValueError("Invalid code. Check digits and try again.") from exc
            except PhoneCodeExpiredError as exc:
                logger.warning(
                    "login_code_expired",
                    telegram_id=telegram_id,
                    hash_keys=list(client._phone_code_hash.keys()),
                )
                raise ValueError(
                    "Code expired. Scan the QR on step 2 again or tap «Resend code»."
                ) from exc

        if not await client.is_user_authorized():
            raise ValueError("Authorization failed")

        session_string = client.session.save()
        _pending.pop(telegram_id, None)
        await client.disconnect()
        logger.info("login_completed", telegram_id=telegram_id)
        return session_string


def get_pending_phone(telegram_id: int) -> str | None:
    pending = _pending.get(telegram_id)
    return pending.phone if pending and pending.mode == "phone" else None


async def cancel_login(telegram_id: int) -> None:
    cancel_qr_task(telegram_id)
    pending = _pending.pop(telegram_id, None)
    if pending:
        await pending.client.disconnect()


def mask_phone(phone: str) -> str:
    if len(phone) < 6:
        return phone
    return f"{phone[:3]}***{phone[-2:]}"
