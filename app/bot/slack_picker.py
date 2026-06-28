from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import CB_SLACK_PICK_DONE, CB_SLACK_PICK_PAGE_PREFIX, CB_SLACK_PICK_TOGGLE_PREFIX
from app.bot.screen import edit_from_callback, edit_screen
from app.config import get_settings
from app.i18n import t
from app.repositories.slack_channel_repository import SlackChannelRepository
from app.repositories.user_repository import UserRepository
from app.services.slack_service import SlackChannelInfo, SlackService

PAGE_SIZE = 8


def _active_channel_ids(channels) -> set[str]:
    return {c.channel_id for c in channels if c.is_active}


def _picker_keyboard(
    lang: str,
    items: list[SlackChannelInfo],
    active: set[str],
    page: int,
) -> InlineKeyboardMarkup:
    total_pages = max(1, (len(items) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    start = page * PAGE_SIZE
    chunk = items[start : start + PAGE_SIZE]

    rows: list[list[InlineKeyboardButton]] = []
    for item in chunk:
        mark = "✅" if item.channel_id in active else "⬜"
        prefix = "🔒" if item.is_private else "#"
        label = f"{mark} {prefix}{item.name[:26]}"
        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"{CB_SLACK_PICK_TOGGLE_PREFIX}{item.channel_id}",
                )
            ]
        )

    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(text="◀️", callback_data=f"{CB_SLACK_PICK_PAGE_PREFIX}{page - 1}")
        )
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="slack:noop"))
    if page < total_pages - 1:
        nav.append(
            InlineKeyboardButton(text="▶️", callback_data=f"{CB_SLACK_PICK_PAGE_PREFIX}{page + 1}")
        )
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton(text=t(lang, "btn_slack_pick_done"), callback_data=CB_SLACK_PICK_DONE)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def fetch_workspace_channels(user) -> list[SlackChannelInfo]:
    settings = get_settings()
    service = SlackService(settings)
    return await service.list_channels(user.slack_tokens_encrypted)


async def show_slack_picker(
    target: Message,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
    telegram_id: int,
    *,
    page: int = 0,
) -> None:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if not user or not UserRepository(session).has_slack(user):
        return

    try:
        workspace_channels = await fetch_workspace_channels(user)
    except ValueError:
        workspace_channels = []

    if not workspace_channels:
        text = t(lang, "slack_picker_empty")
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data=CB_SLACK_PICK_DONE)]
            ]
        )
    else:
        saved = await SlackChannelRepository(session).list_all_for_user(user.id)
        active = _active_channel_ids(saved)
        text = t(lang, "slack_picker_hint", count=len(workspace_channels))
        markup = _picker_keyboard(lang, workspace_channels, active, page)

    await state.update_data(slack_picker_page=page, slack_picker_count=len(workspace_channels))
    await edit_screen(target, state, text, markup)


async def toggle_channel(
    callback: CallbackQuery,
    session: AsyncSession,
    lang: str,
    channel_id: str,
) -> None:
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        return

    repo = SlackChannelRepository(session)
    saved = await repo.list_all_for_user(user.id)
    active = _active_channel_ids(saved)

    if channel_id in active:
        await repo.set_active(user.id, channel_id, False)
        await session.commit()
        return

    try:
        workspace_channels = await fetch_workspace_channels(user)
    except ValueError:
        return

    info = next((c for c in workspace_channels if c.channel_id == channel_id), None)
    if not info:
        return

    await repo.upsert_channel(user.id, info.channel_id, info.name, active=True)
    await session.commit()


async def refresh_picker(callback: CallbackQuery, state: FSMContext, session: AsyncSession, lang: str) -> None:
    data = await state.get_data()
    page = int(data.get("slack_picker_page") or 0)
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        return

    try:
        workspace_channels = await fetch_workspace_channels(user)
    except ValueError:
        workspace_channels = []

    if not workspace_channels:
        return

    saved = await SlackChannelRepository(session).list_all_for_user(user.id)
    active = _active_channel_ids(saved)
    text = t(lang, "slack_picker_hint", count=len(workspace_channels))
    markup = _picker_keyboard(lang, workspace_channels, active, page)
    await edit_from_callback(callback, state, text, markup)
