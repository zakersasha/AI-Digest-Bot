from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.helpers import clear_inline_keyboard, format_sources_text, reset_to_menu
from app.bot.keyboards import (
    BTN_ADD,
    BTN_DIGEST,
    BTN_HELP,
    BTN_SOURCES,
    CB_NAV_ADD,
    CB_NAV_DIGEST,
    CB_NAV_HELP,
    CB_NAV_MENU,
    CB_NAV_SOURCES,
    add_source_keyboard,
    help_keyboard,
    sources_keyboard,
    timeframe_keyboard,
)
from app.bot.states import AddSourceStates
from app.bot.texts import ADD_SOURCE_PROMPT, DIGEST_PICKER_PROMPT, HELP_TEXT
from app.repositories.user_repository import UserRepository
from app.services.source_service import SourceService
from sqlalchemy.ext.asyncio import AsyncSession

router = Router(name="menu")


async def show_add_source(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(AddSourceStates.waiting_for_source)
    await message.answer(ADD_SOURCE_PROMPT, reply_markup=add_source_keyboard())


async def show_sources(
    message: Message,
    session: AsyncSession,
    source_service: SourceService,
    user_id: int,
) -> None:
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(user_id)
    if not user:
        await message.answer("Please tap /start first.")
        return

    sources = await source_service.list_sources(user.id)
    await message.answer(
        format_sources_text(sources),
        reply_markup=sources_keyboard(sources),
    )


async def show_digest_picker(message: Message) -> None:
    await message.answer(DIGEST_PICKER_PROMPT, reply_markup=timeframe_keyboard())


async def show_help(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=help_keyboard())


@router.callback_query(F.data == CB_NAV_MENU)
async def cb_nav_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await reset_to_menu(callback, state)


@router.callback_query(F.data == CB_NAV_ADD)
async def cb_nav_add(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await clear_inline_keyboard(callback.message)
    await show_add_source(callback.message, state)


@router.callback_query(F.data == CB_NAV_SOURCES)
async def cb_nav_sources(
    callback: CallbackQuery,
    session: AsyncSession,
    source_service: SourceService,
) -> None:
    await callback.answer()
    await clear_inline_keyboard(callback.message)
    await show_sources(callback.message, session, source_service, callback.from_user.id)


@router.callback_query(F.data == CB_NAV_DIGEST)
async def cb_nav_digest(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    await clear_inline_keyboard(callback.message)
    await show_digest_picker(callback.message)


@router.callback_query(F.data == CB_NAV_HELP)
async def cb_nav_help(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    await clear_inline_keyboard(callback.message)
    await show_help(callback.message)


@router.message(F.text == BTN_ADD)
async def btn_add(message: Message, state: FSMContext) -> None:
    await show_add_source(message, state)


@router.message(F.text == BTN_SOURCES)
async def btn_sources(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    source_service: SourceService,
) -> None:
    await state.clear()
    await show_sources(message, session, source_service, message.from_user.id)


@router.message(F.text == BTN_DIGEST)
async def btn_digest(message: Message, state: FSMContext) -> None:
    await state.clear()
    await show_digest_picker(message)


@router.message(F.text == BTN_HELP)
async def btn_help(message: Message, state: FSMContext) -> None:
    await state.clear()
    await show_help(message)


@router.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext) -> None:
    await show_add_source(message, state)


@router.message(Command("sources"))
async def cmd_sources(
    message: Message,
    session: AsyncSession,
    source_service: SourceService,
) -> None:
    await show_sources(message, session, source_service, message.from_user.id)


@router.message(Command("digest"))
async def cmd_digest(message: Message, state: FSMContext) -> None:
    await state.clear()
    await show_digest_picker(message)


@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext) -> None:
    await state.clear()
    await show_help(message)
