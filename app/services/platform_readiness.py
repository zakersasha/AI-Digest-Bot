from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform_settings import PlatformSettings
from app.models.user import User
from app.repositories.source_repository import SourceRepository
from app.repositories.user_repository import UserRepository


async def is_platform_connected(session: AsyncSession, user: User, platform: str) -> bool:
    if platform == "telegram":
        return await SourceRepository(session).count_active(user.id) > 0
    if platform == "gmail":
        return UserRepository(session).has_gmail(user)
    return False


def is_platform_scheduled(settings: PlatformSettings | None) -> bool:
    return bool(settings and settings.digest_frequency and settings.delivery_hour is not None)


async def can_deliver_platform(
    session: AsyncSession,
    user: User,
    platform: str,
    settings: PlatformSettings | None,
) -> bool:
    if not is_platform_scheduled(settings):
        return False
    return await is_platform_connected(session, user, platform)
