import httpx
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import (
    CB_SLACK_CHANNELS,
    CB_SLACK_DISCONNECT,
    CB_SLACK_PASTE,
    CB_SLACK_PICK,
    CB_SLACK_PICK_DONE,
    CB_SLACK_PICK_PAGE_PREFIX,
    CB_SLACK_PICK_TOGGLE_PREFIX,
)
from app.bot.platform_screens import show_slack_screen
from app.bot.screen import edit_from_callback, open_screen
from app.bot.slack_picker import refresh_picker, show_slack_picker, toggle_channel
from app.bot.states import OnboardingStates
from app.config import get_settings
from app.i18n import resolve_lang, t
from app.repositories.platform_settings_repository import PlatformSettingsRepository
from app.repositories.slack_channel_repository import SlackChannelRepository
from app.repositories.user_repository import UserRepository
from app.services.digest_reschedule import reschedule_platform_digest
from app.services.slack_link import link_slack_account
from app.utils.gmail_oauth import parse_oauth_code
from app.utils.logging import get_logger
from app.workers.digest_scheduler import get_digest_scheduler

logger = get_logger(__name__)

router = Router(name="slack_auth")


@router.callback_query(F.data == CB_SLACK_CHANNELS)
async def cb_slack_channels(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await callback.answer()
    if callback.message:
        await show_slack_picker(callback.message, state, session, lang, callback.from_user.id)


@router.callback_query(F.data == CB_SLACK_PICK)
async def cb_slack_pick(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await callback.answer()
    if callback.message:
        await show_slack_picker(callback.message, state, session, lang, callback.from_user.id)


@router.callback_query(F.data.startswith(CB_SLACK_PICK_TOGGLE_PREFIX))
async def cb_slack_pick_toggle(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    channel_id = callback.data.removeprefix(CB_SLACK_PICK_TOGGLE_PREFIX)
    await toggle_channel(callback, session, lang, channel_id)
    await callback.answer()
    await refresh_picker(callback, state, session, lang)


@router.callback_query(F.data.startswith(CB_SLACK_PICK_PAGE_PREFIX))
async def cb_slack_pick_page(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    page = int(callback.data.removeprefix(CB_SLACK_PICK_PAGE_PREFIX))
    await callback.answer()
    if callback.message:
        await show_slack_picker(callback.message, state, session, lang, callback.from_user.id, page=page)


@router.callback_query(F.data == CB_SLACK_PICK_DONE)
async def cb_slack_pick_done(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await callback.answer(t(lang, "slack_channels_saved"))
    if callback.message:
        await show_slack_screen(
            callback.message,
            state,
            session,
            lang,
            callback.from_user.id,
            from_user_action=True,
        )


@router.callback_query(F.data == CB_SLACK_PASTE)
async def cb_slack_paste(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await state.set_state(OnboardingStates.waiting_slack_code)
    await callback.answer()
    if callback.message:
        await edit_from_callback(callback, state, t(lang, "slack_paste_prompt"), None)


@router.message(StateFilter(OnboardingStates.waiting_slack_code), F.text, ~F.text.startswith("/"))
async def msg_slack_code(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    lang = await resolve_lang(session, message.from_user.id)
    code = parse_oauth_code(message.text or "")
    if not code:
        await open_screen(message, state, t(lang, "slack_code_invalid"), None)
        return

    settings = get_settings()
    try:
        team_name = await link_slack_account(session, settings, message.from_user.id, code)
    except httpx.HTTPStatusError as exc:
        logger.error("slack_link_http_error", status=exc.response.status_code, body=exc.response.text[:300])
        await open_screen(message, state, t(lang, "slack_link_failed"), None)
        return
    except RuntimeError as exc:
        if "SESSION_ENCRYPTION_KEY" in str(exc):
            await open_screen(message, state, t(lang, "encryption_key_missing"), None)
            return
        await open_screen(message, state, t(lang, "slack_link_failed"), None)
        return
    except Exception:
        logger.exception("slack_link_failed", telegram_id=message.from_user.id)
        await open_screen(message, state, t(lang, "slack_link_failed"), None)
        return

    try:
        await message.delete()
    except Exception:
        pass

    await reschedule_platform_digest(message.from_user.id, "slack")

    await show_slack_screen(
        message,
        state,
        session,
        lang,
        message.from_user.id,
        status_line=t(lang, "slack_linked", team=team_name),
    )


@router.callback_query(F.data == CB_SLACK_DISCONNECT)
async def cb_slack_disconnect(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if user:
        await UserRepository(session).clear_slack(callback.from_user.id)
        await SlackChannelRepository(session).deactivate_all(user.id)
        await PlatformSettingsRepository(session).clear_schedule(user.id, "slack")
    await session.commit()
    await callback.answer(t(lang, "slack_disconnected"))

    scheduler = get_digest_scheduler()
    if scheduler and user:
        scheduler.unschedule_user_platform(user.id, "slack")

    if callback.message:
        await show_slack_screen(
            callback.message,
            state,
            session,
            lang,
            callback.from_user.id,
            from_user_action=True,
        )
