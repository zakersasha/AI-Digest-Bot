def chars_for_tokens(tokens: int) -> int:
    """Rough budget: ~3.5 characters per token for mixed RU/EN text."""
    return max(200, int(tokens * 3.5))


def truncate_text(text: str, max_chars: int) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def digest_messages_char_budget(
    max_context_tokens: int,
    *,
    prompt_overhead_tokens: int = 350,
) -> int:
    """Character budget for raw message blocks inside the single digest prompt."""
    input_tokens = max(600, max_context_tokens - prompt_overhead_tokens)
    return chars_for_tokens(input_tokens)


def format_digest_block(source_label: str, link: str, text: str, max_text_chars: int) -> str:
    body = truncate_text(text, max_text_chars)
    return f"---\n{body}\nSOURCE: {source_label}\nLINK: {link}"


def pack_messages_for_digest(
    items: list[tuple[str, str, str]],
    *,
    total_budget_chars: int,
    max_messages: int,
    per_message_max_chars: int,
    min_message_chars: int,
) -> list[str]:
    """
    Pack (source_label, link, text) tuples into blocks that fit total_budget_chars.
    Newest items should be passed first.
    """
    if not items:
        return []

    eligible = [(s, l, t) for s, l, t in items if len(t.strip()) >= min_message_chars]
    if not eligible:
        return []

    eligible = eligible[:max_messages]
    count = len(eligible)
    per_cap = min(per_message_max_chars, max(80, total_budget_chars // count))

    blocks: list[str] = []
    used = 0
    separator_len = 2  # "\n\n"

    for source_label, link, text in eligible:
        block = format_digest_block(source_label, link, text, per_cap)
        extra = len(block) + (separator_len if blocks else 0)
        if used + extra > total_budget_chars:
            if not blocks:
                block = format_digest_block(
                    source_label,
                    link,
                    text,
                    max(80, total_budget_chars - len(source_label) - len(link) - 20),
                )
                blocks.append(block)
            break
        blocks.append(block)
        used += extra

    return blocks
