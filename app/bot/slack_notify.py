from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.keyboards import CB_SLACK_CONTINUE
from app.i18n import t


async def notify_slack_connected(bot: Bot, telegram_id: int, team_name: str, lang: str) -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_slack_continue"), callback_data=CB_SLACK_CONTINUE)],
        ]
    )
    await bot.send_message(
        telegram_id,
        t(lang, "slack_oauth_done_notify", team=team_name),
        reply_markup=keyboard,
    )
