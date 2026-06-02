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
    CB_ACTION_SCHEDULE,
    CB_ACTION_SETUP,
    CB_CH_DONE,
    CB_FREQ_BACK,
    CB_LANG_EN,
    CB_LANG_RU,
    CB_TIME_BACK,
    channels_keyboard,
    done_keyboard,
    frequency_keyboard,
    language_keyboard,
    main_menu_keyboard,
    time_keyboard,
)
from app.bot.states import OnboardingStates
from app.config import get_settings
from app.i18n import DEFAULT_LANG, frequency_label, resolve_lang, t
from app.repositories.catalog_repository import CatalogRepository
from app.repositories.source_repository import SourceRepository
from app.repositories.user_repository import UserRepository
from app.services.digest_service import DigestService
from app.utils.telegram import split_telegram_message

router = Router(name="onboarding")


async def _get_selected(state: FSMContext) -> set[int]:
    data = await state.get_data()
    raw = data.get("selected_channels", [])
    return set(raw)


async def _set_selected(state: FSMContext, selected: set[int]) -> None:
    await state.update_data(selected_channels=list(selected))


async def _show_welcome(message: Message, lang: str | None = None) -> None:
    text_lang = lang or DEFAULT_LANG
    await message.answer(t(text_lang, "welcome"), reply_markup=language_keyboard())


async def _show_channels(
    message: Message,
    session: AsyncSession,
    lang: str,
    selected: set[int],
    *,
    edit: bool = False,
) -> None:
    catalog = await CatalogRepository(session).list_active()
    text = t(lang, "step_channels", count=len(selected))
    markup = channels_keyboard(catalog, selected, lang)
    if edit:
        await message.edit_text(text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)


async def _show_main_menu(message: Message, lang: str, *, edit: bool = False) -> None:
    text = t(lang, "main_menu")
    markup = main_menu_keyboard(lang)
    if edit:
        await message.edit_text(text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)


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
        await _show_welcome(message)
        return

    if user.onboarding_complete:
        await _show_main_menu(message, user.language)
        return

    lang = user.language
    active = await SourceRepository(session).list_active_for_user(user.id)
    selected = {s.catalog_channel_id for s in active}
    await _set_selected(state, selected)

    if user.delivery_hour is not None and user.digest_frequency:
        await message.answer(
            _format_setup_summary(user, lang, len(selected)),
            reply_markup=done_keyboard(lang),
        )
    elif user.digest_frequency:
        settings = get_settings()
        await message.answer(
            t(lang, "step_time", timezone=settings.default_timezone),
            reply_markup=time_keyboard(lang),
        )
    elif selected:
        await message.answer(t(lang, "step_frequency"), reply_markup=frequency_keyboard(lang))
    else:
        await state.set_state(OnboardingStates.picking_channels)
        await _show_channels(message, session, lang, selected)


@router.callback_query(F.data.in_({CB_LANG_RU, CB_LANG_EN}))
async def cb_language(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = callback.data.split(":")[1]
    repo = UserRepository(session)
    user = await repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    await repo.set_language(callback.from_user.id, lang)
    await session.commit()
    await callback.answer()

    await callback.message.edit_text(t(lang, "welcome"))
    await state.set_state(OnboardingStates.picking_channels)
    await _set_selected(state, set())
    await _show_channels(callback.message, session, lang, set())


@router.callback_query(F.data.startswith("ch:toggle:"))
async def cb_toggle_channel(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    channel_id = int(callback.data.split(":")[2])
    selected = await _get_selected(state)
    if channel_id in selected:
        selected.remove(channel_id)
    else:
        selected.add(channel_id)
    await _set_selected(state, selected)
    await callback.answer()
    await _show_channels(callback.message, session, lang, selected, edit=True)


@router.callback_query(F.data == CB_CH_DONE)
async def cb_channels_done(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    selected = await _get_selected(state)
    if not selected:
        await callback.answer(t(lang, "pick_channel_first"), show_alert=True)
        return

    catalog = await CatalogRepository(session).list_active()
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    await SourceRepository(session).sync_user_selection(user.id, catalog, selected)
    await session.commit()

    onboarding = await state.get_state() == OnboardingStates.picking_channels.state
    await state.clear()
    await callback.answer(t(lang, "channels_saved", count=len(selected)))

    if onboarding:
        await callback.message.edit_text(t(lang, "step_frequency"), reply_markup=frequency_keyboard(lang))
    else:
        await callback.message.edit_text(t(lang, "main_menu"), reply_markup=main_menu_keyboard(lang))


@router.callback_query(F.data.startswith("freq:"))
async def cb_frequency(callback: CallbackQuery, session: AsyncSession) -> None:
    code = callback.data.split(":")[1]
    if code not in ("12h", "1d", "3d", "1w"):
        await callback.answer()
        return

    lang = await resolve_lang(session, callback.from_user.id)
    await UserRepository(session).set_frequency(callback.from_user.id, code)
    await session.commit()
    await callback.answer()

    settings = get_settings()
    await callback.message.edit_text(
        t(lang, "step_time", timezone=settings.default_timezone),
        reply_markup=time_keyboard(lang),
    )


@router.callback_query(F.data == CB_FREQ_BACK)
async def cb_freq_back(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await callback.answer()
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        return
    sources = await SourceRepository(session).list_active_for_user(user.id)
    selected = {s.catalog_channel_id for s in sources}
    await _set_selected(state, selected)
    await state.set_state(OnboardingStates.picking_channels)
    await _show_channels(callback.message, session, lang, selected, edit=True)


@router.callback_query(F.data.startswith("time:"))
async def cb_time(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    part = callback.data.split(":")[1]

    if part == "back":
        await callback.answer()
        await callback.message.edit_text(
            t(lang, "step_frequency"),
            reply_markup=frequency_keyboard(lang),
        )
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
    await callback.message.edit_text(
        _format_setup_summary(user, lang, count),
        reply_markup=done_keyboard(lang),
    )


@router.callback_query(F.data == CB_ACTION_CHANNELS)
async def cb_menu_channels(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    sources = await SourceRepository(session).list_active_for_user(user.id)
    selected = {s.catalog_channel_id for s in sources}
    await _set_selected(state, selected)
    await state.set_state(OnboardingStates.picking_channels)
    await callback.answer()
    await _show_channels(callback.message, session, lang, selected, edit=True)


@router.callback_query(F.data == CB_ACTION_SCHEDULE)
async def cb_menu_schedule(callback: CallbackQuery, session: AsyncSession) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user or not user.onboarding_complete:
        await callback.answer()
        return

    last = t(lang, "last_never")
    if user.last_digest_at:
        last = user.last_digest_at.strftime("%d.%m.%Y %H:%M")

    freq = t(lang, f"freq_{user.digest_frequency}")
    time_str = _format_time(user.delivery_hour or 0, user.delivery_minute or 0)
    text = t(
        lang,
        "schedule_summary",
        frequency=freq,
        time=time_str,
        timezone=user.timezone,
        last=last,
    )
    await callback.answer()
    await callback.message.edit_text(text, reply_markup=main_menu_keyboard(lang))


@router.callback_query(F.data == CB_ACTION_SETUP)
async def cb_menu_setup(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    await UserRepository(session).reset_onboarding(callback.from_user.id)
    await session.commit()
    await callback.answer()

    sources = await SourceRepository(session).list_active_for_user(user.id)
    selected = {s.catalog_channel_id for s in sources} or set()
    await _set_selected(state, selected)
    await state.set_state(OnboardingStates.picking_channels)
    await _show_channels(callback.message, session, lang, selected, edit=True)


@router.callback_query(F.data == CB_ACTION_DIGEST)
async def cb_digest_now(
    callback: CallbackQuery,
    session: AsyncSession,
    digest_service: DigestService,
) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user or not user.onboarding_complete or not user.digest_frequency:
        await callback.answer(t(lang, "pick_channel_first"), show_alert=True)
        return

    await callback.answer()
    label = frequency_label(lang, user.digest_frequency)
    status = await callback.message.answer(t(lang, "digest_generating", label=label))

    try:
        content = await digest_service.generate_for_user(
            user.id, user.digest_frequency, lang
        )
        await status.delete()
        for part in split_telegram_message(content):
            try:
                await callback.message.answer(part, parse_mode=ParseMode.MARKDOWN)
            except TelegramBadRequest:
                await callback.message.answer(part)
        await callback.message.answer(
            t(lang, "digest_delivered_hint"),
            reply_markup=main_menu_keyboard(lang),
        )
    except ValueError as exc:
        await status.edit_text(f"ℹ️ {exc}")
    except RuntimeError as exc:
        await status.edit_text(str(exc))
    except Exception:
        await status.edit_text(t(lang, "digest_failed"))


@router.message(Command("menu"))
async def cmd_menu(message: Message, session: AsyncSession) -> None:
    lang = await resolve_lang(session, message.from_user.id)
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    if user and user.onboarding_complete:
        await _show_main_menu(message, lang)
    else:
        await _show_welcome(message, lang)
