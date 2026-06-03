import re

_LINK_PLACEHOLDER_RE = re.compile(r"<\s*LINK\s*>", re.IGNORECASE)


def repair_digest_link_placeholders(digest: str, post_urls: list[str]) -> str:
    """Replace model placeholders like <LINK> with real POST_URL values."""
    if not post_urls or "<LINK" not in digest.upper():
        return digest

    result = digest
    for url in post_urls:
        if _LINK_PLACEHOLDER_RE.search(result):
            result = _LINK_PLACEHOLDER_RE.sub(f"({url})", result, count=1)
        else:
            break
    return result
