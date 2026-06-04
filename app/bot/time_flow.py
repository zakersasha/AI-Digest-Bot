from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import time_keyboard
from app.bot.screen import edit_from_callback, open_screen
from app.config import get_settings
from app.i18n import t

DEFAULT_DELIVERY_HOUR = 9
_PENDING_HOUR_KEY = "pending_delivery_hour"


def _normalize_hour(hour: int) -> int:
    return hour % 24


async def get_pending_hour(state: FSMContext) -> int:
    data = await state.get_data()
    return _normalize_hour(int(data.get(_PENDING_HOUR_KEY, DEFAULT_DELIVERY_HOUR)))


async def set_pending_hour(state: FSMContext, hour: int) -> int:
    hour = _normalize_hour(hour)
    await state.update_data(**{_PENDING_HOUR_KEY: hour})
    return hour


def _time_step_text(lang: str, hour: int) -> str:
    settings = get_settings()
    time_str = f"{hour:02d}:00"
    return (
        t(lang, "step_time", timezone=settings.default_timezone)
        + "\n\n"
        + t(lang, "time_picker_hint", time=time_str)
    )


async def show_time_picker(
    message: Message,
    state: FSMContext,
    lang: str,
    *,
    hour: int | None = None,
) -> None:
    if hour is not None:
        await set_pending_hour(state, hour)
    else:
        hour = await get_pending_hour(state)
    await open_screen(message, state, _time_step_text(lang, hour), time_keyboard(lang, hour))


async def show_time_picker_callback(
    callback: CallbackQuery,
    state: FSMContext,
    lang: str,
) -> None:
    hour = await get_pending_hour(state)
    await edit_from_callback(
        callback,
        state,
        _time_step_text(lang, hour),
        time_keyboard(lang, hour),
    )
