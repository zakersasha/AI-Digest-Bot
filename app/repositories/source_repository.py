from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source import Source
from app.utils.links import normalize_source


class SourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active_for_user(self, user_id: int) -> list[Source]:
        result = await self._session.execute(
            select(Source).where(Source.user_id == user_id, Source.is_active.is_(True))
        )
        return list(result.scalars().all())

    async def list_all_for_user(self, user_id: int) -> list[Source]:
        result = await self._session.execute(
            select(Source)
            .where(Source.user_id == user_id, Source.is_active.is_(True))
            .order_by(Source.id)
        )
        return list(result.scalars().all())

    async def add_source(self, user_id: int, raw_username: str) -> str | None:
        """Returns 'new', 'exists', or None if invalid."""
        try:
            username = normalize_source(raw_username)
        except ValueError:
            return None

        result = await self._session.execute(
            select(Source).where(
                Source.user_id == user_id,
                Source.telegram_source == username,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            if existing.is_active:
                return "exists"
            existing.is_active = True
            await self._session.flush()
            return "new"

        source = Source(
            user_id=user_id,
            telegram_source=username,
            title=username,
            is_active=True,
        )
        self._session.add(source)
        await self._session.flush()
        return "new"

    async def remove_source(self, user_id: int, raw_username: str) -> bool:
        try:
            username = normalize_source(raw_username)
        except ValueError:
            return False

        result = await self._session.execute(
            select(Source).where(
                Source.user_id == user_id,
                Source.telegram_source == username,
            )
        )
        source = result.scalar_one_or_none()
        if not source:
            return False
        source.is_active = False
        await self._session.flush()
        return True

    async def count_active(self, user_id: int) -> int:
        return len(await self.list_active_for_user(user_id))

    async def active_usernames(self, user_id: int) -> set[str]:
        sources = await self.list_active_for_user(user_id)
        return {source.telegram_source for source in sources}
