from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

# Reply keyboard labels
BTN_ADD = "➕ Add source"
BTN_SOURCES = "📋 My sources"
BTN_DIGEST = "🔥 Digest"
BTN_HELP = "❓ Help"

TIMEFRAMES = [
    ("1h", "⏱ 1 hour"),
    ("3h", "⏱ 3 hours"),
    ("6h", "⏱ 6 hours"),
    ("12h", "⏱ 12 hours"),
]

CB_NAV_MENU = "nav:menu"
CB_NAV_ADD = "nav:add"
CB_NAV_SOURCES = "nav:sources"
CB_NAV_DIGEST = "nav:digest"
CB_NAV_HELP = "nav:help"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_ADD), KeyboardButton(text=BTN_SOURCES)],
            [KeyboardButton(text=BTN_DIGEST), KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def back_button() -> InlineKeyboardButton:
    return InlineKeyboardButton(text="◀️ Back to menu", callback_data=CB_NAV_MENU)


def back_row() -> list[InlineKeyboardButton]:
    return [back_button()]


def timeframe_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=label, callback_data=f"digest:{code}")
        for code, label in TIMEFRAMES
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            buttons[:2],
            buttons[2:],
            back_row(),
        ]
    )


def sources_keyboard(sources: list) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for source in sources:
        status = "✅" if source.is_active else "⏸"
        title = source.title or source.telegram_source
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{status} {title}",
                    callback_data=f"toggle:{source.id}",
                ),
                InlineKeyboardButton(
                    text="🗑",
                    callback_data=f"remove:{source.id}",
                ),
            ]
        )
    rows.append([InlineKeyboardButton(text="➕ Add source", callback_data=CB_NAV_ADD)])
    rows.append(back_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def add_source_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[back_row()])


def help_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[back_row()])
