from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import timeframe_keyboard
from app.repositories.user_repository import UserRepository
from app.services.digest_service import DigestService
from app.utils.telegram import split_telegram_message
from sqlalchemy.ext.asyncio import AsyncSession

router = Router(name="digest")


@router.message(Command("digest"))
async def cmd_digest(message: Message) -> None:
    await message.answer(
        "Choose a timeframe for your digest:",
        reply_markup=timeframe_keyboard(),
    )


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
        await callback.answer("Run /start first.", show_alert=True)
        return

    await callback.answer()
    status_message = await callback.message.answer("⏳ Generating your digest… This may take a minute.")

    try:
        content = await digest_service.generate(user.id, timeframe)
        parts = split_telegram_message(content)
        await status_message.edit_text(parts[0])
        for part in parts[1:]:
            await callback.message.answer(part)
    except ValueError as exc:
        await status_message.edit_text(f"ℹ️ {exc}")
    except TimeoutError as exc:
        await status_message.edit_text(f"⏳ {exc}")
    except RuntimeError as exc:
        await status_message.edit_text(f"❌ {exc}")
    except Exception:
        await status_message.edit_text(
            "❌ Something went wrong while generating the digest. Please try again."
        )
