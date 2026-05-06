from aiogram import Router, F
from aiogram.types import Message
from aiogram.enums import ChatType
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.config import get_settings
from app.middlewares.throttling import ThrottlingMiddleware
from app.repositories.user import UserRepository
from app.services.schedule import ScheduleService
from app.utils.schedule_formatter import format_schedule

router = Router(name="user:schedule")

_CMD = "графік"


@router.message(F.text.lower().startswith(_CMD))
async def cmd_schedule(
    message: Message,
    session: AsyncSession,
    redis: Redis,
) -> None:
    """
    Команда 'Графік' — показує розклад на найближчі 5 днів.

    Правила:
    - В групі: показує власний графік (user_id → pib)
    - Якщо текст містить > 2 слів — ігноруємо (випадкове спрацювання)
    - Throttling: 1 запит / 5 секунд
    """
    settings = get_settings()
    user = message.from_user
    text = (message.text or "").strip()
    parts = text.split()

    # Захист: більше 2 слів — ігноруємо
    if len(parts) > 2:
        return

    # Throttling для команди 'графік'
    throttled = await ThrottlingMiddleware.check_action(
        redis=redis,
        user_id=user.id,
        action="schedule",
        cooldown=settings.schedule_request_cooldown,
    )
    if throttled:
        await message.answer(
            "⏳ Зачекайте кілька секунд перед наступним запитом\.",
            parse_mode="MarkdownV2",
        )
        return

    svc = ScheduleService(session)
    user_repo = UserRepository(session)

    # Визначаємо ПІБ
    if len(parts) == 2:
        # 'Графік Прізвище' — шукаємо за прізвищем
        surname = parts[1]
        pib = await svc.resolve_pib(surname)
        if not pib:
            await message.answer(
                f"❌ Співробітника з прізвищем *{_esc(surname)}* не знайдено\.",
                parse_mode="MarkdownV2",
            )
            return
    else:
        # Просто 'Графік' — беремо власний pib з профілю
        db_user = await user_repo.get_by_id(user.id)
        if not db_user or not db_user.pib:
            await message.answer(
                "❌ Ваш профіль не знайдено\. "
                "Пройдіть реєстрацію через заявку на вступ до групи\.",
                parse_mode="MarkdownV2",
            )
            return
        pib = db_user.pib

    records = await svc.get_upcoming_for_pib(pib)
    reply = format_schedule(records, pib)

    await message.answer(reply, parse_mode="MarkdownV2")
    logger.info(f"Графік видано: user={user.id} pib={pib!r}")


def _esc(text: str) -> str:
    for ch in r"\_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text
