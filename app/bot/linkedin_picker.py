from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import CB_LI_PICK_DONE, CB_LI_PICK_PAGE_PREFIX, CB_LI_PICK_TOGGLE_PREFIX
from app.bot.screen import edit_from_callback, edit_screen
from app.config import get_settings
from app.i18n import t
from app.repositories.linkedin_profile_repository import LinkedInProfileRepository
from app.repositories.user_repository import UserRepository
from app.services.linkedin_service import FollowedProfile, LinkedInService

PAGE_SIZE = 8


def _active_slugs(profiles) -> set[str]:
    return {p.profile_slug.lower() for p in profiles if p.is_active}


def _picker_keyboard(
    lang: str,
    items: list[FollowedProfile],
    active: set[str],
    page: int,
) -> InlineKeyboardMarkup:
    total_pages = max(1, (len(items) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    start = page * PAGE_SIZE
    chunk = items[start : start + PAGE_SIZE]

    rows: list[list[InlineKeyboardButton]] = []
    for item in chunk:
        mark = "✅" if item.slug.lower() in active else "⬜"
        label = f"{mark} {item.title[:28]}"
        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"{CB_LI_PICK_TOGGLE_PREFIX}{item.slug}",
                )
            ]
        )

    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(text="◀️", callback_data=f"{CB_LI_PICK_PAGE_PREFIX}{page - 1}")
        )
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="li:noop"))
    if page < total_pages - 1:
        nav.append(
            InlineKeyboardButton(text="▶️", callback_data=f"{CB_LI_PICK_PAGE_PREFIX}{page + 1}")
        )
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton(text=t(lang, "btn_li_pick_done"), callback_data=CB_LI_PICK_DONE)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def fetch_followed_profiles(user) -> list[FollowedProfile]:
    settings = get_settings()
    service = LinkedInService(settings)
    return await service.fetch_followed_profiles(user.linkedin_tokens_encrypted)


async def show_linkedin_picker(
    target: Message,
    state: FSMContext,
    session: AsyncSession,
    lang: str,
    telegram_id: int,
    *,
    page: int = 0,
) -> None:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if not user or not UserRepository(session).has_linkedin(user):
        return

    try:
        followed = await fetch_followed_profiles(user)
    except ValueError:
        followed = []

    if not followed:
        text = t(lang, "li_picker_empty")
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data=CB_LI_PICK_DONE)]
            ]
        )
    else:
        profiles = await LinkedInProfileRepository(session).list_all_for_user(user.id)
        active = _active_slugs(profiles)
        text = t(lang, "li_picker_hint", count=len(followed))
        markup = _picker_keyboard(lang, followed, active, page)

    await state.update_data(li_picker_page=page, li_picker_count=len(followed))
    await edit_screen(target, state, text, markup)


async def toggle_profile(
    callback: CallbackQuery,
    session: AsyncSession,
    lang: str,
    slug: str,
) -> None:
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        return

    repo = LinkedInProfileRepository(session)
    profiles = await repo.list_all_for_user(user.id)
    active = _active_slugs(profiles)
    key = slug.lower()

    if key in active:
        await repo.remove_profile(user.id, key)
    else:
        followed = await fetch_followed_profiles(user)
        match = next((p for p in followed if p.slug.lower() == key), None)
        if match:
            from app.utils.linkedin_links import ParsedLinkedInProfile

            parsed = ParsedLinkedInProfile(
                slug=match.slug,
                profile_type=match.profile_type,
                url=match.url,
                title=match.title,
            )
            await repo.add_parsed(
                user.id,
                parsed,
                title=match.title,
                linkedin_urn=match.linkedin_urn,
            )
        else:
            await repo.add_profile(user.id, f"https://www.linkedin.com/company/{key}")
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

    try:
        followed = await fetch_followed_profiles(user)
    except ValueError:
        followed = []

    profiles = await LinkedInProfileRepository(session).list_all_for_user(user.id)
    active = _active_slugs(profiles)
    text = t(lang, "li_picker_hint", count=len(followed))
    markup = _picker_keyboard(lang, followed, active, page)
    await edit_from_callback(callback, state, text, markup)
