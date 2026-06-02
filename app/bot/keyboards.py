from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.i18n import t
from app.models.source import Source
from app.utils.links import channel_username

CB_LANG_RU = "lang:ru"
CB_LANG_EN = "lang:en"
CB_SRC_DONE = "src:done"
CB_SRC_ADD = "src:add"
CB_SRC_REMOVE = "src:rm"
CB_FREQ_BACK = "freq:back"
CB_TIME_BACK = "time:back"
CB_ACTION_CHANNELS = "act:channels"
CB_ACTION_SCHEDULE = "act:schedule"
CB_ACTION_DIGEST = "act:digest"
CB_ACTION_SETUP = "act:setup"
CB_ACTION_MENU = "act:menu"


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data=CB_LANG_RU),
                InlineKeyboardButton(text="🇬🇧 English", callback_data=CB_LANG_EN),
            ],
        ]
    )


def sources_keyboard(
    lang: str,
    sources: list[Source] | None = None,
    *,
    onboarding: bool,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for source in sources or []:
        key = channel_username(source.telegram_source)
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"🗑 {source.telegram_source}",
                    callback_data=f"{CB_SRC_REMOVE}:{key}",
                )
            ]
        )

    rows.append([InlineKeyboardButton(text=t(lang, "btn_add_source"), callback_data=CB_SRC_ADD)])
    rows.append([InlineKeyboardButton(text=t(lang, "btn_continue"), callback_data=CB_SRC_DONE)])

    if not onboarding:
        rows.append([InlineKeyboardButton(text=t(lang, "btn_menu"), callback_data=CB_ACTION_MENU)])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def frequency_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(lang, "freq_12h"), callback_data="freq:12h"),
                InlineKeyboardButton(text=t(lang, "freq_1d"), callback_data="freq:1d"),
            ],
            [
                InlineKeyboardButton(text=t(lang, "freq_3d"), callback_data="freq:3d"),
                InlineKeyboardButton(text=t(lang, "freq_1w"), callback_data="freq:1w"),
            ],
            [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data=CB_FREQ_BACK)],
        ]
    )


def time_keyboard(lang: str) -> InlineKeyboardMarkup:
    hours = [7, 8, 9, 10, 12, 14, 18, 19, 20, 21, 22]
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for hour in hours:
        row.append(InlineKeyboardButton(text=f"{hour:02d}:00", callback_data=f"time:{hour}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text=t(lang, "btn_back"), callback_data=CB_TIME_BACK)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def main_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(lang, "menu_channels"), callback_data=CB_ACTION_CHANNELS),
                InlineKeyboardButton(text=t(lang, "menu_schedule"), callback_data=CB_ACTION_SCHEDULE),
            ],
            [
                InlineKeyboardButton(text=t(lang, "menu_digest_now"), callback_data=CB_ACTION_DIGEST),
            ],
            [
                InlineKeyboardButton(text=t(lang, "menu_reconfigure"), callback_data=CB_ACTION_SETUP),
            ],
        ]
    )


def done_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "menu_digest_now"), callback_data=CB_ACTION_DIGEST)],
            [InlineKeyboardButton(text=t(lang, "btn_menu"), callback_data=CB_ACTION_MENU)],
        ]
    )


def back_to_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_menu"), callback_data=CB_ACTION_MENU)],
        ]
    )
