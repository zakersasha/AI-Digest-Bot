from aiogram import Bot

from app.i18n import t


async def notify_gmail_connected(bot: Bot, telegram_id: int, email: str, lang: str) -> None:
    await bot.send_message(telegram_id, t(lang, "gmail_oauth_done_notify", email=email))
