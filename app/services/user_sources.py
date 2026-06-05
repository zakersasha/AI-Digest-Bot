from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.source_repository import SourceRepository
from app.repositories.user_repository import UserRepository


async def channel_count(session: AsyncSession, user_id: int) -> int:
    return await SourceRepository(session).count_active(user_id)


def has_gmail(user: User) -> bool:
    return bool(user.gmail_tokens_encrypted)


async def has_any_source(session: AsyncSession, user: User) -> bool:
    return (await channel_count(session, user.id)) > 0 or UserRepository(session).has_gmail(user)


def digest_platform(has_channels: bool, has_gmail_linked: bool) -> str:
    if has_channels and has_gmail_linked:
        return "combined"
    if has_gmail_linked:
        return "gmail"
    return "telegram"
