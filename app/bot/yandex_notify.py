from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.keyboards import CB_YANDEX_CONTINUE
from app.i18n import t


async def notify_yandex_connected(bot: Bot, telegram_id: int, email: str, lang: str) -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_yandex_continue"), callback_data=CB_YANDEX_CONTINUE)],
        ]
    )
    await bot.send_message(
        telegram_id,
        t(lang, "yandex_oauth_done_notify", email=email),
        reply_markup=keyboard,
    )
