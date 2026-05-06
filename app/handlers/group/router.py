from aiogram import Router

from app.handlers.group import moderation

router = Router(name="group")
router.include_router(moderation.router)
