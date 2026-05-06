from aiogram import Router

from app.handlers.user import start, onboarding, schedule, contact_admin

router = Router(name="user")
router.include_router(onboarding.router)
router.include_router(start.router)
router.include_router(schedule.router)
router.include_router(contact_admin.router)
