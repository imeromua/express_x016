"""Пересилання повідомлень від юзера до адміна з тегом #user:{id}."""

from aiogram import Router, F, Bot
from aiogram.types import Message
from loguru import logger

from app.config import get_settings
from app.filters.is_admin import IsAdminFilter
from app.utils.text import esc

router = Router(name="user:contact_admin")


@router.message(
    ~IsAdminFilter(),
    F.chat.type == "private",
)
async def forward_to_admins(message: Message, bot: Bot) -> None:
    """
    Будь-яке повідомлення від не-адміна в приватному чаті
    пересилається адмінам з caption-тегом для подальшої відповіді.
    """
    settings = get_settings()
    user = message.from_user
    tag = f"#user:{user.id}"
    caption = (
        f"✉️ Звернення від [{esc(user.full_name)}](tg://user?id={user.id})\n"
        f"{tag}"
    )

    for admin_id in settings.admin_ids:
        try:
            await bot.copy_message(
                chat_id=admin_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                caption=caption,
                parse_mode="MarkdownV2",
            )
        except Exception as e:
            logger.warning(f"[contact_admin] Не вдалося {admin_id}: {e}")

    await message.answer(
        "✅ Ваше повідомлення передано адміністрації\. Очікуйте відповіді\.",
        parse_mode="MarkdownV2",
    )
