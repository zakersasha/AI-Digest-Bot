import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError
from aiogram.types import BotCommand, BotCommandScopeDefault

from app.ai.factory import create_ai_provider
from app.bot.handlers import router
from app.bot.logging_middleware import LoggingMiddleware
from app.bot.middlewares import ServicesMiddleware
from app.config import get_settings
from app.db.session import init_db
from app.services.telethon_service import TelethonService
from app.utils.logging import get_logger, setup_logging

logger = get_logger(__name__)


def create_bot_session(settings) -> AiohttpSession | None:
    if not settings.bot_proxy_url:
        return AiohttpSession(timeout=settings.bot_api_timeout)
    logger.info("bot_proxy_enabled")
    return AiohttpSession(proxy=settings.bot_proxy_url, timeout=settings.bot_api_timeout)


async def set_bot_commands(bot: Bot, retries: int = 3) -> None:
    commands = [
        BotCommand(command="start", description="Welcome & setup"),
        BotCommand(command="add", description="Add a public channel"),
        BotCommand(command="sources", description="Manage your sources"),
        BotCommand(command="digest", description="Generate AI digest"),
        BotCommand(command="help", description="Help"),
    ]

    for attempt in range(1, retries + 1):
        try:
            await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
            logger.info("bot_commands_set")
            return
        except TelegramNetworkError as exc:
            logger.warning(
                "bot_commands_failed",
                attempt=attempt,
                retries=retries,
                error=str(exc),
            )
            if attempt < retries:
                await asyncio.sleep(2 ** (attempt - 1))

    logger.warning(
        "bot_commands_skipped",
        reason="Telegram API unreachable; bot will run without command menu",
    )


async def run_bot() -> None:
    setup_logging()
    settings = get_settings()

    await init_db()
    logger.info("database_initialized")

    telethon = await TelethonService.create(settings)
    ai = create_ai_provider(settings)
    logger.info("ai_provider_selected", provider=ai.name)

    session = create_bot_session(settings)
    bot = Bot(
        token=settings.bot_token,
        session=session,
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
