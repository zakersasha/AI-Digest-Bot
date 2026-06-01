from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

TIMEFRAMES = [
    ("1h", "⏱ Last 1 hour"),
    ("3h", "⏱ Last 3 hours"),
    ("6h", "⏱ Last 6 hours"),
    ("12h", "⏱ Last 12 hours"),
]


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/add"), KeyboardButton(text="/sources")],
            [KeyboardButton(text="/digest"), KeyboardButton(text="/help")],
        ],
        resize_keyboard=True,
    )


def timeframe_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=label, callback_data=f"digest:{code}")
        for code, label in TIMEFRAMES
    ]
    return InlineKeyboardMarkup(inline_keyboard=[buttons[:2], buttons[2:]])


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
                    text="🗑 Remove",
                    callback_data=f"remove:{source.id}",
                ),
            ]
        )
    if not rows:
        rows.append(
            [InlineKeyboardButton(text="➕ Add a channel", callback_data="add_hint")]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)
