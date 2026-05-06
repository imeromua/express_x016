"""Admin reply — відповідь користувачу в приватні.
Флоу:
  Користувач пише боту → бот forward адмінам з caption '#user:{user_id}'
  Адмін reply на це повідомлення → бот copy_message юзеру
"""

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger

from app.filters.is_admin import IsAdminFilter
from app.keyboards.admin import kb_back_to_admin
from app.states.admin import AdminStates
from app.utils.text import esc

router = Router(name="admin:reply")
router.message.filter(IsAdminFilter())

_USER_TAG = "#user:"


@router.message(F.reply_to_message & F.reply_to_message.caption.startswith(_USER_TAG))
async def cmd_reply_from_caption(
    message: Message, bot: Bot, state: FSMContext
) -> None:
    """Визначає user_id з caption '#user:123456' і відповідає без додаткових дій."""
    caption = message.reply_to_message.caption or ""
    try:
        target_user_id = int(caption.split(_USER_TAG)[-1].split()[0])
    except (ValueError, IndexError):
        await message.answer("❌ Не вдалося визначити користувача\.")
        return
    await _send_reply(message, bot, target_user_id)


@router.message(F.reply_to_message & F.reply_to_message.forward_origin)
async def cmd_reply_from_forward(
    message: Message, bot: Bot
) -> None:
    """Fallback: reply на повідомлення з forward_origin."""
    origin = message.reply_to_message.forward_origin
    if hasattr(origin, "sender_user") and origin.sender_user:
        await _send_reply(message, bot, origin.sender_user.id)
    else:
        await message.answer("❌ Не вдалося визначити користувача\.")


async def _send_reply(message: Message, bot: Bot, target_user_id: int) -> None:
    try:
        await bot.copy_message(
            chat_id=target_user_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )
        await message.answer(
            f"✅ Переслано користувачу `{target_user_id}`\.",
            reply_markup=kb_back_to_admin(),
            parse_mode="MarkdownV2",
        )
        logger.info(f"[reply] {message.from_user.id} → {target_user_id}")
    except Exception as e:
        await message.answer(f"❌ Не вдалося: `{esc(str(e))}`", parse_mode="MarkdownV2")
