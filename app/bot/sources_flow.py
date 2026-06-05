from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.platform_screens import show_telegram_screen
from app.bot.screen import edit_from_callback
from app.bot.states import OnboardingStates
from app.i18n import t
from app.repositories.user_repository import UserRepository
from app.utils.links import parse_channel_links
from app.repositories.source_repository import SourceRepository


async def show_add_source_prompt(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
) -> None:
    await state.set_state(OnboardingStates.waiting_add_source)
    await edit_from_callback(callback, state, t(lang, "sources_add_prompt"), None)


async def process_source_links(
    message: Message,
    session: AsyncSession,
    text: str,
) -> tuple[int, int, list[str]]:
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    if not user:
        return 0, 0, []

    links = parse_channel_links(text)
    if not links:
        return 0, 0, []

    repo = SourceRepository(session)
    new_count = 0
    dup_count = 0
    for link in links:
        result = await repo.add_source(user.id, link)
        if result == "new":
            new_count += 1
        elif result == "exists":
            dup_count += 1
    await session.commit()
    return new_count, dup_count, []


async def refresh_telegram_screen(
    target: Message,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
    telegram_id: int,
    *,
    status_line: str | None = None,
) -> None:
    await show_telegram_screen(
        target,
        state,
        session,
        lang,
        telegram_id,
        status_line=status_line,
    )
