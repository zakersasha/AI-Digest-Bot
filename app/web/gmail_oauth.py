import secrets
from collections.abc import Awaitable, Callable

from aiohttp import web
from aiogram import Bot

from app.bot.gmail_notify import notify_gmail_connected
from app.db.session import async_session_factory
from app.repositories.user_repository import UserRepository
from app.services.gmail_link import link_gmail_account
from app.utils.logging import get_logger

logger = get_logger(__name__)

_pending_states: dict[str, int] = {}


def create_oauth_state(telegram_id: int) -> str:
    state = secrets.token_urlsafe(24)
    _pending_states[state] = telegram_id
    return state


def pop_oauth_telegram_id(state: str) -> int | None:
    return _pending_states.pop(state, None)


_SUCCESS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Gmail connected</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 480px; margin: 48px auto; padding: 0 16px; }}
    h1 {{ color: #1a73e8; }}
  </style>
</head>
<body>
  <h1>Gmail connected</h1>
  <p><b>{email}</b> is linked.</p>
  <p>Return to <b>Telegram</b> — the bot has sent you a message. Tap <b>Continue</b>.</p>
  <p><small>Можно закрыть эту вкладку.</small></p>
</body>
</html>"""


async def gmail_oauth_callback(request: web.Request) -> web.Response:
    settings = request.app["settings"]
    bot: Bot | None = request.app.get("bot")

    state = request.query.get("state", "")
    code = request.query.get("code", "")
    error = request.query.get("error")

    if error:
        return web.Response(text=f"Gmail authorization failed: {error}", status=400)

    telegram_id = pop_oauth_telegram_id(state)
    if not telegram_id or not code:
        return web.Response(text="Invalid or expired OAuth state.", status=400)

    try:
        async with async_session_factory() as session:
            email = await link_gmail_account(session, settings, telegram_id, code)
            user = await UserRepository(session).get_by_telegram_id(telegram_id)
            lang = (user.language if user else None) or "en"
    except Exception:
        logger.exception("gmail_oauth_callback_failed", telegram_id=telegram_id)
        return web.Response(text="Failed to save Gmail tokens.", status=500)

    if bot:
        try:
            await notify_gmail_connected(bot, telegram_id, email, lang)
        except Exception:
            logger.exception("gmail_notify_failed", telegram_id=telegram_id)

    logger.info("gmail_oauth_success", telegram_id=telegram_id, email=email)
    return web.Response(
        text=_SUCCESS_HTML.format(email=email),
        content_type="text/html",
    )


def create_oauth_app(settings, *, bot: Bot | None = None) -> web.Application:
    app = web.Application()
    app["settings"] = settings
    app["bot"] = bot
    app.router.add_get("/oauth/gmail/callback", gmail_oauth_callback)
    return app


async def start_oauth_server(
    settings,
    *,
    bot: Bot | None = None,
    on_startup: Callable[[], Awaitable[None]] | None = None,
) -> web.AppRunner:
    app = create_oauth_app(settings, bot=bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, settings.gmail_oauth_host, settings.gmail_oauth_port)
    await site.start()
    if on_startup:
        await on_startup()
    logger.info(
        "gmail_oauth_server_started",
        host=settings.gmail_oauth_host,
        port=settings.gmail_oauth_port,
        redirect_uri=settings.gmail_redirect_uri,
        localhost_mode=settings.gmail_redirect_is_localhost(),
    )
    return runner
