from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from app.bot.keyboards import phone_request_keyboard
from app.bot.screen import bind_screen
from app.bot.states import LoginStates
from app.i18n import t


async def show_connect_step(target: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(LoginStates.waiting_phone)
    data = await state.get_data()
    old_chat = data.get("screen_chat_id")
    old_msg = data.get("screen_message_id")
    if old_chat and old_msg:
        try:
            await target.bot.delete_message(chat_id=old_chat, message_id=old_msg)
        except TelegramBadRequest:
            pass

    sent = await target.answer(
        t(lang, "step_connect"),
        reply_markup=phone_request_keyboard(lang),
        parse_mode=ParseMode.HTML,
    )
    await bind_screen(state, sent)


async def hide_phone_keyboard(message: Message) -> None:
    """ReplyKeyboardRemove requires non-empty text; delete the helper message right after."""
    try:
        tmp = await message.answer(".", reply_markup=ReplyKeyboardRemove())
        await tmp.delete()
    except TelegramBadRequest:
        pass
