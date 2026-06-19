import re
from datetime import UTC, datetime, timedelta
from html import unescape
from urllib.parse import quote, unquote

import httpx

from app.models.linkedin_profile import LinkedInProfile
from app.services.content_message import ContentMessage
from app.utils.http_proxy import create_httpx_client
from app.utils.logging import get_logger

logger = get_logger(__name__)

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

_ACTIVITY_PATTERNS = (
    re.compile(r"urn:li:activity:(\d+)", re.I),
    re.compile(r"activity[:-](\d{10,})", re.I),
    re.compile(r"/feed/update/urn:li:activity:(\d+)", re.I),
)


def extract_activity_ids(text: str) -> list[str]:
    found: set[str] = set()
    for pattern in _ACTIVITY_PATTERNS:
        found.update(pattern.findall(text))
    return sorted(found, reverse=True)


def parse_relative_age(value: str) -> timedelta | None:
    text = value.strip().lower()
    match = re.fullmatch(r"(\d+)\s*(s|sec|secs|second|seconds|m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days|w|wk|wks|week|weeks|mo|mos|month|months|y|yr|yrs|year|years)", text)
    if not match:
        return None
    amount = int(match.group(1))
    unit = match.group(2)
    if unit in {"s", "sec", "secs", "second", "seconds"}:
        return timedelta(seconds=amount)
    if unit in {"m", "min", "mins", "minute", "minutes"}:
        return timedelta(minutes=amount)
    if unit in {"h", "hr", "hrs", "hour", "hours"}:
        return timedelta(hours=amount)
    if unit in {"d", "day", "days"}:
        return timedelta(days=amount)
    if unit in {"w", "wk", "wks", "week", "weeks"}:
        return timedelta(weeks=amount)
    if unit in {"mo", "mos", "month", "months"}:
        return timedelta(days=amount * 30)
    return timedelta(days=amount * 365)


def is_within_since(relative: str | None, since: datetime) -> bool:
    if not relative:
        return True
    delta = parse_relative_age(relative)
    if not delta:
        return True
    return datetime.now(tz=UTC) - delta >= since


def extract_author_slug(html: str) -> str | None:
    for pattern in (
        r"linkedin\.com/in/([a-zA-Z0-9\-_%]+)",
        r"linkedin\.com/posts/([a-zA-Z0-9\-_%]+)_",
    ):
        match = re.search(pattern, html, re.I)
        if match:
            return match.group(1).lower()
    return None


def _extract_meta_description(html: str) -> str:
    for pattern in (
        r'<meta[^>]+property="og:description"[^>]+content="([^"]*)"',
        r'<meta[^>]+content="([^"]*)"[^>]+property="og:description"',
        r'<meta[^>]+name="description"[^>]+content="([^"]*)"',
    ):
        match = re.search(pattern, html, re.I | re.S)
        if match and match.group(1).strip():
            return unescape(match.group(1).strip())
    return ""


def _extract_relative_time(html: str) -> str | None:
    match = re.search(r"<time[^>]*>(.*?)</time>", html, re.I | re.S)
    if not match:
        return None
    text = re.sub(r"<[^>]+>", "", match.group(1))
    text = unescape(text).strip()
    return text or None


async def fetch_embed_post(
    client: httpx.AsyncClient,
    activity_id: str,
) -> tuple[str, str, str | None, str | None]:
    url = f"https://www.linkedin.com/embed/feed/update/urn:li:activity:{activity_id}"
    try:
        response = await client.get(url, headers=_BROWSER_HEADERS)
    except httpx.HTTPError as exc:
        logger.warning("linkedin_embed_failed", activity_id=activity_id, error=str(exc))
        return "", "", None, None

    if response.status_code != 200 or len(response.text) < 1000:
        return "", "", None, None

    html = response.text
    text = _extract_meta_description(html)
    if not text:
        return "", "", None, None

    post_url = f"https://www.linkedin.com/feed/update/urn:li:activity:{activity_id}"
    relative = _extract_relative_time(html)
    author_slug = extract_author_slug(html)
    return text, post_url, relative, author_slug


async def _search_activity_ids(
    client: httpx.AsyncClient,
    slug: str,
    profile_type: str,
    *,
    max_ids: int,
) -> list[str]:
    queries: list[str] = []
    if profile_type == "company":
        queries.append(f"site:linkedin.com/posts/{slug}")
        queries.append(f"site:linkedin.com/company/{slug}")
    else:
        queries.append(f"site:linkedin.com/posts/{slug}")
        queries.append(f"site:linkedin.com/in/{slug}")

    found: list[str] = []
    seen: set[str] = set()

    async def collect_from_html(html: str) -> None:
        for activity_id in extract_activity_ids(html):
            if activity_id in seen:
                continue
            seen.add(activity_id)
            found.append(activity_id)
            if len(found) >= max_ids:
                return

    for query in queries:
        ddg_url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
        try:
            response = await client.get(ddg_url, headers=_BROWSER_HEADERS)
            if response.status_code == 200:
                await collect_from_html(response.text)
        except httpx.HTTPError:
            pass
        if len(found) >= max_ids:
            break

        bing_url = "https://www.bing.com/search"
        try:
            response = await client.get(bing_url, params={"q": query}, headers=_BROWSER_HEADERS)
            if response.status_code == 200:
                await collect_from_html(response.text)
        except httpx.HTTPError:
            pass
        if len(found) >= max_ids:
            break

    logger.info("linkedin_public_discovered", slug=slug, count=len(found))
    return found[:max_ids]


async def discover_activity_ids(
    proxy_url: str | None,
    slug: str,
    profile_type: str,
    *,
    max_ids: int,
) -> list[str]:
    async with create_httpx_client(proxy_url, timeout=30.0) as client:
        return await _search_activity_ids(client, slug, profile_type, max_ids=max_ids)


async def fetch_public_posts(
    profile: LinkedInProfile,
    since: datetime,
    *,
    max_posts: int,
    proxy_url: str | None,
) -> list[ContentMessage]:
    activity_ids: list[str] = []

    if profile.linkedin_urn and profile.linkedin_urn.startswith("urn:li:activity:"):
        activity_ids.append(profile.linkedin_urn.rsplit(":", 1)[-1])

    discovered = await discover_activity_ids(
        proxy_url,
        profile.profile_slug,
        profile.profile_type,
        max_ids=max_posts,
    )
    for activity_id in discovered:
        if activity_id not in activity_ids:
            activity_ids.append(activity_id)

    if not activity_ids:
        return []

    label = profile.title or profile.profile_slug
    messages: list[ContentMessage] = []

    async with create_httpx_client(proxy_url, timeout=30.0) as client:
        for activity_id in activity_ids[:max_posts]:
            text, post_url, relative, author_slug = await fetch_embed_post(client, activity_id)
            if not text:
                continue
            if author_slug and author_slug != profile.profile_slug.lower():
                continue
            if not is_within_since(relative, since):
                continue
            created = datetime.now(tz=UTC)
            delta = parse_relative_age(relative) if relative else None
            if delta:
                created = datetime.now(tz=UTC) - delta
            messages.append(
                ContentMessage(
                    text=text[:2000],
                    source=f"linkedin:{label}",
                    date=created,
                    message_id=f"activity:{activity_id}",
                    post_url=post_url,
                )
            )

    logger.info(
        "linkedin_public_fetched",
        slug=profile.profile_slug,
        discovered=len(activity_ids),
        matched=len(messages),
    )
    return messages


async def resolve_profile_from_activity_url(
    activity_url: str,
    *,
    proxy_url: str | None,
) -> tuple[str | None, str | None]:
    ids = extract_activity_ids(activity_url)
    if not ids:
        return None, None
    activity_id = ids[0]
    async with create_httpx_client(proxy_url, timeout=30.0) as client:
        _, _, _, author_slug = await fetch_embed_post(client, activity_id)
    if not author_slug:
        return None, f"urn:li:activity:{activity_id}"
    return author_slug, f"urn:li:activity:{activity_id}"
