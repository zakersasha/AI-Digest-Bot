import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

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

_LOGIN_TTL = timedelta(minutes=10)
_login_locks: dict[int, asyncio.Lock] = {}


class PasswordRequired(Exception):
    def __init__(self, partial_session: str) -> None:
        self.partial_session = partial_session
        super().__init__("password_required")


@dataclass
class TelethonLoginPending:
    phone: str
    partial_session: str
    phone_code_hash: str


@dataclass
class _ActiveLogin:
    client: TelegramClient
    phone: str
    phone_code_hash: str
    created_at: datetime


_active_logins: dict[int, _ActiveLogin] = {}


def _lock_for(telegram_id: int) -> asyncio.Lock:
    return _login_locks.setdefault(telegram_id, asyncio.Lock())


def _new_client(settings: Settings, session: StringSession | None = None) -> TelegramClient:
    return TelegramClient(
        session or StringSession(),
        settings.telegram_api_id,
        settings.telegram_api_hash,
        **_client_kwargs(settings),
    )


async def _disconnect_active(telegram_id: int) -> None:
    active = _active_logins.pop(telegram_id, None)
    if active:
        try:
            await active.client.disconnect()
        except Exception:
            logger.exception("telethon_login_disconnect_failed", telegram_id=telegram_id)


def normalize_phone(raw: str) -> str:
    phone = raw.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if phone.startswith("00"):
        phone = "+" + phone[2:]
    if not phone.startswith("+"):
        digits = phone
        if digits.startswith("8") and len(digits) == 11:
            phone = "+7" + digits[1:]
        elif len(digits) == 10 and digits.startswith("9"):
            phone = "+7" + digits
        else:
            phone = "+" + digits
    if len(phone) < 8:
        raise ValueError("invalid_phone")
    return phone


async def start_phone_login(phone: str, settings: Settings, *, telegram_id: int) -> TelethonLoginPending:
    normalized = normalize_phone(phone)
    lock = _lock_for(telegram_id)

    async with lock:
        await _disconnect_active(telegram_id)
        client = _new_client(settings)
        try:
            await connect_telethon(client, settings)
            sent = await client.send_code_request(normalized)
            partial = client.session.save()
            _active_logins[telegram_id] = _ActiveLogin(
                client=client,
                phone=normalized,
                phone_code_hash=sent.phone_code_hash,
                created_at=datetime.now(tz=UTC),
            )
            logger.info("telethon_code_sent", telegram_id=telegram_id, phone=normalized[-4:])
            return TelethonLoginPending(
                phone=normalized,
                partial_session=partial,
                phone_code_hash=sent.phone_code_hash,
            )
        except PhoneNumberInvalidError as exc:
            await client.disconnect()
            raise ValueError("invalid_phone") from exc
        except FloodWaitError as exc:
            await client.disconnect()
            raise ValueError(f"flood_wait:{exc.seconds}") from exc
        except Exception:
            await client.disconnect()
            raise


def _active_login(telegram_id: int) -> _ActiveLogin | None:
    active = _active_logins.get(telegram_id)
    if not active:
        return None
    if datetime.now(tz=UTC) - active.created_at > _LOGIN_TTL:
        return None
    return active


async def finish_phone_login(
    pending: TelethonLoginPending,
    code: str,
    settings: Settings,
    *,
    telegram_id: int,
) -> str:
    lock = _lock_for(telegram_id)
    async with lock:
        active = _active_login(telegram_id)
        restored = False
        if active and active.phone == pending.phone:
            client = active.client
        else:
            await _disconnect_active(telegram_id)
            client = _new_client(settings, StringSession(pending.partial_session))
            await connect_telethon(client, settings)
            restored = True

        try:
            try:
                await client.sign_in(pending.phone, code.strip())
            except SessionPasswordNeededError as exc:
                _active_logins[telegram_id] = _ActiveLogin(
                    client=client,
                    phone=pending.phone,
                    phone_code_hash=pending.phone_code_hash,
                    created_at=datetime.now(tz=UTC),
                )
                raise PasswordRequired(client.session.save()) from exc

            if not await client.is_user_authorized():
                raise ValueError("login_failed")

            session_string = client.session.save()
            await _disconnect_active(telegram_id)
            logger.info("telethon_login_success", telegram_id=telegram_id)
            return session_string
        except PhoneCodeInvalidError as exc:
            if restored:
                _active_logins[telegram_id] = _ActiveLogin(
                    client=client,
                    phone=pending.phone,
                    phone_code_hash=pending.phone_code_hash,
                    created_at=datetime.now(tz=UTC),
                )
            logger.warning("telethon_code_invalid", telegram_id=telegram_id)
            raise ValueError("invalid_code") from exc
        except PhoneCodeExpiredError as exc:
            logger.warning("telethon_code_expired", telegram_id=telegram_id)
            await _disconnect_active(telegram_id)
            raise ValueError("code_expired") from exc
        except FloodWaitError as exc:
            await _disconnect_active(telegram_id)
            raise ValueError(f"flood_wait:{exc.seconds}") from exc
        except PasswordRequired:
            raise
        except Exception:
            await _disconnect_active(telegram_id)
            raise


async def finish_2fa_login(
    partial_session: str,
    password: str,
    settings: Settings,
    *,
    telegram_id: int,
) -> str:
    lock = _lock_for(telegram_id)
    async with lock:
        active = _active_login(telegram_id)
        if active:
            client = active.client
            owns_client = False
        else:
            client = _new_client(settings, StringSession(partial_session))
            owns_client = True
            await connect_telethon(client, settings)

        try:
            await client.sign_in(password=password)
            if not await client.is_user_authorized():
                raise ValueError("login_failed")
            session_string = client.session.save()
            _active_logins.pop(telegram_id, None)
            await client.disconnect()
            logger.info("telethon_2fa_success", telegram_id=telegram_id)
            return session_string
        except FloodWaitError as exc:
            await _disconnect_active(telegram_id)
            raise ValueError(f"flood_wait:{exc.seconds}") from exc
        except Exception:
            if owns_client:
                await client.disconnect()
            raise ValueError("login_failed") from None


async def cancel_phone_login(telegram_id: int) -> None:
    lock = _lock_for(telegram_id)
    async with lock:
        await _disconnect_active(telegram_id)
