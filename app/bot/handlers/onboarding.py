from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
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
    CB_CH_DONE,
    CB_CH_PAGE,
    CB_CH_REFRESH,
    CB_FREQ_BACK,
    CB_LANG_EN,
    CB_LANG_RU,
    CB_TIME_BACK,
    back_to_menu_keyboard,
    done_keyboard,
    frequency_keyboard,
    language_keyboard,
    main_menu_keyboard,
    time_keyboard,
)
from app.bot.screen import edit_from_callback, open_screen
from app.bot.states import OnboardingStates
from app.bot.subscription_flow import (
    channels_from_state,
    get_selected,
    proceed_after_language,
    render_channels_page,
    set_selected,
    show_channels_loading,
    show_connect_step,
)
from app.config import get_settings
from app.i18n import DEFAULT_LANG, frequency_label, resolve_lang, t
from app.repositories.source_repository import SourceRepository
from app.repositories.user_repository import UserRepository
from app.services.digest_service import DigestService
from app.utils.telegram import split_telegram_message

router = Router(name="onboarding")


def _format_time(hour: int, minute: int) -> str:
    return f"{hour:02d}:{minute:02d}"


def _format_setup_summary(user, lang: str, channel_count: int) -> str:
    freq = t(lang, f"freq_{user.digest_frequency}") if user.digest_frequency else "—"
    time_str = _format_time(user.delivery_hour or 0, user.delivery_minute or 0)
    return t(
        lang,
        "setup_done",
        channels=str(channel_count),
        frequency=freq,
        time=time_str,
    )


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

    await set_selected(state, await SourceRepository(session).active_usernames(user.id))
    tid = message.from_user.id
    if user.delivery_hour is not None and user.digest_frequency:
        await open_screen(
            message,
            state,
            _format_setup_summary(user, lang, await SourceRepository(session).count_active(user.id)),
            done_keyboard(lang),
        )
    elif user.digest_frequency:
        settings = get_settings()
        await open_screen(
            message,
            state,
            t(lang, "step_time", timezone=settings.default_timezone),
            time_keyboard(lang),
        )
    elif await SourceRepository(session).count_active(user.id) > 0:
        await open_screen(message, state, t(lang, "step_frequency"), frequency_keyboard(lang))
    elif user.telethon_session_encrypted:
        await show_channels_loading(message, state, session, lang, tid, await get_selected(state))
    else:
        await show_connect_step(message, state, lang)


@router.callback_query(F.data.in_({CB_LANG_RU, CB_LANG_EN}))
async def cb_language(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = callback.data.split(":")[1]
    await UserRepository(session).set_language(callback.from_user.id, lang)
    await session.commit()
    await proceed_after_language(callback, state, session, lang)


@router.callback_query(F.data.startswith("ch:toggle:"))
async def cb_toggle_channel(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    key = callback.data.split(":")[2]
    data = await state.get_data()
    subscriptions = channels_from_state(data)
    username = next(
        (ch.username for ch in subscriptions if ch.username.lstrip("@").lower() == key),
        f"@{key}",
    )
    selected = await get_selected(state)
    if username in selected:
        selected.remove(username)
    else:
        selected.add(username)
    await set_selected(state, selected)
    await callback.answer()
    await render_channels_page(callback, state, lang, data.get("ch_page", 0))


@router.callback_query(F.data == "ch:noop")
async def cb_channels_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data.startswith(f"{CB_CH_PAGE}:"))
async def cb_channels_page(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    page = int(callback.data.split(":")[1])
    await callback.answer()
    await render_channels_page(callback, state, lang, page)


@router.callback_query(F.data == CB_CH_REFRESH)
async def cb_channels_refresh(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    selected = await get_selected(state)
    await callback.answer(t(lang, "channels_refreshed"))
    if callback.message:
        await show_channels_loading(
            callback.message, state, session, lang, callback.from_user.id, selected
        )


@router.callback_query(F.data == CB_CH_DONE)
async def cb_channels_done(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    selected = await get_selected(state)
    if not selected:
        await callback.answer(t(lang, "pick_channel_first"), show_alert=True)
        return

    data = await state.get_data()
    subscriptions = channels_from_state(data)
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    await SourceRepository(session).sync_subscriptions(user.id, subscriptions, selected)
    await session.commit()

    onboarding = await state.get_state() == OnboardingStates.picking_channels.state
    await callback.answer(t(lang, "channels_saved", count=len(selected)))

    if onboarding:
        await state.clear()
        await state.update_data(
            subscriptions=data.get("subscriptions"),
            selected_usernames=list(selected),
        )
        await edit_from_callback(callback, state, t(lang, "step_frequency"), frequency_keyboard(lang))
    else:
        await edit_from_callback(callback, state, t(lang, "main_menu"), main_menu_keyboard(lang))


@router.callback_query(F.data.startswith("freq:"))
async def cb_frequency(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    code = callback.data.split(":")[1]
    if code not in ("12h", "1d", "3d", "1w"):
        await callback.answer()
        return

    lang = await resolve_lang(session, callback.from_user.id)
    await UserRepository(session).set_frequency(callback.from_user.id, code)
    await session.commit()
    await callback.answer()

    settings = get_settings()
    await edit_from_callback(
        callback,
        state,
        t(lang, "step_time", timezone=settings.default_timezone),
        time_keyboard(lang),
    )


@router.callback_query(F.data == CB_FREQ_BACK)
async def cb_freq_back(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await callback.answer()
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if user:
        await set_selected(state, await SourceRepository(session).active_usernames(user.id))
    await state.set_state(OnboardingStates.picking_channels)
    if callback.message:
        data = await state.get_data()
        if data.get("subscriptions"):
            await render_channels_page(callback, state, lang, data.get("ch_page", 0))
        else:
            await show_channels_loading(
                callback.message, state, session, lang, callback.from_user.id, await get_selected(state)
            )


@router.callback_query(F.data.startswith("time:"))
async def cb_time(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    part = callback.data.split(":")[1]

    if part == "back":
        await callback.answer()
        await edit_from_callback(callback, state, t(lang, "step_frequency"), frequency_keyboard(lang))
        return

    hour = int(part)
    settings = get_settings()
    repo = UserRepository(session)
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

    count = await SourceRepository(session).count_active(user.id)
    await edit_from_callback(
        callback,
        state,
        _format_setup_summary(user, lang, count),
        done_keyboard(lang),
    )


@router.callback_query(F.data == CB_ACTION_MENU)
async def cb_main_menu(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await callback.answer()
    await edit_from_callback(callback, state, t(lang, "main_menu"), main_menu_keyboard(lang))


@router.callback_query(F.data == CB_ACTION_CHANNELS)
async def cb_menu_channels(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if user:
        await set_selected(state, await SourceRepository(session).active_usernames(user.id))
    await state.set_state(OnboardingStates.picking_channels)
    await callback.answer()
    if callback.message:
        await show_channels_loading(
            callback.message, state, session, lang, callback.from_user.id, await get_selected(state)
        )


@router.callback_query(F.data == CB_ACTION_SCHEDULE)
async def cb_menu_schedule(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user or not user.onboarding_complete:
        await callback.answer()
        return

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
    )
    await callback.answer()
    await edit_from_callback(callback, state, text, main_menu_keyboard(lang))


@router.callback_query(F.data == CB_ACTION_SETUP)
async def cb_menu_setup(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await UserRepository(session).reset_onboarding(callback.from_user.id)
    await session.commit()
    await callback.answer()
    await set_selected(state, set())
    await state.set_state(OnboardingStates.picking_channels)
    if callback.message:
        user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
        if user and user.telethon_session_encrypted:
            await show_channels_loading(callback.message, state, session, lang, callback.from_user.id, set())
        else:
            await show_connect_step(callback.message, state, lang)


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
        await callback.answer(t(lang, "pick_channel_first"), show_alert=True)
        return
    if not user.telethon_session_encrypted:
        await callback.answer(t(lang, "telegram_not_linked"), show_alert=True)
        return

    await callback.answer()
    label = frequency_label(lang, user.digest_frequency)
    await edit_from_callback(callback, state, t(lang, "digest_generating", label=label), None)

    try:
        content = await digest_service.generate_for_user(user.id, user.digest_frequency, lang)
        parts = split_telegram_message(content)
        first = parts[0]
        if len(parts) > 1:
            first += f"\n\n_{t(lang, 'digest_truncated')}_"
        try:
            await edit_from_callback(
                callback,
                state,
                first,
                back_to_menu_keyboard(lang),
                parse_mode=ParseMode.MARKDOWN,
            )
        except TelegramBadRequest:
            await edit_from_callback(
                callback,
                state,
                parts[0],
                back_to_menu_keyboard(lang),
                parse_mode=None,
            )
    except ValueError as exc:
        await edit_from_callback(callback, state, f"ℹ️ {exc}", back_to_menu_keyboard(lang))
    except RuntimeError as exc:
        await edit_from_callback(callback, state, str(exc), back_to_menu_keyboard(lang))
    except Exception:
        await edit_from_callback(callback, state, t(lang, "digest_failed"), back_to_menu_keyboard(lang))


@router.message(Command("menu"))
async def cmd_menu(message: Message, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, message.from_user.id)
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    if user and user.onboarding_complete:
        await open_screen(message, state, t(lang, "main_menu"), main_menu_keyboard(lang))
    else:
        await open_screen(message, state, t(DEFAULT_LANG, "welcome"), language_keyboard())
