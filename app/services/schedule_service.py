from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.models.user import User
from app.services.frequency import FREQUENCY_PERIOD, delivery_hours_for_frequency


def user_now(user: User) -> datetime:
    tz = ZoneInfo(user.timezone or "UTC")
    return datetime.now(tz=UTC).astimezone(tz)


def is_delivery_moment(user: User, now: datetime | None = None) -> bool:
    if not user.onboarding_complete or user.delivery_hour is None or not user.digest_frequency:
        return False

    now = now or user_now(user)
    target_minute = user.delivery_minute or 0
    if abs(now.minute - target_minute) > 1:
        return False

    allowed_hours = delivery_hours_for_frequency(user.delivery_hour, user.digest_frequency)
    return now.hour in allowed_hours


def is_digest_due(user: User, now: datetime | None = None) -> bool:
    if not is_delivery_moment(user, now):
        return False

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
