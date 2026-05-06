"""Глобальний обробник помилок.
Бот ніколи не падає — всі виключення ловляться тут.
"""

import traceback

from aiogram import Router, Bot
from aiogram.types import ErrorEvent
from loguru import logger

from app.config import get_settings
from app.utils.text import esc

router = Router(name="errors")


@router.errors()
async def global_error_handler(event: ErrorEvent, bot: Bot) -> None:
    """bot передається aiogram автоматично через DI."""
    exc = event.exception
    tb = traceback.format_exc()
    logger.error(f"[ErrorHandler] {type(exc).__name__}: {exc}\n{tb}")

    settings = get_settings()
    short_tb = tb[-3000:] if len(tb) > 3000 else tb

    text = (
        f"❌ *Помилка бота*\n"
        f"Тип: `{esc(type(exc).__name__)}`\n"
        f"Повідомлення: `{esc(str(exc)[:300])}`\n\n"
        f"```\n{esc(short_tb)}\n```"
    )

    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, text, parse_mode="MarkdownV2")
        except Exception as notify_err:
            logger.error(f"[ErrorHandler] Не вдалося сповістити {admin_id}: {notify_err}")
