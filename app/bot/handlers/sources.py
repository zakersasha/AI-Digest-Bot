from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import sources_keyboard
from app.repositories.user_repository import UserRepository
from app.services.source_service import SourceService
from sqlalchemy.ext.asyncio import AsyncSession

router = Router(name="sources")


async def _render_sources(message: Message, session: AsyncSession, source_service: SourceService, user_id: int) -> None:
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(user_id)
    if not user:
        await message.answer("Please run /start first.")
        return

    sources = await source_service.list_sources(user.id)
    if sources:
        lines = ["<b>Your sources</b>\n"]
        for source in sources:
            status = "active" if source.is_active else "paused"
            title = source.title or source.telegram_source
            lines.append(f"• {title} ({source.telegram_source}) — {status}")
        text = "\n".join(lines)
    else:
        text = "You have no sources yet.\nUse /add to add a public channel."

    await message.answer(text, reply_markup=sources_keyboard(sources))


@router.message(Command("sources"))
async def cmd_sources(
    message: Message,
    session: AsyncSession,
    source_service: SourceService,
) -> None:
    await _render_sources(message, session, source_service, message.from_user.id)


@router.callback_query(F.data == "add_hint")
async def cb_add_hint(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer("Use /add and send a public @username or t.me link.")


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
        await callback.answer("Run /start first.", show_alert=True)
        return

    source = await source_service.toggle_source(user.id, source_id)
    if not source:
        await callback.answer("Source not found.", show_alert=True)
        return

    await session.commit()
    status = "activated" if source.is_active else "paused"
    await callback.answer(f"{source.telegram_source} {status}")

    sources = await source_service.list_sources(user.id)
    title = source.title or source.telegram_source
    status_label = "active" if source.is_active else "paused"
    text = f"<b>Your sources</b>\n\n• {title} ({source.telegram_source}) — {status_label}"
    if len(sources) > 1:
        lines = ["<b>Your sources</b>\n"]
        for item in sources:
            item_status = "active" if item.is_active else "paused"
            item_title = item.title or item.telegram_source
            lines.append(f"• {item_title} ({item.telegram_source}) — {item_status}")
        text = "\n".join(lines)

    await callback.message.edit_text(text, reply_markup=sources_keyboard(sources))


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
        await callback.answer("Run /start first.", show_alert=True)
        return

    removed = await source_service.remove_source(user.id, source_id)
    if not removed:
        await callback.answer("Source not found.", show_alert=True)
        return

    await session.commit()
    await callback.answer("Removed")

    sources = await source_service.list_sources(user.id)
    if sources:
        lines = ["<b>Your sources</b>\n"]
        for source in sources:
            status = "active" if source.is_active else "paused"
            title = source.title or source.telegram_source
            lines.append(f"• {title} ({source.telegram_source}) — {status}")
        text = "\n".join(lines)
    else:
        text = "You have no sources yet.\nUse /add to add a public channel."

    await callback.message.edit_text(text, reply_markup=sources_keyboard(sources))
