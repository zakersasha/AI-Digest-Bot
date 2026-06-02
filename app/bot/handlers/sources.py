from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.bot.helpers import format_sources_text
from app.bot.keyboards import sources_keyboard
from app.repositories.user_repository import UserRepository
from app.services.source_service import SourceService
from sqlalchemy.ext.asyncio import AsyncSession

router = Router(name="sources")


@router.callback_query(F.data.startswith("toggle:"))
async def cb_toggle_source(
    callback: CallbackQuery,
    session: AsyncSession,
    source_service: SourceService,
) -> None:
    source_id = int(callback.data.split(":")[1])
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Tap /start first.", show_alert=True)
        return

    source = await source_service.toggle_source(user.id, source_id)
    if not source:
        await callback.answer("Source not found.", show_alert=True)
        return

    await session.commit()
    status = "activated" if source.is_active else "paused"
    await callback.answer(f"{source.telegram_source} {status}")

    sources = await source_service.list_sources(user.id)
    await callback.message.edit_text(
        format_sources_text(sources),
        reply_markup=sources_keyboard(sources),
    )


@router.callback_query(F.data.startswith("remove:"))
async def cb_remove_source(
    callback: CallbackQuery,
    session: AsyncSession,
    source_service: SourceService,
) -> None:
    source_id = int(callback.data.split(":")[1])
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Tap /start first.", show_alert=True)
        return

    removed = await source_service.remove_source(user.id, source_id)
    if not removed:
        await callback.answer("Source not found.", show_alert=True)
        return

    await session.commit()
    await callback.answer("Removed")

    sources = await source_service.list_sources(user.id)
    await callback.message.edit_text(
        format_sources_text(sources),
        reply_markup=sources_keyboard(sources),
    )
