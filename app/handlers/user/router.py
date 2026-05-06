from aiogram import Router

from app.handlers.user import onboarding, schedule

router = Router(name="user")
router.include_router(onboarding.router)
router.include_router(schedule.router)
