from aiogram import Router, F
from aiogram.enums import ChatType

from app.handlers.user import onboarding

router = Router(name="user")
# Приватні повідомлення + ChatJoinRequest працюють без фільтра по ChatType
# (заявки на вступ не мають chat.type звичайного повідомлення)
router.include_router(onboarding.router)
