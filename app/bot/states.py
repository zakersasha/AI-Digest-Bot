from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    picking_channels = State()
