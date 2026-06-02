from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import code_keyboard, connect_telegram_keyboard
from app.bot.screen import bind_screen, edit_screen
from app.bot.states import LoginStates
from app.config import get_settings
from app.i18n import resolve_lang, t
from app.repositories.user_repository import UserRepository
from app.services.telethon_auth import cancel_login, complete_login, start_login

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
        screen = await message.bot.edit_message_text(
            t(lang, "channels_loading"),
            chat_id=chat_id,
            message_id=msg_id,
        )
        await bind_screen(state, screen)
    await show_channels_loading(
        message, state, session, lang, message.from_user.id, set()
    )


async def show_connect_step(target: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(LoginStates.waiting_phone)
    await edit_screen(target, state, t(lang, "step_connect"), connect_telegram_keyboard(lang))


@router.callback_query(F.data == "auth:connect")
async def cb_auth_connect(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await cancel_login(callback.from_user.id)
    await callback.answer()
    if callback.message:
        await show_connect_step(callback.message, state, lang)


@router.message(LoginStates.waiting_phone, F.text)
async def login_phone_text(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if message.text and message.text.startswith("/"):
        return
    lang = await resolve_lang(session, message.from_user.id)
    settings = get_settings()
    try:
        sent = await start_login(message.from_user.id, message.text, settings)
    except ValueError as exc:
        await message.answer(f"❌ {exc}")
        return

    await state.update_data(login_phone=sent.phone, login_phone_code_hash=sent.phone_code_hash)
    await state.set_state(LoginStates.waiting_code)

    data = await state.get_data()
    if data.get("screen_chat_id") and data.get("screen_message_id"):
        await message.bot.edit_message_text(
            t(lang, "step_code", phone=sent.phone),
            chat_id=data["screen_chat_id"],
            message_id=data["screen_message_id"],
            reply_markup=code_keyboard(lang),
        )


@router.message(LoginStates.waiting_code, F.text)
async def login_code(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    lang = await resolve_lang(session, message.from_user.id)
    data = await state.get_data()
    phone = data.get("login_phone")
    phone_code_hash = data.get("login_phone_code_hash")
    if not phone or not phone_code_hash:
        await show_connect_step(message, state, lang)
        return

    settings = get_settings()
    try:
        session_string = await complete_login(
            message.from_user.id,
            phone,
            message.text or "",
            phone_code_hash,
            settings,
        )
    except ValueError as exc:
        if str(exc) == "2FA_REQUIRED":
            await state.set_state(LoginStates.waiting_2fa)
            data = await state.get_data()
            if data.get("screen_chat_id") and data.get("screen_message_id"):
                await message.bot.edit_message_text(
                    t(lang, "step_2fa"),
                    chat_id=data["screen_chat_id"],
                    message_id=data["screen_message_id"],
                    reply_markup=code_keyboard(lang),
                )
            return
        await message.answer(f"❌ {exc}")
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
    phone = data.get("login_phone")
    phone_code_hash = data.get("login_phone_code_hash")
    settings = get_settings()

    try:
        session_string = await complete_login(
            message.from_user.id,
            phone,
            "",
            phone_code_hash,
            settings,
            password=message.text or "",
        )
    except ValueError as exc:
        await message.answer(f"❌ {exc}")
        return

    await UserRepository(session).save_telethon_session(
        message.from_user.id, session_string, phone
    )
    await session.commit()
    await state.set_state(None)
    await _finish_login(message, state, session, lang)


@router.callback_query(F.data == "auth:resend")
async def cb_auth_resend(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    data = await state.get_data()
    phone = data.get("login_phone")
    if not phone or not callback.message:
        await callback.answer()
        await show_connect_step(callback.message, state, lang)
        return

    settings = get_settings()
    try:
        sent = await start_login(callback.from_user.id, phone, settings)
        await state.update_data(login_phone_code_hash=sent.phone_code_hash)
        await callback.answer(t(lang, "channels_refreshed"))
        await edit_screen(
            callback.message,
            state,
            t(lang, "step_code", phone=sent.phone),
            code_keyboard(lang),
        )
    except ValueError as exc:
        await callback.answer(str(exc), show_alert=True)


@router.callback_query(F.data == "auth:disconnect")
async def cb_auth_disconnect(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await cancel_login(callback.from_user.id)
    await UserRepository(session).clear_telethon_session(callback.from_user.id)
    await session.commit()
    await callback.answer()
    if callback.message:
        await show_connect_step(callback.message, state, lang)
