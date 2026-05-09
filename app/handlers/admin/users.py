"""Управління користувачами бота."""
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters.is_admin import IsAdminFilter
from app.keyboards.admin import kb_users_list, kb_user_actions, kb_back_to_admin
from app.repositories.user import UserRepository
from app.utils.text import esc

router = Router(name="admin:users")
router.callback_query.filter(IsAdminFilter())

_PAGE_SIZE = 10


async def _show_users_page(callback: CallbackQuery, session: AsyncSession, page: int = 0) -> None:
    repo = UserRepository(session)
    users = await repo.get_all()
    total = len(users)
    active = sum(1 for u in users if u.is_active)

    if not users:
        await callback.message.edit_text(
            "👥 *Користувачі*\n\nСписок порожній\.",
            reply_markup=kb_back_to_admin(),
            parse_mode="MarkdownV2",
        )
        return

    text = (
        f"👥 *Користувачі* \(сторінка {page + 1}\)\n"
        f"Всього: *{total}* \| Активних: *{active}*"
    )
    await callback.message.edit_text(
        text,
        reply_markup=kb_users_list(users, page=page, page_size=_PAGE_SIZE),
        parse_mode="MarkdownV2",
    )


@router.callback_query(F.data == "admin:users")
async def cb_users_list(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    await _show_users_page(callback, session, page=0)


@router.callback_query(F.data.startswith("users:page:"))
async def cb_users_page(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    page = int(callback.data.split(":")[2])
    await _show_users_page(callback, session, page=page)


@router.callback_query(F.data.startswith("user:view:"))
async def cb_user_view(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    user_id = int(callback.data.split(":")[2])
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)

    if not user:
        await callback.answer("Користувача не знайдено", show_alert=True)
        return

    name = esc(user.pib or "—")
    uname = esc(f"@{user.username}" if user.username else "—")
    phone = esc(user.phone or "—")
    status = "✅ Активний" if user.is_active else "❌ Неактивний"
    role = "👑 Адмін" if user.role == "admin" else "👤 Співробітник"

    text = (
        f"👤 *Користувач*\n\n"
        f"🆔 ID: `{user.user_id}`\n"
        f"📛 ПІБ: {name}\n"
        f"💬 Username: {uname}\n"
        f"📞 Телефон: {phone}\n"
        f"🎭 Роль: {role}\n"
        f"🔘 Статус: {status}\n"
        f"📅 Приєднався: {esc(str(user.joined_at.strftime('%d.%m.%Y %H:%M')))}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=kb_user_actions(user.user_id, user.is_active, user.role),
        parse_mode="MarkdownV2",
    )


@router.callback_query(F.data.startswith("user:activate:"))
async def cb_user_activate(callback: CallbackQuery, session: AsyncSession) -> None:
    user_id = int(callback.data.split(":")[2])
    repo = UserRepository(session)
    await repo.set_active(user_id, True)
    await callback.answer("✅ Активовано", show_alert=False)
    # Оновлюємо картку
    fake = type("FakeCB", (), {"data": f"user:view:{user_id}", "answer": callback.answer, "message": callback.message})()
    await cb_user_view(fake, session)


@router.callback_query(F.data.startswith("user:deactivate:"))
async def cb_user_deactivate(callback: CallbackQuery, session: AsyncSession) -> None:
    user_id = int(callback.data.split(":")[2])
    repo = UserRepository(session)
    await repo.set_active(user_id, False)
    await callback.answer("🚫 Деактивовано", show_alert=False)
    fake = type("FakeCB", (), {"data": f"user:view:{user_id}", "answer": callback.answer, "message": callback.message})()
    await cb_user_view(fake, session)


@router.callback_query(F.data.startswith("user:set_admin:"))
async def cb_user_set_admin(callback: CallbackQuery, session: AsyncSession) -> None:
    user_id = int(callback.data.split(":")[2])
    repo = UserRepository(session)
    await repo.set_role(user_id, "admin")
    await callback.answer("👑 Роль змінено на адміна", show_alert=False)
    fake = type("FakeCB", (), {"data": f"user:view:{user_id}", "answer": callback.answer, "message": callback.message})()
    await cb_user_view(fake, session)


@router.callback_query(F.data.startswith("user:set_staff:"))
async def cb_user_set_staff(callback: CallbackQuery, session: AsyncSession) -> None:
    user_id = int(callback.data.split(":")[2])
    repo = UserRepository(session)
    await repo.set_role(user_id, "staff")
    await callback.answer("👤 Роль змінено на співробітника", show_alert=False)
    fake = type("FakeCB", (), {"data": f"user:view:{user_id}", "answer": callback.answer, "message": callback.message})()
    await cb_user_view(fake, session)
