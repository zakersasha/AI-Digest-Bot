import asyncio

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.digest_ui import deliver_digest, run_with_digest_progress
from app.bot.keyboards import (
    CB_ACTION_MENU,
    CB_FREQ_BACK,
    CB_GMAIL_CONTINUE,
    CB_PLATFORM_GMAIL,
    CB_PLATFORM_LINKEDIN,
    CB_PLATFORM_TELEGRAM,
    CB_SCHEDULE_PREFIX,
    CB_TEST_DIGEST_PREFIX,
    back_to_menu_keyboard,
    frequency_keyboard,
)
from app.bot.platform_screens import (
    show_gmail_screen,
    show_linkedin_screen,
    show_platforms_menu,
    show_schedule_frequency,
    show_telegram_screen,
)
from app.bot.screen import edit_from_callback
from app.bot.time_flow import (
    DEFAULT_DELIVERY_HOUR,
    get_pending_hour,
    set_pending_hour,
    show_time_picker_callback,
)
from app.config import get_settings
from app.i18n import frequency_label, resolve_lang, t
from app.repositories.platform_settings_repository import PlatformSettingsRepository
from app.repositories.user_repository import UserRepository
from app.services.digest_service import DigestService
from app.services.platform_readiness import can_deliver_platform, is_platform_connected
from app.utils.logging import get_logger
from app.workers.digest_scheduler import get_digest_scheduler

logger = get_logger(__name__)

router = Router(name="platforms_menu")
_digest_locks: dict[int, asyncio.Lock] = {}


@router.callback_query(F.data == CB_ACTION_MENU)
async def cb_platforms_menu(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await callback.answer()
    if callback.message:
        await show_platforms_menu(callback.message, state, session, lang, callback.from_user.id)


@router.callback_query(F.data == CB_PLATFORM_TELEGRAM)
async def cb_open_telegram(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await callback.answer()
    if callback.message:
        await show_telegram_screen(callback.message, state, session, lang, callback.from_user.id)


@router.callback_query(F.data.in_({CB_PLATFORM_GMAIL, CB_GMAIL_CONTINUE}))
async def cb_open_gmail(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await callback.answer()
    if callback.message:
        await show_gmail_screen(
            callback.message,
            state,
            session,
            lang,
            callback.from_user.id,
            from_user_action=True,
        )


@router.callback_query(F.data == CB_PLATFORM_LINKEDIN)
async def cb_open_linkedin(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await show_linkedin_screen(callback, state, lang)


@router.callback_query(F.data.startswith(CB_SCHEDULE_PREFIX))
async def cb_start_schedule(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    platform = callback.data.removeprefix(CB_SCHEDULE_PREFIX)
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    if not await is_platform_connected(session, user, platform):
        await callback.answer(t(lang, "platform_connect_first"), show_alert=True)
        return

    await state.update_data(active_platform=platform)
    await callback.answer()
    await show_schedule_frequency(callback, state, lang, platform)


@router.callback_query(F.data.startswith("freq:"))
async def cb_frequency(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    code = callback.data.split(":")[1]
    lang = await resolve_lang(session, callback.from_user.id)
    data = await state.get_data()
    platform = data.get("scheduling_platform") or data.get("active_platform")
    if not platform:
        await callback.answer()
        return

    if code == "back":
        await callback.answer()
        if not callback.message:
            return
        if platform == "telegram":
            await show_telegram_screen(callback.message, state, session, lang, callback.from_user.id)
        elif platform == "gmail":
            await show_gmail_screen(
                callback.message,
                state,
                session,
                lang,
                callback.from_user.id,
                from_user_action=True,
            )
        return

    if code not in ("12h", "1d", "3d", "1w"):
        await callback.answer()
        return

    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    await state.update_data(scheduling_platform=platform)
    await PlatformSettingsRepository(session).set_frequency(user.id, platform, code)
    await session.commit()
    await callback.answer()
    await show_time_picker_callback(callback, state, lang, hour=DEFAULT_DELIVERY_HOUR)


@router.callback_query(F.data.startswith("time:"))
async def cb_time(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    data = await state.get_data()
    platform = data.get("scheduling_platform") or data.get("active_platform")
    if not platform:
        await callback.answer()
        return

    part = callback.data.split(":")[1]

    if part == "back":
        await callback.answer()
        await edit_from_callback(
            callback,
            state,
            t(lang, "step_frequency_platform", platform=t(lang, f"platform_{platform}")),
            frequency_keyboard(lang, platform=platform),
        )
        return

    if part == "noop":
        await callback.answer()
        return

    if part == "dec":
        hour = await get_pending_hour(state)
        await set_pending_hour(state, hour - 1)
        await callback.answer()
        await show_time_picker_callback(callback, state, lang)
        return

    if part == "inc":
        hour = await get_pending_hour(state)
        await set_pending_hour(state, hour + 1)
        await callback.answer()
        await show_time_picker_callback(callback, state, lang)
        return

    if part != "confirm":
        await callback.answer()
        return

    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    hour = await get_pending_hour(state)
    settings = get_settings()
    await PlatformSettingsRepository(session).set_delivery_time(user.id, platform, hour, 0)
    user.timezone = settings.default_timezone
    user.onboarding_complete = True
    await session.commit()
    await callback.answer(t(lang, "schedule_saved"))

    scheduler = get_digest_scheduler()
    if scheduler:
        await scheduler.schedule_user_platform(user.id, platform)

    if not callback.message:
        return

    if platform == "telegram":
        await show_telegram_screen(
            callback.message,
            state,
            session,
            lang,
            callback.from_user.id,
            status_line=t(lang, "schedule_saved"),
        )
    elif platform == "gmail":
        await show_gmail_screen(
            callback.message,
            state,
            session,
            lang,
            callback.from_user.id,
            status_line=t(lang, "schedule_saved"),
            from_user_action=True,
        )


@router.callback_query(F.data.startswith(CB_TEST_DIGEST_PREFIX))
async def cb_test_digest(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    digest_service: DigestService,
) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    platform = callback.data.removeprefix(CB_TEST_DIGEST_PREFIX)
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    ps = await PlatformSettingsRepository(session).get(user.id, platform)
    if not await can_deliver_platform(session, user, platform, ps):
        await callback.answer(t(lang, "platform_not_ready"), show_alert=True)
        return

    frequency = ps.digest_frequency if ps else "1d"
    lock = _digest_locks.setdefault(callback.from_user.id, asyncio.Lock())
    if lock.locked():
        await callback.answer(t(lang, "digest_in_progress"), show_alert=True)
        return

    await callback.answer()
    label = frequency_label(lang, frequency)
    await edit_from_callback(callback, state, t(lang, "digest_progress_fetch", label=label, dots="."), None)

    async with lock:
        try:

            async def _generate() -> str:
                return await digest_service.generate_for_platform(
                    user.id,
                    platform,
                    frequency,
                    lang,
                )

            content = await run_with_digest_progress(
                callback,
                state,
                lang,
                label,
                _generate,
                platform=platform,
            )
            await deliver_digest(callback, state, lang, content)
        except ValueError as exc:
            await edit_from_callback(callback, state, str(exc), back_to_menu_keyboard(lang))
        except RuntimeError as exc:
            await edit_from_callback(callback, state, str(exc), back_to_menu_keyboard(lang))
        except Exception:
            logger.exception("test_digest_failed", telegram_id=callback.from_user.id, platform=platform)
            await edit_from_callback(callback, state, t(lang, "digest_failed"), back_to_menu_keyboard(lang))
