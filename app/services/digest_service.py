import asyncio
from datetime import UTC, datetime

import httpx
from openai import APIConnectionError, APITimeoutError, RateLimitError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import AIProvider
from app.ai.context_limits import chars_for_tokens, fit_items_to_budget, truncate_text
from app.config import Settings
from app.i18n import frequency_label, t
from app.repositories.digest_repository import DigestRepository
from app.repositories.source_repository import SourceRepository
from app.repositories.user_repository import UserRepository
from app.services.frequency import parse_frequency
from app.services.telethon_client import shared_telethon_client
from app.services.telethon_service import ChannelMessage
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

    async def _score_messages(
        self,
        messages: list[ChannelMessage],
        language: str,
    ) -> list[str]:
        score_char_limit = self._settings.ai_score_message_max_chars
        min_chars = self._settings.ai_min_message_chars
        candidates: list[ChannelMessage] = []
        for msg in messages:
            text = truncate_text(msg.text, score_char_limit)
            if len(text) >= min_chars:
                candidates.append(msg)

        batch_size = max(1, self._settings.ai_score_batch_size)
        concurrency = max(1, self._settings.ai_score_concurrency)
        sem = asyncio.Semaphore(concurrency)

        batches: list[list[ChannelMessage]] = [
            candidates[i : i + batch_size] for i in range(0, len(candidates), batch_size)
        ]

        async def score_batch(batch: list[ChannelMessage]) -> list[str]:
            async with sem:
                texts = [truncate_text(m.text, score_char_limit) for m in batch]
                try:
                    results = await self._ai.score_messages_batch(texts, language)
                except (
                    httpx.HTTPError,
                    APIConnectionError,
                    APITimeoutError,
                    RateLimitError,
                ) as exc:
                    logger.error("ai_score_batch_failed", provider=self._ai.name, error=str(exc))
                    raise RuntimeError(t(language, "ai_failed", provider=self._ai.name)) from exc

                summaries: list[str] = []
                for msg, result in zip(batch, results, strict=False):
                    if result.score >= self._min_score:
                        summary = truncate_text(result.summary, 280)
                        source_link = markdown_source_link(msg.source, msg.message_id)
                        summaries.append(f"SUMMARY: {summary}\nSOURCE_LINK: {source_link}")
                return summaries

        batch_results = await asyncio.gather(*[score_batch(b) for b in batches])
        scored: list[str] = []
        for chunk in batch_results:
            scored.extend(chunk)
        return scored

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

        max_to_score = self._settings.ai_max_messages_to_score
        if len(all_messages) > max_to_score:
            all_messages.sort(key=lambda m: m.date, reverse=True)
            all_messages = all_messages[:max_to_score]
            logger.info("messages_truncated_for_scoring", user_id=user_id, kept=max_to_score)

        scored_summaries = await self._score_messages(all_messages, language)

        if not scored_summaries:
            raise ValueError(t(language, "no_important"))

        max_items = self._settings.ai_max_digest_items
        if len(scored_summaries) > max_items:
            scored_summaries = scored_summaries[:max_items]

        digest_budget = chars_for_tokens(self._settings.ai_digest_input_tokens)
        scored_summaries = fit_items_to_budget(scored_summaries, digest_budget)

        if not scored_summaries:
            raise ValueError(t(language, "no_important"))

        try:
            digest_body = await self._ai.generate_digest(
                scored_summaries,
                language,
                max_chars=digest_budget,
            )
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
            ai_batches=len(scored_summaries) // max(1, self._settings.ai_score_batch_size) + 1,
        )
        return content
