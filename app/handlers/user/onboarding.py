"""Онбординг: ChatJoinRequest → правила → "Погоджуюсь" → вступ в групу.

FSM не використовується — весь флоу через один callback.
"""

from aiogram import Router, F, Bot
from aiogram.types import (
    ChatJoinRequest,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.keyboards.registration import kb_consent
from app.repositories.setting import SettingRepository
from app.repositories.user import UserRepository

router = Router(name="user:onboarding")


def _kb_go_to_group(group_id: int) -> InlineKeyboardMarkup:
    url = f"https://t.me/c/{str(group_id).replace('-100', '')}"
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💬 Перейти в групу", url=url),
    ]])


@router.chat_join_request()
async def handle_join_request(
    event: ChatJoinRequest,
    bot: Bot,
    session: AsyncSession,
) -> None:
    """Нова заявка на вступ: надсилаємо правила + кнопку згоди."""
    user = event.from_user
    repo = SettingRepository(session)
    rules_text = await repo.get_onboarding_rules()

    await bot.send_message(
        chat_id=user.id,
        text=(
            f"👋 Привіт, *{user.first_name}*\!\n\n"
            f"{rules_text}\n\n"
            "Щоб продовжувати, прийміть правила спільноти\."
        ),
        reply_markup=kb_consent(),
        parse_mode="MarkdownV2",
    )
    logger.info(f"[onboarding] заявка від {user.id} (@{user.username})")


@router.callback_query(F.data == "consent:agree")
async def cb_consent_agree(
    callback: CallbackQuery,
    bot: Bot,
    session: AsyncSession,
) -> None:
    """Користувач погодився → схвалюємо заявку + зберігаємо в БД + кнопка в групу."""
    await callback.answer()
    settings = get_settings()
    user = callback.from_user

    try:
        await bot.approve_chat_join_request(
            chat_id=settings.group_id,
            user_id=user.id,
        )
    except Exception as e:
        logger.warning(f"[onboarding] approve failed for {user.id}: {e}")

    user_repo = UserRepository(session)
    await user_repo.upsert(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        is_active=True,
    )

    await callback.message.edit_text(
        "✅ Ви прийняли правила\! До зустрічі в групі 👋",
        parse_mode="MarkdownV2",
        reply_markup=_kb_go_to_group(settings.group_id),
    )
    logger.info(f"[onboarding] прийнято {user.id} (@{user.username})")
