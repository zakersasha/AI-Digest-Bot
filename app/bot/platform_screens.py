from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import (
    CB_ACTION_MENU,
    CB_GMAIL_CHECK,
    CB_GMAIL_DISCONNECT,
    CB_GMAIL_PASTE,
    CB_PLATFORM_GMAIL,
    CB_PLATFORM_LINKEDIN,
    CB_PLATFORM_TELEGRAM,
    CB_SCHEDULE_PREFIX,
    CB_SRC_ADD,
    CB_SRC_REMOVE,
    CB_TEST_DIGEST_PREFIX,
)
from app.bot.screen import edit_by_state, edit_from_callback, replace_screen
from app.bot.states import OnboardingStates
from app.config import get_settings
from app.i18n import t
from app.platforms.registry import PLATFORMS, available_platforms, get_platform
from app.repositories.platform_settings_repository import PlatformSettingsRepository
from app.repositories.source_repository import SourceRepository
from app.repositories.user_repository import UserRepository
from app.services.gmail_service import GmailService
from app.services.platform_readiness import is_platform_scheduled
from app.web.gmail_oauth import create_oauth_state


def _format_time(hour: int, minute: int) -> str:
    return f"{hour:02d}:{minute:02d}"


def _schedule_line(lang: str, settings) -> str:
    if not is_platform_scheduled(settings):
        return t(lang, "schedule_not_set")
    freq = t(lang, f"freq_{settings.digest_frequency}")
    time_str = _format_time(settings.delivery_hour or 0, settings.delivery_minute or 0)
    return t(lang, "schedule_short", frequency=freq, time=time_str)


async def _platform_status_line(
    session: AsyncSession,
    user,
    lang: str,
    platform_id: str,
) -> str:
    p = get_platform(platform_id)
    if not p or not p.available:
        return t(lang, "platform_coming_soon")

    settings = await PlatformSettingsRepository(session).get(user.id, platform_id)
    schedule = _schedule_line(lang, settings)

    if platform_id == "telegram":
        count = await SourceRepository(session).count_active(user.id)
        conn = t(lang, "platform_status_channels", count=str(count)) if count else t(lang, "platform_not_connected")
        return f"{conn} · {schedule}"

    if platform_id == "gmail":
        if UserRepository(session).has_gmail(user):
            conn = t(lang, "platform_status_gmail", email=user.gmail_email or "Gmail")
        else:
            conn = t(lang, "platform_not_connected")
        return f"{conn} · {schedule}"

    return schedule


async def show_platforms_menu(
    target: Message,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
    telegram_id: int,
) -> None:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if not user:
        return

    lines = [t(lang, "platforms_menu")]
    rows: list[list[InlineKeyboardButton]] = []

    for pdef in PLATFORMS:
        status = await _platform_status_line(session, user, lang, pdef.id)
        lines.append(f"{pdef.emoji} <b>{t(lang, pdef.label_key)}</b> — {status}")
        if pdef.available:
            cb = {
                "telegram": CB_PLATFORM_TELEGRAM,
                "gmail": CB_PLATFORM_GMAIL,
            }.get(pdef.id, f"plat:{pdef.id}")
            rows.append(
                [InlineKeyboardButton(text=f"{pdef.emoji} {t(lang, pdef.label_key)}", callback_data=cb)]
            )
        else:
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"{pdef.emoji} {t(lang, pdef.label_key)} ({t(lang, 'soon')})",
                        callback_data=CB_PLATFORM_LINKEDIN,
                    )
                ]
            )

    text = "\n\n".join(lines)
    markup = InlineKeyboardMarkup(inline_keyboard=rows)

    data = await state.get_data()
    screen_chat_id = data.get("screen_chat_id")
    screen_message_id = data.get("screen_message_id")
    await state.set_state(None)
    if screen_chat_id and screen_message_id:
        await state.update_data(
            screen_chat_id=screen_chat_id,
            screen_message_id=screen_message_id,
        )
        await edit_by_state(target.bot, state, text, markup)
    else:
        await replace_screen(target, state, text, markup)


def _telegram_keyboard(lang: str, sources, *, has_channels: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for source in sources:
        from app.utils.links import channel_username

        key = channel_username(source.telegram_source)
        rows.append(
            [InlineKeyboardButton(text=f"🗑 {source.telegram_source}", callback_data=f"{CB_SRC_REMOVE}:{key}")]
        )
    rows.append([InlineKeyboardButton(text=t(lang, "btn_add_source"), callback_data=CB_SRC_ADD)])
    rows.append([InlineKeyboardButton(text=t(lang, "btn_schedule"), callback_data=f"{CB_SCHEDULE_PREFIX}telegram")])
    if has_channels:
        rows.append(
            [InlineKeyboardButton(text=t(lang, "btn_test_digest"), callback_data=f"{CB_TEST_DIGEST_PREFIX}telegram")]
        )
    rows.append([InlineKeyboardButton(text=t(lang, "btn_back"), callback_data=CB_ACTION_MENU)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def show_telegram_screen(
    target: Message,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
    telegram_id: int,
    *,
    status_line: str | None = None,
) -> None:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if not user:
        return

    sources = await SourceRepository(session).list_all_for_user(user.id)
    settings = await PlatformSettingsRepository(session).get(user.id, "telegram")
    text = (
        f"<b>{t(lang, 'platform_telegram')}</b>\n\n"
        f"{t(lang, 'telegram_screen_hint')}\n\n"
        f"{_format_channels_list(sources, lang)}\n\n"
        f"<b>{t(lang, 'schedule_label')}</b> {_schedule_line(lang, settings)}"
    )
    if status_line:
        text += f"\n\n{status_line}"

    await state.set_state(OnboardingStates.managing_sources)
    await state.update_data(active_platform="telegram")
    markup = _telegram_keyboard(lang, sources, has_channels=bool(sources))
    data = await state.get_data()
    if data.get("screen_chat_id") and data.get("screen_message_id"):
        await edit_by_state(target.bot, state, text, markup)
    else:
        await replace_screen(target, state, text, markup)


def _format_channels_list(sources, lang: str) -> str:
    if not sources:
        return t(lang, "sources_list_empty")
    lines = [t(lang, "sources_list_header", count=len(sources))]
    for source in sources:
        lines.append(f"• {source.telegram_source}")
    return "\n".join(lines)


def _gmail_keyboard(lang: str, telegram_id: int, user, linked: bool) -> InlineKeyboardMarkup:
    settings = get_settings()
    gmail = GmailService(settings)
    rows: list[list[InlineKeyboardButton]] = []

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
    elif linked:
        rows.append(
            [InlineKeyboardButton(text=t(lang, "btn_gmail_disconnect"), callback_data=CB_GMAIL_DISCONNECT)]
        )
        rows.append(
            [InlineKeyboardButton(text=t(lang, "btn_schedule"), callback_data=f"{CB_SCHEDULE_PREFIX}gmail")]
        )
        rows.append(
            [InlineKeyboardButton(text=t(lang, "btn_test_digest"), callback_data=f"{CB_TEST_DIGEST_PREFIX}gmail")]
        )

    rows.append([InlineKeyboardButton(text=t(lang, "btn_back"), callback_data=CB_ACTION_MENU)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def show_gmail_screen(
    target: Message,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
    telegram_id: int,
    *,
    status_line: str | None = None,
) -> None:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if not user:
        return

    linked = UserRepository(session).has_gmail(user)
    settings = await PlatformSettingsRepository(session).get(user.id, "gmail")
    text = f"<b>{t(lang, 'platform_gmail')}</b>\n\n{t(lang, 'gmail_screen_hint')}\n\n"
    text += _format_gmail_status(user, lang)
    if linked:
        text += f"\n\n<b>{t(lang, 'schedule_label')}</b> {_schedule_line(lang, settings)}"
    if status_line:
        text += f"\n\n{status_line}"

    await state.set_state(OnboardingStates.connecting_gmail)
    await state.update_data(active_platform="gmail")
    markup = _gmail_keyboard(lang, telegram_id, user, linked)
    data = await state.get_data()
    if data.get("screen_chat_id") and data.get("screen_message_id"):
        await edit_by_state(target.bot, state, text, markup)
    else:
        await replace_screen(target, state, text, markup)


def _format_gmail_status(user, lang: str) -> str:
    if user.gmail_tokens_encrypted:
        return t(lang, "gmail_status_linked", email=user.gmail_email or "Gmail")
    return t(lang, "gmail_status_not_linked")


async def show_linkedin_screen(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    await callback.answer(t(lang, "platform_coming_soon"), show_alert=True)


async def show_schedule_frequency(
    callback: CallbackQuery,
    state: FSMContext,
    lang: str,
    platform: str,
) -> None:
    from app.bot.keyboards import frequency_keyboard

    await state.update_data(scheduling_platform=platform, active_platform=platform)
    await edit_from_callback(
        callback,
        state,
        t(lang, "step_frequency_platform", platform=t(lang, f"platform_{platform}")),
        frequency_keyboard(lang, platform=platform),
    )
