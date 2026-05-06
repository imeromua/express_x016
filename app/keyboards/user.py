from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


def kb_main_menu() -> ReplyKeyboardMarkup:
    """Головне меню користувача (персистентна reply-клавіатура)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Мій графік")],
            [KeyboardButton(text="ℹ️ Довідка"), KeyboardButton(text="📩 Зв'язок з адміном")],
        ],
        resize_keyboard=True,
        persistent=True,
    )


def kb_schedule_inline(has_own: bool = True) -> InlineKeyboardMarkup:
    """Інлайн-кнопки для розділу графіку."""
    buttons = []
    if has_own:
        buttons.append([InlineKeyboardButton(
            text="📅 Мій графік зараз",
            callback_data="schedule:my",
        )])
    buttons.append([InlineKeyboardButton(
        text="🔍 Знайти за прізвищем",
        callback_data="schedule:search",
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def kb_request_contact() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Поділитись номерон", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def kb_agree_rules() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Погоджуюсь", callback_data="consent:agree"),
    ]])


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
