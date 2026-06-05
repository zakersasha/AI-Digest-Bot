from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import (
    CB_ACTION_GMAIL,
    CB_ACTION_PLATFORM,
    CB_GMAIL_CHECK,
    CB_GMAIL_CONTINUE,
    CB_GMAIL_DISCONNECT,
    CB_PLATFORM_GMAIL,
    CB_PLATFORM_TG,
    frequency_keyboard,
)
from app.bot.platform_flow import show_gmail_screen, show_platform_menu, show_platform_picker
from app.bot.screen import edit_from_callback
from app.bot.sources_flow import show_sources_onboarding
from app.i18n import resolve_lang, t
from app.repositories.user_repository import UserRepository

router = Router(name="platform")


async def _after_platform_pick(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
    platform: str,
    *,
    onboarding: bool,
) -> None:
    repo = UserRepository(session)
    await repo.set_content_platform(callback.from_user.id, platform)
    await session.commit()

    if not callback.message:
        return

    if platform == "gmail":
        await show_gmail_screen(
            callback.message,
            state,
            session,
            lang,
            callback.from_user.id,
            onboarding=onboarding,
        )
    elif onboarding:
        await show_sources_onboarding(
            callback.message,
            state,
            session,
            lang,
            callback.from_user.id,
        )
    else:
        await show_platform_menu(callback.message, state, session, lang, callback.from_user.id)


@router.callback_query(F.data == CB_ACTION_PLATFORM)
async def cb_platform_menu(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await callback.answer()
    if callback.message:
        await show_platform_menu(callback.message, state, session, lang, callback.from_user.id)


@router.callback_query(F.data == CB_ACTION_GMAIL)
async def cb_gmail_manage(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await callback.answer()
    if callback.message:
        await show_gmail_screen(
            callback.message,
            state,
            session,
            lang,
            callback.from_user.id,
            onboarding=False,
        )


@router.callback_query(F.data.in_({CB_PLATFORM_TG, CB_PLATFORM_GMAIL}))
async def cb_pick_platform(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    platform = "gmail" if callback.data == CB_PLATFORM_GMAIL else "telegram"
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    onboarding = bool(user and not user.onboarding_complete)
    await callback.answer()
    await _after_platform_pick(
        callback,
        state,
        session,
        lang,
        platform,
        onboarding=onboarding,
    )


@router.callback_query(F.data.in_({CB_GMAIL_CHECK, CB_GMAIL_CONTINUE}))
async def cb_gmail_continue(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    repo = UserRepository(session)
    user = await repo.get_by_telegram_id(callback.from_user.id)
    if not user or not repo.has_gmail(user):
        await callback.answer(t(lang, "gmail_not_linked"), show_alert=True)
        return

    await callback.answer()
    user = await repo.set_content_platform(callback.from_user.id, "gmail")
    await session.commit()

    if user and not user.onboarding_complete:
        await edit_from_callback(callback, state, t(lang, "step_frequency"), frequency_keyboard(lang))
        return

    if callback.message:
        await show_gmail_screen(
            callback.message,
            state,
            session,
            lang,
            callback.from_user.id,
            onboarding=False,
            status_line=t(lang, "gmail_linked", email=user.gmail_email or ""),
        )


@router.callback_query(F.data == CB_GMAIL_DISCONNECT)
async def cb_gmail_disconnect(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await UserRepository(session).clear_gmail(callback.from_user.id)
    await session.commit()
    await callback.answer(t(lang, "gmail_disconnected"))
    if callback.message:
        await show_gmail_screen(
            callback.message,
            state,
            session,
            lang,
            callback.from_user.id,
            onboarding=False,
        )
