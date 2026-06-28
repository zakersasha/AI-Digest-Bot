from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import (
    CB_ACTION_MENU,
    CB_FLOW_DIGEST,
    CB_FLOW_SCHEDULE,
    CB_GMAIL_CHECK,
    CB_GMAIL_DISCONNECT,
    CB_GMAIL_PASTE,
    CB_PLATFORM_GMAIL,
    CB_PLATFORM_SLACK,
    CB_LI_ADD_LINKS,
    CB_LI_DISCONNECT,
    CB_LI_PICK,
    CB_LI_PROFILES,
    CB_SLACK_CHANNELS,
    CB_SLACK_DISCONNECT,
    CB_SLACK_PASTE,
    CB_SLACK_PICK,
    CB_PLATFORM_LINKEDIN,
    CB_PLATFORM_TELEGRAM,
    CB_SCHEDULE_PREFIX,
    CB_LI_REMOVE_PREFIX,
    CB_SRC_ADD,
    CB_SRC_REMOVE,
    CB_TEST_DIGEST_PREFIX,
    CB_TG_ADD_LINKS,
    CB_TG_CHANNELS,
    CB_TG_CONNECT,
    CB_TG_DISCONNECT,
    CB_TG_PICK,
    CB_TG_QR_REFRESH,
)
from app.bot.screen import (
    _delete_screen,
    bind_screen,
    edit_by_state,
    edit_from_callback,
    edit_screen,
    replace_screen,
    replace_screen_at,
    screen_chat_id,
)
from app.bot.onboarding_flow import flow_step, is_guided, set_flow_step, step_text
from app.bot.states import OnboardingStates
from app.config import get_settings
from app.db.session import async_session_factory
from app.i18n import t
from app.platforms.registry import PLATFORMS, available_platforms, get_platform
from app.repositories.linkedin_profile_repository import LinkedInProfileRepository
from app.repositories.platform_settings_repository import PlatformSettingsRepository
from app.repositories.slack_channel_repository import SlackChannelRepository
from app.repositories.source_repository import SourceRepository
from app.repositories.user_repository import UserRepository
from app.services.gmail_service import GmailService
from app.services.linkedin_service import LinkedInService
from app.services.slack_service import SlackService
from app.services.platform_readiness import is_platform_scheduled
from app.bot.inline_channels import warm_channel_cache
from app.utils.oauth_state import create_oauth_state


def _tg_inline_pick_button(lang: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=t(lang, "btn_tg_pick_channels_dropdown"),
        switch_inline_query_current_chat="",
    )


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
        user_repo = UserRepository(session)
        if user_repo.has_telethon(user):
            count = await SourceRepository(session).count_active(user.id)
            if count:
                conn = t(lang, "platform_status_tg_linked_channels", phone=user.telegram_phone or "Telegram", count=str(count))
            else:
                conn = t(lang, "platform_status_tg_linked", phone=user.telegram_phone or "Telegram")
        else:
            count = await SourceRepository(session).count_active(user.id)
            conn = (
                t(lang, "platform_status_channels", count=str(count))
                if count
                else t(lang, "platform_not_connected")
            )
        return f"{conn} · {schedule}"

    if platform_id == "gmail":
        if UserRepository(session).has_gmail(user):
            conn = t(lang, "platform_status_gmail", email=user.gmail_email or "Gmail")
        else:
            conn = t(lang, "platform_not_connected")
        return f"{conn} · {schedule}"

    if platform_id == "slack":
        user_repo = UserRepository(session)
        count = await SlackChannelRepository(session).count_active(user.id)
        if user_repo.has_slack(user):
            if count:
                conn = t(
                    lang,
                    "platform_status_slack_channels",
                    team=user.slack_team_name or "Slack",
                    count=str(count),
                )
            else:
                conn = t(lang, "platform_status_slack", team=user.slack_team_name or "Slack")
        else:
            conn = t(lang, "platform_not_connected")
        return f"{conn} · {schedule}"

    if platform_id == "linkedin":
        user_repo = UserRepository(session)
        count = await LinkedInProfileRepository(session).count_active(user.id)
        if user_repo.has_linkedin(user):
            if count:
                conn = t(
                    lang,
                    "platform_status_li_linked_profiles",
                    name=user.linkedin_name or "LinkedIn",
                    count=str(count),
                )
            else:
                conn = t(lang, "platform_status_li_linked", name=user.linkedin_name or "LinkedIn")
        else:
            conn = (
                t(lang, "platform_status_li_profiles", count=str(count))
                if count
                else t(lang, "platform_not_connected")
            )
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

    guided = await is_guided(state)
    step = await flow_step(state)
    if guided and step == 2:
        lines = [step_text(lang, 2, "platforms_menu_onboarding")]
    elif user.onboarding_complete:
        lines = [t(lang, "platforms_menu_main")]
    else:
        lines = [t(lang, "platforms_menu")]
    rows: list[list[InlineKeyboardButton]] = []

    for pdef in available_platforms():
        status = await _platform_status_line(session, user, lang, pdef.id)
        lines.append(f"{pdef.emoji} <b>{t(lang, pdef.label_key)}</b> — {status}")
        cb = {
            "telegram": CB_PLATFORM_TELEGRAM,
            "gmail": CB_PLATFORM_GMAIL,
            "slack": CB_PLATFORM_SLACK,
        }.get(pdef.id, f"plat:{pdef.id}")
        rows.append(
            [InlineKeyboardButton(text=f"{pdef.emoji} {t(lang, pdef.label_key)}", callback_data=cb)]
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


def _telegram_keyboard(
    lang: str,
    *,
    linked: bool,
    channel_count: int,
    guided_step: int | None = None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    has_channels = channel_count > 0

    if guided_step == 4:
        rows.append(
            [InlineKeyboardButton(text=t(lang, "btn_get_digest"), callback_data=CB_FLOW_DIGEST)]
        )
        rows.append(
            [InlineKeyboardButton(text=t(lang, "btn_tg_channels", count=str(channel_count)), callback_data=CB_TG_CHANNELS)]
        )
        rows.append([InlineKeyboardButton(text=t(lang, "btn_back"), callback_data=CB_ACTION_MENU)])
        return InlineKeyboardMarkup(inline_keyboard=rows)

    if not linked:
        rows.append(
            [
                InlineKeyboardButton(text=t(lang, "btn_tg_connect"), callback_data=CB_TG_CONNECT),
                InlineKeyboardButton(text=t(lang, "btn_tg_add_links"), callback_data=CB_TG_ADD_LINKS),
            ]
        )
    else:
        rows.append(
            [InlineKeyboardButton(text=t(lang, "btn_tg_disconnect"), callback_data=CB_TG_DISCONNECT)]
        )

    if has_channels or linked:
        if linked:
            rows.append([_tg_inline_pick_button(lang)])
        else:
            rows.append(
                [
                    InlineKeyboardButton(
                        text=t(lang, "btn_tg_channels", count=str(channel_count)),
                        callback_data=CB_TG_CHANNELS,
                    )
                ]
            )

    if has_channels:
        if guided_step == 5:
            rows.append(
                [InlineKeyboardButton(text=t(lang, "btn_flow_schedule"), callback_data=CB_FLOW_SCHEDULE)]
            )
        elif not guided_step or guided_step > 5:
            rows.append(
                [
                    InlineKeyboardButton(text=t(lang, "btn_schedule"), callback_data=f"{CB_SCHEDULE_PREFIX}telegram"),
                    InlineKeyboardButton(text=t(lang, "btn_test_digest"), callback_data=f"{CB_TEST_DIGEST_PREFIX}telegram"),
                ]
            )

    rows.append([InlineKeyboardButton(text=t(lang, "btn_back"), callback_data=CB_ACTION_MENU)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def telegram_qr_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_tg_qr_refresh"), callback_data=CB_TG_QR_REFRESH)],
            [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data=CB_PLATFORM_TELEGRAM)],
        ]
    )


def _telegram_channels_keyboard(lang: str, sources, *, linked: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if linked:
        rows.append([_tg_inline_pick_button(lang)])
    rows.append([InlineKeyboardButton(text=t(lang, "btn_tg_add_links"), callback_data=CB_SRC_ADD)])
    rows.append([InlineKeyboardButton(text=t(lang, "btn_back"), callback_data=CB_PLATFORM_TELEGRAM)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _telegram_screen_body(
    state: FSMContext,
    session: AsyncSession,
    user,
    lang: str,
    *,
    linked: bool,
    sources,
    settings,
    status_line: str | None = None,
) -> tuple[str, InlineKeyboardMarkup]:
    guided = await is_guided(state)
    step = await flow_step(state)
    guided_step: int | None = None
    if guided:
        if step == 3:
            guided_step = 3
        elif step == 4 and sources:
            guided_step = 4
        elif step == 5:
            guided_step = 5

    if guided and step == 3:
        text = step_text(lang, 3, "telegram_step3")
    elif guided and step == 4 and sources:
        text = step_text(lang, 4, "step_get_digest")
        text += f"\n\n{t(lang, 'tg_channels_summary', count=str(len(sources)))}"
        text += f"\n\n{_format_channels_list(sources, lang)}"
    elif guided and step == 5:
        text = step_text(lang, 5, "step_set_schedule")
        text += f"\n\n{t(lang, 'tg_channels_summary', count=str(len(sources)))}"
    else:
        text = f"<b>{t(lang, 'platform_telegram')}</b>\n\n"
        text += _format_telegram_status(user, lang, linked, channel_count=len(sources))
        if not linked and not sources:
            text += f"\n\n{t(lang, 'telegram_screen_hint')}"
        elif sources:
            text += f"\n\n{t(lang, 'tg_channels_summary', count=str(len(sources)))}"
            text += f"\n\n{_format_channels_list(sources, lang)}"
        else:
            text += f"\n\n{t(lang, 'tg_no_channels_yet')}"
        if (sources or linked) and not guided:
            text += f"\n\n<b>{t(lang, 'schedule_label')}</b> {_schedule_line(lang, settings)}"

    if status_line:
        text += f"\n\n{status_line}"

    markup = _telegram_keyboard(
        lang,
        linked=linked,
        channel_count=len(sources),
        guided_step=guided_step,
    )
    return text, markup


async def push_telegram_screen(
    bot: Bot,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
    telegram_id: int,
    *,
    status_line: str | None = None,
    chat_id: int | None = None,
) -> None:
    resolved_chat = chat_id or await screen_chat_id(state)
    if not resolved_chat:
        return
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if not user:
        return
    await session.refresh(user)
    user_repo = UserRepository(session)
    linked = user_repo.has_telethon(user)
    if linked:
        try:
            await warm_channel_cache(state, user)
        except ValueError:
            pass
    sources = await SourceRepository(session).list_all_for_user(user.id)
    settings = await PlatformSettingsRepository(session).get(user.id, "telegram")
    text, markup = await _telegram_screen_body(
        state, session, user, lang, linked=linked, sources=sources, settings=settings, status_line=status_line
    )
    await state.set_state(OnboardingStates.managing_sources)
    await state.update_data(active_platform="telegram", tg_ui="main")
    data = await state.get_data()
    if data.get("screen_chat_id") and data.get("screen_message_id"):
        await edit_by_state(bot, state, text, markup)
    else:
        await replace_screen_at(bot, state, resolved_chat, text, markup)


async def push_telegram_channels_screen(
    bot: Bot,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
    telegram_id: int,
    *,
    status_line: str | None = None,
    chat_id: int | None = None,
) -> None:
    resolved_chat = chat_id or await screen_chat_id(state)
    if not resolved_chat:
        return
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if not user:
        return

    user_repo = UserRepository(session)
    linked = user_repo.has_telethon(user)
    sources = await SourceRepository(session).list_all_for_user(user.id)
    guided = await is_guided(state)
    step = await flow_step(state)
    if guided and step == 3:
        text = step_text(lang, 3, "tg_channels_screen_body")
    else:
        text = f"<b>{t(lang, 'tg_channels_screen_title')}</b>\n\n"
        if linked:
            text += f"{t(lang, 'tg_channels_screen_hint_linked')}\n\n"
        else:
            text += f"{t(lang, 'tg_channels_screen_hint_manual')}\n\n"
    text += _format_channels_list(sources, lang)
    if status_line:
        text += f"\n\n{status_line}"

    await state.set_state(OnboardingStates.managing_sources)
    await state.update_data(active_platform="telegram", tg_ui="channels")
    markup = _telegram_channels_keyboard(lang, sources, linked=linked)
    data = await state.get_data()
    if data.get("screen_chat_id") and data.get("screen_message_id"):
        await edit_by_state(bot, state, text, markup)
    else:
        await replace_screen_at(bot, state, resolved_chat, text, markup)


async def show_telegram_screen(
    target: Message,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
    telegram_id: int,
    *,
    status_line: str | None = None,
    from_user_action: bool = False,
) -> None:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if not user:
        return
    await session.refresh(user)

    user_repo = UserRepository(session)
    linked = user_repo.has_telethon(user)
    if linked:
        try:
            await warm_channel_cache(state, user)
        except ValueError:
            pass

    sources = await SourceRepository(session).list_all_for_user(user.id)
    settings = await PlatformSettingsRepository(session).get(user.id, "telegram")
    text, markup = await _telegram_screen_body(
        state, session, user, lang, linked=linked, sources=sources, settings=settings, status_line=status_line
    )

    await state.set_state(OnboardingStates.managing_sources)
    await state.update_data(active_platform="telegram", tg_ui="main")
    data = await state.get_data()
    if from_user_action:
        await replace_screen(target, state, text, markup)
    elif data.get("screen_chat_id") and data.get("screen_message_id"):
        await edit_by_state(target.bot, state, text, markup)
    else:
        await replace_screen(target, state, text, markup)


def _format_telegram_status(user, lang: str, linked: bool, *, channel_count: int = 0) -> str:
    if linked:
        return t(lang, "tg_status_linked", phone=user.telegram_phone or "Telegram")
    if channel_count > 0:
        return t(lang, "tg_status_manual")
    return t(lang, "tg_status_not_linked")


async def show_telegram_channels_screen(
    target: Message,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
    telegram_id: int,
    *,
    status_line: str | None = None,
    from_user_action: bool = False,
) -> None:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if not user:
        return

    user_repo = UserRepository(session)
    linked = user_repo.has_telethon(user)
    sources = await SourceRepository(session).list_all_for_user(user.id)
    guided = await is_guided(state)
    step = await flow_step(state)
    if guided and step == 3:
        text = step_text(lang, 3, "tg_channels_screen_body")
    else:
        text = f"<b>{t(lang, 'tg_channels_screen_title')}</b>\n\n"
        if linked:
            text += f"{t(lang, 'tg_channels_screen_hint_linked')}\n\n"
        else:
            text += f"{t(lang, 'tg_channels_screen_hint_manual')}\n\n"
    text += _format_channels_list(sources, lang)
    if status_line:
        text += f"\n\n{status_line}"

    await state.set_state(OnboardingStates.managing_sources)
    await state.update_data(active_platform="telegram", tg_ui="channels")
    markup = _telegram_channels_keyboard(lang, sources, linked=linked)
    data = await state.get_data()
    if from_user_action:
        await replace_screen(target, state, text, markup)
    elif data.get("screen_chat_id") and data.get("screen_message_id"):
        await edit_by_state(target.bot, state, text, markup)
    else:
        await replace_screen(target, state, text, markup)


def _format_channels_list(sources, lang: str) -> str:
    if not sources:
        return t(lang, "sources_list_empty")
    lines = [t(lang, "sources_list_header", count=len(sources))]
    for source in sources:
        if source.title and source.title != source.telegram_source:
            lines.append(f"• {source.telegram_source} — {source.title}")
        else:
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
    from_user_action: bool = False,
) -> None:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if not user:
        return
    await session.refresh(user)

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
    if from_user_action:
        await _delete_screen(target.bot, state)
        await bind_screen(state, target)
        await edit_screen(target, state, text, markup)
    elif data.get("screen_chat_id") and data.get("screen_message_id"):
        await edit_by_state(target.bot, state, text, markup)
    else:
        await replace_screen(target, state, text, markup)


def _format_gmail_status(user, lang: str) -> str:
    if user.gmail_tokens_encrypted:
        return t(lang, "gmail_status_linked", email=user.gmail_email or "Gmail")
    return t(lang, "gmail_status_not_linked")


def _slack_keyboard(lang: str, telegram_id: int, user, linked: bool, channel_count: int) -> InlineKeyboardMarkup:
    settings = get_settings()
    slack = SlackService(settings)
    rows: list[list[InlineKeyboardButton]] = []

    if not linked and slack.is_configured():
        auth_url = slack.build_auth_url(create_oauth_state(telegram_id))
        rows.append([InlineKeyboardButton(text=t(lang, "btn_slack_connect"), url=auth_url)])
        if settings.slack_redirect_is_localhost():
            rows.append(
                [
                    InlineKeyboardButton(text=t(lang, "btn_slack_paste"), callback_data=CB_SLACK_PASTE),
                ]
            )
    elif linked:
        rows.append(
            [InlineKeyboardButton(text=t(lang, "btn_slack_disconnect"), callback_data=CB_SLACK_DISCONNECT)]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_slack_channels", count=str(channel_count)),
                    callback_data=CB_SLACK_CHANNELS,
                )
            ]
        )
        if channel_count > 0:
            rows.append(
                [InlineKeyboardButton(text=t(lang, "btn_schedule"), callback_data=f"{CB_SCHEDULE_PREFIX}slack")]
            )
            rows.append(
                [InlineKeyboardButton(text=t(lang, "btn_test_digest"), callback_data=f"{CB_TEST_DIGEST_PREFIX}slack")]
            )

    rows.append([InlineKeyboardButton(text=t(lang, "btn_back"), callback_data=CB_ACTION_MENU)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def show_slack_screen(
    target: Message,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
    telegram_id: int,
    *,
    status_line: str | None = None,
    from_user_action: bool = False,
) -> None:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if not user:
        return
    await session.refresh(user)

    linked = UserRepository(session).has_slack(user)
    channel_count = await SlackChannelRepository(session).count_active(user.id)
    settings = await PlatformSettingsRepository(session).get(user.id, "slack")
    text = f"<b>{t(lang, 'platform_slack')}</b>\n\n{t(lang, 'slack_screen_hint')}\n\n"
    if linked:
        text += t(lang, "slack_status_linked", team=user.slack_team_name or "Slack")
        if channel_count:
            text += f"\n{t(lang, 'slack_channels_summary', count=str(channel_count))}"
        else:
            text += f"\n{t(lang, 'slack_no_channels_yet')}"
        text += f"\n\n<b>{t(lang, 'schedule_label')}</b> {_schedule_line(lang, settings)}"
    else:
        text += t(lang, "slack_status_not_linked")
    if status_line:
        text += f"\n\n{status_line}"

    await state.set_state(OnboardingStates.connecting_slack)
    await state.update_data(active_platform="slack")
    markup = _slack_keyboard(lang, telegram_id, user, linked, channel_count)
    data = await state.get_data()
    if from_user_action:
        await _delete_screen(target.bot, state)
        await bind_screen(state, target)
        await edit_screen(target, state, text, markup)
    elif data.get("screen_chat_id") and data.get("screen_message_id"):
        await edit_by_state(target.bot, state, text, markup)
    else:
        await replace_screen(target, state, text, markup)


def _linkedin_keyboard(lang: str, telegram_id: int, user, linked: bool, profile_count: int) -> InlineKeyboardMarkup:
    settings = get_settings()
    li = LinkedInService(settings)
    rows: list[list[InlineKeyboardButton]] = []

    if not linked:
        if li.is_configured():
            auth_url = li.build_auth_url(create_oauth_state(telegram_id))
            rows.append(
                [
                    InlineKeyboardButton(text=t(lang, "btn_li_connect"), url=auth_url),
                    InlineKeyboardButton(text=t(lang, "btn_li_add_links"), callback_data=CB_LI_ADD_LINKS),
                ]
            )
        else:
            rows.append(
                [InlineKeyboardButton(text=t(lang, "btn_li_add_links"), callback_data=CB_LI_ADD_LINKS)]
            )
    elif linked:
        rows.append(
            [InlineKeyboardButton(text=t(lang, "btn_li_disconnect"), callback_data=CB_LI_DISCONNECT)]
        )

    has_profiles = profile_count > 0
    if has_profiles or linked:
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_li_profiles", count=str(profile_count)),
                    callback_data=CB_LI_PROFILES,
                )
            ]
        )

    if has_profiles:
        rows.append(
            [
                InlineKeyboardButton(text=t(lang, "btn_schedule"), callback_data=f"{CB_SCHEDULE_PREFIX}linkedin"),
                InlineKeyboardButton(text=t(lang, "btn_test_digest"), callback_data=f"{CB_TEST_DIGEST_PREFIX}linkedin"),
            ]
        )

    rows.append([InlineKeyboardButton(text=t(lang, "btn_back"), callback_data=CB_ACTION_MENU)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _linkedin_profiles_keyboard(lang: str, profiles, *, linked: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if linked:
        rows.append([InlineKeyboardButton(text=t(lang, "btn_li_pick_profiles"), callback_data=CB_LI_PICK)])
    rows.append([InlineKeyboardButton(text=t(lang, "btn_li_add_links"), callback_data=CB_LI_ADD_LINKS)])
    for profile in profiles:
        label = profile.title or profile.profile_slug
        if len(label) > 28:
            label = label[:28]
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"🗑 {label}",
                    callback_data=f"{CB_LI_REMOVE_PREFIX}{profile.profile_slug}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text=t(lang, "btn_back"), callback_data=CB_PLATFORM_LINKEDIN)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _format_linkedin_status(user, lang: str, linked: bool, *, profile_count: int = 0) -> str:
    if linked:
        return t(lang, "li_status_linked", name=user.linkedin_name or "LinkedIn")
    if profile_count > 0:
        return t(lang, "li_status_manual")
    return t(lang, "li_status_not_linked")


def _format_profiles_list(profiles, lang: str) -> str:
    if not profiles:
        return t(lang, "li_profiles_list_empty")
    lines = [t(lang, "li_profiles_list_header", count=len(profiles))]
    for profile in profiles:
        title = profile.title or profile.profile_slug
        lines.append(f"• {title}")
    return "\n".join(lines)


async def push_linkedin_screen(
    bot: Bot,
    storage,
    telegram_id: int,
    lang: str,
    *,
    status_line: str | None = None,
) -> None:
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.storage.base import StorageKey

    state = FSMContext(
        storage=storage,
        key=StorageKey(bot_id=bot.id, chat_id=telegram_id, user_id=telegram_id),
    )
    chat_id = await screen_chat_id(state)
    if not chat_id:
        return

    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(telegram_id)
        if not user:
            return
        await session.refresh(user)
        user_repo = UserRepository(session)
        linked = user_repo.has_linkedin(user)
        profiles = await LinkedInProfileRepository(session).list_all_for_user(user.id)
        settings = await PlatformSettingsRepository(session).get(user.id, "linkedin")
        text = f"<b>{t(lang, 'platform_linkedin')}</b>\n\n"
        text += _format_linkedin_status(user, lang, linked, profile_count=len(profiles))
        if not linked and not profiles:
            text += f"\n\n{t(lang, 'li_screen_hint')}"
        elif profiles:
            text += f"\n\n{t(lang, 'li_profiles_summary', count=str(len(profiles)))}"
        else:
            text += f"\n\n{t(lang, 'li_no_profiles_yet')}"
        if profiles or linked:
            text += f"\n\n<b>{t(lang, 'schedule_label')}</b> {_schedule_line(lang, settings)}"
        if status_line:
            text += f"\n\n{status_line}"
        await state.set_state(OnboardingStates.connecting_linkedin)
        await state.update_data(active_platform="linkedin", li_ui="main")
        markup = _linkedin_keyboard(lang, telegram_id, user, linked, len(profiles))
        await replace_screen_at(bot, state, chat_id, text, markup)


async def show_linkedin_screen(
    target: Message,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
    telegram_id: int,
    *,
    status_line: str | None = None,
    from_user_action: bool = False,
) -> None:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if not user:
        return
    await session.refresh(user)

    user_repo = UserRepository(session)
    linked = user_repo.has_linkedin(user)
    profiles = await LinkedInProfileRepository(session).list_all_for_user(user.id)
    settings = await PlatformSettingsRepository(session).get(user.id, "linkedin")
    text = f"<b>{t(lang, 'platform_linkedin')}</b>\n\n"
    text += _format_linkedin_status(user, lang, linked, profile_count=len(profiles))
    if not linked and not profiles:
        text += f"\n\n{t(lang, 'li_screen_hint')}"
    elif profiles:
        text += f"\n\n{t(lang, 'li_profiles_summary', count=str(len(profiles)))}"
    else:
        text += f"\n\n{t(lang, 'li_no_profiles_yet')}"
    if profiles or linked:
        text += f"\n\n<b>{t(lang, 'schedule_label')}</b> {_schedule_line(lang, settings)}"
    if status_line:
        text += f"\n\n{status_line}"

    await state.set_state(OnboardingStates.connecting_linkedin)
    await state.update_data(active_platform="linkedin", li_ui="main")
    markup = _linkedin_keyboard(lang, telegram_id, user, linked, len(profiles))
    data = await state.get_data()
    if from_user_action:
        await _delete_screen(target.bot, state)
        await bind_screen(state, target)
        await edit_screen(target, state, text, markup)
    elif data.get("screen_chat_id") and data.get("screen_message_id"):
        await edit_by_state(target.bot, state, text, markup)
    else:
        await replace_screen(target, state, text, markup)


async def show_linkedin_profiles_screen(
    target: Message,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
    telegram_id: int,
    *,
    status_line: str | None = None,
    from_user_action: bool = False,
) -> None:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if not user:
        return

    user_repo = UserRepository(session)
    linked = user_repo.has_linkedin(user)
    profiles = await LinkedInProfileRepository(session).list_all_for_user(user.id)
    text = f"<b>{t(lang, 'li_profiles_screen_title')}</b>\n\n"
    if linked:
        text += f"{t(lang, 'li_profiles_screen_hint_linked')}\n\n"
    else:
        text += f"{t(lang, 'li_profiles_screen_hint_manual')}\n\n"
    text += _format_profiles_list(profiles, lang)
    if status_line:
        text += f"\n\n{status_line}"

    await state.set_state(OnboardingStates.connecting_linkedin)
    await state.update_data(active_platform="linkedin", li_ui="profiles")
    markup = _linkedin_profiles_keyboard(lang, profiles, linked=linked)
    data = await state.get_data()
    if from_user_action:
        await _delete_screen(target.bot, state)
        await bind_screen(state, target)
        await edit_screen(target, state, text, markup)
    elif data.get("screen_chat_id") and data.get("screen_message_id"):
        await edit_by_state(target.bot, state, text, markup)
    else:
        await replace_screen(target, state, text, markup)


async def show_schedule_frequency(
    callback: CallbackQuery,
    state: FSMContext,
    lang: str,
    platform: str,
) -> None:
    from app.bot.keyboards import frequency_keyboard
    from app.bot.onboarding_flow import flow_step, is_guided, step_text

    await state.update_data(scheduling_platform=platform, active_platform=platform)
    guided = await is_guided(state)
    step = await flow_step(state)
    if guided and step == 5:
        text = step_text(lang, 5, "step_set_schedule")
        text += f"\n\n{t(lang, 'step_frequency_platform', platform=t(lang, f'platform_{platform}'))}"
    else:
        text = t(lang, "step_frequency_platform", platform=t(lang, f"platform_{platform}"))
    await edit_from_callback(
        callback,
        state,
        text,
        frequency_keyboard(lang, platform=platform),
    )
