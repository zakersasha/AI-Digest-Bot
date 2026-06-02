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

_pending_clients: dict[int, TelegramClient] = {}


@dataclass
class CodeSent:
    phone: str
    phone_code_hash: str


def normalize_phone(raw: str) -> str:
    phone = raw.strip().replace(" ", "").replace("-", "")
    if phone.startswith("8") and len(phone) == 11:
        phone = "+7" + phone[1:]
    if not phone.startswith("+"):
        phone = f"+{phone}"
    return phone


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
    await cancel_login(telegram_id)

    normalized = normalize_phone(phone)
    client = await _create_client(settings)
    try:
        sent = await client.send_code_request(normalized)
    except PhoneNumberInvalidError as exc:
        await client.disconnect()
        raise ValueError("Invalid phone number. Use format +79001234567") from exc

    _pending_clients[telegram_id] = client
    logger.info("login_code_sent", telegram_id=telegram_id)
    return CodeSent(phone=normalized, phone_code_hash=sent.phone_code_hash)


async def complete_login(
    telegram_id: int,
    phone: str,
    code: str,
    phone_code_hash: str,
    settings: Settings,
    *,
    password: str | None = None,
) -> str:
    client = _pending_clients.get(telegram_id)
    if not client:
        raise ValueError("Login session expired. Start again.")

    normalized = normalize_phone(phone)
    code = code.strip().replace(" ", "")

    try:
        if password:
            await client.sign_in(password=password)
        else:
            await client.sign_in(normalized, code, phone_code_hash=phone_code_hash)
    except SessionPasswordNeededError:
        if password:
            raise ValueError("Invalid 2FA password")
        raise ValueError("2FA_REQUIRED")
    except PhoneCodeInvalidError as exc:
        raise ValueError("Invalid code. Try again.") from exc
    except PhoneCodeExpiredError as exc:
        await cancel_login(telegram_id)
        raise ValueError("Code expired. Request a new one.") from exc

    if not await client.is_user_authorized():
        raise ValueError("Authorization failed")

    session_string = client.session.save()
    _pending_clients.pop(telegram_id, None)
    await client.disconnect()
    logger.info("login_completed", telegram_id=telegram_id)
    return session_string


async def cancel_login(telegram_id: int) -> None:
    client = _pending_clients.pop(telegram_id, None)
    if client:
        await client.disconnect()


def mask_phone(phone: str) -> str:
    if len(phone) < 6:
        return phone
    return f"{phone[:3]}***{phone[-2:]}"
