from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def kb_admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📢 Розсилка", callback_data="admin:broadcast"),
                InlineKeyboardButton(text="📅 Імпорт графіка", callback_data="admin:import"),
            ],
            [
                InlineKeyboardButton(text="🚫 Заборонені слова", callback_data="admin:forbidden"),
                InlineKeyboardButton(text="👥 Користувачі", callback_data="admin:users"),
            ],
        ]
    )


def kb_confirm_broadcast() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Надіслати", callback_data="broadcast:confirm"),
                InlineKeyboardButton(text="❌ Скасувати", callback_data="broadcast:cancel"),
            ]
        ]
    )
