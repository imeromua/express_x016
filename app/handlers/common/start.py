from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router(name="common:start")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """
    /start — відповідь для незареєстрованих користувачів.
    Зареєстровані проходять через onboarding (ChatJoinRequest).
    """
    await message.answer(
        "👋 Привіт\!

"
        "Цей боʹт призначений для співробітників *Epicentr\-Express Samar*\.\n\n"
        "Щоб отримати доступ, подайте заявку на вступ до групи і боʹт автоматично вас верифікує\."
    )
