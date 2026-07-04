from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformDef:
    id: str
    label_key: str
    emoji: str
    available: bool = True
    locked: bool = False


PLATFORMS: tuple[PlatformDef, ...] = (
    PlatformDef("telegram", "platform_telegram", "📱"),
    PlatformDef("gmail", "platform_gmail", "📧"),
    PlatformDef("yandex", "platform_yandex", "📬"),
    PlatformDef("slack", "platform_slack", "💬"),
    PlatformDef("linkedin", "platform_linkedin", "💼", available=False, locked=True),
)


def get_platform(platform_id: str) -> PlatformDef | None:
    return next((p for p in PLATFORMS if p.id == platform_id), None)


def available_platforms() -> tuple[PlatformDef, ...]:
    return tuple(p for p in PLATFORMS if p.available)
