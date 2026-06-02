import asyncio

from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, Message

from app.bot.keyboards import connect_login_keyboard
from app.bot.login_complete import complete_telethon_session
from app.bot.screen import bind_screen, replace_screen
from app.bot.states import LoginStates
from app.config import get_settings
from app.db.session import async_session_factory
from app.i18n import resolve_lang, t
from app.services.telethon_auth import (
    _qr_tasks,
    cancel_login,
    cancel_qr_task,
    refresh_qr_login,
    start_qr_login,
    wait_qr_login,
)
from app.utils.qr import qr_png_bytes


async def _run_qr_wait(telegram_id: int, anchor: Message, state: FSMContext, lang: str) -> None:
    settings = get_settings()
    try:
        session_string = await wait_qr_login(telegram_id, timeout=180)
    except ValueError as exc:
        if str(exc) == "2FA_REQUIRED":
            await state.set_state(LoginStates.waiting_2fa)
            await anchor.answer(t(lang, "step_2fa_password"))
            return
        await anchor.answer(f"❌ {exc}")
        return
    except asyncio.CancelledError:
        return
    except Exception:
        await anchor.answer(t(lang, "qr_failed"))
        return

    async with async_session_factory() as session:
        lang = await resolve_lang(session, telegram_id)
        await complete_telethon_session(
            anchor, state, session, lang, session_string, phone=""
        )


def _schedule_qr_wait(telegram_id: int, anchor: Message, state: FSMContext, lang: str) -> None:
    cancel_qr_task(telegram_id)
    task = asyncio.create_task(_run_qr_wait(telegram_id, anchor, state, lang))
    _qr_tasks[telegram_id] = task


async def show_connect_step(target: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(LoginStates.waiting_qr)
    settings = get_settings()
    telegram_id = target.from_user.id

    cancel_qr_task(telegram_id)
    await cancel_login(telegram_id)

    try:
        url = await start_qr_login(telegram_id, settings)
    except ValueError as exc:
        await replace_screen(target, state, f"❌ {exc}", connect_login_keyboard(lang))
        return
    except Exception:
        await replace_screen(target, state, t(lang, "qr_failed"), connect_login_keyboard(lang))
        return

    await replace_screen(target, state, t(lang, "step_connect_qr"), connect_login_keyboard(lang))
    png = qr_png_bytes(url)
    photo = BufferedInputFile(png, filename="telegram-login.png")
    sent = await target.answer_photo(
        photo,
        caption=t(lang, "step_qr_caption"),
        parse_mode=ParseMode.HTML,
    )
    await bind_screen(state, sent)
    _schedule_qr_wait(telegram_id, target, state, lang)


async def refresh_connect_qr(target: Message, state: FSMContext, lang: str) -> None:
    settings = get_settings()
    telegram_id = target.from_user.id
    cancel_qr_task(telegram_id)
    try:
        url = await refresh_qr_login(telegram_id, settings)
    except Exception:
        await target.answer(t(lang, "qr_failed"))
        return

    png = qr_png_bytes(url)
    photo = BufferedInputFile(png, filename="telegram-login.png")
    await target.answer_photo(
        photo,
        caption=t(lang, "step_qr_caption"),
        parse_mode=ParseMode.HTML,
    )
    _schedule_qr_wait(telegram_id, target, state, lang)
