from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import (
    CB_LI_ADD_LINKS,
    CB_LI_DISCONNECT,
    CB_LI_PICK,
    CB_LI_PICK_DONE,
    CB_LI_PICK_PAGE_PREFIX,
    CB_LI_PICK_TOGGLE_PREFIX,
    CB_LI_PROFILES,
    CB_LI_REMOVE_PREFIX,
)
from app.bot.linkedin_flow import (
    process_profile_links,
    refresh_linkedin_screen,
    show_add_profiles_prompt,
)
from app.bot.linkedin_picker import refresh_picker_callback, show_linkedin_picker, toggle_profile
from app.bot.platform_screens import show_linkedin_profiles_screen, show_linkedin_screen
from app.bot.states import OnboardingStates
from app.i18n import resolve_lang, t
from app.repositories.linkedin_profile_repository import LinkedInProfileRepository
from app.repositories.user_repository import UserRepository

router = Router(name="linkedin_auth")


@router.callback_query(F.data == CB_LI_ADD_LINKS)
async def cb_li_add_links(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    data = await state.get_data()
    if data.get("li_ui") != "profiles":
        await state.update_data(li_ui="main")
    await callback.answer()
    await show_add_profiles_prompt(callback, state, session, lang)


@router.callback_query(F.data == CB_LI_PROFILES)
async def cb_li_profiles(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await callback.answer()
    if callback.message:
        await show_linkedin_profiles_screen(
            callback.message,
            state,
            session,
            lang,
            callback.from_user.id,
            from_user_action=True,
        )


@router.callback_query(F.data == CB_LI_DISCONNECT)
async def cb_li_disconnect(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await UserRepository(session).clear_linkedin(callback.from_user.id)
    await session.commit()
    await callback.answer(t(lang, "li_disconnected"))
    if callback.message:
        await show_linkedin_screen(
            callback.message,
            state,
            session,
            lang,
            callback.from_user.id,
            from_user_action=True,
        )


@router.callback_query(F.data == CB_LI_PICK)
async def cb_li_pick(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user or not UserRepository(session).has_linkedin(user):
        await callback.answer(t(lang, "li_not_linked"), show_alert=True)
        return
    if callback.message:
        try:
            await show_linkedin_picker(callback.message, state, session, lang, callback.from_user.id)
            await callback.answer()
        except ValueError as exc:
            await callback.answer(t(lang, str(exc)), show_alert=True)
    else:
        await callback.answer()


@router.callback_query(F.data == CB_LI_PICK_DONE)
async def cb_li_pick_done(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await callback.answer()
    if callback.message:
        await show_linkedin_profiles_screen(
            callback.message,
            state,
            session,
            lang,
            callback.from_user.id,
            from_user_action=True,
        )


@router.callback_query(F.data.startswith(CB_LI_PICK_PAGE_PREFIX))
async def cb_li_pick_page(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    page = int(callback.data.removeprefix(CB_LI_PICK_PAGE_PREFIX))
    await callback.answer()
    await refresh_picker_callback(callback, state, session, lang, page)


@router.callback_query(F.data.startswith(CB_LI_PICK_TOGGLE_PREFIX))
async def cb_li_pick_toggle(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    slug = callback.data.removeprefix(CB_LI_PICK_TOGGLE_PREFIX)
    await toggle_profile(callback, session, lang, slug)
    data = await state.get_data()
    page = int(data.get("li_picker_page", 0))
    await callback.answer()
    await refresh_picker_callback(callback, state, session, lang, page)


@router.callback_query(F.data.startswith(CB_LI_REMOVE_PREFIX))
async def cb_li_remove(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    slug = callback.data.removeprefix(CB_LI_REMOVE_PREFIX)
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user or not callback.message:
        await callback.answer()
        return

    await LinkedInProfileRepository(session).remove_profile(user.id, slug)
    await session.commit()
    await callback.answer(t(lang, "li_profile_removed"))
    await show_linkedin_profiles_screen(
        callback.message,
        state,
        session,
        lang,
        callback.from_user.id,
    )


@router.message(StateFilter(OnboardingStates.waiting_linkedin_add), F.text, ~F.text.startswith("/"))
async def msg_linkedin_profiles(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    lang = await resolve_lang(session, message.from_user.id)
    new_count, dup_count = await process_profile_links(message, session, message.text or "")

    if new_count == 0 and dup_count == 0:
        data = await state.get_data()
        if data.get("li_ui") == "main":
            await show_linkedin_screen(
                message,
                state,
                session,
                lang,
                message.from_user.id,
                status_line=t(lang, "li_parse_failed"),
                from_user_action=True,
            )
        else:
            await refresh_linkedin_screen(
                message,
                state,
                session,
                lang,
                message.from_user.id,
                status_line=t(lang, "li_parse_failed"),
            )
        return

    try:
        await message.delete()
    except Exception:
        pass

    if new_count > 0:
        status = t(lang, "li_profiles_added", count=new_count)
    elif dup_count > 0:
        status = t(lang, "li_profiles_already")
    else:
        status = None

    data = await state.get_data()
    if data.get("li_ui") == "main":
        await show_linkedin_screen(
            message,
            state,
            session,
            lang,
            message.from_user.id,
            status_line=status,
            from_user_action=True,
        )
    else:
        await refresh_linkedin_screen(
            message,
            state,
            session,
            lang,
            message.from_user.id,
            status_line=status,
        )
