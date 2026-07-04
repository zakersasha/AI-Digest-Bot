from aiohttp import web
from aiogram import Bot

from app.bot.yandex_notify import notify_yandex_connected
from app.db.session import async_session_factory
from app.repositories.user_repository import UserRepository
from app.services.digest_reschedule import reschedule_platform_digest
from app.services.yandex_mail_link import link_yandex_account
from app.utils.logging import get_logger
from app.utils.oauth_state import verify_signed_oauth_state

logger = get_logger(__name__)


def _success_html(email: str, *, bot_username: str | None, lang: str) -> str:
    tg_link = f"https://t.me/{bot_username}" if bot_username else None
    if lang == "ru":
        title = "Яндекс Почта подключена"
        body = f"<b>{email}</b> привязан к Briefly."
        hint = "Вернитесь в Telegram — бот отправил сообщение с кнопкой «Продолжить»."
        btn = "Открыть Telegram"
    else:
        title = "Yandex Mail connected"
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


async def yandex_oauth_callback(request: web.Request) -> web.Response:
    settings = request.app["settings"]
    bot: Bot | None = request.app.get("bot")
    bot_username: str | None = request.app.get("bot_username")

    state = request.query.get("state", "")
    code = request.query.get("code", "")
    error = request.query.get("error")

    if error:
        return web.Response(text=f"Yandex authorization failed: {error}", status=400)

    secret = settings.session_encryption_key or settings.bot_token
    telegram_id = verify_signed_oauth_state(state, secret)
    if not telegram_id or not code:
        return web.Response(
            text="Invalid or expired OAuth link. Open the bot and tap Connect Yandex Mail again.",
            status=400,
        )

    try:
        async with async_session_factory() as session:
            email = await link_yandex_account(session, settings, telegram_id, code)
            user = await UserRepository(session).get_by_telegram_id(telegram_id)
            lang = (user.language if user else None) or "en"
    except Exception:
        logger.exception("yandex_oauth_callback_failed", telegram_id=telegram_id)
        return web.Response(text="Failed to save Yandex tokens.", status=500)

    if bot:
        try:
            await notify_yandex_connected(bot, telegram_id, email, lang)
        except Exception:
            logger.exception("yandex_notify_failed", telegram_id=telegram_id)

    await reschedule_platform_digest(telegram_id, "yandex")

    logger.info("yandex_oauth_success", telegram_id=telegram_id, email=email)
    return web.Response(
        text=_success_html(email, bot_username=bot_username, lang=lang),
        content_type="text/html",
    )
