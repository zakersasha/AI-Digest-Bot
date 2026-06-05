from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.platform_settings_repository import PlatformSettingsRepository
from app.repositories.source_repository import SourceRepository
from app.repositories.user_repository import UserRepository


async def migrate_legacy_schedules(session: AsyncSession) -> None:
    """Copy user-level schedule to per-platform rows (one-time)."""
    result = await session.execute(
        select(User).where(
            User.digest_frequency.isnot(None),
            User.delivery_hour.isnot(None),
        )
    )
    users = list(result.scalars().all())
    if not users:
        return

    repo = PlatformSettingsRepository(session)
    for user in users:
        for platform in ("telegram", "gmail"):
            existing = await repo.get(user.id, platform)
            if existing and existing.digest_frequency:
                continue

            use = False
            if platform == "telegram":
                use = await SourceRepository(session).count_active(user.id) > 0
            elif platform == "gmail":
                use = UserRepository(session).has_gmail(user)

            if not use and platform == "telegram" and (user.content_platform or "telegram") == "telegram":
                use = True
            if not use and platform == "gmail" and user.content_platform == "gmail":
                use = True

            if not use:
                continue

            row = await repo.get_or_create(user.id, platform)
            row.digest_frequency = user.digest_frequency
            row.delivery_hour = user.delivery_hour
            row.delivery_minute = user.delivery_minute or 0
            row.last_digest_at = user.last_digest_at

    await session.flush()
