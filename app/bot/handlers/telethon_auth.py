import asyncio

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import BaseStorage, StorageKey
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.channel_picker import refresh_picker_callback, show_channel_picker, toggle_channel
from app.bot.keyboards import (
    CB_PLATFORM_TELEGRAM,
    CB_TG_ADD_LINKS,
    CB_TG_CHANNELS,
    CB_TG_CONNECT,
    CB_TG_DISCONNECT,
    CB_TG_PICK,
    CB_TG_PICK_DONE,
    CB_TG_PICK_PAGE_PREFIX,
    CB_TG_PICK_TOGGLE_PREFIX,
    CB_TG_QR_REFRESH,
)
from app.bot.platform_screens import (
    push_telegram_screen,
    show_telegram_channels_screen,
    show_telegram_screen,
    telegram_qr_keyboard,
)
from app.bot.screen import edit_from_callback, replace_screen_document, screen_chat_id
from app.bot.sources_flow import show_add_source_prompt
from app.bot.states import OnboardingStates
from app.config import get_settings
from app.db.session import async_session_factory
from app.i18n import resolve_lang, t
from app.repositories.user_repository import UserRepository
from app.services.telethon_link import (
    PasswordRequired,
    cancel_phone_login,
    finish_2fa_login,
    refresh_qr_login,
    start_qr_login,
    wait_qr_login,
)

router = Router(name="telethon_auth")

_QR_WAIT_TASKS: dict[int, asyncio.Task] = {}


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


async def _screen_2fa_prompt(bot: Bot, state: FSMContext, lang: str) -> None:
    chat_id = await screen_chat_id(state)
    if not chat_id:
        return
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data=CB_PLATFORM_TELEGRAM)],
        ]
    )
    from app.bot.screen import replace_screen_at

    await replace_screen_at(bot, state, chat_id, t(lang, "tg_2fa_prompt"), markup)


async def _qr_wait_worker(
    bot: Bot,
    storage: BaseStorage,
    telegram_id: int,
    lang: str,
    *,
    username: str | None = None,
) -> None:
    settings = get_settings()
    state = _fsm_context(bot, storage, telegram_id)
    try:
        session_string, phone = await wait_qr_login(settings, telegram_id=telegram_id)
    except PasswordRequired as exc:
        await state.update_data(tg_login_session=exc.partial_session)
        await state.set_state(OnboardingStates.waiting_telegram_2fa)
        await _screen_2fa_prompt(bot, state, lang)
        return
    except ValueError as exc:
        key = str(exc)
        chat_id = await screen_chat_id(state)
        if not chat_id:
            return
        if key == "qr_expired":
            try:
                png, _url = await refresh_qr_login(telegram_id)
            except ValueError:
                async with async_session_factory() as db:
                    await push_telegram_screen(
                        bot,
                        state,
                        db,
                        lang,
                        telegram_id,
                        status_line=t(lang, "tg_qr_expired"),
                    )
                return
            await replace_screen_document(
                bot,
                state,
                chat_id,
                png,
                "telegram-login-qr.png",
                t(lang, "tg_qr_prompt"),
                telegram_qr_keyboard(lang),
            )
            _start_qr_wait_task(bot, storage, telegram_id, lang, username=username)
        elif key != "qr_not_active":
            async with async_session_factory() as db:
                await push_telegram_screen(
                    bot,
                    state,
                    db,
                    lang,
                    telegram_id,
                    status_line=t(lang, "tg_login_failed"),
                )
        return
    except asyncio.CancelledError:
        return
    except Exception:
        async with async_session_factory() as db:
            await push_telegram_screen(
                bot,
                state,
                db,
                lang,
                telegram_id,
                status_line=t(lang, "tg_login_failed"),
            )
        return

    if not await _persist_session(telegram_id, username, session_string, phone):
        async with async_session_factory() as db:
            await push_telegram_screen(
                bot,
                state,
                db,
                lang,
                telegram_id,
                status_line=t(lang, "tg_login_failed"),
            )
        return

    await state.update_data(tg_login_session=None, tg_ui="main")
    async with async_session_factory() as db:
        await push_telegram_screen(
            bot,
            state,
            db,
            lang,
            telegram_id,
            status_line=t(lang, "tg_linked", phone=phone),
        )


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


async def _show_qr_on_screen(
    callback: CallbackQuery,
    state: FSMContext,
    lang: str,
    telegram_id: int,
) -> None:
    if not callback.message:
        return
    settings = get_settings()
    try:
        png, _url = await start_qr_login(settings, telegram_id=telegram_id)
    except Exception:
        await edit_from_callback(
            callback,
            state,
            t(lang, "tg_login_failed"),
            telegram_qr_keyboard(lang),
        )
        return

    chat_id = callback.message.chat.id
    await replace_screen_document(
        callback.bot,
        state,
        chat_id,
        png,
        "telegram-login-qr.png",
        t(lang, "tg_qr_prompt"),
        telegram_qr_keyboard(lang),
    )
    await state.set_state(OnboardingStates.waiting_telegram_qr)
    _start_qr_wait_task(
        callback.bot,
        state.storage,
        telegram_id,
        lang,
        username=callback.from_user.username,
    )


def cancel_telegram_login(telegram_id: int) -> None:
    _cancel_qr_task(telegram_id)


@router.callback_query(F.data == CB_TG_CONNECT)
async def cb_tg_connect(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await callback.answer()
    await _show_qr_on_screen(callback, state, lang, callback.from_user.id)


@router.callback_query(F.data == CB_TG_ADD_LINKS)
async def cb_tg_add_links(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await state.update_data(tg_ui="main")
    await callback.answer()
    await show_add_source_prompt(callback, state, session, lang)


@router.callback_query(F.data == CB_TG_QR_REFRESH)
async def cb_tg_qr_refresh(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    if not callback.message:
        await callback.answer()
        return
    try:
        png, _url = await refresh_qr_login(callback.from_user.id)
    except ValueError:
        await callback.answer(t(lang, "tg_qr_not_active"), show_alert=True)
        return

    await callback.answer(t(lang, "tg_qr_refreshed"))
    await replace_screen_document(
        callback.bot,
        state,
        callback.message.chat.id,
        png,
        "telegram-login-qr.png",
        t(lang, "tg_qr_prompt"),
        telegram_qr_keyboard(lang),
    )
    _start_qr_wait_task(
        callback.bot,
        state.storage,
        callback.from_user.id,
        lang,
        username=callback.from_user.username,
    )


@router.callback_query(F.data == CB_TG_CHANNELS)
async def cb_tg_channels(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    await callback.answer()
    if callback.message:
        await show_telegram_channels_screen(
            callback.message,
            state,
            session,
            lang,
            callback.from_user.id,
            from_user_action=True,
        )


@router.callback_query(F.data == CB_TG_DISCONNECT)
async def cb_tg_disconnect(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = await resolve_lang(session, callback.from_user.id)
    cancel_telegram_login(callback.from_user.id)
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
        await show_telegram_channels_screen(
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


@router.message(StateFilter(OnboardingStates.waiting_telegram_2fa), F.text, ~F.text.startswith("/"))
async def msg_telegram_2fa(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    lang = await resolve_lang(session, message.from_user.id)
    partial = (await state.get_data()).get("tg_login_session")
    if not partial:
        await show_telegram_screen(
            message,
            state,
            session,
            lang,
            message.from_user.id,
            status_line=t(lang, "tg_login_expired"),
            from_user_action=True,
        )
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
        await show_telegram_screen(
            message,
            state,
            session,
            lang,
            message.from_user.id,
            status_line=t(lang, "tg_2fa_invalid"),
            from_user_action=True,
        )
        return

    repo = UserRepository(session)
    await repo.get_or_create(message.from_user.id, message.from_user.username)
    if not await repo.save_telethon_session(message.from_user.id, session_string, phone):
        await show_telegram_screen(
            message,
            state,
            session,
            lang,
            message.from_user.id,
            status_line=t(lang, "tg_login_failed"),
            from_user_action=True,
        )
        return
    await session.commit()

    await state.update_data(tg_login_session=None, tg_ui="main")
    try:
        await message.delete()
    except Exception:
        pass

    await show_telegram_screen(
        message,
        state,
        session,
        lang,
        message.from_user.id,
        status_line=t(lang, "tg_linked", phone=phone),
        from_user_action=True,
    )
