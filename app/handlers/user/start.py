"""Обробник /start та головне меню користувача."""

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters.is_admin import IsAdminFilter
from app.keyboards.user import kb_main_menu, kb_schedule_inline
from app.repositories.user import UserRepository
from app.utils.text import esc

router = Router(name="user:start")


@router.message(CommandStart(), ~IsAdminFilter())
async def cmd_start(message: Message, session: AsyncSession) -> None:
    repo = UserRepository(session)
    user = await repo.get_by_id(message.from_user.id)

    if user and user.is_active:
        name = esc(user.pib or message.from_user.first_name)
        await message.answer(
            f"👋 Вітаємо, *{name}*\!\n\n"
            "Оберіть дію з меню нижче ⬇️",
            reply_markup=kb_main_menu(),
            parse_mode="MarkdownV2",
        )
    else:
        await message.answer(
            "👋 Привіт\!\n\n"
            "Щоб отримати доступ, подайте заявку на вступ до корпоративної групи\.",
            parse_mode="MarkdownV2",
        )


@router.message(F.text == "ℹ️ Довідка", ~IsAdminFilter())
async def btn_help(message: Message) -> None:
    await message.answer(
        "ℹ️ *Довідка*\n\n"
        "📅 *Мій графік* — ваш розклад роботи на 5 днів вперед\n"
        f"📩 *{esc("Зв'язок з адміном")}* — надіслати повідомлення адміністрації\n\n"
        "❓ Питання — пишіть нам у чат",
        parse_mode="MarkdownV2",
    )


@router.message(F.text == "📅 Мій графік", ~IsAdminFilter())
async def btn_my_schedule(message: Message, session: AsyncSession) -> None:
    repo = UserRepository(session)
    user = await repo.get_by_id(message.from_user.id)
    has_pib = bool(user and user.pib)
    if not has_pib:
        await message.answer(
            "⚠️ Ваш профіль не прив\'язаний до графіку\. "
            "Зверніться до адміністратора для прив\'язки ПІБ\.",
            parse_mode="MarkdownV2",
        )
        return
    await message.answer(
        "📅 Оберіть дію:",
        reply_markup=kb_schedule_inline(has_own=has_pib),
    )


@router.message(F.text == "📩 Зв'язок з адміном", ~IsAdminFilter())
async def btn_contact_admin(message: Message) -> None:
    await message.answer(
        "✏️ Напишіть ваше повідомлення, і адміністратор зв\'яжеться з вами ⬇️",
        parse_mode="MarkdownV2",
    )
