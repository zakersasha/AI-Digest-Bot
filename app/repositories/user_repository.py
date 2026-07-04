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

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self._session.execute(select(User).where(User.id == user_id))
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

    async def set_content_platform(self, telegram_id: int, platform: str) -> User | None:
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return None
        user.content_platform = platform
        await self._session.flush()
        return user

    async def save_gmail_tokens(
        self,
        telegram_id: int,
        tokens: dict,
        email: str,
    ) -> User | None:
        from app.services.gmail_service import GmailService

        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return None
        user.gmail_tokens_encrypted = GmailService.encrypt_tokens(tokens)
        user.gmail_email = email
        user.gmail_linked_at = datetime.now(tz=UTC)
        await self._session.flush()
        return user

    async def update_gmail_tokens(self, user_id: int, tokens: dict) -> None:
        from app.services.gmail_service import GmailService

        result = await self._session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        user.gmail_tokens_encrypted = GmailService.encrypt_tokens(tokens)
        await self._session.flush()

    async def clear_gmail(self, telegram_id: int) -> User | None:
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return None
        user.gmail_tokens_encrypted = None
        user.gmail_email = None
        user.gmail_linked_at = None
        await self._session.flush()
        return user

    def has_gmail(self, user: User) -> bool:
        return bool(user.gmail_tokens_encrypted)

    async def save_yandex_tokens(
        self,
        telegram_id: int,
        tokens: dict,
        email: str,
    ) -> User | None:
        from app.services.yandex_mail_service import YandexMailService

        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return None
        user.yandex_tokens_encrypted = YandexMailService.encrypt_tokens(tokens)
        user.yandex_email = email
        user.yandex_linked_at = datetime.now(tz=UTC)
        await self._session.flush()
        return user

    async def update_yandex_tokens(self, user_id: int, tokens: dict) -> None:
        from app.services.yandex_mail_service import YandexMailService

        result = await self._session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        user.yandex_tokens_encrypted = YandexMailService.encrypt_tokens(tokens)
        await self._session.flush()

    async def clear_yandex(self, telegram_id: int) -> User | None:
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return None
        user.yandex_tokens_encrypted = None
        user.yandex_email = None
        user.yandex_linked_at = None
        await self._session.flush()
        return user

    def has_yandex(self, user: User) -> bool:
        return bool(user.yandex_tokens_encrypted)

    async def save_slack_tokens(
        self,
        telegram_id: int,
        tokens: dict,
        team_name: str,
    ) -> User | None:
        from app.services.slack_service import SlackService

        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return None
        user.slack_tokens_encrypted = SlackService.encrypt_tokens(tokens)
        user.slack_team_name = team_name
        user.slack_linked_at = datetime.now(tz=UTC)
        await self._session.flush()
        return user

    async def clear_slack(self, telegram_id: int) -> User | None:
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return None
        user.slack_tokens_encrypted = None
        user.slack_team_name = None
        user.slack_linked_at = None
        await self._session.flush()
        return user

    def has_slack(self, user: User) -> bool:
        return bool(user.slack_tokens_encrypted)

    async def save_linkedin_tokens(
        self,
        telegram_id: int,
        tokens: dict,
        name: str,
        member_id: str,
    ) -> User | None:
        from app.services.linkedin_service import LinkedInService

        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return None
        user.linkedin_tokens_encrypted = LinkedInService.encrypt_tokens(tokens)
        user.linkedin_name = name
        user.linkedin_member_id = member_id or None
        user.linkedin_linked_at = datetime.now(tz=UTC)
        await self._session.flush()
        return user

    async def update_linkedin_tokens(self, user_id: int, tokens: dict) -> None:
        from app.services.linkedin_service import LinkedInService

        result = await self._session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        user.linkedin_tokens_encrypted = LinkedInService.encrypt_tokens(tokens)
        await self._session.flush()

    async def clear_linkedin(self, telegram_id: int) -> User | None:
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return None
        user.linkedin_tokens_encrypted = None
        user.linkedin_name = None
        user.linkedin_member_id = None
        user.linkedin_linked_at = None
        await self._session.flush()
        return user

    def has_linkedin(self, user: User) -> bool:
        return bool(user.linkedin_tokens_encrypted)

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
