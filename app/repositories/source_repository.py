from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.catalog_channel import CatalogChannel
from app.models.source import Source


class SourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active_for_user(self, user_id: int) -> list[Source]:
        result = await self._session.execute(
            select(Source)
            .where(Source.user_id == user_id, Source.is_active.is_(True))
            .options(selectinload(Source.catalog_channel))
        )
        return list(result.scalars().all())

    async def sync_user_selection(
        self, user_id: int, catalog_channels: list[CatalogChannel], selected_ids: set[int]
    ) -> None:
        for channel in catalog_channels:
            result = await self._session.execute(
                select(Source).where(
                    Source.user_id == user_id,
                    Source.catalog_channel_id == channel.id,
                )
            )
            source = result.scalar_one_or_none()
            is_selected = channel.id in selected_ids
            if source:
                source.is_active = is_selected
                source.title = channel.title
                source.telegram_source = channel.telegram_source
            elif is_selected:
                self._session.add(
                    Source(
                        user_id=user_id,
                        catalog_channel_id=channel.id,
                        telegram_source=channel.telegram_source,
                        title=channel.title,
                        is_active=True,
                    )
                )
            else:
                continue
        await self._session.flush()

    async def count_active(self, user_id: int) -> int:
        sources = await self.list_active_for_user(user_id)
        return len(sources)
