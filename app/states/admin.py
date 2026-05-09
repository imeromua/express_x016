from aiogram.fsm.state import StatesGroup, State


class AdminStates(StatesGroup):
    waiting_broadcast_text = State()
    waiting_broadcast_confirm = State()
    waiting_forbidden_word = State()
    waiting_xlsx_import = State()   # очікування .xlsx файлу після кнопки «Імпорт графіка»
