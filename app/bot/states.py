from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    choosing_platform = State()
    entering_sources = State()
    managing_sources = State()
    waiting_add_source = State()
    connecting_gmail = State()
    waiting_gmail_code = State()
    connecting_yandex = State()
    waiting_yandex_code = State()
    connecting_slack = State()
    waiting_slack_code = State()
    waiting_telegram_qr = State()
    waiting_telegram_2fa = State()
    connecting_linkedin = State()
    waiting_linkedin_add = State()
