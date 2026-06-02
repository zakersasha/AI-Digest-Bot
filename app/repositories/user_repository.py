from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.utils.crypto import encrypt_session


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self._session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, telegram_id: int, username: str | None) -> User:
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            if username and user.username != username:
                user.username = username
            return user

        user = User(telegram_id=telegram_id, username=username, language=None)
        self._session.add(user)
        await self._session.flush()
        return user

    async def set_language(self, telegram_id: int, language: str) -> User | None:
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return None
        user.language = language
        await self._session.flush()
        return user

    async def set_frequency(self, telegram_id: int, frequency: str) -> User | None:
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return None
        user.digest_frequency = frequency
        await self._session.flush()
        return user

    async def set_delivery_time(
        self,
        telegram_id: int,
        hour: int,
        minute: int = 0,
        timezone: str | None = None,
    ) -> User | None:
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return None
        user.delivery_hour = hour
        user.delivery_minute = minute
        if timezone:
            user.timezone = timezone
        await self._session.flush()
        return user

    async def complete_onboarding(self, telegram_id: int) -> User | None:
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return None
        user.onboarding_complete = True
        await self._session.flush()
        return user

    async def reset_onboarding(self, telegram_id: int) -> User | None:
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return None
        user.onboarding_complete = False
        user.digest_frequency = None
        user.delivery_hour = None
        await self._session.flush()
        return user

    def has_telethon(self, user: User) -> bool:
        return bool(user.telethon_session_encrypted)

    async def save_telethon_session(
        self,
        telegram_id: int,
        session_string: str,
        phone: str,
    ) -> User | None:
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return None
        user.telethon_session_encrypted = encrypt_session(session_string)
        user.telegram_phone = phone
        user.telethon_linked_at = datetime.now(tz=UTC)
        await self._session.flush()
        return user

    async def clear_telethon_session(self, telegram_id: int) -> User | None:
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return None
        user.telethon_session_encrypted = None
        user.telegram_phone = None
        user.telethon_linked_at = None
        await self._session.flush()
        return user

    async def update_last_digest(self, user_id: int, at: datetime) -> None:
        result = await self._session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        user.last_digest_at = at
        await self._session.flush()

    async def list_scheduled_users(self) -> list[User]:
        result = await self._session.execute(
            select(User).where(
                User.onboarding_complete.is_(True),
                User.digest_frequency.isnot(None),
                User.delivery_hour.isnot(None),
                User.language.isnot(None),
            )
        )
        return list(result.scalars().all())
