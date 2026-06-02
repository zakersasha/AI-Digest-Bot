from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.connect_step import hide_phone_keyboard, show_connect_step
from app.bot.keyboards import code_keyboard
from app.bot.screen import bind_screen, edit_screen, replace_screen
from app.bot.states import LoginStates
from app.config import get_settings
from app.i18n import resolve_lang, t
from app.repositories.user_repository import UserRepository
from app.services.telethon_auth import (
    cancel_login,
    complete_login,
    get_pending_phone,
    is_plausible_phone,
    looks_like_sms_code,
    normalize_code,
    resend_login_code,
    start_login,
)

router = Router(name="login")


async def _finish_login(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
) -> None:
    from app.bot.subscription_flow import show_channels_loading

    data = await state.get_data()
    chat_id = data.get("screen_chat_id")
    msg_id = data.get("screen_message_id")
    if chat_id and msg_id:
        try:
            screen = await message.bot.edit_message_text(
                t(lang, "channels_loading"),
                chat_id=chat_id,
                message_id=msg_id,
            )
            await bind_screen(state, screen)
        except TelegramBadRequest:
            await replace_screen(message, state, t(lang, "channels_loading"), None)
    await show_channels_loading(
        message, state, session, lang, message.from_user.id, set()
    )


async def _advance_to_code_step(
    message: Message,
    state: FSMContext,
    lang: str,
    phone: str,
) -> None:
    await state.update_data(login_phone=phone, login_code_pending=True)
    await state.set_state(LoginStates.waiting_code)
    await edit_screen(
        message,
        state,
        t(lang, "step_code", phone=phone),
        code_keyboard(lang),
    )


async def _submit_phone(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    raw_phone: str,
) -> None:
    lang = await resolve_lang(session, message.from_user.id)

    if looks_like_sms_code(raw_phone):
        await message.answer(t(lang, "login_wait_for_code_screen"))
        return
    if not is_plausible_phone(raw_phone):
        await message.answer(t(lang, "invalid_phone_format"))
        return

    data = await state.get_data()
    if data.get("login_in_progress"):
        return

    await state.update_data(login_in_progress=True)
    await hide_phone_keyboard(message)
    try:
        await message.delete()
    except Exception:
        pass

    await state.set_state(LoginStates.sending_code)
    await replace_screen(message, state, t(lang, "login_connecting"), None)

    settings = get_settings()
    try:
        sent = await start_login(message.from_user.id, raw_phone, settings)
    except ValueError as exc:
        await message.answer(f"❌ {exc}")
        await state.update_data(login_in_progress=False)
        await show_connect_step(message, state, lang)
        return
    finally:
        await state.update_data(login_in_progress=False)

    await _advance_to_code_step(message, state, lang, sent.phone)


@router.callback_query(F.data == "auth:connect")
async def cb_auth_connect(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await cancel_login(callback.from_user.id)
    await state.update_data(login_in_progress=False)
    await callback.answer()
    if callback.message:
        await show_connect_step(callback.message, state, lang)


@router.message(LoginStates.sending_code, F.text)
async def login_sending_wait(message: Message, session: AsyncSession) -> None:
    lang = await resolve_lang(session, message.from_user.id)
    await message.answer(t(lang, "login_wait"))


@router.message(LoginStates.waiting_phone, F.contact)
async def login_phone_contact(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if not message.contact:
        return
    if message.contact.user_id != message.from_user.id:
        lang = await resolve_lang(session, message.from_user.id)
        await message.answer(t(lang, "contact_must_be_yours"))
        return

    phone = message.contact.phone_number
    if not phone:
        return
    await _submit_phone(message, state, session, phone)


@router.message(LoginStates.waiting_phone, F.text)
async def login_phone_text(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if message.text and message.text.startswith("/"):
        return
    await _submit_phone(message, state, session, message.text or "")


@router.message(LoginStates.waiting_code, F.text)
async def login_code(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    lang = await resolve_lang(session, message.from_user.id)
    data = await state.get_data()
    phone = data.get("login_phone") or get_pending_phone(message.from_user.id)
    if not phone:
        await show_connect_step(message, state, lang)
        return

    code_text = normalize_code(message.text or "")
    if not code_text or len(code_text) < 4:
        await message.answer(t(lang, "invalid_code_format"))
        return

    try:
        await message.delete()
    except Exception:
        pass

    settings = get_settings()
    try:
        session_string = await complete_login(message.from_user.id, code_text, settings)
    except ValueError as exc:
        msg = str(exc)
        if msg == "2FA_REQUIRED":
            await state.set_state(LoginStates.waiting_2fa)
            await edit_screen(message, state, t(lang, "step_2fa"), code_keyboard(lang))
            return
        if "new code was sent" in msg.lower():
            await edit_screen(
                message,
                state,
                t(lang, "step_code", phone=phone) + "\n\n" + t(lang, "code_use_latest"),
                code_keyboard(lang),
            )
        elif "expired" in msg.lower() and "share" in msg.lower():
            await show_connect_step(message, state, lang)
        await message.answer(f"❌ {msg}")
        return

    await UserRepository(session).save_telethon_session(
        message.from_user.id, session_string, phone
    )
    await session.commit()
    await state.set_state(None)
    await _finish_login(message, state, session, lang)


@router.message(LoginStates.waiting_2fa, F.text)
async def login_2fa(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    lang = await resolve_lang(session, message.from_user.id)
    data = await state.get_data()
    phone = data.get("login_phone") or get_pending_phone(message.from_user.id)
    settings = get_settings()

    try:
        session_string = await complete_login(
            message.from_user.id,
            "",
            settings,
            password=message.text or "",
        )
    except ValueError as exc:
        await message.answer(f"❌ {exc}")
        return

    await UserRepository(session).save_telethon_session(
        message.from_user.id, session_string, phone or ""
    )
    await session.commit()
    await state.set_state(None)
    await _finish_login(message, state, session, lang)


@router.callback_query(F.data == "auth:resend")
async def cb_auth_resend(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    data = await state.get_data()
    phone = data.get("login_phone") or get_pending_phone(callback.from_user.id)
    if not phone or not callback.message:
        await callback.answer()
        await show_connect_step(callback.message, state, lang)
        return

    settings = get_settings()
    try:
        sent = await resend_login_code(callback.from_user.id, settings)
        await state.update_data(login_phone=sent.phone)
        await callback.answer(t(lang, "code_resent"))
        await edit_screen(
            callback.message,
            state,
            t(lang, "step_code", phone=sent.phone) + "\n\n" + t(lang, "code_use_latest"),
            code_keyboard(lang),
        )
    except ValueError as exc:
        await callback.answer(str(exc), show_alert=True)
        if "share" in str(exc).lower() and callback.message:
            await show_connect_step(callback.message, state, lang)


@router.callback_query(F.data == "auth:disconnect")
async def cb_auth_disconnect(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await cancel_login(callback.from_user.id)
    await state.update_data(login_in_progress=False)
    await UserRepository(session).clear_telethon_session(callback.from_user.id)
    await session.commit()
    await callback.answer()
    if callback.message:
        await show_connect_step(callback.message, state, lang)
