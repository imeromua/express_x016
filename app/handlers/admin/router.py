from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.filters.is_admin import IsAdminFilter

router = Router(name="admin")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


@router.message(Command("admin"))
async def cmd_admin_panel(message: Message) -> None:
    from app.keyboards.admin import kb_admin_menu
    await message.answer(
        "🔧 *Панель адміністратора*",
        reply_markup=kb_admin_menu(),
    )
