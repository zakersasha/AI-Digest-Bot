from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from app.bot.keyboards import phone_request_keyboard
from app.bot.screen import edit_screen
from app.bot.states import LoginStates
from app.i18n import t


async def _remove_phone_prompt(bot, state: FSMContext) -> None:
    data = await state.get_data()
    chat_id = data.get("phone_prompt_chat_id")
    msg_id = data.get("phone_prompt_message_id")
    if chat_id and msg_id:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception:
            pass
        await state.update_data(phone_prompt_chat_id=None, phone_prompt_message_id=None)


async def show_connect_step(target: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(LoginStates.waiting_phone)
    await edit_screen(target, state, t(lang, "step_connect"), None)
    await _remove_phone_prompt(target.bot, state)
    prompt = await target.answer(
        t(lang, "share_phone_hint"),
        reply_markup=phone_request_keyboard(lang),
    )
    await state.update_data(
        phone_prompt_chat_id=prompt.chat.id,
        phone_prompt_message_id=prompt.message_id,
    )


async def hide_phone_keyboard(message: Message) -> None:
    await message.answer("\u200b", reply_markup=ReplyKeyboardRemove())
