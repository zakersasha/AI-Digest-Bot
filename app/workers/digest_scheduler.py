from __future__ import annotations

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
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.digest_service import DigestService
from app.services.schedule_service import (
    delivery_hours_for_user,
    is_digest_period_elapsed,
    is_scheduled_user_ready,
)
from app.utils.logging import get_logger
from app.utils.telegram import split_telegram_message

logger = get_logger(__name__)

_NO_PREVIEW = LinkPreviewOptions(is_disabled=True)
_JOB_PREFIX = "digest"


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
            users = await UserRepository(session).list_scheduled_users()

        for user in users:
            self.schedule_user(user)

        logger.info("scheduler_jobs_loaded", users=len(users), jobs=len(self._scheduler.get_jobs()))

    def schedule_user(self, user: User) -> None:
        if not is_scheduled_user_ready(user):
            self.unschedule_user(user.id)
            return

        self.unschedule_user(user.id)
        tz = ZoneInfo(user.timezone or "Europe/Moscow")
        minute = user.delivery_minute or 0
        hours = delivery_hours_for_user(user)

        for slot, hour in enumerate(hours):
            job_id = f"{_JOB_PREFIX}:{user.id}:{slot}"
            self._scheduler.add_job(
                self._deliver_scheduled_digest,
                trigger=CronTrigger(
                    hour=hour,
                    minute=minute,
                    timezone=tz,
                ),
                id=job_id,
                args=[user.id],
                replace_existing=True,
                misfire_grace_time=3600,
                coalesce=True,
                max_instances=1,
            )

        logger.info(
            "scheduler_user_scheduled",
            user_id=user.id,
            telegram_id=user.telegram_id,
            timezone=str(tz),
            hours=hours,
            minute=minute,
            frequency=user.digest_frequency,
        )

    def unschedule_user(self, user_id: int) -> None:
        prefix = f"{_JOB_PREFIX}:{user_id}:"
        for job in list(self._scheduler.get_jobs()):
            if job.id.startswith(prefix):
                self._scheduler.remove_job(job.id)

    async def reschedule_user_by_telegram_id(self, telegram_id: int) -> None:
        async with async_session_factory() as session:
            user = await UserRepository(session).get_by_telegram_id(telegram_id)
        if user:
            self.schedule_user(user)

    async def _deliver_scheduled_digest(self, user_id: int) -> None:
        async with async_session_factory() as session:
            user = await UserRepository(session).get_by_id(user_id)
            if not user or not is_scheduled_user_ready(user):
                return

            if not is_digest_period_elapsed(user):
                logger.info(
                    "scheduled_digest_skipped_period",
                    user_id=user_id,
                    frequency=user.digest_frequency,
                )
                return

            language = user.language or "en"
            try:
                digest_service = DigestService(session, self._ai, self._settings)
                content = await digest_service.generate_for_user(
                    user.id,
                    user.digest_frequency,
                    language,
                )
            except ValueError as exc:
                logger.info("scheduled_digest_skipped", user_id=user_id, reason=str(exc))
                return
            except Exception:
                logger.exception("scheduled_digest_failed", user_id=user_id)
                try:
                    await self._bot.send_message(user.telegram_id, t(language, "digest_failed"))
                except Exception:
                    pass
                return

        await self._send_digest(user.telegram_id, content)
        logger.info("scheduled_digest_sent", user_id=user_id, telegram_id=user.telegram_id)

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
                await self._bot.send_message(
                    telegram_id,
                    part,
                    link_preview_options=_NO_PREVIEW,
                )


_scheduler: DigestScheduler | None = None


def init_digest_scheduler(bot: Bot, settings: Settings | None = None) -> DigestScheduler:
    global _scheduler
    _scheduler = DigestScheduler(bot, settings or get_settings())
    return _scheduler


def get_digest_scheduler() -> DigestScheduler | None:
    return _scheduler
