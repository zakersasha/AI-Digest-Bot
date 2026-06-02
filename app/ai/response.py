def extract_chat_content(data: dict) -> str:
    """Normalize OpenAI-compatible chat completion JSON to plain text."""
    choices = data.get("choices") or []
    if not choices:
        return ""

    choice = choices[0]
    message = choice.get("message") or {}

    content = _normalize_text(message.get("content"))
    if content:
        return content

    # Harmony / reasoning models may put text in alternate fields when content is null.
    for key in ("reasoning", "reasoning_content", "thinking"):
        alt = _normalize_text(message.get(key))
        if alt:
            return alt

    text = choice.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()

    return ""


def completion_finish_reason(data: dict) -> str | None:
    choices = data.get("choices") or []
    if not choices:
        return None
    reason = choices[0].get("finish_reason")
    return str(reason) if reason is not None else None


def _normalize_text(value: object) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, list):
        parts: list[str] = []
        for block in value:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                text = block.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        return "\n".join(parts).strip()

    return str(value).strip()
