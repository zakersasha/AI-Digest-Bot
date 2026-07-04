import re

_LINKEDIN_BLOCK_MARKERS = (
    "authwall",
    "session_redirect",
    "/checkpoint/challenge",
    "checkpoint/lg/login",
    "sign in to linkedin",
    "join linkedin",
    'name="session_key"',
    "unusual activity",
    "captcha-internal",
)

_BLOCK_TITLE_RE = re.compile(
    r"<title[^>]*>\s*(sign in|login|join linkedin|security verification)",
    re.I,
)


class LinkedInBlockedError(Exception):
    """LinkedIn authwall, checkpoint, or hard rate limit."""


def is_linkedin_blocked(status_code: int, html: str) -> bool:
    if status_code in (401, 403, 429, 999):
        return True
    if not html:
        return status_code != 200

    sample = html[:80_000].lower()
    if any(marker in sample for marker in _LINKEDIN_BLOCK_MARKERS):
        return True
    if _BLOCK_TITLE_RE.search(html):
        return True

    # Login wall often returns 200 with a tiny HTML shell.
    if status_code == 200 and len(html) < 2500 and "linkedin" in sample:
        if "auth" in sample or "login" in sample or "signup" in sample:
            return True
    return False
