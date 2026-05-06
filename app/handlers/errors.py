"""Глобальний обробник помилок.
Бот ніколи не падає — всі винятки ловляться тут.
"""

import traceback

from aiogram import Router
from aiogram.types import ErrorEvent
from loguru import logger

from app.config import get_settings

router = Router(name="errors")


@router.errors()
async def global_error_handler(event: ErrorEvent) -> None:
    exc = event.exception
    tb = traceback.format_exc()
    logger.error(f"[ErrorHandler] {type(exc).__name__}: {exc}\n{tb}")

    settings = get_settings()
    short_tb = tb[-3000:] if len(tb) > 3000 else tb
    text = (
        f"❌ *Помилка бота*\n"
        f"Тип: `{_esc(type(exc).__name__)}`\n"
        f"Повідомлення: `{_esc(str(exc)[:300])}`\n\n"
        f"```\n{_esc(short_tb)}\n```"
    )

    bot = event.update.bot if hasattr(event.update, "bot") else None
    if not bot:
        return

    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, text, parse_mode="MarkdownV2")
        except Exception:
            pass


def _esc(text: str) -> str:
    for ch in r"\_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text
