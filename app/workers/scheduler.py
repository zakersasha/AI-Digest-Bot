import asyncio

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest

from app.ai.factory import create_ai_provider
from app.config import Settings
from app.db.session import async_session_factory
from app.i18n import t
from app.repositories.user_repository import UserRepository
from app.services.digest_service import DigestService
from app.services.schedule_service import is_digest_due, user_now
from app.utils.logging import get_logger
from app.utils.telegram import split_telegram_message

logger = get_logger(__name__)


async def _send_digest(bot: Bot, telegram_id: int, content: str) -> None:
    for part in split_telegram_message(content):
        try:
            await bot.send_message(telegram_id, part, parse_mode=ParseMode.MARKDOWN)
        except TelegramBadRequest:
            await bot.send_message(telegram_id, part)


async def run_scheduled_tick(bot: Bot, settings: Settings) -> None:
    ai = create_ai_provider(settings)

    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        users = await user_repo.list_scheduled_users()

        if not settings.telegram_session_string:
            return

        for user in users:
            now = user_now(user)
            if not is_digest_due(user, now):
                continue

            language = user.language or "ru"
            try:
                digest_service = DigestService(
                    session,
                    ai,
                    settings,
                    settings.min_importance_score,
                )
                content = await digest_service.generate_for_user(
                    user.id,
                    user.digest_frequency,
                    language,
                )
                await _send_digest(bot, user.telegram_id, content)
                logger.info("scheduled_digest_sent", user_id=user.id, telegram_id=user.telegram_id)
            except ValueError as exc:
                logger.info("scheduled_digest_skipped", user_id=user.id, reason=str(exc))
            except Exception:
                logger.exception("scheduled_digest_failed", user_id=user.id)
                try:
                    await bot.send_message(user.telegram_id, t(language, "digest_failed"))
                except Exception:
                    pass


async def scheduler_loop(bot: Bot, settings: Settings) -> None:
    logger.info("scheduler_started")
    while True:
        try:
            await run_scheduled_tick(bot, settings)
        except Exception:
            logger.exception("scheduler_tick_error")
        await asyncio.sleep(60)
