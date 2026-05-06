from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    waiting_broadcast_text = State()
    waiting_reply_text = State()
    waiting_forbidden_word = State()
