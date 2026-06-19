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

    matched = filter_channels(channels, query.query)[:_MAX_RESULTS]
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

    sources = await SourceRepository(session).list_all_for_user(user.id)
    active = {s.telegram_source.lower() for s in sources if s.is_active}

    results: list[InlineQueryResultArticle] = []
    for ch in matched:
        username = ch.username if ch.username.startswith("@") else f"@{ch.username}"
        mark = "✅ " if username.lower() in active else ""
        results.append(
            InlineQueryResultArticle(
                id=channel_result_id(username),
                title=f"{mark}{ch.title[:64]}",
                description=username,
                input_message_content=InputTextMessageContent(
                    message_text=f"✓ {ch.title}",
                ),
            )
        )

    await state.update_data(tg_inline_picking=True)
    await query.answer(results=results, cache_time=5, is_personal=True)


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
    user = await UserRepository(session).get_by_telegram_id(result.from_user.id)
    if not user:
        return

    repo = SourceRepository(session)
    sources = await repo.list_all_for_user(user.id)
    active = {s.telegram_source.lower() for s in sources if s.is_active}
    key = username.lower()

    if key in active:
        await repo.remove_source(user.id, username)
        await session.commit()
        status = t(lang, "source_removed")
    else:
        title = username
        try:
            channels = await get_channels_for_inline(state, user)
            title = next(
                (ch.title for ch in channels if ch.username.lower() == username.lower()),
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
            result.from_user.id,
            status_line=status,
        )
    else:
        await push_telegram_screen(
            bot,
            state,
            session,
            lang,
            result.from_user.id,
            status_line=status,
        )


@router.message(F.text.startswith("✓ "))
async def inline_pick_cleanup(message: Message) -> None:
    try:
        await message.delete()
    except Exception:
        pass
