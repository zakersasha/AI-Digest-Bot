from app.db.session import async_session_factory
from app.repositories.user_repository import UserRepository
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def reschedule_platform_digest(telegram_id: int, platform: str) -> None:
    """Re-register APScheduler jobs after a platform is connected or schedule changes."""
    from app.workers.digest_scheduler import get_digest_scheduler

    scheduler = get_digest_scheduler()
    if not scheduler:
        return

    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(telegram_id)
        if not user:
            return
        await scheduler.schedule_user_platform(user.id, platform)
        logger.info("platform_digest_rescheduled", user_id=user.id, platform=platform)
