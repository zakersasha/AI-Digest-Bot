from aiohttp import web
from aiogram import Bot

from app.config import get_settings
from app.db.session import async_session_factory
from app.repositories.user_repository import UserRepository
from app.services.linkedin_link import link_linkedin_account
from app.utils.logging import get_logger
from app.utils.oauth_state import verify_signed_oauth_state

logger = get_logger(__name__)


def _success_html(name: str, *, bot_username: str | None, lang: str) -> str:
    tg_link = f"https://t.me/{bot_username}" if bot_username else None
    if lang == "ru":
        title = "LinkedIn подключён"
        body = f"<b>{name}</b> привязан к Briefly."
        hint = "Вернитесь в Telegram — экран LinkedIn уже обновлён."
        btn = "Открыть Telegram"
    else:
        title = "LinkedIn connected"
        body = f"<b>{name}</b> is linked to Briefly."
        hint = "Return to Telegram — the LinkedIn screen is updated."
        btn = "Open Telegram"
    btn_html = (
        f'<p><a href="{tg_link}" style="display:inline-block;background:#0a66c2;color:#fff;'
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
    body {{ font-family: system-ui, sans-serif; background: #0d1240; color: #f0f2ff;
      max-width: 480px; margin: 48px auto; padding: 24px 16px; text-align: center; }}
    h1 {{ color: #70b5f9; font-size: 1.5rem; }}
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


async def linkedin_oauth_callback(request: web.Request) -> web.Response:
    settings = request.app["settings"]
    bot: Bot | None = request.app.get("bot")

    state = request.query.get("state", "")
    code = request.query.get("code", "")
    error = request.query.get("error")

    if error:
        return web.Response(text=f"LinkedIn authorization failed: {error}", status=400)

    secret = settings.session_encryption_key or settings.bot_token
    telegram_id = verify_signed_oauth_state(state, secret)
    if not telegram_id or not code:
        return web.Response(
            text="Invalid or expired OAuth link. Open the bot and tap Connect LinkedIn again.",
            status=400,
        )

    try:
        async with async_session_factory() as session:
            name = await link_linkedin_account(session, settings, telegram_id, code)
            user = await UserRepository(session).get_by_telegram_id(telegram_id)
            lang = (user.language if user else None) or "en"
    except Exception:
        logger.exception("linkedin_oauth_callback_failed", telegram_id=telegram_id)
        return web.Response(text="Failed to save LinkedIn tokens.", status=500)

    if bot:
        try:
            from app.bot.platform_screens import push_linkedin_screen

            storage = request.app.get("storage")
            if storage:
                await push_linkedin_screen(bot, storage, telegram_id, lang, status_line=None)
        except Exception:
            logger.exception("linkedin_screen_push_failed", telegram_id=telegram_id)

    bot_username = request.app.get("bot_username")
    logger.info("linkedin_oauth_success", telegram_id=telegram_id, name=name)
    return web.Response(
        text=_success_html(name, bot_username=bot_username, lang=lang),
        content_type="text/html",
    )
