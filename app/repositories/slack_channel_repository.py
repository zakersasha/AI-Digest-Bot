from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.slack_channel import SlackChannel


class SlackChannelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active_for_user(self, user_id: int) -> list[SlackChannel]:
        result = await self._session.execute(
            select(SlackChannel).where(
                SlackChannel.user_id == user_id,
                SlackChannel.is_active.is_(True),
            )
        )
        return list(result.scalars().all())

    async def list_all_for_user(self, user_id: int) -> list[SlackChannel]:
        result = await self._session.execute(
            select(SlackChannel).where(SlackChannel.user_id == user_id).order_by(SlackChannel.id)
        )
        return list(result.scalars().all())

    async def upsert_channel(
        self,
        user_id: int,
        channel_id: str,
        channel_name: str,
        *,
        active: bool = True,
    ) -> SlackChannel:
        result = await self._session.execute(
            select(SlackChannel).where(
                SlackChannel.user_id == user_id,
                SlackChannel.channel_id == channel_id,
            )
        )
        row = result.scalar_one_or_none()
        if row:
            row.channel_name = channel_name
            row.is_active = active
            await self._session.flush()
            return row

        row = SlackChannel(
            user_id=user_id,
            channel_id=channel_id,
            channel_name=channel_name,
            is_active=active,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def set_active(self, user_id: int, channel_id: str, active: bool) -> bool:
        result = await self._session.execute(
            select(SlackChannel).where(
                SlackChannel.user_id == user_id,
                SlackChannel.channel_id == channel_id,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            return False
        row.is_active = active
        await self._session.flush()
        return True

    async def count_active(self, user_id: int) -> int:
        return len(await self.list_active_for_user(user_id))

    async def deactivate_all(self, user_id: int) -> None:
        for row in await self.list_all_for_user(user_id):
            row.is_active = False
        await self._session.flush()
