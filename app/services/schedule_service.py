from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.models.user import User
from app.services.frequency import FREQUENCY_PERIOD, delivery_hours_for_frequency


def user_now(user: User) -> datetime:
    tz = ZoneInfo(user.timezone or "UTC")
    return datetime.now(tz=UTC).astimezone(tz)


def delivery_hours_for_user(user: User) -> list[int]:
    if user.delivery_hour is None or not user.digest_frequency:
        return []
    return delivery_hours_for_frequency(user.delivery_hour, user.digest_frequency)


def is_digest_period_elapsed(user: User, now: datetime | None = None) -> bool:
    """True if enough time passed since the last digest for this frequency."""
    period = FREQUENCY_PERIOD.get(user.digest_frequency or "")
    if not period:
        return False

    now_utc = (now or user_now(user)).astimezone(UTC)
    if user.last_digest_at is None:
        return True

    last = user.last_digest_at
    if last.tzinfo is None:
        last = last.replace(tzinfo=UTC)
    return now_utc - last >= period


def is_scheduled_user_ready(user: User) -> bool:
    if not (
        user.onboarding_complete
        and user.digest_frequency
        and user.delivery_hour is not None
        and user.language
    ):
        return False

    return True
