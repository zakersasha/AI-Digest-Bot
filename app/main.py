import asyncio

import socks
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram.client.session.aiohttp import AiohttpSession

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
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())


async def run_bot() -> None:
    setup_logging()
    settings = get_settings()

    await init_db()
    logger.info("database_initialized")

    telethon = await TelethonService.create(settings)
    ai = create_ai_provider(settings)
    logger.info("ai_provider_selected", provider=ai.name)
    PROXY_IP = '45.93.137.80'  # IP-адрес прокси
    PROXY_PORT = 3128  # Порт прокси
    PROXY_USER = 'proxy_user'  # Логин (если прокси без авторизации, поставьте None)
    PROXY_PASS = '97vAN1S'  # Пароль (если прокси без авторизации, поставьте None)

    # Формируем конфигурацию прокси (для HTTPS используется socks.HTTP)
    proxy_config = (socks.HTTP, PROXY_IP, PROXY_PORT, True, PROXY_USER, PROXY_PASS)

    session = AiohttpSession(
        proxy=proxy_config
    )

    bot = Bot(
        token=settings.bot_token,
        session=session,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        ),
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
