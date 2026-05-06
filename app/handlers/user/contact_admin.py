"""Пересилання повідомлень від юзера до адміна з тегом #user:{id}.

Працює ТІЛЬКИ коли юзер не перебуває в жодному FSM-стані.
Завдяки StateFilter(state=None) не перехоплює повідомлення під час реєстрації.
"""

from aiogram import Router, F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.state import default_state
from aiogram.types import Message
from loguru import logger

from app.config import get_settings
from app.filters.is_admin import IsAdminFilter
from app.utils.text import esc

router = Router(name="user:contact_admin")


@router.message(
    ~IsAdminFilter(),
    F.chat.type == "private",
    StateFilter(default_state),          # тільки поза FSM-станами
    ~F.text.startswith("/"),             # не команди
    ~F.text.in_({
        "📅 Мій графік",
        "ℹ️ Довідка",
        "📩 Зв'язок з адміном",
    }),                                   # не кнопки головного меню
)
async def forward_to_admins(message: Message, bot: Bot) -> None:
    """
    Будь-яке вільне повідомлення від не-адміна в приваті
    пересилається адмінам з caption-тегом для reply.
    """
    settings = get_settings()
    user = message.from_user
    tag = f"#user:{user.id}"
    caption = (
        f"✉️ Звернення від [{esc(user.full_name)}](tg://user?id={user.id})\n"
        f"{tag}"
    )

    forwarded = False
    for admin_id in settings.admin_ids:
        try:
            await bot.copy_message(
                chat_id=admin_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                caption=caption,
                parse_mode="MarkdownV2",
            )
            forwarded = True
        except Exception as e:
            logger.warning(f"[contact_admin] Не вдалося {admin_id}: {e}")

    if forwarded:
        await message.answer(
            "✅ Ваше повідомлення передано адміністрації\. Очікуйте відповіді\.",
            parse_mode="MarkdownV2",
        )
    else:
        await message.answer(
            "⚠️ Не вдалося надіслати повідомлення\. Спробуйте пізніше\.",
            parse_mode="MarkdownV2",
        )
