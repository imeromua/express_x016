from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

_PIB_PAGE_SIZE = 8


def kb_admin_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📢 Розсилка"), KeyboardButton(text="📂 Імпорт графіка")],
            [KeyboardButton(text="🚫 Стоп-слова"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="📅 Графік працівника"), KeyboardButton(text="⚙️ Налаштування Excel")],
            [KeyboardButton(text="👥 Користувачі")],
        ],
        resize_keyboard=True,
        persistent=True,
    )


def kb_stats_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Загальна", callback_data="stats:general"),
            InlineKeyboardButton(text="👤 По працівнику", callback_data="stats:by_employee"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back"),
        ],
    ])


def kb_pib_picker(
    pib_list: list[str],
    callback_prefix: str,
    page: int = 0,
    back_cb: str = "admin:back",
) -> InlineKeyboardMarkup:
    """Універсальний inline-вибір ПІБ з пагінацією.

    Замість самого ПІБ у callback_data передається його ІНДЕКС у pib_list,
    щоб не перевищити ліміт Telegram у 64 байти.

    callback_data кнопки вибору: f"{callback_prefix}:i:{global_index}"
    callback_data пагінації:     f"{callback_prefix}:page:{page}"
    """
    start = page * _PIB_PAGE_SIZE
    chunk = list(enumerate(pib_list[start: start + _PIB_PAGE_SIZE], start=start))
    total_pages = max(1, (len(pib_list) + _PIB_PAGE_SIZE - 1) // _PIB_PAGE_SIZE)

    buttons = [
        [InlineKeyboardButton(text=pib, callback_data=f"{callback_prefix}:i:{idx}")]
        for idx, pib in chunk
    ]

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"{callback_prefix}:page:{page - 1}"))
    nav.append(InlineKeyboardButton(
        text=f"{page + 1}/{total_pages}",
        callback_data="noop",
    ))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"{callback_prefix}:page:{page + 1}"))
    buttons.append(nav)

    buttons.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def kb_admin_panel_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📢 Розсилка", callback_data="admin:broadcast"),
            InlineKeyboardButton(text="📂 Імпорт", callback_data="admin:import"),
        ],
        [
            InlineKeyboardButton(text="🚫 Стоп-слова", callback_data="admin:forbidden"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats"),
        ],
        [
            InlineKeyboardButton(text="⚙️ Excel-графік", callback_data="admin:xlsx_settings"),
            InlineKeyboardButton(text="👥 Користувачі", callback_data="admin:users"),
        ],
    ])


def kb_xlsx_settings() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📂 Завантажити .xlsx", callback_data="xlsx:upload"),
        ],
        [
            InlineKeyboardButton(text="📌 Діапазон комірок", callback_data="xlsx:set_range"),
            InlineKeyboardButton(text="📄 Аркуш", callback_data="xlsx:set_sheet"),
        ],
        [
            InlineKeyboardButton(text="📸 Скріншот графіка", callback_data="xlsx:preview"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back"),
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
        InlineKeyboardButton(text="♻️ Очистити", callback_data="forbidden:clear"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back"),
    ]])


def kb_back_to_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ Назад до панелі", callback_data="admin:back"),
    ]])


def kb_back_to_xlsx() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ Назад до налаштувань", callback_data="admin:xlsx_settings"),
    ]])


def kb_users_list(users: list, page: int = 0, page_size: int = 10) -> InlineKeyboardMarkup:
    start = page * page_size
    chunk = users[start:start + page_size]
    total_pages = (len(users) + page_size - 1) // page_size

    buttons = []
    for u in chunk:
        label = u.pib or u.username or str(u.user_id)
        status = "✅" if u.is_active else "❌"
        linked = "🔗" if u.pib else "⚠️"
        buttons.append([
            InlineKeyboardButton(
                text=f"{status}{linked} {label}",
                callback_data=f"user:view:{u.user_id}",
            )
        ])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"users:page:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"users:page:{page + 1}"))
    if nav:
        buttons.append(nav)

    buttons.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def kb_user_actions(user_id: int, is_active: bool, role: str, has_pib: bool = False) -> InlineKeyboardMarkup:
    toggle_text = "🚫 Деактивувати" if is_active else "✅ Активувати"
    toggle_cb = f"user:deactivate:{user_id}" if is_active else f"user:activate:{user_id}"
    role_btn = (
        InlineKeyboardButton(text="👑 Зробити адміном", callback_data=f"user:set_admin:{user_id}")
        if role != "admin"
        else InlineKeyboardButton(text="👤 Зняти адміна", callback_data=f"user:set_staff:{user_id}")
    )
    assign_btn = InlineKeyboardButton(
        text="🔗 Присвоїти ПІБ" if not has_pib else "✏️ Змінити ПІБ",
        callback_data=f"user:assign_pib:{user_id}",
    )
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle_text, callback_data=toggle_cb)],
        [role_btn],
        [assign_btn],
        [InlineKeyboardButton(text="⬅️ Назад до списку", callback_data="admin:users")],
    ])
