from urllib.parse import parse_qs, urlparse


def parse_oauth_code(text: str) -> str | None:
    """Extract OAuth authorization code from a raw code or full redirect URL."""
    raw = (text or "").strip()
    if not raw:
        return None

    if "code=" in raw:
        if "://" in raw:
            parsed = urlparse(raw)
            query = parse_qs(parsed.query)
            codes = query.get("code")
            return codes[0] if codes else None
        if raw.startswith("code="):
            return raw.split("=", 1)[1].split("&", 1)[0].strip()
        for part in raw.split("&"):
            if part.startswith("code="):
                return part.split("=", 1)[1].strip()

    if "/" not in raw and len(raw) > 20:
        return raw

    return None


def parse_yandex_oauth_code(text: str) -> str | None:
    """Extract Yandex OAuth code from URL or plain text from verification_code page."""
    code = parse_oauth_code(text)
    if code:
        return code
    raw = (text or "").strip()
    if not raw or "/" in raw or " " in raw:
        return None
    # Code copied from https://oauth.yandex.ru/verification_code page
    if len(raw) >= 7:
        return raw
    return None
