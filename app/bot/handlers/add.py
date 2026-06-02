from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards import BTN_ADD, BTN_DIGEST, BTN_HELP, BTN_SOURCES, main_menu_keyboard
from app.bot.states import AddSourceStates
from app.bot.texts import MENU_PROMPT
from app.repositories.user_repository import UserRepository
from app.services.source_service import SourceService
from sqlalchemy.ext.asyncio import AsyncSession

router = Router(name="add")


@router.message(
    AddSourceStates.waiting_for_source,
    F.text,
    ~F.text.in_({BTN_ADD, BTN_SOURCES, BTN_DIGEST, BTN_HELP}),
)
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
        await message.answer(
            f"✅ Added <b>{title}</b> (<code>{source.telegram_source}</code>)",
        )
    except ValueError as exc:
        await message.answer(f"❌ {exc}")
    except TimeoutError as exc:
        await message.answer(f"⏳ {exc}")
    except Exception:
        await message.answer("❌ Failed to add source. Check the username and try again.")
    finally:
        await state.clear()
        await message.answer(MENU_PROMPT, reply_markup=main_menu_keyboard())
