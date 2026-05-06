from aiogram.fsm.state import State, StatesGroup


class UserStates(StatesGroup):
    waiting_contact = State()
    registration_pending = State()
