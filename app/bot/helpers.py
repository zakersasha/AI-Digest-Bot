from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import main_menu_keyboard
from app.bot.texts import MENU_PROMPT
from app.models.source import Source


async def clear_inline_keyboard(message: Message) -> None:
    try:
        await message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass


async def send_main_menu(
    message: Message,
    *,
    text: str | None = None,
    edit: bool = False,
) -> None:
    prompt = text or MENU_PROMPT
    markup = main_menu_keyboard()
    if edit:
        try:
            await message.edit_text(prompt)
        except TelegramBadRequest:
            await message.answer(prompt, reply_markup=markup)
        else:
            await message.answer(prompt, reply_markup=markup)
    else:
        await message.answer(prompt, reply_markup=markup)


async def answer_markdown(message: Message, text: str) -> None:
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)


async def reset_to_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    await clear_inline_keyboard(callback.message)
    await send_main_menu(callback.message)


def format_sources_text(sources: list[Source]) -> str:
    from app.bot.texts import SOURCES_EMPTY, SOURCES_TITLE

    if not sources:
        return SOURCES_EMPTY
    lines = [SOURCES_TITLE, ""]
    for source in sources:
        status = "active" if source.is_active else "paused"
        title = source.title or source.telegram_source
        lines.append(f"• {title} — <code>{source.telegram_source}</code> ({status})")
    return "\n".join(lines)
