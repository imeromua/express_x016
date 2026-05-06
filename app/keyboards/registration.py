from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)


def kb_consent() -> InlineKeyboardMarkup:
    """Кнопка "Згоден з правилами" в inline-повідомленні."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Згоден з правилами",
                    callback_data="consent:agree",
                )
            ]
        ]
    )


def kb_request_contact() -> ReplyKeyboardMarkup:
    """Кнопка "Поділитися номером" — reply-клавіатура з request_contact."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📱 Поділитися номером",
                    request_contact=True,
                )
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def kb_remove() -> ReplyKeyboardRemove:
    """'Прибрати' reply-клавіатуру."""
    return ReplyKeyboardRemove()
