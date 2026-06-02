from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import subscriptions_keyboard
from app.bot.screen import edit_from_callback, edit_screen, open_screen
from app.bot.states import OnboardingStates
from app.config import get_settings
from app.i18n import t
from app.repositories.user_repository import UserRepository
from app.services.telethon_client import user_telethon_client
from app.services.telethon_service import SubscribedChannel
from app.utils.crypto import decrypt_session


def channels_from_state(data: dict) -> list[SubscribedChannel]:
    raw = data.get("subscriptions", [])
    return [
        SubscribedChannel(
            username=item["username"],
            title=item["title"],
            peer_id=item["peer_id"],
        )
        for item in raw
    ]


async def get_selected(state: FSMContext) -> set[str]:
    data = await state.get_data()
    return set(data.get("selected_usernames", []))


async def set_selected(state: FSMContext, selected: set[str]) -> None:
    await state.update_data(selected_usernames=list(selected))


async def save_channels_to_state(state: FSMContext, channels: list[SubscribedChannel]) -> None:
    payload = [
        {"username": ch.username, "title": ch.title, "peer_id": ch.peer_id}
        for ch in channels
    ]
    await state.update_data(subscriptions=payload, ch_page=0)


async def load_user_subscriptions(user, state: FSMContext) -> list[SubscribedChannel]:
    settings = get_settings()
    session_string = decrypt_session(user.telethon_session_encrypted)
    async with user_telethon_client(session_string, settings) as telethon:
        channels = await telethon.fetch_subscribed_channels()
    await save_channels_to_state(state, channels)
    return channels


async def show_connect_step(target: Message, state: FSMContext, lang: str) -> None:
    from app.bot.connect_step import show_connect_step as _show

    await _show(target, state, lang)


async def show_channels_screen(
    target: Message,
    state: FSMContext,
    lang: str,
    channels: list[SubscribedChannel],
    selected: set[str],
) -> None:
    if not channels:
        await edit_screen(target, state, t(lang, "channels_empty"), None)
        return
    await state.set_state(OnboardingStates.picking_channels)
    text = t(lang, "step_channels", count=len(selected))
    markup = subscriptions_keyboard(channels, selected, lang, page=0)
    await edit_screen(target, state, text, markup)


async def show_channels_loading(
    target: Message,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
    telegram_id: int,
    selected: set[str] | None = None,
) -> None:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if not user or not user.telethon_session_encrypted:
        await show_connect_step(target, state, lang)
        return

    await edit_screen(target, state, t(lang, "channels_loading"), None)
    channels = await load_user_subscriptions(user, state)
    sel = selected if selected is not None else set()
    await show_channels_screen(target, state, lang, channels, sel)


async def proceed_after_language(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
) -> None:
    await callback.answer()
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not callback.message:
        return
    if user and user.telethon_session_encrypted:
        await set_selected(state, set())
        await show_channels_loading(
            callback.message, state, session, lang, callback.from_user.id, set()
        )
    else:
        await show_connect_step(callback.message, state, lang)


async def proceed_to_channels(
    target: Message,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
    telegram_id: int,
) -> None:
    await set_selected(state, set())
    await show_channels_loading(target, state, session, lang, telegram_id, set())


async def render_channels_page(
    callback: CallbackQuery,
    state: FSMContext,
    lang: str,
    page: int,
) -> None:
    data = await state.get_data()
    subscriptions = channels_from_state(data)
    selected = set(data.get("selected_usernames", []))
    await state.update_data(ch_page=page)
    text = t(lang, "step_channels", count=len(selected))
    markup = subscriptions_keyboard(subscriptions, selected, lang, page=page)
    await edit_from_callback(callback, state, text, markup)
