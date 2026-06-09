import re

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.channel_picker import refresh_picker_callback, show_channel_picker, toggle_channel
from app.bot.keyboards import (
    CB_TG_CONNECT,
    CB_TG_DISCONNECT,
    CB_TG_PICK,
    CB_TG_PICK_DONE,
    CB_TG_PICK_PAGE_PREFIX,
    CB_TG_PICK_TOGGLE_PREFIX,
)
from app.bot.platform_screens import show_telegram_screen
from app.bot.states import OnboardingStates
from app.bot.telethon_notify import notify_telethon_connected
from app.config import get_settings
from app.i18n import resolve_lang, t
from app.repositories.user_repository import UserRepository
from app.services.telethon_link import (
    PasswordRequired,
    TelethonLoginPending,
    finish_2fa_login,
    finish_phone_login,
    normalize_phone,
    start_phone_login,
)

router = Router(name="telethon_auth")

_CODE_RE = re.compile(r"^\d{4,8}$")


def _phone_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "btn_share_phone"), request_contact=True)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def _pending_from_state(data: dict) -> TelethonLoginPending | None:
    phone = data.get("tg_login_phone")
    partial = data.get("tg_login_session")
    code_hash = data.get("tg_login_hash")
    if phone and partial and code_hash:
        return TelethonLoginPending(phone=phone, partial_session=partial, phone_code_hash=code_hash)
    return None


@router.callback_query(F.data == CB_TG_CONNECT)
async def cb_tg_connect(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await state.set_state(OnboardingStates.waiting_telegram_phone)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            t(lang, "tg_connect_phone_prompt"),
            reply_markup=_phone_keyboard(lang),
        )


@router.callback_query(F.data == CB_TG_DISCONNECT)
async def cb_tg_disconnect(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await UserRepository(session).clear_telethon_session(callback.from_user.id)
    await session.commit()
    await callback.answer(t(lang, "tg_disconnected"))
    if callback.message:
        await show_telegram_screen(
            callback.message,
            state,
            session,
            lang,
            callback.from_user.id,
            from_user_action=True,
        )


@router.callback_query(F.data == CB_TG_PICK)
async def cb_tg_pick(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user or not UserRepository(session).has_telethon(user):
        await callback.answer(t(lang, "tg_not_linked"), show_alert=True)
        return
    if callback.message:
        try:
            await show_channel_picker(callback.message, state, session, lang, callback.from_user.id)
            await callback.answer()
        except ValueError as exc:
            await callback.answer(t(lang, str(exc)), show_alert=True)
            return
    else:
        await callback.answer()


@router.callback_query(F.data == CB_TG_PICK_DONE)
async def cb_tg_pick_done(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await callback.answer()
    if callback.message:
        await show_telegram_screen(
            callback.message,
            state,
            session,
            lang,
            callback.from_user.id,
            from_user_action=True,
        )


@router.callback_query(F.data.startswith(CB_TG_PICK_PAGE_PREFIX))
async def cb_tg_pick_page(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    page = int(callback.data.removeprefix(CB_TG_PICK_PAGE_PREFIX))
    await callback.answer()
    await refresh_picker_callback(callback, state, session, lang, page)


@router.callback_query(F.data.startswith(CB_TG_PICK_TOGGLE_PREFIX))
async def cb_tg_pick_toggle(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    username = callback.data.removeprefix(CB_TG_PICK_TOGGLE_PREFIX)
    await toggle_channel(callback, session, lang, username)
    data = await state.get_data()
    page = int(data.get("tg_picker_page", 0))
    await callback.answer()
    await refresh_picker_callback(callback, state, session, lang, page)


@router.callback_query(F.data == "tg:noop")
async def cb_tg_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.message(StateFilter(OnboardingStates.waiting_telegram_phone), F.contact)
async def msg_telegram_contact(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if not message.contact or message.contact.user_id != message.from_user.id:
        lang = await resolve_lang(session, message.from_user.id)
        await message.answer(t(lang, "tg_contact_invalid"), reply_markup=ReplyKeyboardRemove())
        return
    await _handle_phone(message, state, session, message.contact.phone_number or "")


@router.message(StateFilter(OnboardingStates.waiting_telegram_phone), F.text, ~F.text.startswith("/"))
async def msg_telegram_phone_text(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await _handle_phone(message, state, session, message.text or "")


async def _handle_phone(message: Message, state: FSMContext, session: AsyncSession, raw_phone: str) -> None:
    lang = await resolve_lang(session, message.from_user.id)
    settings = get_settings()

    try:
        phone = normalize_phone(raw_phone)
        pending = await start_phone_login(phone, settings)
    except ValueError as exc:
        key = str(exc)
        if key.startswith("flood_wait:"):
            seconds = key.split(":", 1)[1]
            await message.answer(t(lang, "tg_flood_wait", seconds=seconds), reply_markup=ReplyKeyboardRemove())
            return
        await message.answer(t(lang, "tg_invalid_phone"), reply_markup=ReplyKeyboardRemove())
        return

    await state.update_data(
        tg_login_phone=pending.phone,
        tg_login_session=pending.partial_session,
        tg_login_hash=pending.phone_code_hash,
    )
    await state.set_state(OnboardingStates.waiting_telegram_code)
    await message.answer(t(lang, "tg_code_prompt"), reply_markup=ReplyKeyboardRemove())


@router.message(StateFilter(OnboardingStates.waiting_telegram_code), F.text, ~F.text.startswith("/"))
async def msg_telegram_code(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    lang = await resolve_lang(session, message.from_user.id)
    code = (message.text or "").strip().replace(" ", "")
    if not _CODE_RE.match(code):
        await message.answer(t(lang, "tg_invalid_code"))
        return

    data = await state.get_data()
    pending = _pending_from_state(data)
    if not pending:
        await state.clear()
        await message.answer(t(lang, "tg_login_expired"))
        return

    settings = get_settings()
    try:
        session_string = await finish_phone_login(pending, code, settings)
    except PasswordRequired as exc:
        await state.update_data(tg_login_session=exc.partial_session)
        await state.set_state(OnboardingStates.waiting_telegram_2fa)
        await message.answer(t(lang, "tg_2fa_prompt"))
        return
    except ValueError as exc:
        key = str(exc)
        if key == "invalid_code":
            await message.answer(t(lang, "tg_invalid_code"))
            return
        if key == "code_expired":
            await state.set_state(OnboardingStates.waiting_telegram_phone)
            await message.answer(t(lang, "tg_code_expired"))
            return
        if key.startswith("flood_wait:"):
            seconds = key.split(":", 1)[1]
            await message.answer(t(lang, "tg_flood_wait", seconds=seconds))
            return
        await message.answer(t(lang, "tg_login_failed"))
        return

    await _save_session(message, state, session, lang, pending.phone, session_string)


@router.message(StateFilter(OnboardingStates.waiting_telegram_2fa), F.text, ~F.text.startswith("/"))
async def msg_telegram_2fa(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    lang = await resolve_lang(session, message.from_user.id)
    data = await state.get_data()
    pending = _pending_from_state(data)
    if not pending:
        await state.clear()
        await message.answer(t(lang, "tg_login_expired"))
        return

    partial = data.get("tg_login_session")
    if not partial:
        await message.answer(t(lang, "tg_login_expired"))
        return

    settings = get_settings()
    try:
        session_string = await finish_2fa_login(partial, message.text or "", settings)
    except ValueError:
        await message.answer(t(lang, "tg_2fa_invalid"))
        return

    await _save_session(message, state, session, lang, pending.phone, session_string)


async def _save_session(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
    phone: str,
    session_string: str,
) -> None:
    repo = UserRepository(session)
    await repo.get_or_create(message.from_user.id, message.from_user.username)
    saved = await repo.save_telethon_session(message.from_user.id, session_string, phone)
    if not saved:
        await message.answer(t(lang, "tg_login_failed"))
        return
    await session.commit()

    await state.update_data(
        tg_login_phone=None,
        tg_login_session=None,
        tg_login_hash=None,
    )
    await state.set_state(OnboardingStates.managing_sources)

    try:
        await message.delete()
    except Exception:
        pass

    await notify_telethon_connected(message.bot, message.from_user.id, lang, phone)
    await show_telegram_screen(
        message,
        state,
        session,
        lang,
        message.from_user.id,
        status_line=t(lang, "tg_linked", phone=phone),
    )
