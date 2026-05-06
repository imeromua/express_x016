"""Admin reply — відповідь адміна користувачу в приватні.
Флоу:
  Користувач пише боту → бот forward адмінам з user_id в підписі
  Адмін reply на це повідомлення + /reply → бот пересилає юзеру
"""

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger

from app.filters.is_admin import IsAdminFilter
from app.states.admin import AdminStates

router = Router(name="admin:reply")
router.message.filter(IsAdminFilter())

# Ключ FSM: зберігаємо target_user_id
_FORWARD_PREFIX = "✉️ Повідомлення від користувача #"


@router.message(
    Command("reply"),
    F.reply_to_message,
)
async def cmd_reply(
    message: Message,
    state: FSMContext,
) -> None:
    """
    /reply в відповідь на форвард від юзера — зарусковує FSM.
    """
    forwarded = message.reply_to_message
    user_id = _extract_user_id(forwarded)

    if not user_id:
        await message.answer(
            "❌ Не вдалося визначити користувача\. "
            "Переконайтесь, що відповідаєте на форвард бота\.",
            parse_mode="MarkdownV2",
        )
        return

    await state.set_state(AdminStates.waiting_reply_text)
    await state.update_data(target_user_id=user_id)
    await message.answer(
        f"Запишіть текст або надішліть медіа для пересилки користувачу `{user_id}`:",
        parse_mode="MarkdownV2",
    )


@router.message(AdminStates.waiting_reply_text)
async def send_admin_reply(
    message: Message,
    bot: Bot,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    target_user_id = data.get("target_user_id")
    await state.clear()

    if not target_user_id:
        await message.answer("❌ Сесію втрачено\. Спробуйте ще раз\.", parse_mode="MarkdownV2")
        return

    try:
        await bot.copy_message(
            chat_id=target_user_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )
        await message.answer(
            f"✅ Повідомлення переслано користувачу `{target_user_id}`\.",
            parse_mode="MarkdownV2",
        )
        logger.info(f"[admin_reply] Адмін {message.from_user.id} → користувач {target_user_id}")
    except Exception as e:
        await message.answer(
            f"❌ Не вдалося надіслати: `{_esc(str(e))}`",
            parse_mode="MarkdownV2",
        )


def _extract_user_id(msg: Message) -> int | None:
    """
    Витягує user_id з підпису форварда або з forward_origin.
    """
    if msg is None:
        return None
    if msg.forward_origin:
        origin = msg.forward_origin
        if hasattr(origin, "sender_user") and origin.sender_user:
            return origin.sender_user.id
    # Fallback: шукаємо user_id в тексті підпису (#123456789)
    if msg.caption and _FORWARD_PREFIX in msg.caption:
        try:
            return int(msg.caption.split(_FORWARD_PREFIX)[-1].split()[0])
        except (ValueError, IndexError):
            pass
    return None


def _esc(text: str) -> str:
    for ch in r"\_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text
