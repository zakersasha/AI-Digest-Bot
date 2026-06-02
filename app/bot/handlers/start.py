from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.bot.helpers import send_main_menu
from app.bot.keyboards import main_menu_keyboard
from app.bot.texts import WELCOME_TEXT
from app.repositories.user_repository import UserRepository
from sqlalchemy.ext.asyncio import AsyncSession

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession) -> None:
    repo = UserRepository(session)
    await repo.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
    )
    await session.commit()
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_keyboard())
