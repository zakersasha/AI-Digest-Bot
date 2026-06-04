import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import TypeVar

from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LinkPreviewOptions

from app.bot.keyboards import back_to_menu_keyboard
from app.bot.screen import edit_from_callback
from app.i18n import t
from app.utils.telegram import split_telegram_message

T = TypeVar("T")

NO_LINK_PREVIEW = LinkPreviewOptions(is_disabled=True)

_PROGRESS_KEYS = (
    "digest_progress_fetch",
    "digest_progress_read",
    "digest_progress_ai",
)


async def _progress_loop(
    callback: CallbackQuery,
    state: FSMContext,
    lang: str,
    label: str,
) -> None:
    frame = 0
    tick = 0
    while True:
        dots = "." * (tick % 3 + 1)
        key = _PROGRESS_KEYS[frame % len(_PROGRESS_KEYS)]
        try:
            await edit_from_callback(
                callback,
                state,
                t(lang, key, label=label, dots=dots),
                None,
            )
        except TelegramBadRequest:
            pass
        tick += 1
        if tick % 2 == 0:
            frame += 1
        await asyncio.sleep(1.4)


async def run_with_digest_progress(
    callback: CallbackQuery,
    state: FSMContext,
    lang: str,
    label: str,
    work: Callable[[], Awaitable[T]],
) -> T:
    progress = asyncio.create_task(_progress_loop(callback, state, lang, label))
    try:
        return await work()
    finally:
        progress.cancel()
        with suppress(asyncio.CancelledError):
            await progress


async def deliver_digest(
    callback: CallbackQuery,
    state: FSMContext,
    lang: str,
    content: str,
) -> None:
    """Show full digest without link previews; no truncated preview footnote."""
    parts = split_telegram_message(content)
    keyboard = back_to_menu_keyboard(lang)

    try:
        await edit_from_callback(
            callback,
            state,
            parts[0],
            keyboard,
            parse_mode=ParseMode.MARKDOWN,
            link_preview_options=NO_LINK_PREVIEW,
        )
    except TelegramBadRequest:
        await edit_from_callback(
            callback,
            state,
            parts[0],
            keyboard,
            parse_mode=None,
            link_preview_options=NO_LINK_PREVIEW,
        )

    if not callback.message or len(parts) <= 1:
        return

    chat_id = callback.message.chat.id
    for part in parts[1:]:
        try:
            await callback.message.bot.send_message(
                chat_id,
                part,
                parse_mode=ParseMode.MARKDOWN,
                link_preview_options=NO_LINK_PREVIEW,
            )
        except TelegramBadRequest:
            await callback.message.bot.send_message(
                chat_id,
                part,
                link_preview_options=NO_LINK_PREVIEW,
            )
