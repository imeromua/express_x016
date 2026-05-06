from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    waiting_consent = State()
    waiting_contact = State()
