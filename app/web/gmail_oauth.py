from collections.abc import Awaitable, Callable

from aiohttp import web
from aiogram import Bot

from app.bot.gmail_notify import notify_gmail_connected
from app.db.session import async_session_factory
from app.repositories.user_repository import UserRepository
from app.services.digest_reschedule import reschedule_platform_digest
from app.services.gmail_link import link_gmail_account
from app.utils.logging import get_logger
from app.config import get_settings
from app.utils.oauth_state import create_signed_oauth_state, verify_signed_oauth_state
from app.web.linkedin_oauth import linkedin_oauth_callback
from app.web.slack_oauth import slack_oauth_callback
from app.web.yandex_oauth import yandex_oauth_callback

logger = get_logger(__name__)


def _success_html(email: str, *, bot_username: str | None, lang: str) -> str:
    tg_link = f"https://t.me/{bot_username}" if bot_username else None
    if lang == "ru":
        title = "Gmail подключён"
        body = f"<b>{email}</b> привязан к Briefly."
        hint = "Вернитесь в Telegram — бот уже отправил сообщение с кнопкой «Продолжить»."
        btn = "Открыть Telegram"
    else:
        title = "Gmail connected"
        body = f"<b>{email}</b> is linked to Briefly."
        hint = "Return to Telegram — the bot sent you a message with a Continue button."
        btn = "Open Telegram"
    btn_html = (
        f'<p><a href="{tg_link}" style="display:inline-block;background:#f5a8c8;color:#0d1240;'
        f'padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600;">{btn}</a></p>'
        if tg_link
        else ""
    )
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    body {{
      font-family: system-ui, sans-serif;
      background: #0d1240;
      color: #f0f2ff;
      max-width: 480px;
      margin: 48px auto;
      padding: 24px 16px;
      text-align: center;
      line-height: 1.6;
    }}
    h1 {{ color: #f5a8c8; font-size: 1.5rem; }}
    p {{ color: #a0a8d0; }}
  </style>
</head>
<body>
  <h1>✅ {title}</h1>
  <p>{body}</p>
  <p>{hint}</p>
  {btn_html}
</body>
</html>"""


async def gmail_oauth_callback(request: web.Request) -> web.Response:
    settings = request.app["settings"]
    bot: Bot | None = request.app.get("bot")
    bot_username: str | None = request.app.get("bot_username")

    state = request.query.get("state", "")
    code = request.query.get("code", "")
    error = request.query.get("error")

    if error:
        return web.Response(text=f"Gmail authorization failed: {error}", status=400)

    secret = settings.session_encryption_key or settings.bot_token
    telegram_id = verify_signed_oauth_state(state, secret)
    if not telegram_id or not code:
        return web.Response(
            text="Invalid or expired OAuth link. Open the bot and tap Connect Gmail again.",
            status=400,
        )

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

    await reschedule_platform_digest(telegram_id, "gmail")

    logger.info("gmail_oauth_success", telegram_id=telegram_id, email=email)
    return web.Response(
        text=_success_html(email, bot_username=bot_username, lang=lang),
        content_type="text/html",
    )


def create_oauth_app(
    settings,
    *,
    bot: Bot | None = None,
    bot_username: str | None = None,
    storage=None,
) -> web.Application:
    app = web.Application()
    app["settings"] = settings
    app["bot"] = bot
    app["bot_username"] = bot_username
    app["storage"] = storage
    app.router.add_get("/oauth/gmail/callback", gmail_oauth_callback)
    app.router.add_get("/oauth/yandex/callback", yandex_oauth_callback)
    app.router.add_get("/oauth/slack/callback", slack_oauth_callback)
    app.router.add_get("/oauth/linkedin/callback", linkedin_oauth_callback)
    return app


async def start_oauth_server(
    settings,
    *,
    bot: Bot | None = None,
    bot_username: str | None = None,
    storage=None,
    on_startup: Callable[[], Awaitable[None]] | None = None,
) -> web.AppRunner:
    app = create_oauth_app(settings, bot=bot, bot_username=bot_username, storage=storage)
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
