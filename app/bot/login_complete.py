from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession


async def hide_phone_keyboard(message: Message) -> None:
    try:
        tmp = await message.answer(".", reply_markup=ReplyKeyboardRemove())
        await tmp.delete()
    except TelegramBadRequest:
        pass

from app.bot.subscription_flow import show_channels_loading
from app.repositories.user_repository import UserRepository
from app.services.telethon_auth import cancel_login, cancel_qr_task


async def complete_telethon_session(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
    session_string: str,
    phone: str,
) -> None:
    cancel_qr_task(message.from_user.id)
    await cancel_login(message.from_user.id)
    await hide_phone_keyboard(message)
    await UserRepository(session).save_telethon_session(
        message.from_user.id,
        session_string,
        phone or "",
    )
    await session.commit()
    await state.set_state(None)
    await show_channels_loading(
        message, state, session, lang, message.from_user.id, set()
    )
