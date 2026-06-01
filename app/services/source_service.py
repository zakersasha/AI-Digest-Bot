from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source import Source
from app.repositories.source_repository import SourceRepository
from app.services.telethon_service import TelethonService

class SourceService:
    def __init__(
        self,
        session: AsyncSession,
        telethon: TelethonService,
    ) -> None:
        self._session = session
        self._telethon = telethon
        self._repo = SourceRepository(session)

    async def add_source(self, user_id: int, raw_input: str) -> Source:
        username, title = await self._telethon.resolve_channel(raw_input)
        existing = await self._repo.get_by_username(user_id, username)
        if existing:
            existing.is_active = True
            if title:
                existing.title = title
            await self._session.flush()
            return existing
        return await self._repo.create(user_id, username, title)

    async def list_sources(self, user_id: int) -> list[Source]:
        return await self._repo.list_for_user(user_id)

    async def toggle_source(self, user_id: int, source_id: int) -> Source | None:
        source = await self._repo.get_by_id(source_id, user_id)
        if not source:
            return None
        return await self._repo.toggle_active(source)

    async def remove_source(self, user_id: int, source_id: int) -> bool:
        source = await self._repo.get_by_id(source_id, user_id)
        if not source:
            return False
        await self._repo.delete(source)
        return True
