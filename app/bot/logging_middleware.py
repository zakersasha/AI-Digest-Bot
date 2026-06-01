from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.utils.logging import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = None
        event_type = type(event).__name__

        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
            logger.info(
                "update_received",
                event_type=event_type,
                user_id=user_id,
                text=event.text,
            )
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None
            logger.info(
                "update_received",
                event_type=event_type,
                user_id=user_id,
                data=event.data,
            )

        try:
            return await handler(event, data)
        except Exception:
            logger.exception("handler_error", event_type=event_type, user_id=user_id)
            raise
