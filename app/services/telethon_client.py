from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from telethon import TelegramClient
from telethon.sessions import StringSession

from app.config import Settings
from app.services.telethon_service import TelethonService


def _proxy_from_settings(settings: Settings):
    if not settings.telegram_proxy_url:
        return None
    try:
        import socks

        from urllib.parse import urlparse

        parsed = urlparse(settings.telegram_proxy_url)
        if parsed.scheme not in ("http", "https", "socks5", "socks4"):
            return None
        proxy_type = socks.HTTP if parsed.scheme in ("http", "https") else socks.SOCKS5
        host = parsed.hostname
        port = parsed.port or 1080
        username = parsed.username
        password = parsed.password
        return (proxy_type, host, port, True, username, password)
    except Exception:
        return None


@asynccontextmanager
async def user_telethon_client(
    session_string: str,
    settings: Settings,
) -> AsyncIterator[TelethonService]:
    proxy = _proxy_from_settings(settings)
    client = TelegramClient(
        StringSession(session_string),
        settings.telegram_api_id,
        settings.telegram_api_hash,
        proxy=proxy,
    )
    await client.connect()
    if not await client.is_user_authorized():
        raise ValueError("Telegram session is not authorized")

    service = TelethonService(client, settings.max_messages_per_source)
    try:
        yield service
    finally:
        await client.disconnect()
