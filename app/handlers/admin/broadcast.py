"""Broadcast — розсилка усім активним користувачам.
Алгоритм:
1. Адмін натискає /broadcast
2. Бот запитує повідомлення/медіа
3. Адмін надсилає повідомлення-превю
4. Підтверджує → бачимо повідомлення з превю → натискає Старт
5. Батч-надсилка з затримкою BROADCAST_DELAY секунд
"""

import asyncio

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.filters.is_admin import IsAdminFilter
from app.keyboards.admin import kb_confirm_broadcast
from app.repositories.user import UserRepository
from app.states.admin import AdminStates

router = Router(name="admin:broadcast")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_broadcast_text)
    await message.answer(
        "📢 Надішліть повідомлення або медіа для розсилки\."
        " Це буде передано всім активним співробітникам\.",
        parse_mode="MarkdownV2",
    )


@router.message(AdminStates.waiting_broadcast_text)
async def receive_broadcast_content(
    message: Message, state: FSMContext
) -> None:
    # Зберігаємо message_id для подальшого forward
    await state.update_data(
        src_chat_id=message.chat.id,
        src_message_id=message.message_id,
    )
    await state.set_state(None)  # завишаємо дані в FSM, виходимо зі стану

    await message.answer(
        "Вище буде повідомлення для розсилки:",
        parse_mode="MarkdownV2",
    )
    # Передаємо превю
    await message.forward(chat_id=message.chat.id)
    await message.answer(
        "Відправити цю розсилку?",
        reply_markup=kb_confirm_broadcast(),
        parse_mode="MarkdownV2",
    )


@router.callback_query(F.data == "broadcast:confirm")
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
        await callback.message.answer("❌ Дані розсилки втрачено\. Спробуйте ще раз\.", parse_mode="MarkdownV2")
        return

    settings = get_settings()
    repo = UserRepository(session)
    user_ids = await repo.get_all_active_ids()

    sent = failed = 0
    status_msg = await callback.message.answer(
        f"⏳ Розсилка розпочатаїться\.\.\. \(0 / {len(user_ids)}\)",
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
            logger.warning(f"[broadcast] Не вдалося надіслати {uid}: {e}")

        # Оновлюємо статус кожні 25 повідомлень
        if i % 25 == 0:
            try:
                await status_msg.edit_text(
                    f"⏳ Розсилка\.\.\. \({i} / {len(user_ids)}\)",
                    parse_mode="MarkdownV2",
                )
            except Exception:
                pass

        await asyncio.sleep(settings.broadcast_delay)

    await status_msg.edit_text(
        f"✅ Розсилка завершена\!\n"
        f"Успішно: *{sent}* ✔️ Т невдало: *{failed}* ❌",
        parse_mode="MarkdownV2",
    )
    logger.info(f"[broadcast] Завершено: відправлено={sent}, помилок={failed}")


@router.callback_query(F.data == "broadcast:cancel")
async def cb_broadcast_cancel(
    callback: CallbackQuery, state: FSMContext
) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.edit_text("❌ Розсилку скасовано\.", parse_mode="MarkdownV2")
