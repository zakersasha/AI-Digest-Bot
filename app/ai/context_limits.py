def chars_for_tokens(tokens: int) -> int:
    """Rough budget: ~3.5 characters per token for mixed RU/EN text."""
    return max(200, int(tokens * 3.5))


def truncate_text(text: str, max_chars: int) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def fit_items_to_budget(items: list[str], max_chars: int, separator: str = "\n\n") -> list[str]:
    if not items:
        return []
    selected: list[str] = []
    used = 0
    sep_len = len(separator)
    for item in items:
        piece = truncate_text(item, max_chars // 4)
        extra = len(piece) + (sep_len if selected else 0)
        if used + extra > max_chars:
            break
        selected.append(piece)
        used += extra
    return selected
