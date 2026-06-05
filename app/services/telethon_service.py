import re
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse

from telethon import TelegramClient
from telethon.tl.types import Channel
from telethon.errors import (
    ChannelInvalidError,
    ChannelPrivateError,
    FloodWaitError,
    UsernameInvalidError,
    UsernameNotOccupiedError,
)

from app.services.content_message import ContentMessage
from app.utils.links import message_url
from app.utils.logging import get_logger

logger = get_logger(__name__)

_USERNAME_PATTERN = re.compile(r"^@?[a-zA-Z][a-zA-Z0-9_]{3,31}$")


@dataclass
class SubscribedChannel:
    username: str
    title: str
    peer_id: int


class TelethonService:
    def __init__(self, client: TelegramClient, max_messages: int) -> None:
        self._client = client
        self._max_messages = max_messages

    async def fetch_subscribed_channels(self, limit: int = 200) -> list[SubscribedChannel]:
        channels: list[SubscribedChannel] = []
        seen: set[str] = set()

        async for dialog in self._client.iter_dialogs(limit=limit):
            entity = dialog.entity
            if not isinstance(entity, Channel):
                continue
            raw_username = getattr(entity, "username", None)
            if not raw_username:
                continue

            username = f"@{raw_username.lower()}"
            if username in seen:
                continue
            seen.add(username)

            title = (dialog.title or raw_username).strip()
            channels.append(
                SubscribedChannel(username=username, title=title, peer_id=entity.id)
            )

        channels.sort(key=lambda item: item.title.lower())
        logger.info("subscriptions_fetched", count=len(channels))
        return channels

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

    async def fetch_messages(
        self,
        telegram_source: str,
        since: datetime,
    ) -> list[ContentMessage]:
        username = self.normalize_source(telegram_source)
        entity = await self._client.get_entity(username)
        messages: list[ContentMessage] = []

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
                    ContentMessage(
                        text=text,
                        source=username,
                        date=msg_date,
                        message_id=str(message.id),
                        post_url=message_url(username, message.id),
                    )
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
