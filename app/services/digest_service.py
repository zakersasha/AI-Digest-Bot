from datetime import UTC, datetime

import httpx
from openai import APIConnectionError, APITimeoutError, RateLimitError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import AIProvider
from app.ai.context_limits import pack_messages_for_digest, pack_messages_for_digest_by_source
from app.config import Settings
from app.i18n import digest_title, frequency_label, t
from app.models.user import User
from app.repositories.digest_repository import DigestRepository
from app.repositories.platform_settings_repository import PlatformSettingsRepository
from app.repositories.linkedin_profile_repository import LinkedInProfileRepository
from app.repositories.slack_channel_repository import SlackChannelRepository
from app.repositories.source_repository import SourceRepository
from app.repositories.user_repository import UserRepository
from app.services.content_message import ContentMessage
from app.services.frequency import digest_content_since
from app.services.gmail_service import GmailService
from app.services.yandex_mail_service import YandexMailService
from app.services.linkedin_service import LinkedInService
from app.services.linkedin_public import fetch_public_posts
from app.utils.linkedin_block import LinkedInBlockedError
from app.services.slack_service import SlackService
from app.services.message_selection import interleave_messages_by_source, select_balanced_messages_by_source
from app.services.platform_readiness import can_deliver_platform
from app.services.telethon_client import telethon_for_digest
from app.utils.digest_links import format_digest_links, is_no_new_content_response
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
        self._platform_repo = PlatformSettingsRepository(session)
        self._gmail = GmailService(settings)
        self._yandex = YandexMailService(settings)
        self._slack = SlackService(settings)
        self._linkedin = LinkedInService(settings)
        self._linkedin_repo = LinkedInProfileRepository(session)
        self._slack_repo = SlackChannelRepository(session)

    async def generate_for_platform(
        self,
        user_id: int,
        platform: str,
        frequency: str,
        language: str,
    ) -> str:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise ValueError(t(language, "pick_source_first"))

        if platform == "telegram":
            return await self._generate_telegram_digest(user, frequency, language)
        if platform == "gmail":
            return await self._generate_gmail_digest(user, frequency, language)
        if platform == "yandex":
            return await self._generate_yandex_digest(user, frequency, language)
        if platform == "slack":
            return await self._generate_slack_digest(user, frequency, language)
        if platform == "linkedin":
            raise ValueError(t(language, "platform_linkedin_locked"))
        raise ValueError(t(language, "platform_unavailable"))

    async def generate_scheduled(
        self,
        user_id: int,
        platform: str,
        language: str,
    ) -> str:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise ValueError(t(language, "pick_source_first"))

        settings = await self._platform_repo.get(user_id, platform)
        if not await can_deliver_platform(self._session, user, platform, settings):
            raise ValueError(t(language, "platform_not_ready"))

        frequency = settings.digest_frequency or "1d"
        return await self.generate_for_platform(user_id, platform, frequency, language)

    async def _generate_telegram_digest(self, user: User, frequency: str, language: str) -> str:
        sources = await self._source_repo.list_active_for_user(user.id)
        if not sources:
            raise ValueError(t(language, "no_channels_selected"))

        if not self._settings.telegram_session_string and not self._user_repo.has_telethon(user):
            raise ValueError(t(language, "reader_not_configured"))

        since = digest_content_since(frequency)
        label = frequency_label(language, frequency)

        all_messages: list[ContentMessage] = []
        async with telethon_for_digest(user, self._settings) as telethon:
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

        channel_titles: dict[str, str] = {}
        for source in sources:
            username = channel_username(source.telegram_source).lower()
            channel_titles[username] = (source.title or f"@{username}").strip()

        return await self._build_digest(
            user.id,
            "telegram",
            frequency,
            language,
            all_messages,
            channel_titles=channel_titles,
        )

    async def _generate_gmail_digest(self, user: User, frequency: str, language: str) -> str:
        if not self._user_repo.has_gmail(user):
            raise ValueError(t(language, "gmail_not_linked"))

        if not self._gmail.is_configured():
            raise ValueError(t(language, "gmail_not_configured"))

        since = digest_content_since(frequency)
        label = frequency_label(language, frequency)

        try:
            messages, tokens = await self._gmail.fetch_messages(
                user.gmail_tokens_encrypted,
                since,
                self._settings.gmail_max_messages,
            )
            await self._user_repo.update_gmail_tokens(user.id, tokens)
            await self._session.flush()
        except ValueError as exc:
            reason = str(exc)
            if reason == "gmail_api_disabled":
                raise ValueError(t(language, "gmail_api_disabled")) from exc
            if reason == "gmail_token_expired":
                await self._user_repo.clear_gmail(user.telegram_id)
                await self._session.commit()
                raise ValueError(t(language, "gmail_token_expired")) from exc
            if reason == "gmail_token_invalid":
                await self._user_repo.clear_gmail(user.telegram_id)
                await self._session.commit()
                raise ValueError(t(language, "gmail_token_invalid")) from exc
            raise ValueError(t(language, "gmail_not_linked")) from exc
        except httpx.HTTPError as exc:
            logger.error("gmail_fetch_failed", user_id=user.id, error=str(exc))
            raise RuntimeError(t(language, "gmail_fetch_failed")) from exc

        if not messages:
            raise ValueError(t(language, "no_emails", label=label))

        return await self._build_digest(
            user.id,
            "gmail",
            frequency,
            language,
            messages,
        )

    async def _generate_yandex_digest(self, user: User, frequency: str, language: str) -> str:
        if not self._user_repo.has_yandex(user):
            raise ValueError(t(language, "yandex_not_linked"))

        if not self._yandex.is_configured():
            raise ValueError(t(language, "yandex_not_configured"))

        since = digest_content_since(frequency)
        label = frequency_label(language, frequency)

        try:
            messages, tokens = await self._yandex.fetch_messages(
                user.yandex_tokens_encrypted,
                since,
                self._settings.yandex_max_messages,
            )
            await self._user_repo.update_yandex_tokens(user.id, tokens)
            await self._session.flush()
        except ValueError as exc:
            reason = str(exc)
            if reason == "yandex_token_expired":
                await self._user_repo.clear_yandex(user.telegram_id)
                await self._session.commit()
                raise ValueError(t(language, "yandex_token_expired")) from exc
            if reason == "yandex_token_invalid":
                await self._user_repo.clear_yandex(user.telegram_id)
                await self._session.commit()
                raise ValueError(t(language, "yandex_token_invalid")) from exc
            if reason == "yandex_imap_disabled":
                raise ValueError(t(language, "yandex_imap_disabled")) from exc
            if reason == "yandex_imap_auth_failed":
                raise ValueError(t(language, "yandex_imap_auth_failed")) from exc
            raise ValueError(t(language, "yandex_not_linked")) from exc
        except Exception as exc:
            logger.error("yandex_fetch_failed", user_id=user.id, error=str(exc))
            raise RuntimeError(t(language, "yandex_fetch_failed")) from exc

        if not messages:
            raise ValueError(t(language, "no_yandex_emails", label=label))

        return await self._build_digest(
            user.id,
            "yandex",
            frequency,
            language,
            messages,
        )

    async def _generate_slack_digest(self, user: User, frequency: str, language: str) -> str:
        if not self._user_repo.has_slack(user):
            raise ValueError(t(language, "slack_not_linked"))

        channels = await self._slack_repo.list_active_for_user(user.id)
        if not channels:
            raise ValueError(t(language, "no_slack_channels"))

        if not self._slack.is_configured():
            raise ValueError(t(language, "slack_not_configured"))

        since = digest_content_since(frequency)
        label = frequency_label(language, frequency)
        all_messages: list[ContentMessage] = []

        for channel in channels:
            try:
                messages = await self._slack.fetch_messages(
                    user.slack_tokens_encrypted,
                    channel.channel_id,
                    channel.channel_name,
                    since,
                    self._settings.slack_max_messages,
                )
                all_messages.extend(messages)
            except ValueError as exc:
                reason = str(exc)
                if reason == "slack_token_expired":
                    await self._user_repo.clear_slack(user.telegram_id)
                    await self._session.commit()
                    raise ValueError(t(language, "slack_token_expired")) from exc
                if reason == "slack_token_invalid":
                    await self._user_repo.clear_slack(user.telegram_id)
                    await self._session.commit()
                    raise ValueError(t(language, "slack_token_invalid")) from exc
                logger.warning(
                    "slack_channel_fetch_failed",
                    channel=channel.channel_name,
                    error=reason,
                )
            except httpx.HTTPError as exc:
                logger.error(
                    "slack_fetch_failed",
                    user_id=user.id,
                    channel=channel.channel_name,
                    error=str(exc),
                )

        if not all_messages:
            raise ValueError(t(language, "no_slack_messages", label=label))

        channel_titles = {f"slack:#{c.channel_name}": f"#{c.channel_name}" for c in channels}

        return await self._build_digest(
            user.id,
            "slack",
            frequency,
            language,
            all_messages,
            channel_titles=channel_titles,
        )

    async def _fetch_linkedin_public_posts(
        self,
        profile,
        since: datetime,
    ) -> list[ContentMessage]:
        return await fetch_public_posts(
            profile,
            since,
            max_posts=self._settings.linkedin_max_posts,
            router=self._linkedin.router,
            lookback_days=self._settings.linkedin_public_lookback_days,
            google_cse_api_key=self._settings.google_cse_api_key,
            google_cse_cx=self._settings.google_cse_cx,
        )

    async def _generate_linkedin_digest(self, user: User, frequency: str, language: str) -> str:
        profiles = await self._linkedin_repo.list_active_for_user(user.id)
        if not profiles:
            raise ValueError(t(language, "li_no_profiles"))

        since = digest_content_since(frequency)
        label = frequency_label(language, frequency)

        all_messages: list[ContentMessage] = []
        api_errors: list[str] = []
        latest_tokens: dict | None = None
        linked = self._user_repo.has_linkedin(user)
        use_api = linked and self._linkedin.is_configured()
        has_proxy = any(slot.proxy_url for slot in self._linkedin.router.slots)

        if not use_api and not has_proxy:
            raise ValueError(t(language, "li_proxy_missing"))

        try:
            if use_api:
                tracked_slugs = {
                    p.profile_slug.lower() for p in profiles if not p.profile_slug.startswith("activity-")
                }
                org_urns: list[str] = []
                try:
                    followed = await self._linkedin.fetch_followed_profiles(user.linkedin_tokens_encrypted)
                    org_urns = [p.linkedin_urn for p in followed if p.linkedin_urn]
                except Exception:
                    pass

                feed_posts, feed_tokens = await self._linkedin.fetch_network_feed_posts(
                    user.linkedin_tokens_encrypted,
                    tracked_slugs,
                    since,
                )
                if feed_posts:
                    all_messages.extend(feed_posts)
                latest_tokens = feed_tokens or latest_tokens

                for profile in profiles:
                    try:
                        posts, tokens, err = await self._linkedin.fetch_posts(
                            user.linkedin_tokens_encrypted,
                            profile,
                            since,
                            member_id=user.linkedin_member_id,
                            org_urns=org_urns,
                        )
                        latest_tokens = tokens
                        if err:
                            api_errors.append(f"{profile.profile_slug}: {err}")
                        all_messages.extend(posts)
                    except ValueError as exc:
                        logger.warning(
                            "linkedin_profile_fetch_failed",
                            slug=profile.profile_slug,
                            error=str(exc),
                        )
                        api_errors.append(f"{profile.profile_slug}: {exc}")
                    except LinkedInBlockedError as exc:
                        raise ValueError(t(language, "li_blocked")) from exc
            else:
                for profile in profiles:
                    try:
                        posts = await self._fetch_linkedin_public_posts(profile, since)
                        all_messages.extend(posts)
                    except httpx.HTTPError as exc:
                        logger.warning(
                            "linkedin_public_fetch_failed",
                            slug=profile.profile_slug,
                            error=str(exc),
                        )
                        api_errors.append(f"{profile.profile_slug}: {exc}")
                    except LinkedInBlockedError as exc:
                        logger.warning(
                            "linkedin_public_blocked",
                            slug=profile.profile_slug,
                            error=str(exc),
                        )
                        raise ValueError(t(language, "li_blocked")) from exc
        except LinkedInBlockedError as exc:
            raise ValueError(t(language, "li_blocked")) from exc
        except httpx.HTTPError as exc:
            logger.error("linkedin_fetch_failed", user_id=user.id, error=str(exc))
            raise RuntimeError(t(language, "li_fetch_failed")) from exc

        if latest_tokens:
            await self._user_repo.update_linkedin_tokens(user.id, latest_tokens)
            await self._session.flush()

        if not all_messages:
            if use_api and api_errors and any("403" in e or "401" in e for e in api_errors):
                raise ValueError(t(language, "li_api_denied"))
            if api_errors and not use_api:
                logger.warning("linkedin_fetch_errors", user_id=user.id, errors=api_errors)
                raise RuntimeError(t(language, "li_fetch_failed"))
            if api_errors:
                logger.warning("linkedin_fetch_errors", user_id=user.id, errors=api_errors)
            raise ValueError(t(language, "no_linkedin_posts", label=label))

        return await self._build_digest(
            user.id,
            "linkedin",
            frequency,
            language,
            all_messages,
        )

    async def record_digest_delivery(self, user_id: int, platform: str) -> None:
        await self._platform_repo.update_last_digest(user_id, platform, datetime.now(tz=UTC))
        await self._session.commit()

    async def _build_digest(
        self,
        user_id: int,
        platform: str,
        frequency: str,
        language: str,
        all_messages: list[ContentMessage],
        *,
        channel_titles: dict[str, str] | None = None,
    ) -> str:
        limits = self._settings.digest_ai_limits()
        if platform == "telegram":
            selected = select_balanced_messages_by_source(all_messages, limits.max_messages)
        elif platform == "slack":
            selected = select_balanced_messages_by_source(all_messages, limits.max_messages)
        else:
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
            elif msg.source.startswith("yandex:"):
                source_label = msg.source.removeprefix("yandex:")
                items.append((source_label, msg.post_url, msg.text))
            elif msg.source.startswith("linkedin:"):
                source_label = msg.source.removeprefix("linkedin:")
                items.append((source_label, msg.post_url, msg.text))
            elif msg.source.startswith("slack:"):
                label = (
                    channel_titles.get(msg.source, msg.source.removeprefix("slack:"))
                    if channel_titles
                    else msg.source.removeprefix("slack:")
                )
                items.append((label, msg.post_url, msg.text))
            else:
                username = channel_username(msg.source)
                label = (
                    channel_titles.get(username.lower(), f"@{username}")
                    if channel_titles
                    else f"@{username}"
                )
                items.append((label, msg.post_url, msg.text))
            post_urls.append(msg.post_url)

        budget = self._settings.digest_input_char_budget()
        pack_kwargs = dict(
            total_budget_chars=budget,
            max_messages=limits.max_messages,
            per_message_max_chars=limits.message_max_chars,
            min_message_chars=limits.min_message_chars,
        )
        if platform in ("telegram", "slack") and len({msg.source for msg in selected}) > 1:
            blocks = pack_messages_for_digest_by_source(items, **pack_kwargs)
        else:
            blocks = pack_messages_for_digest(items, **pack_kwargs)

        if not blocks:
            label = frequency_label(language, frequency)
            raise ValueError(t(language, "digest_nothing_new", label=label))

        try:
            digest_body = await self._ai.generate_digest(blocks, language, platform=platform)
        except (httpx.HTTPError, APIConnectionError, APITimeoutError, RateLimitError) as exc:
            logger.error("ai_digest_failed", provider=self._ai.name, error=str(exc))
            raise RuntimeError(t(language, "ai_failed", provider=self._ai.name)) from exc
        except Exception as exc:
            logger.error("ai_digest_failed", provider=self._ai.name, error=str(exc))
            raise RuntimeError(t(language, "ai_failed", provider=self._ai.name)) from exc

        digest_body = digest_body.strip()
        label = frequency_label(language, frequency)

        if is_no_new_content_response(digest_body):
            logger.info("digest_no_new_content", user_id=user_id, platform=platform)
            raise ValueError(t(language, "digest_nothing_new", label=label))

        link_label = t(language, "digest_link_label")
        digest_body = format_digest_links(digest_body, link_label, post_urls)

        if not digest_body or is_no_new_content_response(digest_body):
            raise ValueError(t(language, "digest_nothing_new", label=label))

        header = digest_title(language, frequency, platform=platform) + "\n\n"
        content = header + digest_body

        await self._digest_repo.create(user_id, frequency, content)
        await self._session.commit()

        logger.info(
            "digest_generated",
            user_id=user_id,
            platform=platform,
            frequency=frequency,
            language=language,
            messages=len(selected),
            blocks=len(blocks),
        )
        return content
