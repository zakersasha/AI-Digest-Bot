from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.i18n import t
CB_LANG_RU = "lang:ru"
CB_LANG_EN = "lang:en"
CB_SRC_DONE = "src:done"
CB_SRC_ADD = "src:add"
CB_SRC_REMOVE = "src:rm"
CB_FREQ_BACK = "freq:back"
CB_TIME_BACK = "time:back"
CB_ACTION_CHANNELS = "act:channels"
CB_ACTION_GMAIL = "act:gmail"
CB_ACTION_PLATFORM = "act:platform"
CB_ACTION_SCHEDULE = "act:schedule"
CB_ACTION_DIGEST = "act:digest"
CB_ACTION_SETUP = "act:setup"
CB_ACTION_MENU = "act:menu"
CB_PLATFORM_TG = "plat:tg"
CB_PLATFORM_GMAIL = "plat:gmail"
CB_GMAIL_CONNECT = "gmail:connect"
CB_GMAIL_DISCONNECT = "gmail:disconnect"
CB_GMAIL_CHECK = "gmail:check"
CB_GMAIL_CONTINUE = "gmail:done"
CB_GMAIL_PASTE = "gmail:paste"


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇷🇺 Russian", callback_data=CB_LANG_RU),
                InlineKeyboardButton(text="🇬🇧 English", callback_data=CB_LANG_EN),
            ],
        ]
    )


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


def time_keyboard(lang: str, hour: int) -> InlineKeyboardMarkup:
    hour = hour % 24
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="◀️", callback_data="time:dec"),
                InlineKeyboardButton(text=f"🕐 {hour:02d}:00", callback_data="time:noop"),
                InlineKeyboardButton(text="▶️", callback_data="time:inc"),
            ],
            [InlineKeyboardButton(text=t(lang, "btn_confirm_time"), callback_data="time:confirm")],
            [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data=CB_TIME_BACK)],
        ]
    )


def main_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "menu_sources"), callback_data=CB_ACTION_CHANNELS)],
            [
                InlineKeyboardButton(text=t(lang, "menu_schedule"), callback_data=CB_ACTION_SCHEDULE),
                InlineKeyboardButton(text=t(lang, "menu_digest_now"), callback_data=CB_ACTION_DIGEST),
            ],
            [InlineKeyboardButton(text=t(lang, "menu_reconfigure"), callback_data=CB_ACTION_SETUP)],
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
