from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import sources_keyboard
from app.bot.screen import edit_from_callback, edit_screen, open_screen, replace_screen
from app.bot.states import OnboardingStates
from app.i18n import t
from app.repositories.source_repository import SourceRepository
from app.repositories.user_repository import UserRepository
from app.utils.links import parse_channel_links


def _format_sources_list(sources, lang: str) -> str:
    if not sources:
        return t(lang, "sources_list_empty")
    lines = [t(lang, "sources_list_header", count=len(sources))]
    for source in sources:
        lines.append(f"• {source.telegram_source}")
    return "\n".join(lines)


async def show_sources_onboarding(target: Message, state: FSMContext, lang: str) -> None:
    await state.update_data(sources_onboarding=True)
    await state.set_state(OnboardingStates.entering_sources)
    await replace_screen(target, state, t(lang, "step_sources"), sources_keyboard(lang, onboarding=True))


async def show_sources_manage(
    target: Message,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
    telegram_id: int,
) -> None:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if not user:
        return

    sources = await SourceRepository(session).list_all_for_user(user.id)
    await state.update_data(sources_onboarding=False)
    await state.set_state(OnboardingStates.managing_sources)
    text = t(lang, "sources_manage") + "\n\n" + _format_sources_list(sources, lang)
    await edit_screen(target, state, text, sources_keyboard(lang, sources, onboarding=False))


async def show_add_source_prompt(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
) -> None:
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    onboarding = bool(user and not user.onboarding_complete)
    await state.update_data(sources_onboarding=onboarding)
    await state.set_state(OnboardingStates.waiting_add_source)
    await edit_from_callback(callback, state, t(lang, "sources_add_prompt"), None)


async def process_source_links(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
    text: str,
) -> tuple[int, int]:
    """Returns (added_count, skipped_count)."""
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    if not user:
        return 0, 0

    links = parse_channel_links(text)
    if not links:
        return 0, 0

    repo = SourceRepository(session)
    added = 0
    for link in links:
        if await repo.add_source(user.id, link):
            added += 1
    await session.commit()
    skipped = len(links) - added
    return added, skipped


async def refresh_sources_screen(
    target: Message,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
    telegram_id: int,
    *,
    onboarding: bool | None = None,
) -> None:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if not user:
        return

    if onboarding is None:
        data = await state.get_data()
        onboarding = data.get("sources_onboarding", not user.onboarding_complete)

    sources = await SourceRepository(session).list_all_for_user(user.id)
    if onboarding:
        await state.set_state(OnboardingStates.entering_sources)
        text = t(lang, "step_sources") + "\n\n" + _format_sources_list(sources, lang)
    else:
        await state.set_state(OnboardingStates.managing_sources)
        text = t(lang, "sources_manage") + "\n\n" + _format_sources_list(sources, lang)

    await edit_screen(
        target,
        state,
        text,
        sources_keyboard(lang, sources, onboarding=onboarding),
    )


def source_key_from_callback(data: str) -> str:
    return data.split(":", 2)[2]
