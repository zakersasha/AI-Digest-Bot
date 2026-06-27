from datetime import UTC, datetime, timedelta

FREQUENCY_CODES = ("12h", "1d", "3d", "1w")

FREQUENCY_PERIOD: dict[str, timedelta] = {
    "12h": timedelta(hours=12),
    "1d": timedelta(days=1),
    "3d": timedelta(days=3),
    "1w": timedelta(weeks=1),
}

FREQUENCY_DAYS: dict[str, int] = {
    "1d": 1,
    "3d": 3,
    "1w": 7,
}


def parse_frequency(code: str) -> timedelta:
    if code not in FREQUENCY_PERIOD:
        raise ValueError(f"Unknown frequency: {code}")
    return FREQUENCY_PERIOD[code]


def digest_content_since(frequency: str, now: datetime | None = None) -> datetime:
    """Rolling window start for digest content (e.g. 1d → last 24 hours)."""
    moment = now or datetime.now(tz=UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment - parse_frequency(frequency)


def delivery_hours_for_frequency(delivery_hour: int, frequency: str) -> list[int]:
    """Hours (0-23) when digest is delivered in user's timezone."""
    if frequency == "12h":
        return [delivery_hour % 24, (delivery_hour + 12) % 24]
    return [delivery_hour % 24]
