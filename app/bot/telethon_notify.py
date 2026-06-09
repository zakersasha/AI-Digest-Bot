from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.keyboards import CB_TG_CONTINUE
from app.i18n import t


async def notify_telethon_connected(bot: Bot, telegram_id: int, lang: str, phone: str) -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_tg_continue"), callback_data=CB_TG_CONTINUE)],
        ]
    )
    await bot.send_message(
        telegram_id,
        t(lang, "tg_oauth_done_notify", phone=phone),
        reply_markup=keyboard,
    )
