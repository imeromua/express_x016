import asyncio
from datetime import datetime, timezone

from aiogram import Router, F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    ChatJoinRequest,
    CallbackQuery,
    Message,
    ContentType,
)
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.keyboards.registration import kb_consent, kb_request_contact, kb_remove
from app.repositories.user import UserRepository
from app.repositories.setting import SettingRepository
from app.states.registration import RegistrationStates

router = Router(name="user:onboarding")


# ────────────────────────────────────────────────────────────────────────
# 1. ChatJoinRequest — надходить заявка на вступ до групи
# ────────────────────────────────────────────────────────────────────────
@router.chat_join_request()
async def handle_join_request(
    request: ChatJoinRequest,
    bot: Bot,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    settings = get_settings()
    user = request.from_user

    # Перевіряємо, чи не зареєстрований вже
    repo = UserRepository(session)
    existing = await repo.get_by_id(user.id)
    if existing and existing.is_active:
        await request.approve()
        logger.info(f"Авто-схвалення (вже зареєстрований): {user.id}")
        return

    # Зберігаємо поточний стан в FSM з часом початку
    await state.update_data(
        chat_id=request.chat.id,
        started_at=datetime.now(timezone.utc).isoformat(),
    )
    await state.set_state(RegistrationStates.waiting_consent)

    # Читаємо правила з БД
    setting_repo = SettingRepository(session)
    rules = await setting_repo.get_onboarding_rules()

    try:
        await bot.send_message(
            chat_id=user.id,
            text=(
                f"👋 Вітаємо, *{_escape(user.full_name)}*\!

"
                f"Щоб отримати доступ, ознайомтесь з правилами групи:

"
                f"{rules}"
            ),
            reply_markup=kb_consent(),
            parse_mode="MarkdownV2",
        )
        logger.info(f"Надіслано правила користувачу {user.id}")
    except Exception as e:
        # Користувач заблокував приватні від бота
        logger.warning(f"Не вдалося написати користувачу {user.id}: {e}")
        await _decline_with_notify(request, bot, settings)
        await state.clear()

    # Запускаємо фонову задачу таймауту
    asyncio.create_task(
        _registration_timeout(user.id, bot, state, settings.registration_timeout_minutes)
    )


# ────────────────────────────────────────────────────────────────────────
# 2. Натискання "Згоден" — перехід до запиту контакту
# ────────────────────────────────────────────────────────────────────────
@router.callback_query(
    StateFilter(RegistrationStates.waiting_consent),
    F.data == "consent:agree",
)
async def cb_consent_agree(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)

    await state.set_state(RegistrationStates.waiting_contact)

    await callback.message.answer(
        "чудово\! Тепер поділіться своїм номером для верифікації\.
"
        "Натисніть кнопку нижче 👇",
        reply_markup=kb_request_contact(),
        parse_mode="MarkdownV2",
    )


# ────────────────────────────────────────────────────────────────────────
# 3. Отримання контакту — верифікація та approve
# ────────────────────────────────────────────────────────────────────────
@router.message(
    StateFilter(RegistrationStates.waiting_contact),
    F.content_type == ContentType.CONTACT,
)
async def handle_contact(
    message: Message,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
) -> None:
    settings = get_settings()
    contact = message.contact
    user = message.from_user

    # Захист: контакт має належати цьому ж юзеру
    if contact.user_id != user.id:
        await message.answer(
            "⚠️ Будь ласка, надішліть *свій* контакт\.",
            parse_mode="MarkdownV2",
        )
        return

    phone = _normalize_phone(contact.phone_number)
    full_name = contact.full_name or user.full_name
    username = user.username

    # Перевіряємо, чи цей номер вже використовується
    repo = UserRepository(session)
    by_phone = await repo.get_by_phone(phone)
    if by_phone and by_phone.user_id != user.id:
        await message.answer(
            "⚠️ Цей номер вже зареєстровано в системі\.
"
            "Зверніться до адміністратора\.",
            parse_mode="MarkdownV2",
        )
        await state.clear()
        return

    # Зберігаємо користувача
    await repo.upsert(
        user_id=user.id,
        phone=phone,
        pib=full_name,
        username=username,
        role="staff",
        is_active=True,
        joined_at=datetime.now(timezone.utc),
    )

    # Прибираємо чат з FSM і схвалюємо заявку
    data = await state.get_data()
    chat_id = data.get("chat_id", settings.group_id)
    await state.clear()

    try:
        await bot.approve_chat_join_request(chat_id=chat_id, user_id=user.id)
        logger.info(f"Заявку схвалено: {user.id} ({full_name})")
    except Exception as e:
        logger.error(f"Помилка approve {user.id}: {e}")

    await message.answer(
        "✅ Верифікацію пройдено\! Добро пожалувати до спільноти 🎉

"
        "Тепер ви можете:
"
        "• Перевіряти графік: напишіть мені `Графік`
",
        reply_markup=kb_remove(),
        parse_mode="MarkdownV2",
    )


# ────────────────────────────────────────────────────────────────────────
# 4. У стані waiting_contact надійшли не контакт, а текст
# ────────────────────────────────────────────────────────────────────────
@router.message(StateFilter(RegistrationStates.waiting_contact))
async def handle_wrong_contact(message: Message) -> None:
    await message.answer(
        "📱 Будь ласка, скористайтесь кнопкою *Поділитися номером* нижче\.",
        reply_markup=kb_request_contact(),
        parse_mode="MarkdownV2",
    )


# ────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────
async def _registration_timeout(
    user_id: int,
    bot: Bot,
    state: FSMContext,
    timeout_minutes: int,
) -> None:
    """Timeout: якщо через N хв реєстрація не завершена — скидаємо стан."""
    await asyncio.sleep(timeout_minutes * 60)
    current_state = await state.get_state()
    if current_state in (
        RegistrationStates.waiting_consent,
        RegistrationStates.waiting_contact,
    ):
        await state.clear()
        logger.info(f"Таймаут реєстрації: {user_id}")
        try:
            await bot.send_message(
                user_id,
                "⏰ Час верифікації сплив. Будь ласка, подайте нову заявку на вступ до групи\.",
                parse_mode="MarkdownV2",
            )
        except Exception:
            pass


async def _decline_with_notify(
    request: ChatJoinRequest,
    bot: Bot,
    settings,
) -> None:
    """Fallback: не вдалося написати — повідомляємо адмінів."""
    try:
        await request.decline()
    except Exception:
        pass
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(
                admin_id,
                f"⚠️ Користувач `{request.from_user.id}` заблокував листування від бота\. Заявка відхилена\.",
                parse_mode="MarkdownV2",
            )
        except Exception:
            pass


def _escape(text: str) -> str:
    """MarkdownV2 екранування для довільного тексту."""
    for ch in r"\_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text


def _normalize_phone(phone: str) -> str:
    """380XXXXXXXXX формат: видаляємо все нецифрове."""
    digits = "".join(filter(str.isdigit, phone))
    if digits.startswith("38"):
        return "+" + digits
    if digits.startswith("0"):
        return "+38" + digits
    return "+" + digits
