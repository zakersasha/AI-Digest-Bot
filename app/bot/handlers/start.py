from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.bot.keyboards import main_menu_keyboard
from app.repositories.user_repository import UserRepository
from sqlalchemy.ext.asyncio import AsyncSession

router = Router(name="start")

WELCOME_TEXT = (
    "👋 <b>Welcome to AI Digest Bot</b>\n\n"
    "Get AI summaries from Telegram channels without information overload.\n\n"
    "<b>How it works:</b>\n"
    "1️⃣ Add public channels with /add\n"
    "2️⃣ Manage sources with /sources\n"
    "3️⃣ Generate a digest with /digest\n\n"
    "Only public @usernames are supported."
)

HELP_TEXT = (
    "<b>Commands</b>\n\n"
    "/start — welcome message\n"
    "/add — add a public channel or group (@username)\n"
    "/sources — list, toggle, or remove sources\n"
    "/digest — generate AI digest for a time period\n"
    "/help — show this help"
)


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession) -> None:
    repo = UserRepository(session)
    await repo.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
    )
    await session.commit()
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)
