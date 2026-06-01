import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from app.ai.factory import create_ai_provider
from app.bot.handlers import router
from app.bot.logging_middleware import LoggingMiddleware
from app.bot.middlewares import ServicesMiddleware
from app.config import get_settings
from app.db.session import init_db
from app.services.telethon_service import TelethonService
from app.utils.logging import get_logger, setup_logging

logger = get_logger(__name__)


async def set_bot_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="start", description="Welcome & setup"),
        BotCommand(command="add", description="Add a public channel"),
        BotCommand(command="sources", description="Manage your sources"),
        BotCommand(command="digest", description="Generate AI digest"),
        BotCommand(command="help", description="Help"),
    ]
    await bot.set_my_commands(commands)


async def run_bot() -> None:
    setup_logging()
    settings = get_settings()

    await init_db()
    logger.info("database_initialized")

    telethon = await TelethonService.create(settings)
    ai = create_ai_provider(settings)
    logger.info("ai_provider_selected", provider=ai.name)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.update.middleware(LoggingMiddleware())
    dp.update.middleware(
        ServicesMiddleware(
            telethon=telethon,
            ai=ai,
            min_importance_score=settings.min_importance_score,
        )
    )
    dp.include_router(router)

    await set_bot_commands(bot)
    logger.info("bot_starting")

    try:
        await dp.start_polling(bot)
    finally:
        await telethon.close()
        await bot.session.close()


def main() -> None:
    asyncio.run(run_bot())
