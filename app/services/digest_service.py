from datetime import UTC, datetime

import httpx
from openai import APIConnectionError, APITimeoutError, RateLimitError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import AIProvider
from app.config import Settings
from app.i18n import frequency_label, t
from app.models.user import User
from app.repositories.digest_repository import DigestRepository
from app.repositories.source_repository import SourceRepository
from app.repositories.user_repository import UserRepository
from app.services.frequency import parse_frequency
from app.services.telethon_client import user_telethon_client
from app.services.telethon_service import ChannelMessage
from app.utils.crypto import decrypt_session
from app.utils.links import markdown_source_link
from app.utils.logging import get_logger

logger = get_logger(__name__)


class DigestService:
    def __init__(
        self,
        session: AsyncSession,
        ai: AIProvider,
        settings: Settings,
        min_importance_score: int,
    ) -> None:
        self._session = session
        self._ai = ai
        self._settings = settings
        self._min_score = min_importance_score
        self._source_repo = SourceRepository(session)
        self._digest_repo = DigestRepository(session)
        self._user_repo = UserRepository(session)

    async def _get_user_session(self, user_id: int, language: str) -> str:
        result = await self._session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or not user.telethon_session_encrypted:
            raise ValueError(t(language, "telegram_not_linked"))
        return decrypt_session(user.telethon_session_encrypted)

    async def generate_for_user(self, user_id: int, frequency: str, language: str) -> str:
        sources = await self._source_repo.list_active_for_user(user_id)
        if not sources:
            raise ValueError(t(language, "no_channels_selected"))

        session_string = await self._get_user_session(user_id, language)
        delta = parse_frequency(frequency)
        since = datetime.now(tz=UTC) - delta
        label = frequency_label(language, frequency)

        all_messages: list[ChannelMessage] = []
        async with user_telethon_client(session_string, self._settings) as telethon:
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

        scored_summaries: list[str] = []
        for msg in all_messages:
            try:
                result = await self._ai.score_message(msg.text, language)
                if result.score >= self._min_score:
                    source_link = markdown_source_link(msg.source, msg.message_id)
                    scored_summaries.append(
                        f"SUMMARY: {result.summary}\nSOURCE_LINK: {source_link}"
                    )
            except (httpx.HTTPError, APIConnectionError, APITimeoutError, RateLimitError) as exc:
                logger.error("ai_score_failed", provider=self._ai.name, error=str(exc))
                raise RuntimeError(t(language, "ai_failed", provider=self._ai.name)) from exc

        if not scored_summaries:
            raise ValueError(t(language, "no_important"))

        try:
            digest_body = await self._ai.generate_digest(scored_summaries, language)
        except (httpx.HTTPError, APIConnectionError, APITimeoutError, RateLimitError) as exc:
            logger.error("ai_digest_failed", provider=self._ai.name, error=str(exc))
            raise RuntimeError(t(language, "ai_failed", provider=self._ai.name)) from exc

        header = t(language, "digest_header", label=label) + "\n\n"
        content = header + digest_body.strip()

        await self._digest_repo.create(user_id, frequency, content)
        await self._user_repo.update_last_digest(user_id, datetime.now(tz=UTC))
        await self._session.commit()

        logger.info(
            "digest_generated",
            user_id=user_id,
            frequency=frequency,
            language=language,
            messages=len(all_messages),
            highlights=len(scored_summaries),
        )
        return content
