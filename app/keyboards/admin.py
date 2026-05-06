from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def kb_confirm_broadcast() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Відправити", callback_data="broadcast:confirm"),
        InlineKeyboardButton(text="❌ Скасувати", callback_data="broadcast:cancel"),
    ]])


def kb_admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📢 Розсилка", callback_data="admin:broadcast"),
            InlineKeyboardButton(text="📂 Імпорт", callback_data="admin:import"),
        ],
        [
            InlineKeyboardButton(text="🚫 Стоп-слова", callback_data="admin:forbidden"),
        ],
    ])
