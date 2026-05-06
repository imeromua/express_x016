from aiogram import Router

from app.handlers.user import onboarding, start

router = Router(name="user")

# Онбординг перший — обробляє ChatJoinRequest + FSM реєстрації
# start — /start: перенаправляє в групу або пояснює як вступити
router.include_router(onboarding.router)
router.include_router(start.router)
