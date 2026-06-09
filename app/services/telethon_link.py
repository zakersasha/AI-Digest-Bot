from dataclasses import dataclass

from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
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


class PasswordRequired(Exception):
    def __init__(self, partial_session: str) -> None:
        self.partial_session = partial_session
        super().__init__("password_required")


@dataclass
class TelethonLoginPending:
    phone: str
    partial_session: str
    phone_code_hash: str


def normalize_phone(raw: str) -> str:
    phone = raw.strip().replace(" ", "").replace("-", "")
    if phone.startswith("00"):
        phone = "+" + phone[2:]
    if not phone.startswith("+"):
        phone = "+" + phone
    if len(phone) < 8:
        raise ValueError("invalid_phone")
    return phone


async def start_phone_login(phone: str, settings: Settings) -> TelethonLoginPending:
    normalized = normalize_phone(phone)
    client = TelegramClient(
        StringSession(),
        settings.telegram_api_id,
        settings.telegram_api_hash,
        **_client_kwargs(settings),
    )
    try:
        await connect_telethon(client, settings)
        sent = await client.send_code_request(normalized)
        partial = client.session.save()
        return TelethonLoginPending(
            phone=normalized,
            partial_session=partial,
            phone_code_hash=sent.phone_code_hash,
        )
    except PhoneNumberInvalidError as exc:
        raise ValueError("invalid_phone") from exc
    except FloodWaitError as exc:
        raise ValueError(f"flood_wait:{exc.seconds}") from exc
    finally:
        await client.disconnect()


async def finish_phone_login(
    pending: TelethonLoginPending,
    code: str,
    settings: Settings,
) -> str:
    client = TelegramClient(
        StringSession(pending.partial_session),
        settings.telegram_api_id,
        settings.telegram_api_hash,
        **_client_kwargs(settings),
    )
    try:
        await connect_telethon(client, settings)
        try:
            await client.sign_in(
                pending.phone,
                code.strip(),
                phone_code_hash=pending.phone_code_hash,
            )
        except SessionPasswordNeededError as exc:
            raise PasswordRequired(client.session.save()) from exc
        if not await client.is_user_authorized():
            raise ValueError("login_failed")
        return client.session.save()
    except PhoneCodeInvalidError as exc:
        raise ValueError("invalid_code") from exc
    except PhoneCodeExpiredError as exc:
        raise ValueError("code_expired") from exc
    except FloodWaitError as exc:
        raise ValueError(f"flood_wait:{exc.seconds}") from exc
    finally:
        await client.disconnect()


async def finish_2fa_login(partial_session: str, password: str, settings: Settings) -> str:
    client = TelegramClient(
        StringSession(partial_session),
        settings.telegram_api_id,
        settings.telegram_api_hash,
        **_client_kwargs(settings),
    )
    try:
        await connect_telethon(client, settings)
        await client.sign_in(password=password)
        if not await client.is_user_authorized():
            raise ValueError("login_failed")
        return client.session.save()
    except FloodWaitError as exc:
        raise ValueError(f"flood_wait:{exc.seconds}") from exc
    finally:
        await client.disconnect()
