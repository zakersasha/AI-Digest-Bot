import asyncio

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import (
    CB_ACTION_CHANNELS,
    CB_ACTION_DIGEST,
    CB_ACTION_MENU,
    CB_ACTION_SCHEDULE,
    CB_ACTION_SETUP,
    CB_LANG_EN,
    CB_LANG_RU,
    back_to_menu_keyboard,
    done_keyboard,
    frequency_keyboard,
    language_keyboard,
    main_menu_keyboard,
)
from app.bot.digest_ui import deliver_digest, run_with_digest_progress
from app.bot.screen import edit_from_callback, open_screen
from app.bot.sources_flow import show_sources_manage, show_sources_onboarding
from app.bot.time_flow import (
    DEFAULT_DELIVERY_HOUR,
    get_pending_hour,
    set_pending_hour,
    show_time_picker,
    show_time_picker_callback,
)
from app.config import get_settings
from app.i18n import DEFAULT_LANG, frequency_label, resolve_lang, t
from app.repositories.user_repository import UserRepository
from app.services.digest_service import DigestService
from app.services.user_sources import digest_platform, has_any_source, has_gmail
from app.repositories.source_repository import SourceRepository
from app.utils.logging import get_logger
from app.workers.digest_scheduler import get_digest_scheduler

logger = get_logger(__name__)

_digest_user_locks: dict[int, asyncio.Lock] = {}

router = Router(name="onboarding")


def _format_time(hour: int, minute: int) -> str:
    return f"{hour:02d}:{minute:02d}"


async def _format_setup_summary(session: AsyncSession, user, lang: str) -> str:
    channels = await SourceRepository(session).count_active(user.id)
    gmail = t(lang, "gmail_status_linked", email=user.gmail_email or "Gmail") if has_gmail(user) else "—"
    freq = t(lang, f"freq_{user.digest_frequency}") if user.digest_frequency else "—"
    time_str = _format_time(user.delivery_hour or 0, user.delivery_minute or 0)
    return t(
        lang,
        "setup_done",
        channels=str(channels),
        gmail=gmail,
        frequency=freq,
        time=time_str,
    )


async def _resume_onboarding(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user,
    lang: str,
) -> None:
    if user.delivery_hour is not None and user.digest_frequency:
        await open_screen(
            message,
            state,
            await _format_setup_summary(session, user, lang),
            done_keyboard(lang),
        )
        return

    if user.digest_frequency:
        await show_time_picker(message, state, lang, hour=DEFAULT_DELIVERY_HOUR)
        return

    await show_sources_onboarding(message, state, session, lang, message.from_user.id)


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    repo = UserRepository(session)
    user = await repo.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
    )
    await session.commit()

    if not user.language:
        await open_screen(message, state, t(DEFAULT_LANG, "welcome"), language_keyboard())
        return

    lang = user.language
    if user.onboarding_complete:
        await open_screen(message, state, t(lang, "main_menu"), main_menu_keyboard(lang))
        return

    await _resume_onboarding(message, state, session, user, lang)


@router.callback_query(F.data.in_({CB_LANG_RU, CB_LANG_EN}))
async def cb_language(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = callback.data.split(":")[1]
    await UserRepository(session).set_language(callback.from_user.id, lang)
    await session.commit()
    await callback.answer()
    if callback.message:
        await show_sources_onboarding(
            callback.message,
            state,
            session,
            lang,
            callback.from_user.id,
        )


@router.callback_query(F.data.startswith("freq:"))
async def cb_frequency(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    code = callback.data.split(":")[1]
    lang = await resolve_lang(session, callback.from_user.id)

    if code == "back":
        await callback.answer()
        if callback.message:
            user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
            onboarding = bool(user and not user.onboarding_complete)
            if onboarding:
                await show_sources_onboarding(
                    callback.message, state, session, lang, callback.from_user.id
                )
            else:
                await show_sources_manage(
                    callback.message, state, session, lang, callback.from_user.id
                )
        return

    if code not in ("12h", "1d", "3d", "1w"):
        await callback.answer()
        return

    await UserRepository(session).set_frequency(callback.from_user.id, code)
    await session.commit()
    await callback.answer()
    await show_time_picker_callback(callback, state, lang, hour=DEFAULT_DELIVERY_HOUR)


@router.callback_query(F.data.startswith("time:"))
async def cb_time(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    part = callback.data.split(":")[1]

    if part == "back":
        await callback.answer()
        await edit_from_callback(callback, state, t(lang, "step_frequency"), frequency_keyboard(lang))
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

    hour = await get_pending_hour(state)
    settings = get_settings()
    repo = UserRepository(session)
    user = await repo.get_by_telegram_id(callback.from_user.id)
    if not user or not await has_any_source(session, user):
        await callback.answer(t(lang, "pick_source_first"), show_alert=True)
        return

    await repo.set_delivery_time(
        callback.from_user.id,
        hour,
        0,
        timezone=settings.default_timezone,
    )
    user = await repo.complete_onboarding(callback.from_user.id)
    await session.commit()
    await state.clear()
    await callback.answer()

    if not user:
        return

    scheduler = get_digest_scheduler()
    if scheduler:
        scheduler.schedule_user(user)

    await edit_from_callback(
        callback,
        state,
        await _format_setup_summary(session, user, lang),
        done_keyboard(lang),
    )


@router.callback_query(F.data == CB_ACTION_MENU)
async def cb_main_menu(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await state.clear()
    await callback.answer()
    await edit_from_callback(callback, state, t(lang, "main_menu"), main_menu_keyboard(lang))


@router.callback_query(F.data == CB_ACTION_CHANNELS)
async def cb_menu_sources(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await callback.answer()
    if callback.message:
        await show_sources_manage(callback.message, state, session, lang, callback.from_user.id)


@router.callback_query(F.data == CB_ACTION_SCHEDULE)
async def cb_menu_schedule(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user or not user.onboarding_complete:
        await callback.answer()
        return

    channels = await SourceRepository(session).count_active(user.id)
    gmail_line = user.gmail_email if has_gmail(user) else "—"

    last = t(lang, "last_never")
    if user.last_digest_at:
        last = user.last_digest_at.strftime("%d.%m.%Y %H:%M")

    text = t(
        lang,
        "schedule_summary",
        frequency=t(lang, f"freq_{user.digest_frequency}"),
        time=_format_time(user.delivery_hour or 0, user.delivery_minute or 0),
        timezone=user.timezone,
        last=last,
        channels=str(channels),
        gmail=gmail_line,
    )
    await callback.answer()
    await edit_from_callback(callback, state, text, main_menu_keyboard(lang))


@router.callback_query(F.data == CB_ACTION_SETUP)
async def cb_menu_setup(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if user:
        scheduler = get_digest_scheduler()
        if scheduler:
            scheduler.unschedule_user(user.id)
    await UserRepository(session).reset_onboarding(callback.from_user.id)
    await session.commit()
    await callback.answer()
    if callback.message:
        await show_sources_onboarding(
            callback.message,
            state,
            session,
            lang,
            callback.from_user.id,
        )


@router.callback_query(F.data == CB_ACTION_DIGEST)
async def cb_digest_now(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    digest_service: DigestService,
) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user or not user.onboarding_complete or not user.digest_frequency:
        await callback.answer(t(lang, "pick_source_first"), show_alert=True)
        return

    if not await has_any_source(session, user):
        await callback.answer(t(lang, "pick_source_first"), show_alert=True)
        return

    lock = _digest_user_locks.setdefault(callback.from_user.id, asyncio.Lock())
    if lock.locked():
        await callback.answer(t(lang, "digest_in_progress"), show_alert=True)
        return

    channels = await SourceRepository(session).count_active(user.id)
    platform = digest_platform(channels > 0, has_gmail(user))

    await callback.answer()
    label = frequency_label(lang, user.digest_frequency)
    await edit_from_callback(callback, state, t(lang, "digest_progress_fetch", label=label, dots="."), None)

    async with lock:
        try:

            async def _generate() -> str:
                return await digest_service.generate_for_user(
                    user.id,
                    user.digest_frequency,
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
            await edit_from_callback(callback, state, f"ℹ️ {exc}", back_to_menu_keyboard(lang))
        except RuntimeError as exc:
            await edit_from_callback(callback, state, str(exc), back_to_menu_keyboard(lang))
        except Exception:
            logger.exception("digest_handler_failed", telegram_id=callback.from_user.id)
            await edit_from_callback(
                callback,
                state,
                t(lang, "digest_failed"),
                back_to_menu_keyboard(lang),
            )


@router.message(Command("menu"))
async def cmd_menu(message: Message, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, message.from_user.id)
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    if user and user.onboarding_complete:
        await open_screen(message, state, t(lang, "main_menu"), main_menu_keyboard(lang))
    else:
        await open_screen(message, state, t(DEFAULT_LANG, "welcome"), language_keyboard())
