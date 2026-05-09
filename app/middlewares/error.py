import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseMiddleware):
    """Middleware that catches unhandled exceptions and logs them."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as exc:
            logger.exception("Unhandled exception in handler: %s", exc)
            if isinstance(event, Message):
                try:
                    await event.answer("⚠️ Сталася неочікувана помилка. Спробуйте пізніше.")
                except Exception:
                    pass
            return None
