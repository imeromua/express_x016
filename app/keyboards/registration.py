from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)


def kb_consent() -> InlineKeyboardMarkup:
    """Inline-кнопка згоди з правилами."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Погоджуюсь з правилами", callback_data="consent:agree"),
    ]])


def kb_request_contact() -> ReplyKeyboardMarkup:
    """Reply-клавіатура з кнопкою передачі номера."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Поділитись номером", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def kb_remove() -> ReplyKeyboardRemove:
    """Прибрати reply-клавіатуру."""
    return ReplyKeyboardRemove()
