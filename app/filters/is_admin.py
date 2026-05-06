from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from app.config import get_settings


class IsAdminFilter(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        settings = get_settings()
        user_id = (
            event.from_user.id
            if hasattr(event, "from_user")
            else None
        )
        return user_id in settings.admin_ids
