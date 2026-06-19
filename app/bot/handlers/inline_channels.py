import re
import time

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    ChosenInlineResult,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    Message,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.inline_channels import (
    channel_result_id,
    filter_channels,
    get_channels_for_inline,
    sort_channels_for_picker,
    username_from_result_id,
    warm_channel_cache,
)
from app.bot.onboarding_flow import is_guided, set_flow_step
from app.bot.platform_screens import push_telegram_channels_screen, push_telegram_screen
from app.i18n import resolve_lang, t
from app.repositories.source_repository import SourceRepository
from app.repositories.user_repository import UserRepository

router = Router(name="inline_channels")

_MAX_RESULTS = 50
_INLINE_PICK_PREFIX = "✓ "
_INLINE_PICK_USERNAME_RE = re.compile(r"^✓\s+(@\S+)")


async def apply_inline_channel_pick(
    bot: Bot,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
    telegram_id: int,
    username: str,
    *,
    chat_id: int | None = None,
) -> None:
    data = await state.get_data()
    dedup_key = username.lower().removeprefix("@")
    last_key = data.get("tg_inline_dedup_key")
    last_ts = float(data.get("tg_inline_dedup_ts") or 0)
    now = time.time()
    if last_key == dedup_key and now - last_ts < 3:
        return
    await state.update_data(tg_inline_dedup_key=dedup_key, tg_inline_dedup_ts=now)

    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if not user:
        return

    repo = SourceRepository(session)
    sources = await repo.list_all_for_user(user.id)
    active = {s.telegram_source.lower().removeprefix("@") for s in sources if s.is_active}
    key = username.lower().removeprefix("@")

    if key in active:
        await repo.remove_source(user.id, username)
        await session.commit()
        status = t(lang, "source_removed")
    else:
        title = username
        try:
            channels = await get_channels_for_inline(state, user)
            title = next(
                (
                    ch.title
                    for ch in channels
                    if ch.username.lower().removeprefix("@") == key
                ),
                username,
            )
        except ValueError:
            pass

        add_result = await repo.add_source(user.id, username, title=title)
        await session.commit()

        if add_result == "new":
            status = t(lang, "sources_added", count=1)
        elif add_result == "exists":
            status = t(lang, "sources_already")
        else:
            status = None

    if await is_guided(state):
        count = await repo.count_active(user.id)
        if count > 0:
            await set_flow_step(state, 4)

    data = await state.get_data()
    tg_ui = data.get("tg_ui", "main")
    if tg_ui == "channels":
        await push_telegram_channels_screen(
            bot,
            state,
            session,
            lang,
            telegram_id,
            status_line=status,
            chat_id=chat_id,
        )
    else:
        await push_telegram_screen(
            bot,
            state,
            session,
            lang,
            telegram_id,
            status_line=status,
            chat_id=chat_id,
        )


def username_from_pick_message(text: str, channels_cache: list | None = None) -> str | None:
    match = _INLINE_PICK_USERNAME_RE.match(text.strip())
    if match:
        return match.group(1)
    title = text.strip().removeprefix(_INLINE_PICK_PREFIX).strip()
    if not title or not channels_cache:
        return None
    for ch in channels_cache:
        if ch.title.strip() == title:
            username = ch.username if ch.username.startswith("@") else f"@{ch.username}"
            return username
    return None


@router.inline_query()
async def inline_channel_query(
    query: InlineQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    lang = await resolve_lang(session, query.from_user.id)
    user = await UserRepository(session).get_by_telegram_id(query.from_user.id)
    if not user or not UserRepository(session).has_telethon(user):
        await query.answer(
            results=[
                InlineQueryResultArticle(
                    id="hint:not_linked",
                    title=t(lang, "tg_inline_not_linked_title"),
                    description=t(lang, "tg_inline_not_linked_desc"),
                    input_message_content=InputTextMessageContent(
                        message_text=t(lang, "tg_inline_not_linked_desc"),
                    ),
                )
            ],
            cache_time=5,
            is_personal=True,
        )
        return

    try:
        channels = await get_channels_for_inline(state, user)
    except ValueError as exc:
        await query.answer(
            results=[
                InlineQueryResultArticle(
                    id="hint:error",
                    title=t(lang, "tg_inline_fetch_failed_title"),
                    description=str(exc),
                    input_message_content=InputTextMessageContent(message_text=str(exc)),
                )
            ],
            cache_time=5,
            is_personal=True,
        )
        return

    matched = filter_channels(channels, query.query)
    sources = await SourceRepository(session).list_all_for_user(user.id)
    active = {s.telegram_source.lower().removeprefix("@") for s in sources if s.is_active}
    matched = sort_channels_for_picker(matched, active)[:_MAX_RESULTS]
    if not matched:
        await query.answer(
            results=[
                InlineQueryResultArticle(
                    id="hint:empty",
                    title=t(lang, "tg_picker_empty"),
                    description=t(lang, "tg_inline_type_to_search"),
                    input_message_content=InputTextMessageContent(
                        message_text=t(lang, "tg_picker_empty"),
                    ),
                )
            ],
            cache_time=5,
            is_personal=True,
        )
        return

    results: list[InlineQueryResultArticle] = []
    for ch in matched:
        username = ch.username if ch.username.startswith("@") else f"@{ch.username}"
        key = username.lower().removeprefix("@")
        selected = key in active
        mark = "✅ " if selected else ""
        action = t(lang, "tg_inline_tap_remove") if selected else t(lang, "tg_inline_tap_add")
        results.append(
            InlineQueryResultArticle(
                id=channel_result_id(username),
                title=f"{mark}{ch.title[:56]}",
                description=f"{username} · {action}",
                input_message_content=InputTextMessageContent(
                    message_text=f"✓ {username}",
                ),
            )
        )

    await state.update_data(tg_inline_picking=True)
    await query.answer(results=results, cache_time=0, is_personal=True)


@router.chosen_inline_result()
async def inline_channel_chosen(
    result: ChosenInlineResult,
    bot: Bot,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    username = username_from_result_id(result.result_id)
    if not username:
        return

    lang = await resolve_lang(session, result.from_user.id)
    await apply_inline_channel_pick(
        bot,
        state,
        session,
        lang,
        result.from_user.id,
        username,
    )


@router.message(F.text.startswith(_INLINE_PICK_PREFIX))
async def inline_pick_message(
    message: Message,
    bot: Bot,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    lang = await resolve_lang(session, message.from_user.id)
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    if not user:
        return

    channels_cache = None
    try:
        channels_cache = await get_channels_for_inline(state, user)
    except ValueError:
        pass

    username = username_from_pick_message(message.text or "", channels_cache)
    if not username:
        try:
            await message.delete()
        except Exception:
            pass
        return

    await apply_inline_channel_pick(
        bot,
        state,
        session,
        lang,
        message.from_user.id,
        username,
        chat_id=message.chat.id,
    )

    try:
        await message.delete()
    except Exception:
        pass
