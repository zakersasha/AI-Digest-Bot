from datetime import UTC, datetime

import httpx
from openai import APIConnectionError, APITimeoutError, RateLimitError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import AIProvider
from app.ai.context_limits import pack_messages_for_digest
from app.config import Settings
from app.i18n import digest_title, frequency_label, t
from app.models.user import User
from app.repositories.digest_repository import DigestRepository
from app.repositories.source_repository import SourceRepository
from app.repositories.user_repository import UserRepository
from app.services.content_message import ContentMessage
from app.services.frequency import parse_frequency
from app.services.gmail_service import GmailService
from app.services.message_selection import interleave_messages_by_source
from app.services.telethon_client import shared_telethon_client
from app.services.user_sources import channel_count, digest_platform, has_gmail
from app.utils.digest_links import repair_digest_link_placeholders
from app.utils.links import channel_username
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
        self._gmail = GmailService(settings)

    async def generate_for_user(self, user_id: int, frequency: str, language: str) -> str:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise ValueError(t(language, "pick_source_first"))

        channels = await channel_count(self._session, user.id)
        gmail_linked = has_gmail(user)
        if not channels and not gmail_linked:
            raise ValueError(t(language, "pick_source_first"))

        delta = parse_frequency(frequency)
        since = datetime.now(tz=UTC) - delta
        label = frequency_label(language, frequency)
        all_messages: list[ContentMessage] = []

        if channels:
            tg_messages = await self._fetch_telegram_messages(user, since, language)
            all_messages.extend(tg_messages)

        if gmail_linked:
            gmail_messages = await self._fetch_gmail_messages(user, since, language)
            all_messages.extend(gmail_messages)

        if not all_messages:
            if channels and gmail_linked:
                raise ValueError(t(language, "no_content", label=label))
            if gmail_linked:
                raise ValueError(t(language, "no_emails", label=label))
            raise ValueError(t(language, "no_messages", label=label))

        platform = digest_platform(channels > 0, gmail_linked)
        return await self._build_digest(
            user.id,
            frequency,
            language,
            all_messages,
            platform=platform,
        )

    async def _fetch_telegram_messages(
        self,
        user: User,
        since: datetime,
        language: str,
    ) -> list[ContentMessage]:
        sources = await self._source_repo.list_active_for_user(user.id)
        if not sources:
            return []

        if not self._settings.telegram_session_string:
            raise ValueError(t(language, "reader_not_configured"))

        messages: list[ContentMessage] = []
        async with shared_telethon_client(self._settings) as telethon:
            for source in sources:
                try:
                    messages.extend(await telethon.fetch_messages(source.telegram_source, since))
                except ValueError as exc:
                    logger.warning(
                        "source_fetch_failed",
                        source=source.telegram_source,
                        error=str(exc),
                    )
                except TimeoutError:
                    raise
        return messages

    async def _fetch_gmail_messages(
        self,
        user: User,
        since: datetime,
        language: str,
    ) -> list[ContentMessage]:
        if not self._gmail.is_configured():
            raise ValueError(t(language, "gmail_not_configured"))

        try:
            messages, tokens = await self._gmail.fetch_messages(
                user.gmail_tokens_encrypted,
                since,
                self._settings.gmail_max_messages,
            )
            await self._user_repo.update_gmail_tokens(user.id, tokens)
            await self._session.flush()
            return messages
        except ValueError as exc:
            if str(exc) == "gmail_api_disabled":
                raise ValueError(t(language, "gmail_api_disabled")) from exc
            raise ValueError(t(language, "gmail_not_linked")) from exc
        except httpx.HTTPError as exc:
            logger.error("gmail_fetch_failed", user_id=user.id, error=str(exc))
            raise RuntimeError(t(language, "gmail_fetch_failed")) from exc

    async def _build_digest(
        self,
        user_id: int,
        frequency: str,
        language: str,
        all_messages: list[ContentMessage],
        *,
        platform: str,
    ) -> str:
        limits = self._settings.digest_ai_limits()
        selected = interleave_messages_by_source(all_messages, limits.max_messages)
        if len(selected) < len(all_messages):
            logger.info(
                "messages_truncated_for_digest",
                user_id=user_id,
                kept=len(selected),
                sources=len({m.source for m in selected}),
                platform=platform,
            )

        items: list[tuple[str, str, str]] = []
        post_urls: list[str] = []
        for msg in selected:
            if msg.source.startswith("email:"):
                source_label = msg.source.removeprefix("email:")
                items.append((source_label, msg.post_url, msg.text))
            else:
                username = channel_username(msg.source)
                items.append((f"@{username}", msg.post_url, msg.text))
            post_urls.append(msg.post_url)

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
            digest_body = await self._ai.generate_digest(blocks, language, platform=platform)
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

        header = digest_title(language, frequency, platform=platform) + "\n\n"
        content = header + digest_body

        await self._digest_repo.create(user_id, frequency, content)
        await self._user_repo.update_last_digest(user_id, datetime.now(tz=UTC))
        await self._session.commit()

        logger.info(
            "digest_generated",
            user_id=user_id,
            frequency=frequency,
            language=language,
            platform=platform,
            messages=len(selected),
            blocks=len(blocks),
            input_budget_chars=budget,
        )
        return content
