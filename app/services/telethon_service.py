import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

import socks
from telethon import TelegramClient
from telethon.errors import (
    ChannelInvalidError,
    ChannelPrivateError,
    FloodWaitError,
    UsernameInvalidError,
    UsernameNotOccupiedError,
)
from telethon.sessions import StringSession

from app.config import Settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

_USERNAME_PATTERN = re.compile(r"^@?[a-zA-Z][a-zA-Z0-9_]{3,31}$")
PROXY_IP = '45.93.137.80'   # IP-адрес прокси
PROXY_PORT = 3128           # Порт прокси
PROXY_USER = 'proxy_user'     # Логин (если прокси без авторизации, поставьте None)
PROXY_PASS = '97vAN1S'     # Пароль (если прокси без авторизации, поставьте None)

# Формируем конфигурацию прокси (для HTTPS используется socks.HTTP)
proxy_config = (socks.HTTP, PROXY_IP, PROXY_PORT, True, PROXY_USER, PROXY_PASS)

@dataclass
class ChannelMessage:
    text: str
    source: str
    date: datetime


class TelethonService:
    def __init__(self, client: TelegramClient, max_messages: int) -> None:
        self._client = client
        self._max_messages = max_messages

    @classmethod
    async def create(cls, settings: Settings) -> "TelethonService":
        client = TelegramClient(
            session=StringSession(settings.telegram_session_string),
            api_id=settings.telegram_api_id,
            api_hash=settings.telegram_api_hash,
            proxy=proxy_config
        )
        await client.connect()
        if not await client.is_user_authorized():
            raise RuntimeError(
                "Telethon session is not authorized. Generate TELEGRAM_SESSION_STRING first."
            )
        logger.info("telethon_connected")
        return cls(client, settings.max_messages_per_source)

    async def close(self) -> None:
        await self._client.disconnect()

    @staticmethod
    def normalize_source(raw: str) -> str:
        text = raw.strip()

        if text.startswith("https://") or text.startswith("http://"):
            parsed = urlparse(text)
            host = (parsed.netloc or "").lower().removeprefix("www.")
            if host not in ("t.me", "telegram.me"):
                raise ValueError("Use a t.me link or @username. Example: t.me/python")
            path = parsed.path.strip("/")
            if path.startswith("+"):
                raise ValueError("Private invite links are not supported. Use public @username.")
            text = path.split("/")[0].split("?")[0] if path else ""
        elif re.match(r"^(?:t\.me|telegram\.me)/", text, re.IGNORECASE):
            text = text.split("/", 1)[1].split("?")[0]

        text = text.lstrip("@").strip()
        if not text:
            raise ValueError("Invalid channel username. Example: @ai_news or t.me/ai_news")
        if not _USERNAME_PATTERN.match(f"@{text}"):
            raise ValueError("Invalid channel username. Example: @ai_news or t.me/ai_news")

        return f"@{text.lower()}"

    async def resolve_channel(self, telegram_source: str) -> tuple[str, str]:
        username = self.normalize_source(telegram_source)
        try:
            entity = await self._client.get_entity(username)
        except (UsernameInvalidError, UsernameNotOccupiedError) as exc:
            raise ValueError(f"Channel {username} not found.") from exc
        except ChannelPrivateError as exc:
            raise ValueError(f"Channel {username} is private.") from exc
        except ChannelInvalidError as exc:
            raise ValueError(f"Channel {username} is invalid.") from exc

        title = getattr(entity, "title", None) or username
        return username, title

    async def fetch_messages(
        self,
        telegram_source: str,
        since: datetime,
    ) -> list[ChannelMessage]:
        username = self.normalize_source(telegram_source)
        entity = await self._client.get_entity(username)
        messages: list[ChannelMessage] = []

        try:
            async for message in self._client.iter_messages(entity, limit=self._max_messages):
                if not message.date:
                    continue
                msg_date = message.date.replace(tzinfo=UTC) if message.date.tzinfo is None else message.date
                if msg_date < since:
                    break
                text = (message.text or message.message or "").strip()
                if not text:
                    continue
                messages.append(
                    ChannelMessage(text=text, source=username, date=msg_date)
                )
        except FloodWaitError as exc:
            raise TimeoutError(f"Telegram rate limit. Retry in {exc.seconds}s.") from exc

        messages.reverse()
        logger.info(
            "messages_fetched",
            source=username,
            count=len(messages),
            since=since.isoformat(),
        )
        return messages


def parse_timeframe(timeframe: str) -> timedelta:
    mapping = {
        "1h": timedelta(hours=1),
        "3h": timedelta(hours=3),
        "6h": timedelta(hours=6),
        "12h": timedelta(hours=12),
    }
    if timeframe not in mapping:
        raise ValueError(f"Unknown timeframe: {timeframe}")
    return mapping[timeframe]


def timeframe_label(timeframe: str) -> str:
    labels = {"1h": "Last 1h", "3h": "Last 3h", "6h": "Last 6h", "12h": "Last 12h"}
    return labels.get(timeframe, timeframe)
