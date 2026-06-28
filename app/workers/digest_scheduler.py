from __future__ import annotations

import asyncio
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import LinkPreviewOptions
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.ai.factory import create_ai_provider
from app.config import Settings, get_settings
from app.db.session import async_session_factory
from app.i18n import t
from app.models.platform_settings import PlatformSettings
from app.repositories.platform_settings_repository import PlatformSettingsRepository
from app.repositories.user_repository import UserRepository
from app.services.digest_service import DigestService
from app.services.platform_readiness import can_deliver_platform
from app.services.schedule_service import delivery_hours_for_settings, is_digest_period_elapsed
from app.utils.logging import get_logger
from app.utils.telegram import split_telegram_message

logger = get_logger(__name__)

_NO_PREVIEW = LinkPreviewOptions(is_disabled=True)
_JOB_PREFIX = "digest"
_PLATFORM_MINUTE_OFFSET = {"telegram": 0, "gmail": 2, "slack": 4, "linkedin": 6}
_user_delivery_locks: dict[int, asyncio.Lock] = {}


class DigestScheduler:
    def __init__(self, bot: Bot, settings: Settings) -> None:
        self._bot = bot
        self._settings = settings
        self._ai = create_ai_provider(settings)
        self._scheduler = AsyncIOScheduler(timezone="UTC")

    async def start(self) -> None:
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("apscheduler_started")
        await self.reload_all()

    async def stop(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("apscheduler_stopped")

    async def reload_all(self) -> None:
        for job in self._scheduler.get_jobs():
            if job.id.startswith(f"{_JOB_PREFIX}:"):
                self._scheduler.remove_job(job.id)

        async with async_session_factory() as session:
            rows = await PlatformSettingsRepository(session).list_scheduled()

        for user, ps in rows:
            await self.schedule_user_platform(user.id, ps.platform)

        logger.info("scheduler_jobs_loaded", jobs=len(self._scheduler.get_jobs()))

    async def schedule_user_platform(self, user_id: int, platform: str) -> None:
        self.unschedule_user_platform(user_id, platform)

        async with async_session_factory() as session:
            user = await UserRepository(session).get_by_id(user_id)
            ps = await PlatformSettingsRepository(session).get(user_id, platform)
            if not user or not ps:
                return
            if not await can_deliver_platform(session, user, platform, ps):
                return
            self._add_jobs(user, ps)

    def _add_jobs(self, user, ps: PlatformSettings) -> None:
        tz = ZoneInfo(user.timezone or "Europe/Moscow")
        base_minute = ps.delivery_minute or 0
        offset = _PLATFORM_MINUTE_OFFSET.get(ps.platform, 0)
        minute = (base_minute + offset) % 60
        hours = delivery_hours_for_settings(ps)

        for slot, hour in enumerate(hours):
            job_id = f"{_JOB_PREFIX}:{user.id}:{ps.platform}:{slot}"
            self._scheduler.add_job(
                self._deliver_scheduled_digest,
                trigger=CronTrigger(hour=hour, minute=minute, timezone=tz),
                id=job_id,
                args=[user.id, ps.platform],
                replace_existing=True,
                misfire_grace_time=3600,
                coalesce=True,
                max_instances=1,
            )

        logger.info(
            "scheduler_platform_scheduled",
            user_id=user.id,
            platform=ps.platform,
            hours=hours,
            minute=minute,
        )

    def unschedule_user_platform(self, user_id: int, platform: str) -> None:
        prefix = f"{_JOB_PREFIX}:{user_id}:{platform}:"
        for job in list(self._scheduler.get_jobs()):
            if job.id.startswith(prefix):
                self._scheduler.remove_job(job.id)

    def unschedule_user(self, user_id: int) -> None:
        prefix = f"{_JOB_PREFIX}:{user_id}:"
        for job in list(self._scheduler.get_jobs()):
            if job.id.startswith(prefix):
                self._scheduler.remove_job(job.id)

    async def _deliver_scheduled_digest(self, user_id: int, platform: str) -> None:
        lock = _user_delivery_locks.setdefault(user_id, asyncio.Lock())
        async with lock:
            async with async_session_factory() as session:
                user = await UserRepository(session).get_by_id(user_id)
                ps = await PlatformSettingsRepository(session).get(user_id, platform)
                if not user or not ps:
                    return
                if not await can_deliver_platform(session, user, platform, ps):
                    logger.info(
                        "scheduled_digest_skipped_not_ready",
                        user_id=user_id,
                        platform=platform,
                    )
                    return
                if not is_digest_period_elapsed(ps, user):
                    logger.info(
                        "scheduled_digest_skipped_period",
                        user_id=user_id,
                        platform=platform,
                    )
                    return

                language = user.language or "en"
                try:
                    digest_service = DigestService(session, self._ai, self._settings)
                    content = await digest_service.generate_scheduled(user_id, platform, language)
                except ValueError as exc:
                    logger.info("scheduled_digest_skipped", user_id=user_id, platform=platform, reason=str(exc))
                    try:
                        await self._bot.send_message(user.telegram_id, str(exc))
                    except Exception:
                        pass
                    return
                except Exception:
                    logger.exception("scheduled_digest_failed", user_id=user_id, platform=platform)
                    try:
                        await self._bot.send_message(user.telegram_id, t(language, "digest_failed"))
                    except Exception:
                        pass
                    return

            await self._send_digest(user.telegram_id, content)

            async with async_session_factory() as session:
                digest_service = DigestService(session, self._ai, self._settings)
                await digest_service.record_digest_delivery(user_id, platform)

            logger.info("scheduled_digest_sent", user_id=user_id, platform=platform)

    async def _send_digest(self, telegram_id: int, content: str) -> None:
        for part in split_telegram_message(content):
            try:
                await self._bot.send_message(
                    telegram_id,
                    part,
                    parse_mode=ParseMode.MARKDOWN,
                    link_preview_options=_NO_PREVIEW,
                )
            except TelegramBadRequest:
                await self._bot.send_message(telegram_id, part, link_preview_options=_NO_PREVIEW)


_scheduler: DigestScheduler | None = None


def init_digest_scheduler(bot: Bot, settings: Settings | None = None) -> DigestScheduler:
    global _scheduler
    _scheduler = DigestScheduler(bot, settings or get_settings())
    return _scheduler


def get_digest_scheduler() -> DigestScheduler | None:
    return _scheduler
