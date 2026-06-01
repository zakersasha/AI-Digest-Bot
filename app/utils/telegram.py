def split_telegram_message(text: str, limit: int = 4000) -> list[str]:
    if len(text) <= limit:
        return [text]

    parts: list[str] = []
    remaining = text
    while remaining:
        parts.append(remaining[:limit])
        remaining = remaining[limit:]
    return parts
