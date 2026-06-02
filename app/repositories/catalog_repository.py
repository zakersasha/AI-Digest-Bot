from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog_channel import CatalogChannel


class CatalogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active(self) -> list[CatalogChannel]:
        result = await self._session.execute(
            select(CatalogChannel)
            .where(CatalogChannel.is_active.is_(True))
            .order_by(CatalogChannel.sort_order, CatalogChannel.id)
        )
        return list(result.scalars().all())

    async def get_by_id(self, channel_id: int) -> CatalogChannel | None:
        result = await self._session.execute(
            select(CatalogChannel).where(CatalogChannel.id == channel_id)
        )
        return result.scalar_one_or_none()
