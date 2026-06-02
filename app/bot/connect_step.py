from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.exceptions import TelegramBadRequest

from app.bot.keyboards import phone_request_keyboard
from app.bot.screen import replace_screen
from app.bot.states import LoginStates
from app.i18n import t


async def show_connect_step(target: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(LoginStates.waiting_phone)
    await replace_screen(
        target,
        state,
        t(lang, "step_connect"),
        phone_request_keyboard(lang),
    )


async def hide_phone_keyboard(message: Message) -> None:
    try:
        tmp = await message.answer(".", reply_markup=ReplyKeyboardRemove())
        await tmp.delete()
    except TelegramBadRequest:
        pass
