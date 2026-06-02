from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.ai.base import AIProvider
from app.config import get_settings
from app.db.session import async_session_factory
from app.services.digest_service import DigestService


class ServicesMiddleware(BaseMiddleware):
    def __init__(
        self,
        ai: AIProvider,
        min_importance_score: int = 5,
    ) -> None:
        self._ai = ai
        self._settings = get_settings()
        self._min_importance_score = min_importance_score

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with async_session_factory() as session:
            data["session"] = session
            data["digest_service"] = DigestService(
                session,
                self._ai,
                self._settings,
                min_importance_score=self._min_importance_score,
            )
            return await handler(event, data)
