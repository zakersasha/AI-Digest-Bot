from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import (
    CB_ACTION_MENU,
    CB_GMAIL_CHECK,
    CB_GMAIL_CONTINUE,
    CB_GMAIL_DISCONNECT,
    platform_keyboard,
)
from app.bot.screen import edit_by_state, edit_screen, replace_screen
from app.bot.states import OnboardingStates
from app.config import get_settings
from app.i18n import t
from app.repositories.user_repository import UserRepository
from app.services.gmail_service import GmailService
from app.web.gmail_oauth import create_oauth_state


def platform_label(lang: str, platform: str) -> str:
    key = "platform_gmail" if platform == "gmail" else "platform_telegram"
    return t(lang, key)


def build_gmail_connect_keyboard(
    lang: str,
    telegram_id: int,
    *,
    linked: bool,
    onboarding: bool,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    settings = get_settings()
    gmail = GmailService(settings)

    if not linked and gmail.is_configured():
        auth_url = gmail.build_auth_url(create_oauth_state(telegram_id))
        rows.append([InlineKeyboardButton(text=t(lang, "btn_gmail_connect"), url=auth_url)])
        rows.append([InlineKeyboardButton(text=t(lang, "btn_gmail_continue"), callback_data=CB_GMAIL_CHECK)])

    if linked:
        rows.append(
            [InlineKeyboardButton(text=t(lang, "btn_gmail_disconnect"), callback_data=CB_GMAIL_DISCONNECT)]
        )

    if onboarding and linked:
        rows.append([InlineKeyboardButton(text=t(lang, "btn_gmail_continue"), callback_data=CB_GMAIL_CONTINUE)])

    if not onboarding:
        rows.append([InlineKeyboardButton(text=t(lang, "btn_menu"), callback_data=CB_ACTION_MENU)])

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def show_platform_picker(
    target: Message,
    state: FSMContext,
    lang: str,
) -> None:
    await state.set_state(OnboardingStates.choosing_platform)
    await replace_screen(target, state, t(lang, "step_platform"), platform_keyboard(lang))


async def show_platform_menu(
    target: Message,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
    telegram_id: int,
) -> None:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if not user:
        return

    platform = user.content_platform or "telegram"
    text = t(lang, "platform_menu", platform=platform_label(lang, platform))
    await state.clear()
    await replace_screen(target, state, text, platform_keyboard(lang, current=platform))


async def show_gmail_screen(
    target: Message,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
    telegram_id: int,
    *,
    onboarding: bool = False,
    status_line: str | None = None,
) -> None:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if not user:
        return

    settings = get_settings()
    linked = UserRepository(session).has_gmail(user)
    text = t(lang, "gmail_connect", redirect=settings.gmail_redirect_uri)
    if linked and user.gmail_email:
        text = t(lang, "gmail_linked", email=user.gmail_email)
    if status_line:
        text += f"\n\n{status_line}"

    if onboarding:
        await state.set_state(OnboardingStates.connecting_gmail)

    markup = build_gmail_connect_keyboard(
        lang,
        telegram_id,
        linked=linked,
        onboarding=onboarding,
    )
    data = await state.get_data()
    if data.get("screen_chat_id") and data.get("screen_message_id"):
        await edit_by_state(target.bot, state, text, markup)
    else:
        await replace_screen(target, state, text, markup)
