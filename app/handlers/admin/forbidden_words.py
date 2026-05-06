import json

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters.is_admin import IsAdminFilter
from app.repositories.setting import SettingRepository
from app.states.admin import AdminStates

# Ключ інвалідації кешу заборонених слів в Redis
_CACHE_KEY = "moderation:forbidden_words"

router = Router(name="admin:forbidden")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


@router.message(Command("forbidden"))
async def cmd_forbidden_list(
    message: Message, session: AsyncSession
) -> None:
    repo = SettingRepository(session)
    words = await repo.get_forbidden_words()
    if not words:
        text = "⚪ Список заборонених слів порожній\."
    else:
        items = "\n".join(f"• `{_esc(w)}`" for w in words)
        text = f"🚫 *Заборонені слова* \({len(words)}\):\n{items}"

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="➕ Додати", callback_data="forbidden:add"),
        InlineKeyboardButton(text="♻️ Очистити все", callback_data="forbidden:clear"),
    ]])
    await message.answer(text, reply_markup=kb, parse_mode="MarkdownV2")


@router.callback_query(F.data == "forbidden:add")
async def cb_forbidden_add(
    callback: CallbackQuery, state: FSMContext
) -> None:
    await callback.answer()
    await state.set_state(AdminStates.waiting_forbidden_word)
    await callback.message.answer(
        "✏️ Надішліть слово або фразу для додавання в список заборонених:",
        parse_mode="MarkdownV2",
    )


@router.message(AdminStates.waiting_forbidden_word)
async def receive_forbidden_word(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    redis: Redis,
) -> None:
    word = (message.text or "").strip().lower()
    await state.clear()

    if not word:
        await message.answer("❌ Порожнє слово\.", parse_mode="MarkdownV2")
        return

    repo = SettingRepository(session)
    words = await repo.get_forbidden_words()
    if word not in words:
        words.append(word)
        await repo.set_forbidden_words(words)
        # Інвалідуємо кеш Redis
        await redis.delete(_CACHE_KEY)

    await message.answer(
        f"✅ Слово `{_esc(word)}` додано до списку\. Всього: *{len(words)}*",
        parse_mode="MarkdownV2",
    )


@router.callback_query(F.data == "forbidden:clear")
async def cb_forbidden_clear(
    callback: CallbackQuery,
    session: AsyncSession,
    redis: Redis,
) -> None:
    await callback.answer()
    repo = SettingRepository(session)
    await repo.set_forbidden_words([])
    await redis.delete(_CACHE_KEY)
    await callback.message.edit_text(
        "✅ Список заборонених слів очищено\.",
        parse_mode="MarkdownV2",
    )


def _esc(text: str) -> str:
    for ch in r"\_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text
