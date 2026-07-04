from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform_settings import PlatformSettings
from app.models.user import User
from app.repositories.linkedin_profile_repository import LinkedInProfileRepository
from app.repositories.source_repository import SourceRepository
from app.repositories.slack_channel_repository import SlackChannelRepository
from app.repositories.user_repository import UserRepository


async def is_platform_connected(session: AsyncSession, user: User, platform: str) -> bool:
    if platform == "telegram":
        return await SourceRepository(session).count_active(user.id) > 0
    if platform == "gmail":
        return UserRepository(session).has_gmail(user)
    if platform == "yandex":
        return UserRepository(session).has_yandex(user)
    if platform == "slack":
        repo = UserRepository(session)
        if not repo.has_slack(user):
            return False
        return await SlackChannelRepository(session).count_active(user.id) > 0
    if platform == "linkedin":
        return await LinkedInProfileRepository(session).count_active(user.id) > 0
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


async def can_test_digest(
    session: AsyncSession,
    user: User,
    platform: str,
) -> bool:
    """On-demand test digest: connected sources only, schedule not required."""
    return await is_platform_connected(session, user, platform)
