"""Присвоєння реального ПІБ (з графіка) до Telegram-юзера.

Флоу:
  1. Адмін відкриває картку юзера → натискає "🔗 Присвоїти ПІБ"
  2. Бот показує inline-список всіх ПІБ з графіка (з пагінацією)
  3. Адмін вибирає ПІБ → зберігається в users.pib
"""

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters.is_admin import IsAdminFilter
from app.keyboards.admin import kb_pib_picker, kb_user_actions
from app.repositories.schedule import ScheduleRepository
from app.repositories.user import UserRepository
from app.utils.text import esc

router = Router(name="admin:assign_pib")
router.callback_query.filter(IsAdminFilter())

_PREFIX = "assign_pib"


async def _show_pib_picker(
    callback: CallbackQuery,
    session: AsyncSession,
    user_id: int,
    page: int = 0,
) -> None:
    repo = ScheduleRepository(session)
    pib_list = await repo.get_all_unique_pib()

    if not pib_list:
        await callback.answer("⚠️ Графік порожній, спочатку імпортуйте Excel", show_alert=True)
        return

    kb = kb_pib_picker(
        pib_list=pib_list,
        callback_prefix=f"{_PREFIX}:{user_id}",
        page=page,
        back_cb=f"user:view:{user_id}",
    )
    await callback.message.edit_text(
        f"🔗 Оберіть ПІБ для присвоєння юзеру `{user_id}`:",
        reply_markup=kb,
        parse_mode="MarkdownV2",
    )


@router.callback_query(F.data.regexp(r"^user:assign_pib:(\d+)$"))
async def cb_assign_pib_start(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    await callback.answer()
    user_id = int(callback.data.split(":")[2])
    await _show_pib_picker(callback, session, user_id, page=0)


@router.callback_query(F.data.regexp(rf"^{_PREFIX}:(\d+):page:(\d+)$"))
async def cb_assign_pib_page(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    await callback.answer()
    _, user_id_str, _, page_str = callback.data.split(":")
    user_id = int(user_id_str)
    page = int(page_str)
    await _show_pib_picker(callback, session, user_id, page=page)


@router.callback_query(F.data.regexp(rf"^{_PREFIX}:(\d+):(.+)$"))
async def cb_assign_pib_select(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    await callback.answer()
    parts = callback.data.split(":", 2)  # ["assign_pib", user_id, pib]
    user_id = int(parts[1])
    pib = parts[2]

    # Перевірка чи цей ПІБ вже присвоєно іншому юзеру
    user_repo = UserRepository(session)
    existing = await user_repo.get_by_pib(pib)
    if existing and existing.user_id != user_id:
        await callback.answer(
            f"⚠️ Цей ПІБ вже присвоєно @{existing.username or existing.user_id}",
            show_alert=True,
        )
        return

    await user_repo.set_pib(user_id, pib)

    user = await user_repo.get_by_id(user_id)
    name = user.username or str(user_id)
    await callback.message.edit_text(
        f"✅ ПІБ *{esc(pib)}* успішно присвоєно @{esc(name)}\!",
        reply_markup=kb_user_actions(
            user_id=user_id,
            is_active=user.is_active,
            role=user.role,
            has_pib=True,
        ),
        parse_mode="MarkdownV2",
    )
