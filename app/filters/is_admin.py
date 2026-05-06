from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from app.config import get_settings


class IsAdminFilter(BaseFilter):
    """True якщо user_id є в ADMIN_IDS з .env."""

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        settings = get_settings()
        user = event.from_user
        if user is None:
            return False
        return user.id in settings.admin_ids
