from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    entering_sources = State()
    managing_sources = State()
    waiting_add_source = State()
