from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.filters.is_admin import IsAdminFilter
from app.handlers.admin import broadcast, reply_user, forbidden_words, import_schedule

router = Router(name="admin")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


@router.message(Command("admin"))
async def cmd_admin_panel(message: Message) -> None:
    from app.keyboards.admin import kb_admin_menu
    await message.answer(
        "🔧 *Панель адміністратора*\n\n"
        "Доступні команди:\n"
        "• /broadcast — розсилка\n"
        "• /import — імпорт графіка\n"
        "• /forbidden — заборонені слова\n"
        "• /reply \(reply на форвард\) — відповідь юзеру",
        reply_markup=kb_admin_menu(),
        parse_mode="MarkdownV2",
    )


router.include_router(broadcast.router)
router.include_router(reply_user.router)
router.include_router(forbidden_words.router)
router.include_router(import_schedule.router)
