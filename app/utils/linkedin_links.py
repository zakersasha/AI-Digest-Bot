import re
from dataclasses import dataclass
from urllib.parse import urlparse

_PROFILE_PATH_RE = re.compile(
    r"^/?(?P<kind>in|company|school|showcase)/(?P<slug>[a-zA-Z0-9\-_%]+)/?",
    re.IGNORECASE,
)
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


def normalize_linkedin_profile(raw: str) -> ParsedLinkedInProfile:
    text = raw.strip()
    if not text:
        raise ValueError("empty")

    if text.startswith("http://") or text.startswith("https://"):
        parsed = urlparse(text)
        host = (parsed.netloc or "").lower().removeprefix("www.")
        if host not in ("linkedin.com", "www.linkedin.com"):
            raise ValueError("host")
        path = parsed.path or ""
    elif text.lower().startswith("linkedin.com/"):
        path = "/" + text.split("/", 1)[1]
    elif text.startswith("@"):
        slug = text.lstrip("@").strip().lower()
        if not slug:
            raise ValueError("slug")
        url = f"https://www.linkedin.com/in/{slug}"
        return ParsedLinkedInProfile(slug=slug.lower(), profile_type="person", url=url, title=slug)
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

    match = _PROFILE_PATH_RE.match(path)
    if not match:
        raise ValueError("path")

    kind = match.group("kind").lower()
    slug = match.group("slug").lower().rstrip("/")
    if not slug:
        raise ValueError("slug")

    profile_type = "company" if kind in ("company", "school", "showcase") else "person"
    url = f"https://www.linkedin.com/{kind}/{slug}"
    return ParsedLinkedInProfile(slug=slug, profile_type=profile_type, url=url, title=slug)


def parse_linkedin_profiles(text: str) -> list[str]:
    lines = [line.strip() for line in text.replace(",", "\n").splitlines()]
    return [line for line in lines if line]
