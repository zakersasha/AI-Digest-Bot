import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from telethon import TelegramClient
from telethon.sessions import StringSession

from app.config import Settings, effective_telethon_proxy_url
from app.models.user import User
from app.services.telethon_service import TelethonService
from app.utils.crypto import decrypt_session
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _proxy_from_settings(settings: Settings):
    url = effective_telethon_proxy_url(settings)
    if not url:
        return None
    try:
        import socks

        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https", "socks5", "socks4"):
            logger.warning("telethon_proxy_unsupported_scheme", scheme=parsed.scheme)
            return None
        proxy_type = socks.HTTP if parsed.scheme in ("http", "https") else socks.SOCKS5
        host = parsed.hostname
        port = parsed.port or (3128 if parsed.scheme in ("http", "https") else 1080)
        username = parsed.username
        password = parsed.password
        logger.info("telethon_proxy_enabled", host=host, port=port, scheme=parsed.scheme)
        return (proxy_type, host, port, True, username, password)
    except Exception:
        logger.exception("telethon_proxy_parse_failed")
        return None


def _client_kwargs(settings: Settings) -> dict:
    return {
        "connection_retries": 3,
        "retry_delay": 2,
        "timeout": 20,
        "proxy": _proxy_from_settings(settings),
    }


async def connect_telethon(client: TelegramClient, settings: Settings) -> None:
    try:
        await asyncio.wait_for(client.connect(), timeout=settings.telethon_connect_timeout)
    except TimeoutError as exc:
        await client.disconnect()
        if not effective_telethon_proxy_url(settings):
            raise ValueError(
                "Cannot connect to Telegram. Set BOT_PROXY_URL (or TELEGRAM_PROXY_URL) in .env."
            ) from exc
        raise ValueError(
            "Cannot connect to Telegram via proxy. Check BOT_PROXY_URL / TELEGRAM_PROXY_URL."
        ) from exc


@asynccontextmanager
async def shared_telethon_client(settings: Settings) -> AsyncIterator[TelethonService]:
    """Reader session from TELEGRAM_SESSION_STRING (server-side, for fetching public channels)."""
    if not settings.telegram_session_string:
        raise ValueError("TELEGRAM_SESSION_STRING is not configured")

    client = TelegramClient(
        StringSession(settings.telegram_session_string),
        settings.telegram_api_id,
        settings.telegram_api_hash,
        **_client_kwargs(settings),
    )
    await connect_telethon(client, settings)
    if not await client.is_user_authorized():
        raise ValueError("Telegram reader session is not authorized")

    service = TelethonService(client, settings.max_messages_per_source)
    try:
        yield service
    finally:
        await client.disconnect()


@asynccontextmanager
async def user_telethon_client(user: User, settings: Settings) -> AsyncIterator[TelethonService]:
    """Per-user Telethon session (encrypted in DB)."""
    if not user.telethon_session_encrypted:
        raise ValueError("telethon_not_linked")

    session_string = decrypt_session(user.telethon_session_encrypted)
    client = TelegramClient(
        StringSession(session_string),
        settings.telegram_api_id,
        settings.telegram_api_hash,
        **_client_kwargs(settings),
    )
    await connect_telethon(client, settings)
    if not await client.is_user_authorized():
        raise ValueError("telethon_session_expired")

    service = TelethonService(client, settings.max_messages_per_source)
    try:
        yield service
    finally:
        await client.disconnect()


@asynccontextmanager
async def telethon_for_digest(user: User, settings: Settings) -> AsyncIterator[TelethonService]:
    """User session if linked, otherwise shared reader session."""
    if user.telethon_session_encrypted:
        async with user_telethon_client(user, settings) as service:
            yield service
        return
    async with shared_telethon_client(settings) as service:
        yield service
