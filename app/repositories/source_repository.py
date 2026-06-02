from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source import Source
from app.services.telethon_service import SubscribedChannel


class SourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active_for_user(self, user_id: int) -> list[Source]:
        result = await self._session.execute(
            select(Source).where(Source.user_id == user_id, Source.is_active.is_(True))
        )
        return list(result.scalars().all())

    async def list_all_for_user(self, user_id: int) -> list[Source]:
        result = await self._session.execute(select(Source).where(Source.user_id == user_id))
        return list(result.scalars().all())

    async def sync_subscriptions(
        self,
        user_id: int,
        subscriptions: list[SubscribedChannel],
        selected_usernames: set[str],
    ) -> None:
        by_username = {item.username: item for item in subscriptions}
        result = await self._session.execute(select(Source).where(Source.user_id == user_id))
        existing = {source.telegram_source: source for source in result.scalars().all()}

        for username, channel in by_username.items():
            is_selected = username in selected_usernames
            source = existing.get(username)
            if source:
                source.is_active = is_selected
                source.title = channel.title
                source.telegram_peer_id = channel.peer_id
            elif is_selected:
                self._session.add(
                    Source(
                        user_id=user_id,
                        telegram_source=username,
                        title=channel.title,
                        telegram_peer_id=channel.peer_id,
                        is_active=True,
                    )
                )

        for username, source in existing.items():
            if username not in by_username:
                source.is_active = False
            elif username not in selected_usernames:
                source.is_active = False

        await self._session.flush()

    async def count_active(self, user_id: int) -> int:
        return len(await self.list_active_for_user(user_id))

    async def active_usernames(self, user_id: int) -> set[str]:
        sources = await self.list_active_for_user(user_id)
        return {source.telegram_source for source in sources}
