from datetime import UTC, datetime

import httpx
from openai import APIConnectionError, APITimeoutError, RateLimitError

from app.ai.base import AIProvider
from app.repositories.digest_repository import DigestRepository
from app.repositories.source_repository import SourceRepository
from app.services.telethon_service import (
    ChannelMessage,
    TelethonService,
    parse_timeframe,
    timeframe_label,
)
from app.utils.logging import get_logger
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class DigestService:
    def __init__(
        self,
        session: AsyncSession,
        telethon: TelethonService,
        ai: AIProvider,
        min_importance_score: int,
    ) -> None:
        self._session = session
        self._telethon = telethon
        self._ai = ai
        self._min_score = min_importance_score
        self._source_repo = SourceRepository(session)
        self._digest_repo = DigestRepository(session)

    async def generate(self, user_id: int, timeframe: str) -> str:
        sources = await self._source_repo.list_active_for_user(user_id)
        if not sources:
            raise ValueError("No active sources. Add channels with /add first.")

        delta = parse_timeframe(timeframe)
        since = datetime.now(tz=UTC) - delta

        all_messages: list[ChannelMessage] = []
        for source in sources:
            try:
                messages = await self._telethon.fetch_messages(source.telegram_source, since)
                all_messages.extend(messages)
            except ValueError as exc:
                logger.warning("source_fetch_failed", source=source.telegram_source, error=str(exc))
            except TimeoutError:
                raise

        if not all_messages:
            raise ValueError(
                f"No messages found for {timeframe_label(timeframe).lower()}. "
                "Try a longer period or check your sources."
            )

        scored_summaries: list[str] = []
        for msg in all_messages:
            try:
                result = await self._ai.score_message(msg.text)
                if result.score >= self._min_score:
                    scored_summaries.append(f"[{msg.source}] {result.summary}")
            except (httpx.HTTPError, APIConnectionError, APITimeoutError, RateLimitError) as exc:
                logger.error("ai_score_failed", provider=self._ai.name, error=str(exc))
                raise RuntimeError(
                    f"AI provider ({self._ai.name}) failed while scoring messages. Try again later."
                ) from exc

        if not scored_summaries:
            raise ValueError(
                "No important messages found for this period. Try a longer timeframe."
            )

        try:
            digest_body = await self._ai.generate_digest(scored_summaries)
        except (httpx.HTTPError, APIConnectionError, APITimeoutError, RateLimitError) as exc:
            logger.error("ai_digest_failed", provider=self._ai.name, error=str(exc))
            raise RuntimeError(
                f"AI provider ({self._ai.name}) failed while generating digest. Try again later."
            ) from exc

        header = f"🔥 AI Digest ({timeframe_label(timeframe)})\n\n"
        content = header + digest_body

        await self._digest_repo.create(user_id, timeframe, content)
        await self._session.commit()

        logger.info(
            "digest_generated",
            user_id=user_id,
            timeframe=timeframe,
            messages=len(all_messages),
            highlights=len(scored_summaries),
        )
        return content
