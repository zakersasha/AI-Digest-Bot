import re

_TME_RE = re.compile(
    r"(?:https?://)?(?:www\.)?t\.me/(?!\+)([a-zA-Z0-9_]{4,32})",
    re.IGNORECASE,
)
_AT_RE = re.compile(r"@([a-zA-Z0-9_]{4,32})")


def channel_username(telegram_source: str) -> str:
    return telegram_source.lstrip("@").lower()


def normalize_source(username: str) -> str:
    name = channel_username(username)
    if not name:
        raise ValueError("empty username")
    return f"@{name}"


def parse_channel_links(text: str) -> list[str]:
    """Extract @usernames from text (t.me/..., @channel, one or many per message)."""
    found: list[str] = []
    seen: set[str] = set()

    for token in re.split(r"[\s,;]+", text.strip()):
        token = token.strip()
        if not token:
            continue

        for match in _TME_RE.finditer(token):
            key = match.group(1).lower()
            if key not in seen:
                seen.add(key)
                found.append(f"@{key}")

        if _TME_RE.search(token):
            continue

        for match in _AT_RE.finditer(token):
            key = match.group(1).lower()
            if key not in seen:
                seen.add(key)
                found.append(f"@{key}")

    return found


def channel_url(telegram_source: str) -> str:
    return f"https://t.me/{channel_username(telegram_source)}"


def message_url(telegram_source: str, message_id: int) -> str:
    return f"https://t.me/{channel_username(telegram_source)}/{message_id}"


def markdown_source_link(telegram_source: str, message_id: int) -> str:
    username = channel_username(telegram_source)
    url = message_url(telegram_source, message_id)
    return f"[@{username}]({url})"
