from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    LinkPreviewOptions,
    Message,
    ReplyKeyboardMarkup,
)

ScreenMarkup = InlineKeyboardMarkup | ReplyKeyboardMarkup | None


async def bind_screen(state: FSMContext, message: Message) -> None:
    await state.update_data(
        screen_chat_id=message.chat.id,
        screen_message_id=message.message_id,
    )


async def _delete_screen(bot, state: FSMContext) -> None:
    data = await state.get_data()
    old_chat = data.get("screen_chat_id")
    old_msg = data.get("screen_message_id")
    if old_chat and old_msg:
        try:
            await bot.delete_message(chat_id=old_chat, message_id=old_msg)
        except TelegramBadRequest:
            pass


def _is_edit_forbidden(exc: TelegramBadRequest) -> bool:
    err = str(exc).lower()
    return "can't be edited" in err or "message to edit not found" in err


async def replace_screen(
    anchor: Message,
    state: FSMContext,
    text: str,
    markup: ScreenMarkup = None,
    *,
    parse_mode: str | None = ParseMode.HTML,
    link_preview_options: LinkPreviewOptions | None = None,
) -> Message:
    """Delete the current screen and send a new message (required after reply keyboards)."""
    await _delete_screen(anchor.bot, state)
    sent = await anchor.answer(
        text,
        reply_markup=markup,
        parse_mode=parse_mode,
        link_preview_options=link_preview_options,
    )
    await bind_screen(state, sent)
    return sent


async def open_screen(
    message: Message,
    state: FSMContext,
    text: str,
    markup: ScreenMarkup,
    *,
    parse_mode: str | None = ParseMode.HTML,
    link_preview_options: LinkPreviewOptions | None = None,
) -> Message:
    await _delete_screen(message.bot, state)
    return await replace_screen(
        message,
        state,
        text,
        markup,
        parse_mode=parse_mode,
        link_preview_options=link_preview_options,
    )


async def edit_screen(
    target: Message,
    state: FSMContext,
    text: str,
    markup: ScreenMarkup = None,
    *,
    parse_mode: str | None = ParseMode.HTML,
    link_preview_options: LinkPreviewOptions | None = None,
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
            link_preview_options=link_preview_options,
        )
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            return
        if _is_edit_forbidden(exc):
            await replace_screen(
                target,
                state,
                text,
                markup,
                parse_mode=parse_mode,
                link_preview_options=link_preview_options,
            )
            return
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
    link_preview_options: LinkPreviewOptions | None = None,
) -> None:
    if callback.message:
        await bind_screen(state, callback.message)
        await edit_screen(
            callback.message,
            state,
            text,
            markup,
            parse_mode=parse_mode,
            link_preview_options=link_preview_options,
        )


async def edit_by_state(
    bot,
    state: FSMContext,
    text: str,
    markup: InlineKeyboardMarkup | None = None,
    *,
    parse_mode: str | None = ParseMode.HTML,
    link_preview_options: LinkPreviewOptions | None = None,
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
            link_preview_options=link_preview_options,
        )
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            raise
