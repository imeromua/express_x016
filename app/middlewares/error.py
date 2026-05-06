import traceback
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from loguru import logger


class ErrorHandlerMiddleware(BaseMiddleware):
    """
    Глобальний обробник помилок.
    - Логує traceback через loguru
    - Надсилає повідомлення кожному адміну
    - Бот не падає (мовчкий креш)
    """

    def __init__(self, admin_ids: list[int], bot: Any = None) -> None:
        self._admin_ids = admin_ids
        self._bot = bot  # підключається після створення bot

    def set_bot(self, bot: Any) -> None:
        self._bot = bot

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as exc:
            tb = traceback.format_exc()
            error_type = type(exc).__name__
            logger.error(f"[{error_type}] {exc}\n{tb}")

            if self._bot:
                short_tb = tb[-3000:]  # Telegram обмежує довжину повідомлення
                text = (
                    f"⚠️ *Помилка \[{error_type}\]*\n"
                    f"```\n{short_tb}\n```"
                )
                for admin_id in self._admin_ids:
                    try:
                        await self._bot.send_message(
                            admin_id,
                            text,
                            parse_mode="MarkdownV2",
                        )
                    except Exception as notify_exc:
                        logger.warning(
                            f"Не вдалося надіслати сповіщення адміну {admin_id}: {notify_exc}"
                        )
            # Не перезапускаємо — бот продовжує роботу
            return None
