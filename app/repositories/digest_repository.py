from sqlalchemy.ext.asyncio import AsyncSession

from app.models.digest import Digest


class DigestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user_id: int, timeframe: str, content: str) -> Digest:
        digest = Digest(user_id=user_id, timeframe=timeframe, content=content)
        self._session.add(digest)
        await self._session.flush()
        return digest
