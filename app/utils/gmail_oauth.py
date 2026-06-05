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
