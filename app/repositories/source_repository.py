from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source import Source


class SourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, source_id: int, user_id: int) -> Source | None:
        result = await self._session.execute(
            select(Source).where(Source.id == source_id, Source.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: int) -> list[Source]:
        result = await self._session.execute(
            select(Source).where(Source.user_id == user_id).order_by(Source.id)
        )
        return list(result.scalars().all())

    async def list_active_for_user(self, user_id: int) -> list[Source]:
        result = await self._session.execute(
            select(Source).where(Source.user_id == user_id, Source.is_active.is_(True))
        )
        return list(result.scalars().all())

    async def get_by_username(self, user_id: int, telegram_source: str) -> Source | None:
        result = await self._session.execute(
            select(Source).where(
                Source.user_id == user_id,
                Source.telegram_source == telegram_source,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        user_id: int,
        telegram_source: str,
        title: str | None,
    ) -> Source:
        source = Source(
            user_id=user_id,
            telegram_source=telegram_source,
            title=title,
            is_active=True,
        )
        self._session.add(source)
        await self._session.flush()
        return source

    async def delete(self, source: Source) -> None:
        await self._session.delete(source)

    async def toggle_active(self, source: Source) -> Source:
        source.is_active = not source.is_active
        await self._session.flush()
        return source
