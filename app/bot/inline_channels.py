import time

from aiogram.fsm.context import FSMContext

from app.config import get_settings
from app.services.telethon_client import user_telethon_client
from app.services.telethon_service import SubscribedChannel

INLINE_RESULT_PREFIX = "ch:"
CACHE_TTL_SEC = 300


def channel_result_id(username: str) -> str:
    key = username.lower().removeprefix("@")
    return f"{INLINE_RESULT_PREFIX}{key}"[:64]


def username_from_result_id(result_id: str) -> str | None:
    if not result_id.startswith(INLINE_RESULT_PREFIX):
        return None
    slug = result_id.removeprefix(INLINE_RESULT_PREFIX).strip()
    return f"@{slug}" if slug else None


async def fetch_user_channels(user) -> list[SubscribedChannel]:
    settings = get_settings()
    async with user_telethon_client(user, settings) as telethon:
        return await telethon.fetch_subscribed_channels()


def _serialize_channels(channels: list[SubscribedChannel]) -> list[dict]:
    return [
        {"username": ch.username, "title": ch.title, "peer_id": ch.peer_id}
        for ch in channels
    ]


def _deserialize_channels(items: list[dict]) -> list[SubscribedChannel]:
    return [SubscribedChannel(**item) for item in items]


async def warm_channel_cache(state: FSMContext, user) -> list[SubscribedChannel]:
    channels = await fetch_user_channels(user)
    await state.update_data(
        tg_inline_cache={
            "ts": time.time(),
            "items": _serialize_channels(channels),
        }
    )
    return channels


async def get_channels_for_inline(state: FSMContext, user) -> list[SubscribedChannel]:
    data = await state.get_data()
    cached = data.get("tg_inline_cache")
    if cached and time.time() - float(cached.get("ts", 0)) < CACHE_TTL_SEC:
        return _deserialize_channels(cached.get("items", []))
    return await warm_channel_cache(state, user)


def filter_channels(channels: list[SubscribedChannel], query: str) -> list[SubscribedChannel]:
    needle = query.strip().lower().removeprefix("@")
    if not needle:
        return channels
    return [
        ch
        for ch in channels
        if needle in ch.title.lower() or needle in ch.username.lower().removeprefix("@")
    ]


def sort_channels_for_picker(
    channels: list[SubscribedChannel],
    active: set[str],
) -> list[SubscribedChannel]:
    selected: list[SubscribedChannel] = []
    unselected: list[SubscribedChannel] = []
    for ch in channels:
        key = ch.username.lower().removeprefix("@")
        if key in active:
            selected.append(ch)
        else:
            unselected.append(ch)
    selected.sort(key=lambda ch: ch.title.lower())
    unselected.sort(key=lambda ch: ch.title.lower())
    return selected + unselected
