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
CB_GMAIL_CONTINUE = "gmail:done"
CB_GMAIL_CHECK = "gmail:check"
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

    if sources:
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


def platform_keyboard(lang: str, current: str | None = None) -> InlineKeyboardMarkup:
    tg_mark = " ✓" if current == "telegram" else ""
    gmail_mark = " ✓" if current == "gmail" else ""
    rows = [
        [
            InlineKeyboardButton(
                text=f"📱 {t(lang, 'platform_telegram')}{tg_mark}",
                callback_data=CB_PLATFORM_TG,
            ),
            InlineKeyboardButton(
                text=f"📧 {t(lang, 'platform_gmail')}{gmail_mark}",
                callback_data=CB_PLATFORM_GMAIL,
            ),
        ],
    ]
    if current:
        rows.append([InlineKeyboardButton(text=t(lang, "btn_menu"), callback_data=CB_ACTION_MENU)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def main_menu_keyboard(lang: str, platform: str = "telegram") -> InlineKeyboardMarkup:
    source_btn = t(lang, "menu_gmail") if platform == "gmail" else t(lang, "menu_channels")
    source_cb = CB_ACTION_GMAIL if platform == "gmail" else CB_ACTION_CHANNELS
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(lang, "menu_platform"), callback_data=CB_ACTION_PLATFORM),
                InlineKeyboardButton(text=source_btn, callback_data=source_cb),
            ],
            [
                InlineKeyboardButton(text=t(lang, "menu_schedule"), callback_data=CB_ACTION_SCHEDULE),
                InlineKeyboardButton(text=t(lang, "menu_digest_now"), callback_data=CB_ACTION_DIGEST),
            ],
            [
                InlineKeyboardButton(text=t(lang, "menu_reconfigure"), callback_data=CB_ACTION_SETUP),
            ],
        ]
    )


def done_keyboard(lang: str, platform: str = "telegram") -> InlineKeyboardMarkup:
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
