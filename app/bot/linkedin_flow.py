from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import CB_PLATFORM_LINKEDIN, CB_LI_PROFILES
from app.bot.platform_screens import show_linkedin_profiles_screen, show_linkedin_screen
from app.bot.screen import edit_from_callback
from app.bot.states import OnboardingStates
from app.i18n import t
from app.repositories.linkedin_profile_repository import LinkedInProfileRepository
from app.repositories.user_repository import UserRepository
from app.utils.linkedin_links import parse_linkedin_profiles


def _add_links_back_keyboard(lang: str, li_ui: str) -> InlineKeyboardMarkup:
    back_cb = CB_PLATFORM_LINKEDIN if li_ui == "main" else CB_LI_PROFILES
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data=back_cb)],
        ]
    )


async def show_add_profiles_prompt(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
) -> None:
    data = await state.get_data()
    li_ui = data.get("li_ui", "profiles")
    await state.set_state(OnboardingStates.waiting_linkedin_add)
    await edit_from_callback(
        callback,
        state,
        t(lang, "li_add_prompt"),
        _add_links_back_keyboard(lang, li_ui),
    )


async def process_profile_links(
    message: Message,
    session: AsyncSession,
    text: str,
) -> tuple[int, int]:
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    if not user:
        return 0, 0

    links = parse_linkedin_profiles(text)
    if not links:
        return 0, 0

    repo = LinkedInProfileRepository(session)
    new_count = 0
    dup_count = 0
    for link in links:
        result = await repo.add_profile(user.id, link)
        if result == "new":
            new_count += 1
        elif result == "exists":
            dup_count += 1
    await session.commit()
    return new_count, dup_count


async def refresh_linkedin_screen(
    target: Message,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
    telegram_id: int,
    *,
    status_line: str | None = None,
) -> None:
    data = await state.get_data()
    if data.get("li_ui") == "profiles":
        await show_linkedin_profiles_screen(
            target,
            state,
            session,
            lang,
            telegram_id,
            status_line=status_line,
        )
    else:
        await show_linkedin_screen(
            target,
            state,
            session,
            lang,
            telegram_id,
            status_line=status_line,
        )
