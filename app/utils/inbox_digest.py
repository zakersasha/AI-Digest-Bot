def fallback_inbox_digest(
    items: list[tuple[str, str, str]],
    link_label: str,
    *,
    max_items: int = 7,
) -> str:
    """Plain subject/body preview digest when the AI returns NO_NEW_CONTENT."""
    lines: list[str] = []
    for idx, (source, url, text) in enumerate(items[:max_items], 1):
        subject = "(no subject)"
        for line in text.splitlines():
            if line.startswith("Subject:"):
                subject = line.removeprefix("Subject:").strip() or subject
                break

        preview = ""
        parts = text.split("\n\n", 1)
        if len(parts) > 1:
            preview = parts[1].strip().replace("\n", " ")
            if len(preview) > 160:
                preview = preview[:157] + "..."

        summary = preview or subject
        lines.append(f"{idx}. **{source}** — {summary} [{link_label}]({url})")

    return "\n\n".join(lines)


def fallback_channel_digest(
    items: list[tuple[str, str, str]],
    link_label: str,
    *,
    max_items: int = 7,
) -> str:
    """Plain preview digest for Telegram/Slack when the AI returns NO_NEW_CONTENT."""
    lines: list[str] = []
    for idx, (source, url, text) in enumerate(items[:max_items], 1):
        preview = text.strip().replace("\n", " ")
        if len(preview) > 180:
            preview = preview[:177] + "..."
        lines.append(f"{idx}. **{source}** — {preview} [{link_label}]({url})")
    return "\n\n".join(lines)
