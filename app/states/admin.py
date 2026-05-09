from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    waiting_broadcast_text = State()
    waiting_broadcast_confirm = State()
    waiting_forbidden_word = State()
    waiting_xlsx_import = State()
    waiting_xlsx_range = State()
    waiting_xlsx_sheet = State()
    # Статистика по працівнику
    waiting_stats_employee = State()
