from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

from app.bot.helpers import clear_inline_keyboard
from app.bot.keyboards import main_menu_keyboard
from app.bot.texts import MENU_PROMPT
from app.repositories.user_repository import UserRepository
from app.services.digest_service import DigestService
from app.services.telethon_service import timeframe_label
from app.utils.telegram import split_telegram_message
from sqlalchemy.ext.asyncio import AsyncSession

router = Router(name="digest")


async def _send_digest_part(message, text: str) -> None:
    try:
        await message.answer(text, parse_mode=ParseMode.MARKDOWN)
    except TelegramBadRequest:
        await message.answer(text)


@router.callback_query(F.data.startswith("digest:"))
async def cb_generate_digest(
    callback: CallbackQuery,
    session: AsyncSession,
    digest_service: DigestService,
) -> None:
    timeframe = callback.data.split(":")[1]
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Tap /start first.", show_alert=True)
        return

    await callback.answer()
    await clear_inline_keyboard(callback.message)

    label = timeframe_label(timeframe)
    status_message = await callback.message.edit_text(
        f"⏳ Generating digest for <b>{label}</b>…\nThis may take a minute.",
    )

    try:
        content = await digest_service.generate(user.id, timeframe)
        parts = split_telegram_message(content)
        await status_message.delete()
        for part in parts:
            await _send_digest_part(callback.message, part)
        await callback.message.answer(MENU_PROMPT, reply_markup=main_menu_keyboard())
    except ValueError as exc:
        await status_message.edit_text(f"ℹ️ {exc}")
        await callback.message.answer(MENU_PROMPT, reply_markup=main_menu_keyboard())
    except TimeoutError as exc:
        await status_message.edit_text(f"⏳ {exc}")
        await callback.message.answer(MENU_PROMPT, reply_markup=main_menu_keyboard())
    except RuntimeError as exc:
        await status_message.edit_text(f"❌ {exc}")
        await callback.message.answer(MENU_PROMPT, reply_markup=main_menu_keyboard())
    except Exception:
        await status_message.edit_text(
            "❌ Something went wrong while generating the digest. Please try again.",
        )
        await callback.message.answer(MENU_PROMPT, reply_markup=main_menu_keyboard())
