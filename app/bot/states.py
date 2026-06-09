from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    choosing_platform = State()
    entering_sources = State()
    managing_sources = State()
    waiting_add_source = State()
    connecting_gmail = State()
    waiting_gmail_code = State()
    waiting_telegram_phone = State()
    waiting_telegram_code = State()
    waiting_telegram_2fa = State()
