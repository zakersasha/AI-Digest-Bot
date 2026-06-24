from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import CB_LANG_EN, CB_LANG_RU, language_keyboard
from app.bot.onboarding_flow import finish_guided, is_guided, set_flow_step, start_guided, step_text
from app.bot.platform_screens import show_platforms_menu
from app.bot.screen import open_screen
from app.i18n import DEFAULT_LANG, resolve_lang, t
from app.repositories.user_repository import UserRepository

router = Router(name="onboarding")


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    repo = UserRepository(session)
    user = await repo.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
    )
    await session.commit()

    if not user.language:
        await start_guided(state)
        await open_screen(
            message,
            state,
            step_text(DEFAULT_LANG, 1, "welcome"),
            language_keyboard(),
        )
        return

    if not user.onboarding_complete:
        await start_guided(state)
        await set_flow_step(state, 2)

    await show_platforms_menu(message, state, session, user.language, message.from_user.id)


@router.callback_query(F.data.in_({CB_LANG_RU, CB_LANG_EN}))
async def cb_language(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = callback.data.split(":")[1]
    user = await UserRepository(session).set_language(callback.from_user.id, lang)
    await session.commit()
    await callback.answer()
    if callback.message:
        await set_flow_step(state, 2)
        await show_platforms_menu(callback.message, state, session, lang, callback.from_user.id)
