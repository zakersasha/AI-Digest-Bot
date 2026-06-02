from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from app.i18n import t
from app.services.telethon_service import SubscribedChannel

CHANNELS_PER_PAGE = 7

CB_LANG_RU = "lang:ru"
CB_LANG_EN = "lang:en"
CB_CH_DONE = "ch:done"
CB_CH_REFRESH = "ch:refresh"
CB_CH_PAGE = "ch:page"
CB_FREQ_BACK = "freq:back"
CB_TIME_BACK = "time:back"
CB_ACTION_CHANNELS = "act:channels"
CB_ACTION_SCHEDULE = "act:schedule"
CB_ACTION_DIGEST = "act:digest"
CB_ACTION_SETUP = "act:setup"
CB_ACTION_MENU = "act:menu"
CB_AUTH_CONNECT = "auth:connect"
CB_AUTH_DISCONNECT = "auth:disconnect"
CB_AUTH_RESEND = "auth:resend"


def phone_request_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "btn_share_phone"), request_contact=True)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def code_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_resend_code"), callback_data=CB_AUTH_RESEND)],
        ]
    )


def linked_account_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_disconnect"), callback_data=CB_AUTH_DISCONNECT)],
        ]
    )


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data=CB_LANG_RU),
                InlineKeyboardButton(text="🇬🇧 English", callback_data=CB_LANG_EN),
            ],
        ]
    )


def _username_key(username: str) -> str:
    return username.lstrip("@").lower()


def subscriptions_keyboard(
    subscriptions: list[SubscribedChannel],
    selected: set[str],
    lang: str,
    page: int = 0,
) -> InlineKeyboardMarkup:
    total_pages = max(1, (len(subscriptions) + CHANNELS_PER_PAGE - 1) // CHANNELS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    start = page * CHANNELS_PER_PAGE
    chunk = subscriptions[start : start + CHANNELS_PER_PAGE]

    rows: list[list[InlineKeyboardButton]] = []
    for channel in chunk:
        mark = "✅" if channel.username in selected else "⬜"
        title = channel.title[:28] + "…" if len(channel.title) > 28 else channel.title
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{mark} {title}",
                    callback_data=f"ch:toggle:{_username_key(channel.username)}",
                )
            ]
        )

    if total_pages > 1:
        nav: list[InlineKeyboardButton] = []
        if page > 0:
            nav.append(
                InlineKeyboardButton(text="◀️", callback_data=f"{CB_CH_PAGE}:{page - 1}")
            )
        nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="ch:noop"))
        if page < total_pages - 1:
            nav.append(
                InlineKeyboardButton(text="▶️", callback_data=f"{CB_CH_PAGE}:{page + 1}")
            )
        rows.append(nav)

    rows.append(
        [
            InlineKeyboardButton(text="🔄", callback_data=CB_CH_REFRESH),
            InlineKeyboardButton(text=t(lang, "btn_continue"), callback_data=CB_CH_DONE),
        ]
    )
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
