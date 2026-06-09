from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.keyboards import CB_PLATFORM_GMAIL
from app.i18n import t


async def notify_gmail_connected(bot: Bot, telegram_id: int, email: str, lang: str) -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_gmail_continue"), callback_data=CB_PLATFORM_GMAIL)],
        ]
    )
    await bot.send_message(
        telegram_id,
        t(lang, "gmail_oauth_done_notify", email=email),
        reply_markup=keyboard,
    )
