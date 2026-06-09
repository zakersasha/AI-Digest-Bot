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
from app.config import effective_openai_proxy_url, effective_telethon_proxy_url, get_settings
from app.db.session import init_db
from app.utils.logging import get_logger, setup_logging
from app.web.gmail_oauth import start_oauth_server
from app.workers.digest_scheduler import init_digest_scheduler

logger = get_logger(__name__)


def create_bot_session(settings) -> AiohttpSession:
    if not settings.bot_proxy_url:
        return AiohttpSession(timeout=settings.bot_api_timeout)
    logger.info("bot_proxy_enabled")
    return AiohttpSession(proxy=settings.bot_proxy_url, timeout=settings.bot_api_timeout)


async def set_bot_commands(bot: Bot, retries: int = 3) -> None:
    commands = [
        BotCommand(command="start", description="Start / main menu"),
        BotCommand(command="menu", description="Main menu"),
    ]

    for attempt in range(1, retries + 1):
        try:
            await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
            logger.info("bot_commands_set")
            return
        except TelegramNetworkError as exc:
            logger.warning("bot_commands_failed", attempt=attempt, error=str(exc))
            if attempt < retries:
                await asyncio.sleep(2 ** (attempt - 1))

    logger.warning("bot_commands_skipped")


async def run_bot() -> None:
    setup_logging()
    settings = get_settings()

    await init_db()
    logger.info("database_initialized")

    ai = create_ai_provider(settings)
    model = settings.openai_model if settings.ai_provider == "openai" else settings.local_ai_model
    limits = settings.digest_ai_limits()
    logger.info(
        "ai_provider_selected",
        provider=ai.name,
        model=model,
        context_tokens=limits.max_context_tokens,
        max_messages=limits.max_messages,
    )

    telethon_proxy = effective_telethon_proxy_url(settings)
    if telethon_proxy:
        source = "TELEGRAM_PROXY_URL" if settings.telegram_proxy_url else "BOT_PROXY_URL"
        logger.info("telethon_proxy_configured", source=source)
    else:
        logger.warning("telethon_proxy_missing")

    if settings.ai_provider == "openai":
        openai_proxy = effective_openai_proxy_url(settings)
        if openai_proxy:
            if settings.openai_proxy_url:
                src = "OPENAI_PROXY_URL"
            elif settings.bot_proxy_url:
                src = "BOT_PROXY_URL"
            else:
                src = "TELEGRAM_PROXY_URL"
            logger.info("openai_proxy_configured", source=src)
        else:
            logger.warning(
                "openai_proxy_missing",
                hint="Set OPENAI_PROXY_URL or TELEGRAM_PROXY_URL / BOT_PROXY_URL",
            )

    session = create_bot_session(settings)
    bot = Bot(
        token=settings.bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.update.middleware(LoggingMiddleware())
    dp.update.middleware(
        ServicesMiddleware(ai=ai),
    )
    dp.include_router(router)

    await set_bot_commands(bot)
    logger.info("bot_starting")

    digest_scheduler = init_digest_scheduler(bot, settings)
    await digest_scheduler.start()

    oauth_runner = None
    oauth_enabled = (settings.gmail_client_id and settings.gmail_client_secret) or (
        settings.linkedin_client_id and settings.linkedin_client_secret
    )
    if oauth_enabled:
        bot_username = settings.bot_username.strip().lstrip("@")
        if not bot_username:
            me = await bot.get_me()
            bot_username = me.username or ""
        oauth_runner = await start_oauth_server(
            settings,
            bot=bot,
            bot_username=bot_username or None,
            storage=dp.storage,
        )
        if settings.gmail_client_id and settings.gmail_client_secret:
            logger.info(
                "gmail_oauth_enabled",
                redirect_uri=settings.gmail_redirect_uri,
                bot_username=bot_username,
            )
            if settings.gmail_redirect_is_localhost():
                logger.error(
                    "gmail_oauth_localhost_redirect",
                    hint="Set GMAIL_REDIRECT_URI=https://brieflybot.pro/oauth/gmail/callback in .env",
                )
        if settings.linkedin_client_id and settings.linkedin_client_secret:
            logger.info(
                "linkedin_oauth_enabled",
                redirect_uri=settings.linkedin_redirect_uri,
                bot_username=bot_username,
            )
    else:
        logger.info("oauth_server_disabled")

    try:
        await dp.start_polling(bot)
    finally:
        await digest_scheduler.stop()
        if oauth_runner:
            await oauth_runner.cleanup()
        await bot.session.close()
        if hasattr(ai, "aclose"):
            await ai.aclose()


def main() -> None:
    asyncio.run(run_bot())
