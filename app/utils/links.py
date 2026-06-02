def channel_username(telegram_source: str) -> str:
    return telegram_source.lstrip("@").lower()


def channel_url(telegram_source: str) -> str:
    return f"https://t.me/{channel_username(telegram_source)}"


def message_url(telegram_source: str, message_id: int) -> str:
    return f"https://t.me/{channel_username(telegram_source)}/{message_id}"


def markdown_source_link(telegram_source: str, message_id: int) -> str:
    """Clickable source label for Telegram Markdown."""
    username = channel_username(telegram_source)
    url = message_url(telegram_source, message_id)
    return f"[@{username}]({url})"
