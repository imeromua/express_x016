from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    """
    FSM-стани для адмінських операцій.

    waiting_broadcast_text — очікуємо текст/медіа для розсилки
    waiting_reply_text     — очікуємо текст відповіді користувачу
    waiting_forbidden_word — очікуємо слово для додавання до чорного списку
    """
    waiting_broadcast_text = State()
    waiting_reply_text = State()
    waiting_forbidden_word = State()
