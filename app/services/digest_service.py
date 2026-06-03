from datetime import UTC, datetime

import httpx
from openai import APIConnectionError, APITimeoutError, RateLimitError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import AIProvider
from app.ai.context_limits import pack_messages_for_digest
from app.config import Settings
from app.i18n import frequency_label, t
from app.repositories.digest_repository import DigestRepository
from app.repositories.source_repository import SourceRepository
from app.repositories.user_repository import UserRepository
from app.services.frequency import parse_frequency
from app.services.message_selection import interleave_messages_by_source
from app.services.telethon_client import shared_telethon_client
from app.services.telethon_service import ChannelMessage
from app.utils.digest_links import repair_digest_link_placeholders
from app.utils.links import channel_username, message_url
from app.utils.logging import get_logger

logger = get_logger(__name__)


class DigestService:
    def __init__(
        self,
        session: AsyncSession,
        ai: AIProvider,
        settings: Settings,
    ) -> None:
        self._session = session
        self._ai = ai
        self._settings = settings
        self._source_repo = SourceRepository(session)
        self._digest_repo = DigestRepository(session)
        self._user_repo = UserRepository(session)

    async def generate_for_user(self, user_id: int, frequency: str, language: str) -> str:
        sources = await self._source_repo.list_active_for_user(user_id)
        if not sources:
            raise ValueError(t(language, "no_channels_selected"))

        if not self._settings.telegram_session_string:
            raise ValueError(t(language, "reader_not_configured"))

        delta = parse_frequency(frequency)
        since = datetime.now(tz=UTC) - delta
        label = frequency_label(language, frequency)

        all_messages: list[ChannelMessage] = []
        async with shared_telethon_client(self._settings) as telethon:
            for source in sources:
                try:
                    messages = await telethon.fetch_messages(source.telegram_source, since)
                    all_messages.extend(messages)
                except ValueError as exc:
                    logger.warning(
                        "source_fetch_failed",
                        source=source.telegram_source,
                        error=str(exc),
                    )
                except TimeoutError:
                    raise

        if not all_messages:
            raise ValueError(t(language, "no_messages", label=label))

        limits = self._settings.digest_ai_limits()
        selected = interleave_messages_by_source(all_messages, limits.max_messages)
        if len(selected) < len(all_messages):
            logger.info(
                "messages_truncated_for_digest",
                user_id=user_id,
                kept=len(selected),
                sources=len({m.source for m in selected}),
            )

        items: list[tuple[str, str, str]] = []
        post_urls: list[str] = []
        for msg in selected:
            username = channel_username(msg.source)
            post_url = message_url(msg.source, msg.message_id)
            items.append((f"@{username}", post_url, msg.text))
            post_urls.append(post_url)

        budget = self._settings.digest_input_char_budget()
        blocks = pack_messages_for_digest(
            items,
            total_budget_chars=budget,
            max_messages=limits.max_messages,
            per_message_max_chars=limits.message_max_chars,
            min_message_chars=limits.min_message_chars,
        )

        if not blocks:
            raise ValueError(t(language, "no_important"))

        try:
            digest_body = await self._ai.generate_digest(blocks, language)
        except (httpx.HTTPError, APIConnectionError, APITimeoutError, RateLimitError) as exc:
            logger.error("ai_digest_failed", provider=self._ai.name, error=str(exc))
            raise RuntimeError(t(language, "ai_failed", provider=self._ai.name)) from exc
        except Exception as exc:
            logger.error("ai_digest_failed", provider=self._ai.name, error=str(exc))
            raise RuntimeError(t(language, "ai_failed", provider=self._ai.name)) from exc

        digest_body = repair_digest_link_placeholders(digest_body.strip(), post_urls)

        if not digest_body:
            logger.error("ai_digest_empty", provider=self._ai.name)
            raise RuntimeError(t(language, "ai_failed", provider=self._ai.name))

        header = t(language, "digest_header", label=label) + "\n\n"
        content = header + digest_body

        await self._digest_repo.create(user_id, frequency, content)
        await self._user_repo.update_last_digest(user_id, datetime.now(tz=UTC))
        await self._session.commit()

        logger.info(
            "digest_generated",
            user_id=user_id,
            frequency=frequency,
            language=language,
            messages=len(selected),
            blocks=len(blocks),
            input_budget_chars=budget,
        )
        return content
