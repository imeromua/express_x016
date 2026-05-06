from aiogram import Router

from app.handlers.user import onboarding, start, schedule, contact_admin

router = Router(name="user")

# Порядок важливий:
# 1. onboarding — ChatJoinRequest + FSM реєстрації (найвищий пріоритет)
# 2. start — /start + reply-кнопки головного меню
# 3. schedule — inline callbacks + FSM пошуку прізвища
# 4. contact_admin — catch-all (ОСТАННІЙ, з StateFilter(default_state))
router.include_router(onboarding.router)
router.include_router(start.router)
router.include_router(schedule.router)
router.include_router(contact_admin.router)
