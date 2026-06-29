import re
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

_PROFILE_KINDS = frozenset({"in", "company", "school", "showcase"})
_ACTIVITY_IN_PATH_RE = re.compile(
    r"(?:feed/update/urn:li:(?:activity|share):|posts/[^/]+activity[-:])"
    r"(?P<id>\d{10,})",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ParsedLinkedInProfile:
    slug: str
    profile_type: str
    url: str
    title: str
    linkedin_urn: str | None = None


def _activity_from_path(path: str) -> str | None:
    match = _ACTIVITY_IN_PATH_RE.search(path)
    return match.group("id") if match else None


def _normalize_linkedin_path(path: str) -> str:
    path = unquote(path or "").strip()
    if not path.startswith("/"):
        path = f"/{path}"
    path = path.rstrip("/")

    parts = [part for part in path.split("/") if part]
    if len(parts) >= 3 and parts[0].lower() == "mwlite" and parts[1].lower() == "in":
        parts = ["in", parts[2], *parts[3:]]

    if parts and parts[0].lower() in _PROFILE_KINDS and len(parts) >= 2:
        return f"/{parts[0].lower()}/{parts[1]}"

    return path


def normalize_linkedin_profile(raw: str) -> ParsedLinkedInProfile:
    text = raw.strip()
    if not text:
        raise ValueError("empty")

    if text.startswith("http://") or text.startswith("https://"):
        parsed = urlparse(text)
        host = (parsed.netloc or "").lower().removeprefix("www.")
        if host not in ("linkedin.com", "m.linkedin.com"):
            raise ValueError("host")
        path = _normalize_linkedin_path(parsed.path or "")
    elif text.lower().startswith("linkedin.com/") or text.lower().startswith("m.linkedin.com/"):
        path = _normalize_linkedin_path("/" + text.split("/", 1)[1])
    elif text.lower().startswith("in/") or text.lower().startswith("company/"):
        path = _normalize_linkedin_path("/" + text)
    elif text.startswith("@"):
        slug = text.lstrip("@").strip().lower()
        if not slug:
            raise ValueError("slug")
        url = f"https://www.linkedin.com/in/{slug}"
        return ParsedLinkedInProfile(slug=slug, profile_type="person", url=url, title=slug)
    else:
        raise ValueError("format")

    activity_id = _activity_from_path(path)
    if activity_id:
        urn = f"urn:li:activity:{activity_id}"
        url = f"https://www.linkedin.com/feed/update/{urn}"
        return ParsedLinkedInProfile(
            slug=f"activity-{activity_id}",
            profile_type="person",
            url=url,
            title=activity_id,
            linkedin_urn=urn,
        )

    parts = [part for part in path.strip("/").split("/") if part]
    if len(parts) < 2 or parts[0].lower() not in _PROFILE_KINDS:
        raise ValueError("path")

    kind = parts[0].lower()
    slug = unquote(parts[1]).lower().rstrip("/")
    if not slug:
        raise ValueError("slug")

    profile_type = "company" if kind in ("company", "school", "showcase") else "person"
    url = f"https://www.linkedin.com/{kind}/{slug}"
    return ParsedLinkedInProfile(slug=slug, profile_type=profile_type, url=url, title=slug)


def parse_linkedin_profiles(text: str) -> list[str]:
    lines = [line.strip() for line in text.replace(",", "\n").splitlines()]
    return [line for line in lines if line]
