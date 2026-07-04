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
CB_ACTION_MENU = "act:menu"
CB_PLATFORM_TELEGRAM = "plat:telegram"
CB_PLATFORM_GMAIL = "plat:gmail"
CB_PLATFORM_YANDEX = "plat:yandex"
CB_PLATFORM_SLACK = "plat:slack"
CB_PLATFORM_LINKEDIN = "plat:linkedin"
CB_GMAIL_DISCONNECT = "gmail:disconnect"
CB_GMAIL_CHECK = "gmail:check"
CB_GMAIL_PASTE = "gmail:paste"
CB_GMAIL_CONTINUE = "gmail:continue"
CB_YANDEX_DISCONNECT = "yandex:disconnect"
CB_YANDEX_CHECK = "yandex:check"
CB_YANDEX_PASTE = "yandex:paste"
CB_YANDEX_CONTINUE = "yandex:continue"
CB_SLACK_DISCONNECT = "slack:disconnect"
CB_SLACK_CHECK = "slack:check"
CB_SLACK_PASTE = "slack:paste"
CB_SLACK_CONTINUE = "slack:continue"
CB_SLACK_CHANNELS = "slack:channels"
CB_SLACK_PICK = "slack:pick"
CB_SLACK_PICK_DONE = "slack:pick:done"
CB_SLACK_PICK_PAGE_PREFIX = "slack:pick:page:"
CB_SLACK_PICK_TOGGLE_PREFIX = "slack:pick:toggle:"
CB_TG_CONNECT = "tg:connect"
CB_TG_ADD_LINKS = "tg:add:links"
CB_TG_QR_REFRESH = "tg:qr:refresh"
CB_TG_CHANNELS = "tg:channels"
CB_TG_CONTINUE = "tg:continue"
CB_TG_DISCONNECT = "tg:disconnect"
CB_TG_PICK = "tg:pick"
CB_TG_PICK_DONE = "tg:pick:done"
CB_TG_PICK_PAGE_PREFIX = "tg:pick:page:"
CB_TG_PICK_TOGGLE_PREFIX = "tg:pick:toggle:"

CB_LI_CONNECT = "li:connect"
CB_LI_ADD_LINKS = "li:add:links"
CB_LI_PROFILES = "li:profiles"
CB_LI_DISCONNECT = "li:disconnect"
CB_LI_PICK = "li:pick"
CB_LI_PICK_DONE = "li:pick:done"
CB_LI_PICK_PAGE_PREFIX = "li:pick:page:"
CB_LI_PICK_TOGGLE_PREFIX = "li:pick:toggle:"
CB_LI_REMOVE_PREFIX = "li:remove:"
CB_SCHEDULE_PREFIX = "sched:"
CB_TEST_DIGEST_PREFIX = "test:"
CB_FLOW_DIGEST = "flow:digest"
CB_FLOW_SCHEDULE = "flow:schedule"


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇷🇺 Russian", callback_data=CB_LANG_RU),
                InlineKeyboardButton(text="🇬🇧 English", callback_data=CB_LANG_EN),
            ],
        ]
    )


def frequency_keyboard(lang: str, *, platform: str | None = None) -> InlineKeyboardMarkup:
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


def back_to_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_menu"), callback_data=CB_ACTION_MENU)],
        ]
    )
