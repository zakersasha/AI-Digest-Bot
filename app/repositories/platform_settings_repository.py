from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform_settings import PlatformSettings
from app.models.user import User


class PlatformSettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self, user_id: int, platform: str) -> PlatformSettings:
        result = await self._session.execute(
            select(PlatformSettings).where(
                PlatformSettings.user_id == user_id,
                PlatformSettings.platform == platform,
            )
        )
        row = result.scalar_one_or_none()
        if row:
            return row
        row = PlatformSettings(user_id=user_id, platform=platform)
        self._session.add(row)
        await self._session.flush()
        return row

    async def get(self, user_id: int, platform: str) -> PlatformSettings | None:
        result = await self._session.execute(
            select(PlatformSettings).where(
                PlatformSettings.user_id == user_id,
                PlatformSettings.platform == platform,
            )
        )
        return result.scalar_one_or_none()

    async def set_frequency(self, user_id: int, platform: str, frequency: str) -> PlatformSettings:
        row = await self.get_or_create(user_id, platform)
        row.digest_frequency = frequency
        await self._session.flush()
        return row

    async def set_delivery_time(
        self,
        user_id: int,
        platform: str,
        hour: int,
        minute: int = 0,
    ) -> PlatformSettings:
        row = await self.get_or_create(user_id, platform)
        row.delivery_hour = hour
        row.delivery_minute = minute
        await self._session.flush()
        return row

    async def update_last_digest(self, user_id: int, platform: str, at: datetime) -> None:
        row = await self.get_or_create(user_id, platform)
        row.last_digest_at = at
        await self._session.flush()

    async def clear_schedule(self, user_id: int, platform: str) -> None:
        row = await self.get(user_id, platform)
        if not row:
            return
        row.digest_frequency = None
        row.delivery_hour = None
        row.last_digest_at = None
        await self._session.flush()

    async def list_scheduled(self) -> list[tuple[User, PlatformSettings]]:
        result = await self._session.execute(
            select(User, PlatformSettings)
            .join(PlatformSettings, PlatformSettings.user_id == User.id)
            .where(
                PlatformSettings.digest_frequency.isnot(None),
                PlatformSettings.delivery_hour.isnot(None),
                User.language.isnot(None),
            )
        )
        return list(result.all())
