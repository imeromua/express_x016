from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    """
    FSM-флоу онбордингу.

    waiting_consent   — бот надіслав правила, чекаємо натискання "Згоден"
    waiting_contact   — згода отримана, чекаємо передачі контакту
    """
    waiting_consent = State()
    waiting_contact = State()
