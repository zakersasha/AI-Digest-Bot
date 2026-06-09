from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import CB_TG_PICK_DONE, CB_TG_PICK_PAGE_PREFIX, CB_TG_PICK_TOGGLE_PREFIX
from app.bot.screen import edit_from_callback, edit_screen
from app.config import get_settings
from app.i18n import t
from app.repositories.source_repository import SourceRepository
from app.repositories.user_repository import UserRepository
from app.services.telethon_client import user_telethon_client
from app.services.telethon_service import SubscribedChannel

PAGE_SIZE = 8


def _active_usernames(sources) -> set[str]:
    return {s.telegram_source.lower() for s in sources if s.is_active}


def _picker_keyboard(
    lang: str,
    channels: list[SubscribedChannel],
    active: set[str],
    page: int,
) -> InlineKeyboardMarkup:
    total_pages = max(1, (len(channels) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    start = page * PAGE_SIZE
    chunk = channels[start : start + PAGE_SIZE]

    rows: list[list[InlineKeyboardButton]] = []
    for ch in chunk:
        mark = "✅" if ch.username.lower() in active else "⬜"
        label = f"{mark} {ch.title[:28]}"
        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"{CB_TG_PICK_TOGGLE_PREFIX}{ch.username.removeprefix('@')}",
                )
            ]
        )

    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(text="◀️", callback_data=f"{CB_TG_PICK_PAGE_PREFIX}{page - 1}")
        )
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="tg:noop"))
    if page < total_pages - 1:
        nav.append(
            InlineKeyboardButton(text="▶️", callback_data=f"{CB_TG_PICK_PAGE_PREFIX}{page + 1}")
        )
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton(text=t(lang, "btn_tg_pick_done"), callback_data=CB_TG_PICK_DONE)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def fetch_user_channels(user) -> list[SubscribedChannel]:
    settings = get_settings()
    async with user_telethon_client(user, settings) as telethon:
        return await telethon.fetch_subscribed_channels()


async def show_channel_picker(
    target: Message,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
    telegram_id: int,
    *,
    page: int = 0,
) -> None:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if not user or not UserRepository(session).has_telethon(user):
        return

    channels = await fetch_user_channels(user)
    if not channels:
        text = t(lang, "tg_picker_empty")
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data=CB_TG_PICK_DONE)]
            ]
        )
    else:
        sources = await SourceRepository(session).list_all_for_user(user.id)
        active = _active_usernames(sources)
        text = t(lang, "tg_picker_hint", count=len(channels))
        markup = _picker_keyboard(lang, channels, active, page)

    await state.update_data(tg_picker_page=page, tg_picker_count=len(channels))
    await edit_screen(target, state, text, markup)


async def toggle_channel(
    callback: CallbackQuery,
    session: AsyncSession,
    lang: str,
    username: str,
) -> None:
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        return

    repo = SourceRepository(session)
    sources = await repo.list_all_for_user(user.id)
    active = _active_usernames(sources)
    key = f"@{username.lower().removeprefix('@')}"

    if key in active:
        await repo.remove_source(user.id, key)
    else:
        channels = await fetch_user_channels(user)
        title = next(
            (ch.title for ch in channels if ch.username.lower() == key.lower()),
            key,
        )
        await repo.add_source(user.id, key, title=title)
    await session.commit()


async def refresh_picker_callback(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
    page: int,
) -> None:
    if not callback.message:
        return
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        return

    channels = await fetch_user_channels(user)
    sources = await SourceRepository(session).list_all_for_user(user.id)
    active = _active_usernames(sources)
    text = t(lang, "tg_picker_hint", count=len(channels))
    markup = _picker_keyboard(lang, channels, active, page)
    await edit_from_callback(callback, state, text, markup)
