from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.states import AddSourceStates
from app.repositories.user_repository import UserRepository
from app.services.source_service import SourceService
from sqlalchemy.ext.asyncio import AsyncSession

router = Router(name="add")


@router.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext) -> None:
    await state.set_state(AddSourceStates.waiting_for_source)
    await message.answer(
        "Send a public channel or group:\n\n"
        "Examples:\n"
        "• @ai_news\n"
        "• https://t.me/python"
    )


@router.message(AddSourceStates.waiting_for_source, F.text)
async def process_source_input(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    source_service: SourceService,
) -> None:
    user_repo = UserRepository(session)
    user = await user_repo.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
    )

    try:
        source = await source_service.add_source(user.id, message.text)
        await session.commit()
        title = source.title or source.telegram_source
        await message.answer(f"✅ Added <b>{title}</b> ({source.telegram_source})")
    except ValueError as exc:
        await message.answer(f"❌ {exc}")
    except TimeoutError as exc:
        await message.answer(f"⏳ {exc}")
    except Exception:
        await message.answer("❌ Failed to add source. Check the username and try again.")
    finally:
        await state.clear()
