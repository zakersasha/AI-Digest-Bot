import re

from app.ai.prompts import NO_NEW_CONTENT_MARKER

_LINK_PLACEHOLDER_RE = re.compile(r"<\s*LINK\s*>", re.IGNORECASE)
_URL_IN_PARENS_RE = re.compile(r"\(https?://[^\s)]+\)")


def is_no_new_content_response(text: str) -> bool:
    cleaned = text.strip().strip("*_").upper()
    if not cleaned:
        return True
    if cleaned == NO_NEW_CONTENT_MARKER:
        return True
    if cleaned.startswith(NO_NEW_CONTENT_MARKER) and len(cleaned) < 40:
        return True
    return NO_NEW_CONTENT_MARKER in cleaned and len(cleaned) < 60


def _markdown_link(link_label: str, url: str) -> str:
    return f"[{link_label}]({url})"


def format_digest_links(digest: str, link_label: str, post_urls: list[str] | None = None) -> str:
    """Normalize AI output: placeholders and parenthetical URLs → [{label}](url)."""
    result = digest.strip()

    if post_urls:
        for url in post_urls:
            if _LINK_PLACEHOLDER_RE.search(result):
                result = _LINK_PLACEHOLDER_RE.sub(_markdown_link(link_label, url), result, count=1)

    result = _URL_IN_PARENS_RE.sub(
        lambda m: _markdown_link(link_label, m.group(0)[1:-1]),
        result,
    )
    return result


def repair_digest_link_placeholders(
    digest: str,
    post_urls: list[str],
    *,
    link_label: str = "open",
) -> str:
    return format_digest_links(digest, link_label, post_urls)
