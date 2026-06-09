import asyncio
import re

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import BaseStorage, StorageKey
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.channel_picker import refresh_picker_callback, show_channel_picker, toggle_channel
from app.bot.keyboards import (
    CB_TG_CONNECT,
    CB_TG_CONNECT_PHONE,
    CB_TG_DISCONNECT,
    CB_TG_PICK,
    CB_TG_PICK_DONE,
    CB_TG_PICK_PAGE_PREFIX,
    CB_TG_PICK_TOGGLE_PREFIX,
    CB_TG_QR_REFRESH,
)
from app.bot.platform_screens import show_telegram_screen
from app.bot.states import OnboardingStates
from app.bot.telethon_notify import notify_telethon_connected
from app.config import get_settings
from app.db.session import async_session_factory
from app.i18n import resolve_lang, t
from app.repositories.user_repository import UserRepository
from app.services.telethon_link import (
    PasswordRequired,
    TelethonLoginPending,
    cancel_phone_login,
    finish_2fa_login,
    finish_phone_login,
    normalize_phone,
    refresh_qr_login,
    start_phone_login,
    start_qr_login,
    wait_qr_login,
)

router = Router(name="telethon_auth")

_CODE_RE = re.compile(r"^\d{4,8}$")
_PHONE_IN_PROGRESS: set[int] = set()
_QR_WAIT_TASKS: dict[int, asyncio.Task] = {}


def _phone_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "btn_share_phone"), request_contact=True)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def _qr_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_tg_qr_refresh"), callback_data=CB_TG_QR_REFRESH)],
            [InlineKeyboardButton(text=t(lang, "btn_tg_connect_phone"), callback_data=CB_TG_CONNECT_PHONE)],
        ]
    )


def _pending_from_state(data: dict) -> TelethonLoginPending | None:
    phone = data.get("tg_login_phone")
    partial = data.get("tg_login_session")
    code_hash = data.get("tg_login_hash")
    if phone and partial and code_hash:
        return TelethonLoginPending(phone=phone, partial_session=partial, phone_code_hash=code_hash)
    return None


def _cancel_qr_task(telegram_id: int) -> None:
    task = _QR_WAIT_TASKS.pop(telegram_id, None)
    if task and not task.done():
        task.cancel()


def _fsm_context(bot: Bot, storage: BaseStorage, telegram_id: int) -> FSMContext:
    return FSMContext(
        storage=storage,
        key=StorageKey(bot_id=bot.id, chat_id=telegram_id, user_id=telegram_id),
    )


async def _persist_session(telegram_id: int, username: str | None, session_string: str, phone: str) -> bool:
    async with async_session_factory() as db:
        repo = UserRepository(db)
        await repo.get_or_create(telegram_id, username)
        saved = await repo.save_telethon_session(telegram_id, session_string, phone)
        if not saved:
            return False
        await db.commit()
    return True


async def _qr_wait_worker(
    bot: Bot,
    storage: BaseStorage,
    telegram_id: int,
    lang: str,
    *,
    username: str | None = None,
) -> None:
    settings = get_settings()
    try:
        session_string, phone = await wait_qr_login(settings, telegram_id=telegram_id)
    except PasswordRequired as exc:
        state = _fsm_context(bot, storage, telegram_id)
        await state.update_data(
            tg_login_session=exc.partial_session,
            tg_login_phone=None,
            tg_login_hash=None,
        )
        await state.set_state(OnboardingStates.waiting_telegram_2fa)
        await bot.send_message(telegram_id, t(lang, "tg_2fa_prompt"))
        return
    except ValueError as exc:
        key = str(exc)
        if key == "qr_expired":
            await bot.send_message(
                telegram_id,
                t(lang, "tg_qr_expired"),
                reply_markup=_qr_keyboard(lang),
            )
        elif key == "qr_not_active":
            return
        else:
            await bot.send_message(telegram_id, t(lang, "tg_login_failed"))
        return
    except asyncio.CancelledError:
        return
    except Exception:
        await bot.send_message(telegram_id, t(lang, "tg_login_failed"))
        return

    if not await _persist_session(telegram_id, username, session_string, phone):
        await bot.send_message(telegram_id, t(lang, "tg_login_failed"))
        return

    state = _fsm_context(bot, storage, telegram_id)
    await state.update_data(
        tg_login_phone=None,
        tg_login_session=None,
        tg_login_hash=None,
    )
    await state.set_state(OnboardingStates.managing_sources)
    await notify_telethon_connected(bot, telegram_id, lang, phone)


def _start_qr_wait_task(
    bot: Bot,
    storage: BaseStorage,
    telegram_id: int,
    lang: str,
    *,
    username: str | None = None,
) -> None:
    _cancel_qr_task(telegram_id)
    task = asyncio.create_task(
        _qr_wait_worker(bot, storage, telegram_id, lang, username=username),
        name=f"tg-qr-wait-{telegram_id}",
    )
    _QR_WAIT_TASKS[telegram_id] = task


async def _send_qr_prompt(
    target: Message,
    state: FSMContext,
    lang: str,
    telegram_id: int,
    *,
    username: str | None = None,
) -> None:
    settings = get_settings()
    try:
        png, _url = await start_qr_login(settings, telegram_id=telegram_id)
    except Exception:
        await target.answer(t(lang, "tg_login_failed"))
        return

    await state.set_state(OnboardingStates.waiting_telegram_qr)
    await target.answer_photo(
        BufferedInputFile(png, filename="telegram-qr.png"),
        caption=t(lang, "tg_qr_prompt"),
        reply_markup=_qr_keyboard(lang),
    )
    _start_qr_wait_task(target.bot, state.storage, telegram_id, lang, username=username)


@router.callback_query(F.data == CB_TG_CONNECT)
async def cb_tg_connect(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await callback.answer()
    if callback.message:
        await _send_qr_prompt(
            callback.message,
            state,
            lang,
            callback.from_user.id,
            username=callback.from_user.username,
        )


@router.callback_query(F.data == CB_TG_QR_REFRESH)
async def cb_tg_qr_refresh(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    try:
        png, _url = await refresh_qr_login(callback.from_user.id)
    except ValueError:
        await callback.answer(t(lang, "tg_qr_not_active"), show_alert=True)
        return

    await callback.answer(t(lang, "tg_qr_refreshed"))
    if callback.message:
        await callback.message.answer_photo(
            BufferedInputFile(png, filename="telegram-qr.png"),
            caption=t(lang, "tg_qr_prompt"),
            reply_markup=_qr_keyboard(lang),
        )
        _start_qr_wait_task(
            callback.bot,
            state.storage,
            callback.from_user.id,
            lang,
            username=callback.from_user.username,
        )


@router.callback_query(F.data == CB_TG_CONNECT_PHONE)
async def cb_tg_connect_phone(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    _cancel_qr_task(callback.from_user.id)
    await cancel_phone_login(callback.from_user.id)
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
    _cancel_qr_task(callback.from_user.id)
    await cancel_phone_login(callback.from_user.id)
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
    user_id = message.from_user.id
    if user_id in _PHONE_IN_PROGRESS:
        return

    _cancel_qr_task(user_id)
    _PHONE_IN_PROGRESS.add(user_id)
    settings = get_settings()

    try:
        phone = normalize_phone(raw_phone)
        pending = await start_phone_login(phone, settings, telegram_id=user_id)
    except ValueError as exc:
        key = str(exc)
        if key.startswith("flood_wait:"):
            seconds = key.split(":", 1)[1]
            await message.answer(t(lang, "tg_flood_wait", seconds=seconds), reply_markup=ReplyKeyboardRemove())
            return
        await message.answer(t(lang, "tg_invalid_phone"), reply_markup=ReplyKeyboardRemove())
        return
    finally:
        _PHONE_IN_PROGRESS.discard(user_id)

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
        session_string = await finish_phone_login(
            pending,
            code,
            settings,
            telegram_id=message.from_user.id,
        )
    except PasswordRequired as exc:
        await state.update_data(tg_login_session=exc.partial_session)
        await state.set_state(OnboardingStates.waiting_telegram_2fa)
        await message.answer(t(lang, "tg_2fa_prompt"))
        return
    except ValueError as exc:
        key = str(exc)
        if key == "invalid_code":
            await message.answer(t(lang, "tg_code_retry"))
            return
        if key == "code_expired":
            await state.update_data(
                tg_login_phone=None,
                tg_login_session=None,
                tg_login_hash=None,
            )
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
    partial = data.get("tg_login_session")
    if not partial:
        await message.answer(t(lang, "tg_login_expired"))
        return

    settings = get_settings()
    try:
        session_string, phone = await finish_2fa_login(
            partial,
            message.text or "",
            settings,
            telegram_id=message.from_user.id,
        )
    except ValueError:
        await message.answer(t(lang, "tg_2fa_invalid"))
        return

    await _save_session(message, state, session, lang, phone, session_string)


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
