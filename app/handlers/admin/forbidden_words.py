from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters.is_admin import IsAdminFilter
from app.keyboards.admin import kb_forbidden_actions, kb_back_to_admin
from app.repositories.setting import SettingRepository
from app.states.admin import AdminStates
from app.utils.text import esc

router = Router(name="admin:forbidden")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())

_CACHE_KEY = "moderation:forbidden_words"


async def show_forbidden_list(message: Message, session: AsyncSession = None) -> None:
    """Показати список — виклик з reply-кнопки або callback."""
    if session is None:
        await message.answer("⚙️ Отримую список...")
        return
    repo = SettingRepository(session)
    words = await repo.get_forbidden_words()
    if not words:
        text = "⚪ Список заборонених слів порожній\."
    else:
        items = "\n".join(f"• `{esc(w)}`" for w in words)
        text = f"🚫 *Заборонені слова* \({len(words)}\):\n{items}"
    await message.answer(text, reply_markup=kb_forbidden_actions(), parse_mode="MarkdownV2")


@router.message(F.text == "🚫 Стоп-слова")
async def btn_forbidden(message: Message, session: AsyncSession) -> None:
    await show_forbidden_list(message, session)


@router.callback_query(F.data == "forbidden:add")
async def cb_forbidden_add(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(AdminStates.waiting_forbidden_word)
    await callback.message.answer("✏️ Надішліть слово для додавання:")


@router.message(AdminStates.waiting_forbidden_word)
async def receive_forbidden_word(
    message: Message, state: FSMContext, session: AsyncSession, redis: Redis
) -> None:
    word = (message.text or "").strip().lower()
    await state.clear()
    if not word:
        await message.answer("❌ Порожне слово\.")
        return
    repo = SettingRepository(session)
    words = await repo.get_forbidden_words()
    if word not in words:
        words.append(word)
        await repo.set_forbidden_words(words)
        await redis.delete(_CACHE_KEY)
    await message.answer(
        f"✅ Додано: `{esc(word)}`\. Всього: *{len(words)}*",
        reply_markup=kb_forbidden_actions(),
        parse_mode="MarkdownV2",
    )


@router.callback_query(F.data == "forbidden:clear")
async def cb_forbidden_clear(
    callback: CallbackQuery, session: AsyncSession, redis: Redis
) -> None:
    await callback.answer()
    repo = SettingRepository(session)
    await repo.set_forbidden_words([])
    await redis.delete(_CACHE_KEY)
    await callback.message.edit_text(
        "✅ Список заборонених слів очищено\.",
        reply_markup=kb_back_to_admin(),
        parse_mode="MarkdownV2",
    )
