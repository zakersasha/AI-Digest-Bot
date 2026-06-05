import httpx
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import CB_ACTION_GMAIL, CB_GMAIL_CHECK, CB_GMAIL_DISCONNECT, CB_GMAIL_PASTE
from app.bot.screen import edit_from_callback, open_screen
from app.bot.sources_flow import refresh_sources_screen, show_sources_manage
from app.bot.states import OnboardingStates
from app.config import get_settings
from app.i18n import resolve_lang, t
from app.repositories.user_repository import UserRepository
from app.services.gmail_link import link_gmail_account
from app.utils.gmail_oauth import parse_oauth_code
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = Router(name="platform")


@router.callback_query(F.data == CB_ACTION_GMAIL)
async def cb_gmail_manage(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await callback.answer()
    if callback.message:
        await show_sources_manage(callback.message, state, session, lang, callback.from_user.id)


@router.callback_query(F.data == CB_GMAIL_CHECK)
async def cb_gmail_check(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    repo = UserRepository(session)
    user = await repo.get_by_telegram_id(callback.from_user.id)
    if not user or not repo.has_gmail(user):
        await callback.answer(t(lang, "gmail_not_linked"), show_alert=True)
        return

    await callback.answer(t(lang, "gmail_linked", email=user.gmail_email or ""))
    if callback.message:
        data = await state.get_data()
        onboarding = data.get("sources_onboarding", not user.onboarding_complete)
        await refresh_sources_screen(
            callback.message,
            state,
            session,
            lang,
            callback.from_user.id,
            onboarding=onboarding,
            status_line=t(lang, "gmail_linked", email=user.gmail_email or ""),
        )


@router.callback_query(F.data == CB_GMAIL_PASTE)
async def cb_gmail_paste(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await callback.answer()
    await state.set_state(OnboardingStates.waiting_gmail_code)
    if callback.message:
        await edit_from_callback(callback, state, t(lang, "gmail_paste_prompt"), None)


@router.message(StateFilter(OnboardingStates.waiting_gmail_code), F.text, ~F.text.startswith("/"))
async def msg_gmail_code(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    lang = await resolve_lang(session, message.from_user.id)
    code = parse_oauth_code(message.text or "")
    if not code:
        await open_screen(message, state, t(lang, "gmail_code_invalid"), None)
        return

    settings = get_settings()
    try:
        email = await link_gmail_account(session, settings, message.from_user.id, code)
    except httpx.HTTPStatusError as exc:
        logger.error(
            "gmail_link_http_error",
            status=exc.response.status_code,
            body=exc.response.text[:300],
        )
        await open_screen(message, state, t(lang, "gmail_link_failed"), None)
        return
    except RuntimeError as exc:
        if "SESSION_ENCRYPTION_KEY" in str(exc):
            await open_screen(message, state, t(lang, "encryption_key_missing"), None)
            return
        logger.exception("gmail_link_failed", telegram_id=message.from_user.id)
        await open_screen(message, state, t(lang, "gmail_link_failed"), None)
        return
    except Exception:
        logger.exception("gmail_link_failed", telegram_id=message.from_user.id)
        await open_screen(message, state, t(lang, "gmail_link_failed"), None)
        return

    try:
        await message.delete()
    except Exception:
        pass

    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    onboarding = bool(user and not user.onboarding_complete)
    await refresh_sources_screen(
        message,
        state,
        session,
        lang,
        message.from_user.id,
        onboarding=onboarding,
        status_line=t(lang, "gmail_linked", email=email),
    )


@router.callback_query(F.data == CB_GMAIL_DISCONNECT)
async def cb_gmail_disconnect(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await UserRepository(session).clear_gmail(callback.from_user.id)
    await session.commit()
    await callback.answer(t(lang, "gmail_disconnected"))
    if callback.message:
        user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
        onboarding = bool(user and not user.onboarding_complete)
        await refresh_sources_screen(
            callback.message,
            state,
            session,
            lang,
            callback.from_user.id,
            onboarding=onboarding,
        )
