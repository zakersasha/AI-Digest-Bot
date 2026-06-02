from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    picking_channels = State()


class LoginStates(StatesGroup):
    waiting_phone = State()
    waiting_code = State()
    waiting_2fa = State()
