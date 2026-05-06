"""Обробник /start.
Юзер який вже в групі — перенаправляємо в групу.
Новий юзер — онбординг обробляє onboarding.py через ChatJoinRequest.
"""

from aiogram import Router, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.filters.is_admin import IsAdminFilter
from app.repositories.user import UserRepository

router = Router(name="user:start")


def _kb_go_to_group(group_id: int) -> InlineKeyboardMarkup:
    url = f"https://t.me/c/{str(group_id).replace('-100', '')}"
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💬 Перейти в групу", url=url),
    ]])


@router.message(CommandStart(), ~IsAdminFilter())
async def cmd_start(message: Message, bot: Bot, session: AsyncSession) -> None:
    settings = get_settings()
    user_id = message.from_user.id

    # Перевіряємо членство в групі через Telegram API
    try:
        member = await bot.get_chat_member(settings.group_id, user_id)
        is_member = member.status not in ("left", "kicked", "banned")
    except Exception:
        is_member = False

    if is_member:
        await message.answer(
            "👋 Ви вже є учасником групи\!",
            reply_markup=_kb_go_to_group(settings.group_id),
            parse_mode="MarkdownV2",
        )
    else:
        await message.answer(
            "👋 Привіт\!\n\n"
            "Щоб отримати доступ, подайте заявку на вступ до групи\.",
            parse_mode="MarkdownV2",
        )
