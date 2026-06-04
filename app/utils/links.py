import re

_TME_RE = re.compile(
    r"(?:https?://)?(?:www\.)?t\.me/(?!\+)([a-zA-Z0-9_]{4,32})",
    re.IGNORECASE,
)
_AT_RE = re.compile(r"@([a-zA-Z0-9_]{4,32})")

MAX_CHANNELS_PER_MESSAGE = 15


def channel_username(telegram_source: str) -> str:
    return telegram_source.lstrip("@").lower()


def normalize_source(username: str) -> str:
    name = channel_username(username)
    if not name:
        raise ValueError("empty username")
    return f"@{name}"


def _links_from_chunk(chunk: str, seen: set[str], found: list[str]) -> None:
    for match in _TME_RE.finditer(chunk):
        key = match.group(1).lower()
        if key not in seen:
            seen.add(key)
            found.append(f"@{key}")

    if _TME_RE.search(chunk):
        return

    for match in _AT_RE.finditer(chunk):
        key = match.group(1).lower()
        if key not in seen:
            seen.add(key)
            found.append(f"@{key}")


def parse_channel_links(text: str) -> list[str]:
    """Extract @usernames from bulk paste (newlines, spaces, commas)."""
    text = text.strip()
    if not text:
        return []

    found: list[str] = []
    seen: set[str] = set()

    lines = [line.strip() for line in re.split(r"[\r\n]+", text) if line.strip()]
    if len(lines) > 1:
        for line in lines:
            _links_from_chunk(line, seen, found)
    else:
        for token in re.split(r"[\s,;]+", text):
            token = token.strip()
            if token:
                _links_from_chunk(token, seen, found)

    return found[:MAX_CHANNELS_PER_MESSAGE]


def channel_url(telegram_source: str) -> str:
    return f"https://t.me/{channel_username(telegram_source)}"


def message_url(telegram_source: str, message_id: int) -> str:
    return f"https://t.me/{channel_username(telegram_source)}/{message_id}"


def markdown_source_link(telegram_source: str, message_id: int) -> str:
    username = channel_username(telegram_source)
    url = message_url(telegram_source, message_id)
    return f"[@{username}]({url})"
