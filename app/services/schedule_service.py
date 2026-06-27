from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from app.models.platform_settings import PlatformSettings
from app.models.user import User
from app.services.frequency import FREQUENCY_DAYS, FREQUENCY_PERIOD, delivery_hours_for_frequency


def user_now(user: User) -> datetime:
    tz = ZoneInfo(user.timezone or "UTC")
    return datetime.now(tz=UTC).astimezone(tz)


def delivery_hours_for_settings(settings: PlatformSettings) -> list[int]:
    if settings.delivery_hour is None or not settings.digest_frequency:
        return []
    return delivery_hours_for_frequency(settings.delivery_hour, settings.digest_frequency)


def _normalize_last_digest(last: datetime) -> datetime:
    if last.tzinfo is None:
        return last.replace(tzinfo=UTC)
    return last


def _latest_slot_at_or_before(
    now_local: datetime,
    hour: int,
    minute: int,
) -> datetime:
    slot = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if now_local < slot:
        slot -= timedelta(days=1)
    return slot


def _latest_slot_for_12h(
    now_local: datetime,
    hour: int,
    minute: int,
) -> datetime:
    slots = [
        _latest_slot_at_or_before(now_local, (hour + offset) % 24, minute)
        for offset in (0, 12)
    ]
    return max(slots)


def is_digest_period_elapsed(
    settings: PlatformSettings,
    user: User,
    now: datetime | None = None,
) -> bool:
    """
    Whether a new scheduled digest may be sent.

    Daily / multi-day frequencies use calendar delivery slots in the user's timezone
    so a digest at 11:03 yesterday does not block today's 11:00 run.
    """
    frequency = settings.digest_frequency or ""
    if frequency not in FREQUENCY_PERIOD:
        return False

    if settings.last_digest_at is None:
        return True

    now_local = (now or user_now(user)).astimezone(
        ZoneInfo(user.timezone or "UTC")
    )
    last_local = _normalize_last_digest(settings.last_digest_at).astimezone(now_local.tzinfo)
    hour = settings.delivery_hour if settings.delivery_hour is not None else 0
    minute = settings.delivery_minute or 0

    if frequency == "12h":
        slot = _latest_slot_for_12h(now_local, hour, minute)
        return last_local < slot

    period_days = FREQUENCY_DAYS.get(frequency)
    if period_days is not None:
        slot = _latest_slot_at_or_before(now_local, hour, minute)
        threshold = slot - timedelta(days=period_days - 1)
        return last_local < threshold

    period = FREQUENCY_PERIOD[frequency]
    now_utc = now_local.astimezone(UTC)
    last_utc = last_local.astimezone(UTC)
    return now_utc - last_utc >= period
