from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message


async def bind_screen(state: FSMContext, message: Message) -> None:
    await state.update_data(
        screen_chat_id=message.chat.id,
        screen_message_id=message.message_id,
    )


async def open_screen(
    message: Message,
    state: FSMContext,
    text: str,
    markup: InlineKeyboardMarkup | None,
    *,
    parse_mode: str | None = ParseMode.HTML,
) -> Message:
    data = await state.get_data()
    old_chat = data.get("screen_chat_id")
    old_msg = data.get("screen_message_id")
    if old_chat and old_msg:
        try:
            await message.bot.delete_message(chat_id=old_chat, message_id=old_msg)
        except TelegramBadRequest:
            pass

    sent = await message.answer(text, reply_markup=markup, parse_mode=parse_mode)
    await bind_screen(state, sent)
    return sent


async def edit_screen(
    target: Message,
    state: FSMContext,
    text: str,
    markup: InlineKeyboardMarkup | None = None,
    *,
    parse_mode: str | None = ParseMode.HTML,
) -> None:
    data = await state.get_data()
    chat_id = data.get("screen_chat_id") or target.chat.id
    message_id = data.get("screen_message_id") or target.message_id

    try:
        await target.bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=markup,
            parse_mode=parse_mode,
        )
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            raise

    if not data.get("screen_message_id"):
        await bind_screen(state, target)


async def edit_from_callback(
    callback: CallbackQuery,
    state: FSMContext,
    text: str,
    markup: InlineKeyboardMarkup | None = None,
    *,
    parse_mode: str | None = ParseMode.HTML,
) -> None:
    if callback.message:
        await bind_screen(state, callback.message)
        await edit_screen(callback.message, state, text, markup, parse_mode=parse_mode)


async def edit_by_state(
    bot,
    state: FSMContext,
    text: str,
    markup: InlineKeyboardMarkup | None = None,
    *,
    parse_mode: str | None = ParseMode.HTML,
) -> None:
    data = await state.get_data()
    chat_id = data.get("screen_chat_id")
    message_id = data.get("screen_message_id")
    if not chat_id or not message_id:
        return
    try:
        await bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=markup,
            parse_mode=parse_mode,
        )
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            raise
