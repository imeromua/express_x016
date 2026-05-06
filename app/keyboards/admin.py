from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)


def kb_admin_main_menu() -> ReplyKeyboardMarkup:
    """Головна reply-клавіатура адміна."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📢 Розсилка"), KeyboardButton(text="📂 Імпорт графіка")],
            [KeyboardButton(text="🚫 Стоп-слова"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="📅 Графік працівника")],
        ],
        resize_keyboard=True,
        persistent=True,
    )


def kb_admin_panel_inline() -> InlineKeyboardMarkup:
    """Інлайн-панель з розділом."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📢 Розсилка", callback_data="admin:broadcast"),
            InlineKeyboardButton(text="📂 Імпорт", callback_data="admin:import"),
        ],
        [
            InlineKeyboardButton(text="🚫 Стоп-слова", callback_data="admin:forbidden"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats"),
        ],
    ])


def kb_confirm_broadcast() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Відправити", callback_data="broadcast:confirm"),
        InlineKeyboardButton(text="❌ Скасувати", callback_data="broadcast:cancel"),
    ]])


def kb_forbidden_actions() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="➕ Додати", callback_data="forbidden:add"),
        InlineKeyboardButton(text="♻️ Очистити все", callback_data="forbidden:clear"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back"),
    ]])


def kb_back_to_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ Назад до панелі", callback_data="admin:back"),
    ]])
