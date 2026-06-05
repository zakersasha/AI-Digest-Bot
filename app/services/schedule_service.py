from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.models.platform_settings import PlatformSettings
from app.models.user import User
from app.services.frequency import FREQUENCY_PERIOD, delivery_hours_for_frequency


def user_now(user: User) -> datetime:
    tz = ZoneInfo(user.timezone or "UTC")
    return datetime.now(tz=UTC).astimezone(tz)


def delivery_hours_for_settings(settings: PlatformSettings) -> list[int]:
    if settings.delivery_hour is None or not settings.digest_frequency:
        return []
    return delivery_hours_for_frequency(settings.delivery_hour, settings.digest_frequency)


def is_digest_period_elapsed(
    settings: PlatformSettings,
    user: User,
    now: datetime | None = None,
) -> bool:
    period = FREQUENCY_PERIOD.get(settings.digest_frequency or "")
    if not period:
        return False

    now_utc = (now or user_now(user)).astimezone(UTC)
    if settings.last_digest_at is None:
        return True

    last = settings.last_digest_at
    if last.tzinfo is None:
        last = last.replace(tzinfo=UTC)
    return now_utc - last >= period
