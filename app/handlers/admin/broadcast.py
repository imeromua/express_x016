"""Broadcast — розсилка всім активним користувачам.

Флоу:
1. Адмін натискає кнопку 📢 Розсилка (reply) або inline
2. FSM → waiting_broadcast_text
3. Надсилає контент → preview → кнопки підтвердити/скасувати
4. FSM → waiting_broadcast_confirm
5. Підтверджує → batch-розсилка з прогресом
"""

import asyncio

from aiogram import Router, F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.filters.is_admin import IsAdminFilter
from app.keyboards.admin import kb_confirm_broadcast, kb_back_to_admin
from app.repositories.user import UserRepository
from app.states.admin import AdminStates

router = Router(name="admin:broadcast")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


@router.message(F.text == "📢 Розсилка")
async def btn_broadcast(message: Message, state: FSMContext) -> None:
    """Reply-кнопка — коректно приймає state."""
    await state.set_state(AdminStates.waiting_broadcast_text)
    await message.answer(
        r"📢 Надішліть повідомлення або медіа для розсилки\.",
        parse_mode="MarkdownV2",
    )


@router.message(StateFilter(AdminStates.waiting_broadcast_text))
async def receive_broadcast_content(message: Message, state: FSMContext) -> None:
    await state.update_data(
        src_chat_id=message.chat.id,
        src_message_id=message.message_id,
    )
    await state.set_state(AdminStates.waiting_broadcast_confirm)

    await message.answer("Ось як виглядатиме повідомлення:")
    await message.forward(chat_id=message.chat.id)
    await message.answer(
        "Відправити цю розсилку?",
        reply_markup=kb_confirm_broadcast(),
    )


@router.callback_query(
    F.data == "broadcast:confirm",
    StateFilter(AdminStates.waiting_broadcast_confirm),
)
async def cb_broadcast_confirm(
    callback: CallbackQuery,
    bot: Bot,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)

    data = await state.get_data()
    src_chat_id = data.get("src_chat_id")
    src_message_id = data.get("src_message_id")
    await state.clear()

    if not src_chat_id or not src_message_id:
        await callback.message.answer(
            r"❌ Дані розсилки втрачено\. Спробуйте ще раз\.",
            parse_mode="MarkdownV2",
        )
        return

    settings = get_settings()
    repo = UserRepository(session)
    user_ids = await repo.get_all_active_ids()

    sent = failed = 0
    status_msg = await callback.message.answer(
        rf"⏳ Розсилка\.\.\. \(0 / {len(user_ids)}\)",
        parse_mode="MarkdownV2",
    )

    for i, uid in enumerate(user_ids, 1):
        try:
            await bot.forward_message(
                chat_id=uid,
                from_chat_id=src_chat_id,
                message_id=src_message_id,
            )
            sent += 1
        except Exception as e:
            failed += 1
            logger.warning(f"[broadcast] {uid}: {e}")

        if i % 25 == 0:
            try:
                await status_msg.edit_text(
                    rf"⏳ Розсилка\.\.\. \({i} / {len(user_ids)}\)",
                    parse_mode="MarkdownV2",
                )
            except Exception:
                pass
        await asyncio.sleep(settings.broadcast_delay)

    await status_msg.edit_text(
        rf"✅ Завершено\! Відправлено: *{sent}* ✔️ Невдало: *{failed}* ❌",
        reply_markup=kb_back_to_admin(),
        parse_mode="MarkdownV2",
    )
    logger.info(f"[broadcast] sent={sent}, failed={failed}")


@router.callback_query(F.data == "broadcast:cancel")
async def cb_broadcast_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(
        r"❌ Розсилку скасовано\.",
        reply_markup=kb_back_to_admin(),
        parse_mode="MarkdownV2",
    )
