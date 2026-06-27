def chars_for_tokens(tokens: int) -> int:
    """Rough budget: ~3.5 characters per token for mixed RU/EN text."""
    return max(200, int(tokens * 3.5))


def estimate_tokens(text: str) -> int:
    return max(1, int(len(text) / 3.5))


def truncate_text(text: str, max_chars: int) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def capped_output_tokens(max_context_tokens: int, max_output_tokens: int) -> int:
    """Cap completion size; large-context models keep a fixed output ceiling."""
    if max_context_tokens >= 8192:
        return min(max_output_tokens, 4096)
    return min(max_output_tokens, max(400, max_context_tokens // 2))


def digest_input_char_budget(
    max_context_tokens: int,
    *,
    max_output_tokens: int,
    template_chars: int = 650,
    margin_tokens: int = 80,
) -> int:
    """Character budget for message blocks (prompt template and completion excluded)."""
    output_tokens = capped_output_tokens(max_context_tokens, max_output_tokens)
    input_token_budget = max_context_tokens - output_tokens - margin_tokens
    template_tokens = estimate_tokens("x" * template_chars)
    block_tokens = max(250, input_token_budget - template_tokens)
    return chars_for_tokens(block_tokens)


def digest_prompt_max_chars(
    max_context_tokens: int,
    *,
    max_output_tokens: int,
    template_chars: int = 650,
) -> int:
    return template_chars + digest_input_char_budget(
        max_context_tokens,
        max_output_tokens=max_output_tokens,
        template_chars=template_chars,
    )


def effective_output_tokens_for_prompt(
    max_context_tokens: int,
    max_output_tokens: int,
    prompt_chars: int,
    *,
    safety_tokens: int = 96,
) -> int:
    """Fit completion budget so prompt_tokens + completion_tokens <= context."""
    prompt_tokens = estimate_tokens("x" * prompt_chars)
    room = max_context_tokens - prompt_tokens - safety_tokens
    cap = capped_output_tokens(max_context_tokens, max_output_tokens)
    return max(256, min(cap, int(room)))


def format_digest_block(source_label: str, post_url: str, text: str, max_text_chars: int) -> str:
    body = truncate_text(text, max_text_chars)
    return f"---\n{body}\nSOURCE: {source_label}\nPOST_URL: {post_url}"


def pack_messages_for_digest(
    items: list[tuple[str, str, str]],
    *,
    total_budget_chars: int,
    max_messages: int,
    per_message_max_chars: int,
    min_message_chars: int,
) -> list[str]:
    """
    Pack (source_label, post_url, text) tuples into blocks that fit total_budget_chars.
    Newest items should be passed first.
    """
    if not items:
        return []

    eligible = [(s, u, t) for s, u, t in items if len(t.strip()) >= min_message_chars]
    if not eligible:
        return []

    eligible = eligible[:max_messages]
    count = len(eligible)
    per_cap = min(per_message_max_chars, max(80, total_budget_chars // count))

    blocks: list[str] = []
    used = 0
    separator_len = 2

    for source_label, post_url, text in eligible:
        block = format_digest_block(source_label, post_url, text, per_cap)
        extra = len(block) + (separator_len if blocks else 0)
        if used + extra > total_budget_chars:
            if not blocks:
                overhead = len(source_label) + len(post_url) + 24
                block = format_digest_block(
                    source_label,
                    post_url,
                    text,
                    max(80, total_budget_chars - overhead),
                )
                blocks.append(block)
            break
        blocks.append(block)
        used += extra

    return blocks


def pack_messages_for_digest_by_source(
    items: list[tuple[str, str, str]],
    *,
    total_budget_chars: int,
    max_messages: int,
    per_message_max_chars: int,
    min_message_chars: int,
) -> list[str]:
    """Group posts by channel with a fair char budget per source for multi-channel digests."""
    if not items:
        return []

    groups: dict[str, list[tuple[str, str, str]]] = {}
    order: list[str] = []
    for item in items:
        label = item[0]
        if label not in groups:
            groups[label] = []
            order.append(label)
        groups[label].append(item)

    if len(order) <= 1:
        return pack_messages_for_digest(
            items,
            total_budget_chars=total_budget_chars,
            max_messages=max_messages,
            per_message_max_chars=per_message_max_chars,
            min_message_chars=min_message_chars,
        )

    section_blocks: list[str] = []
    source_count = len(order)
    per_source_budget = max(400, total_budget_chars // source_count)
    per_source_messages = max(2, max_messages // source_count)

    for label in order:
        group_blocks = pack_messages_for_digest(
            groups[label],
            total_budget_chars=per_source_budget,
            max_messages=per_source_messages,
            per_message_max_chars=per_message_max_chars,
            min_message_chars=min_message_chars,
        )
        if not group_blocks:
            continue
        section_blocks.append(f"=== {label} ===\n" + "\n\n".join(group_blocks))

    return section_blocks
