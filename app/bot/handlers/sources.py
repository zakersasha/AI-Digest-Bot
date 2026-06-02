from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import (
    CB_SRC_ADD,
    CB_SRC_DONE,
    CB_SRC_REMOVE,
    frequency_keyboard,
    main_menu_keyboard,
)
from app.bot.screen import edit_from_callback
from app.bot.sources_flow import (
    process_source_links,
    refresh_sources_screen,
    show_add_source_prompt,
    show_sources_manage,
    source_key_from_callback,
)
from app.bot.states import OnboardingStates
from app.i18n import resolve_lang, t
from app.repositories.source_repository import SourceRepository
from app.repositories.user_repository import UserRepository

router = Router(name="sources")

_SOURCE_STATES = (
    OnboardingStates.entering_sources,
    OnboardingStates.managing_sources,
    OnboardingStates.waiting_add_source,
)


@router.message(StateFilter(*_SOURCE_STATES), F.text)
async def msg_source_links(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if message.text and message.text.startswith("/"):
        return

    lang = await resolve_lang(session, message.from_user.id)
    data = await state.get_data()
    onboarding = data.get("sources_onboarding", True)

    new_count, dup_count, _ = await process_source_links(message, session, message.text or "")

    if new_count == 0 and dup_count == 0:
        await refresh_sources_screen(
            message,
            state,
            session,
            lang,
            message.from_user.id,
            onboarding=onboarding,
            status_line=t(lang, "sources_parse_failed"),
        )
        return

    try:
        await message.delete()
    except Exception:
        pass

    if new_count > 0:
        status = t(lang, "sources_added", count=new_count)
    elif dup_count > 0:
        status = t(lang, "sources_already")
    else:
        status = None

    await refresh_sources_screen(
        message,
        state,
        session,
        lang,
        message.from_user.id,
        onboarding=onboarding,
        status_line=status,
    )


@router.callback_query(F.data == CB_SRC_ADD)
async def cb_src_add(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await callback.answer()
    await show_add_source_prompt(callback, state, session, lang)


@router.callback_query(F.data.startswith(f"{CB_SRC_REMOVE}:"))
async def cb_src_remove(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    key = source_key_from_callback(callback.data)
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user or not callback.message:
        await callback.answer()
        return

    await SourceRepository(session).remove_source(user.id, f"@{key}")
    await session.commit()
    await callback.answer(t(lang, "source_removed"))

    data = await state.get_data()
    onboarding = data.get("sources_onboarding", False)
    await refresh_sources_screen(
        callback.message,
        state,
        session,
        lang,
        callback.from_user.id,
        onboarding=onboarding,
    )


@router.callback_query(F.data == CB_SRC_DONE)
async def cb_src_done(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user or not callback.message:
        await callback.answer()
        return

    count = await SourceRepository(session).count_active(user.id)
    if count == 0:
        await callback.answer(t(lang, "pick_channel_first"), show_alert=True)
        return

    current = await state.get_state()
    if current == OnboardingStates.entering_sources.state:
        await callback.answer(t(lang, "channels_saved", count=count))
        await edit_from_callback(callback, state, t(lang, "step_frequency"), frequency_keyboard(lang))
        return

    await callback.answer()
    await edit_from_callback(callback, state, t(lang, "main_menu"), main_menu_keyboard(lang))
