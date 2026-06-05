from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import (
    CB_ACTION_MENU,
    CB_GMAIL_CHECK,
    CB_GMAIL_DISCONNECT,
    CB_GMAIL_PASTE,
    CB_SRC_ADD,
    CB_SRC_DONE,
    CB_SRC_REMOVE,
)
from app.bot.screen import edit_by_state, edit_from_callback, replace_screen
from app.bot.states import OnboardingStates
from app.config import get_settings
from app.i18n import t
from app.repositories.source_repository import SourceRepository
from app.repositories.user_repository import UserRepository
from app.services.gmail_service import GmailService
from app.services.user_sources import has_gmail
from app.utils.links import parse_channel_links
from app.web.gmail_oauth import create_oauth_state


def _format_channels_list(sources, lang: str) -> str:
    if not sources:
        return t(lang, "sources_list_empty")
    lines = [t(lang, "sources_list_header", count=len(sources))]
    for source in sources:
        lines.append(f"• {source.telegram_source}")
    return "\n".join(lines)


def _format_gmail_status(user, lang: str) -> str:
    if has_gmail(user):
        return t(lang, "gmail_status_linked", email=user.gmail_email or "Gmail")
    return t(lang, "gmail_status_not_linked")


def _format_hub_text(user, sources, lang: str, *, onboarding: bool) -> str:
    header = t(lang, "step_sources") if onboarding else t(lang, "sources_manage")
    return (
        f"{header}\n\n"
        f"<b>Telegram</b>\n{_format_channels_list(sources, lang)}\n\n"
        f"<b>Gmail</b>\n{_format_gmail_status(user, lang)}"
    )


def build_sources_hub_keyboard(
    lang: str,
    sources,
    telegram_id: int,
    user,
    *,
    onboarding: bool,
) -> InlineKeyboardMarkup:
    settings = get_settings()
    gmail = GmailService(settings)
    linked = has_gmail(user)
    rows: list[list[InlineKeyboardButton]] = []

    for source in sources or []:
        from app.utils.links import channel_username

        key = channel_username(source.telegram_source)
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"🗑 {source.telegram_source}",
                    callback_data=f"{CB_SRC_REMOVE}:{key}",
                )
            ]
        )

    rows.append([InlineKeyboardButton(text=t(lang, "btn_add_source"), callback_data=CB_SRC_ADD)])

    if not linked and gmail.is_configured():
        auth_url = gmail.build_auth_url(create_oauth_state(telegram_id))
        rows.append([InlineKeyboardButton(text=t(lang, "btn_gmail_connect"), url=auth_url)])
        if settings.gmail_redirect_is_localhost():
            rows.append(
                [
                    InlineKeyboardButton(text=t(lang, "btn_gmail_paste"), callback_data=CB_GMAIL_PASTE),
                    InlineKeyboardButton(text=t(lang, "btn_gmail_check"), callback_data=CB_GMAIL_CHECK),
                ]
            )
        else:
            rows.append(
                [InlineKeyboardButton(text=t(lang, "btn_gmail_check"), callback_data=CB_GMAIL_CHECK)]
            )
    elif linked:
        rows.append(
            [InlineKeyboardButton(text=t(lang, "btn_gmail_disconnect"), callback_data=CB_GMAIL_DISCONNECT)]
        )

    if sources or linked:
        rows.append([InlineKeyboardButton(text=t(lang, "btn_continue"), callback_data=CB_SRC_DONE)])

    if not onboarding:
        rows.append([InlineKeyboardButton(text=t(lang, "btn_menu"), callback_data=CB_ACTION_MENU)])

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def show_sources_onboarding(
    target: Message,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
    telegram_id: int,
) -> None:
    await refresh_sources_screen(
        target,
        state,
        session,
        lang,
        telegram_id,
        onboarding=True,
    )


async def show_sources_manage(
    target: Message,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
    telegram_id: int,
) -> None:
    await refresh_sources_screen(
        target,
        state,
        session,
        lang,
        telegram_id,
        onboarding=False,
    )


async def show_add_source_prompt(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
) -> None:
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    onboarding = bool(user and not user.onboarding_complete)
    await state.update_data(sources_onboarding=onboarding)
    await state.set_state(OnboardingStates.waiting_add_source)
    await edit_from_callback(callback, state, t(lang, "sources_add_prompt"), None)


async def process_source_links(
    message: Message,
    session: AsyncSession,
    text: str,
) -> tuple[int, int, list[str]]:
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    if not user:
        return 0, 0, []

    links = parse_channel_links(text)
    if not links:
        return 0, 0, []

    repo = SourceRepository(session)
    new_count = 0
    dup_count = 0
    for link in links:
        result = await repo.add_source(user.id, link)
        if result == "new":
            new_count += 1
        elif result == "exists":
            dup_count += 1
    await session.commit()
    return new_count, dup_count, []


async def _render_sources_screen(
    target: Message,
    state: FSMContext,
    text: str,
    sources,
    user,
    lang: str,
    telegram_id: int,
    *,
    onboarding: bool,
) -> None:
    markup = build_sources_hub_keyboard(
        lang,
        sources,
        telegram_id,
        user,
        onboarding=onboarding,
    )
    data = await state.get_data()
    if data.get("screen_chat_id") and data.get("screen_message_id"):
        await edit_by_state(target.bot, state, text, markup)
    else:
        await replace_screen(target, state, text, markup)


async def refresh_sources_screen(
    target: Message,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
    telegram_id: int,
    *,
    onboarding: bool | None = None,
    status_line: str | None = None,
) -> None:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if not user:
        return

    if onboarding is None:
        data = await state.get_data()
        onboarding = data.get("sources_onboarding", not user.onboarding_complete)

    sources = await SourceRepository(session).list_all_for_user(user.id)
    if onboarding:
        await state.set_state(OnboardingStates.entering_sources)
    else:
        await state.set_state(OnboardingStates.managing_sources)

    text = _format_hub_text(user, sources, lang, onboarding=onboarding)
    if status_line:
        text += f"\n\n{status_line}"

    await _render_sources_screen(
        target,
        state,
        text,
        sources,
        user,
        lang,
        telegram_id,
        onboarding=onboarding,
    )


def source_key_from_callback(data: str) -> str:
    return data.split(":", 2)[2]
