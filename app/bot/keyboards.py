from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.i18n import t
from app.models.catalog_channel import CatalogChannel

CB_LANG_RU = "lang:ru"
CB_LANG_EN = "lang:en"
CB_CH_DONE = "ch:done"
CB_FREQ_BACK = "freq:back"
CB_TIME_BACK = "time:back"
CB_ACTION_CHANNELS = "act:channels"
CB_ACTION_SCHEDULE = "act:schedule"
CB_ACTION_DIGEST = "act:digest"
CB_ACTION_SETUP = "act:setup"


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data=CB_LANG_RU),
                InlineKeyboardButton(text="🇬🇧 English", callback_data=CB_LANG_EN),
            ],
        ]
    )


def channels_keyboard(
    catalog: list[CatalogChannel],
    selected: set[int],
    lang: str,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for channel in catalog:
        mark = "✅" if channel.id in selected else "⬜"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{mark} {channel.title}",
                    callback_data=f"ch:toggle:{channel.id}",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(text=t(lang, "btn_continue"), callback_data=CB_CH_DONE),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def frequency_keyboard(lang: str) -> InlineKeyboardMarkup:
    rows = [
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
    return InlineKeyboardMarkup(inline_keyboard=rows)


def time_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Popular delivery hours."""
    hours = [7, 8, 9, 10, 12, 14, 18, 19, 20, 21, 22]
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for hour in hours:
        row.append(
            InlineKeyboardButton(text=f"{hour:02d}:00", callback_data=f"time:{hour}")
        )
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
            [
                InlineKeyboardButton(text=t(lang, "menu_digest_now"), callback_data=CB_ACTION_DIGEST),
            ],
            [
                InlineKeyboardButton(text=t(lang, "menu_channels"), callback_data=CB_ACTION_CHANNELS),
            ],
        ]
    )
