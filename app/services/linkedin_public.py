import re
from datetime import UTC, datetime, timedelta
from html import unescape
from urllib.parse import quote, unquote

import httpx

from app.models.linkedin_profile import LinkedInProfile
from app.services.content_message import ContentMessage
from app.utils.linkedin_block import LinkedInBlockedError, is_linkedin_blocked
from app.utils.linkedin_http import LinkedInHttpRouter
from app.utils.logging import get_logger

logger = get_logger(__name__)

_ACTIVITY_PATTERNS = (
    re.compile(r"urn:li:activity:(\d+)", re.I),
    re.compile(r"activity%3A(\d{10,})", re.I),
    re.compile(r"activity%2D(\d{10,})", re.I),
    re.compile(r"activity[:-](\d{10,})", re.I),
    re.compile(r"/feed/update/urn:li:activity:(\d+)", re.I),
)


def extract_activity_ids(text: str) -> list[str]:
    decoded = unescape(text)
    url_decoded = unquote(decoded)
    blob = f"{text}\n{decoded}\n{url_decoded}"
    found: set[str] = set()
    for pattern in _ACTIVITY_PATTERNS:
        found.update(pattern.findall(blob))
    for match in re.finditer(r"uddg=([^&\"]+)", blob):
        link = unquote(match.group(1))
        for pattern in _ACTIVITY_PATTERNS:
            found.update(pattern.findall(link))
    return sorted(found, reverse=True)


def parse_relative_age(value: str) -> timedelta | None:
    text = value.strip().lower()
    match = re.fullmatch(
        r"(\d+)\s*"
        r"(s|sec|secs|second|seconds|m|min|mins|minute|minutes|h|hr|hrs|hour|hours|"
        r"d|day|days|w|wk|wks|week|weeks|mo|mos|month|months|y|yr|yrs|year|years)",
        text,
    )
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


def is_within_since(
    relative: str | None,
    since: datetime,
    *,
    absolute: datetime | None = None,
) -> bool:
    if absolute is not None:
        return absolute >= since
    if not relative:
        return True
    delta = parse_relative_age(relative)
    if not delta:
        return True
    return datetime.now(tz=UTC) - delta >= since


def post_created_at(relative: str | None, absolute: datetime | None) -> datetime:
    if absolute is not None:
        return absolute
    if relative:
        delta = parse_relative_age(relative)
        if delta:
            return datetime.now(tz=UTC) - delta
    return datetime.now(tz=UTC)


def widen_public_since(since: datetime, lookback_days: int) -> datetime:
    floor = datetime.now(tz=UTC) - timedelta(days=lookback_days)
    return min(since, floor)


def _slug_matches(author_slug: str | None, expected: str) -> bool:
    if not author_slug:
        return True
    return author_slug.replace("-", "").lower() == expected.replace("-", "").lower()


def extract_author_slug(html: str) -> str | None:
    for pattern in (
        r"linkedin\.com/in/([a-zA-Z0-9\-_%]+)",
        r"linkedin\.com/posts/([a-zA-Z0-9\-_%]+)_",
    ):
        match = re.search(pattern, html, re.I)
        if match:
            return unquote(match.group(1)).lower()
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


def _extract_absolute_time(html: str) -> datetime | None:
    match = re.search(r'<time[^>]+datetime="([^"]+)"', html, re.I)
    if not match:
        return None
    raw = match.group(1).strip()
    try:
        if raw.endswith("Z"):
            raw = f"{raw[:-1]}+00:00"
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except ValueError:
        return None


async def fetch_embed_post(
    client: httpx.AsyncClient,
    activity_id: str,
    headers: dict[str, str],
) -> tuple[str, str, str | None, str | None, datetime | None]:
    url = f"https://www.linkedin.com/embed/feed/update/urn:li:activity:{activity_id}"
    try:
        response = await client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning("linkedin_embed_failed", activity_id=activity_id, error=str(exc))
        return "", "", None, None, None

    if is_linkedin_blocked(response.status_code, response.text):
        logger.warning(
            "linkedin_embed_blocked",
            activity_id=activity_id,
            status=response.status_code,
            body_len=len(response.text),
        )
        raise LinkedInBlockedError(f"embed blocked status={response.status_code}")

    if response.status_code != 200 or len(response.text) < 1000:
        logger.info(
            "linkedin_embed_skip",
            activity_id=activity_id,
            status=response.status_code,
            body_len=len(response.text),
        )
        return "", "", None, None, None

    html = response.text
    text = _extract_meta_description(html)
    if not text:
        return "", "", None, None, None

    post_url = f"https://www.linkedin.com/feed/update/urn:li:activity:{activity_id}"
    relative = _extract_relative_time(html)
    absolute = _extract_absolute_time(html)
    author_slug = extract_author_slug(html)
    return text, post_url, relative, author_slug, absolute


async def _google_cse_search(
    client: httpx.AsyncClient,
    query: str,
    *,
    api_key: str,
    cx: str,
    max_ids: int,
) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    start = 1
    while len(found) < max_ids and start <= 31:
        try:
            response = await client.get(
                "https://www.googleapis.com/customsearch/v1",
                params={
                    "key": api_key,
                    "cx": cx,
                    "q": query,
                    "num": min(10, max_ids - len(found)),
                    "start": start,
                },
            )
        except httpx.HTTPError as exc:
            logger.warning("linkedin_google_cse_failed", error=str(exc))
            break
        if response.status_code != 200:
            logger.warning(
                "linkedin_google_cse_failed",
                status=response.status_code,
                body=response.text[:200],
            )
            break
        data = response.json()
        items = data.get("items", [])
        if not items:
            break
        for item in items:
            link = item.get("link", "")
            for activity_id in extract_activity_ids(link):
                if activity_id in seen:
                    continue
                seen.add(activity_id)
                found.append(activity_id)
                if len(found) >= max_ids:
                    break
        start += 10
    logger.info("linkedin_google_cse_discovered", query=query[:80], count=len(found))
    return found


async def _probe_forward_posts(
    client: httpx.AsyncClient,
    slug: str,
    seed_id: str,
    since: datetime,
    headers: dict[str, str],
    *,
    max_checks: int = 24,
) -> list[tuple[str, str, str | None, str]]:
    found: list[tuple[str, str, str | None, str]] = []
    try:
        base = int(seed_id)
    except ValueError:
        return found

    step = 400
    for i in range(max_checks):
        activity_id = str(base + (i + 1) * step)
        text, post_url, relative, author_slug, absolute = await fetch_embed_post(
            client, activity_id, headers
        )
        if not text:
            continue
        if not _slug_matches(author_slug, slug):
            continue
        if not is_within_since(relative, since, absolute=absolute):
            continue
        found.append((activity_id, text, relative, post_url))
    return found


async def scrape_profile_activity_ids(
    client: httpx.AsyncClient,
    slug: str,
    headers: dict[str, str],
    *,
    max_ids: int,
) -> list[str]:
    """Extract activity IDs from public profile / recent-activity HTML pages."""
    templates = (
        "https://www.linkedin.com/in/{slug}/recent-activity/all/",
        "https://www.linkedin.com/in/{slug}/recent-activity/shares/",
        "https://www.linkedin.com/mwlite/in/{slug}/recent-activity/all",
        "https://www.linkedin.com/in/{slug}/",
    )
    found: list[str] = []
    seen: set[str] = set()

    for template in templates:
        url = template.format(slug=slug)
        try:
            response = await client.get(url, headers=headers)
        except httpx.HTTPError as exc:
            logger.warning("linkedin_profile_scrape_failed", url=url, error=str(exc))
            continue
        if response.status_code != 200:
            if is_linkedin_blocked(response.status_code, response.text):
                logger.warning(
                    "linkedin_profile_blocked",
                    url=url,
                    status=response.status_code,
                )
            else:
                logger.info(
                    "linkedin_profile_scrape_skip",
                    url=url,
                    status=response.status_code,
                )
            continue
        for activity_id in extract_activity_ids(response.text):
            if activity_id in seen:
                continue
            seen.add(activity_id)
            found.append(activity_id)
            if len(found) >= max_ids:
                return found[:max_ids]

    logger.info("linkedin_profile_scrape_discovered", slug=slug, count=len(found))
    return found[:max_ids]


async def _search_activity_ids(
    client: httpx.AsyncClient,
    slug: str,
    profile_type: str,
    headers: dict[str, str],
    *,
    max_ids: int,
    google_cse_api_key: str | None = None,
    google_cse_cx: str | None = None,
) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()

    def add_ids(ids: list[str]) -> None:
        for activity_id in ids:
            if activity_id in seen:
                continue
            seen.add(activity_id)
            found.append(activity_id)

    if google_cse_api_key and google_cse_cx:
        cse_queries = [
            f"site:linkedin.com/posts/{slug}",
            f"site:linkedin.com/in/{slug}",
        ]
        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as direct:
            for query in cse_queries:
                add_ids(
                    await _google_cse_search(
                        direct,
                        query,
                        api_key=google_cse_api_key,
                        cx=google_cse_cx,
                        max_ids=max_ids,
                    )
                )
                if len(found) >= max_ids:
                    logger.info("linkedin_cse_discovered", slug=slug, count=len(found))
                    return found[:max_ids]

    if profile_type == "person" and len(found) < max_ids:
        add_ids(await scrape_profile_activity_ids(client, slug, headers, max_ids=max_ids))
        if found:
            logger.info("linkedin_profile_scrape_ids", slug=slug, count=len(found))

    if len(found) >= max_ids:
        return found[:max_ids]

    queries: list[str] = []
    if profile_type == "company":
        queries.append(f"site:linkedin.com/posts/{slug}")
        queries.append(f"site:linkedin.com/company/{slug} posts")
    else:
        queries.append(f"site:linkedin.com/posts/{slug}")
        queries.append(f"site:linkedin.com/in/{slug} posts")

    def collect_from_html(html: str) -> None:
        add_ids(extract_activity_ids(html))
        if len(found) >= max_ids:
            return

    async with httpx.AsyncClient(timeout=30.0, trust_env=False) as direct:
        for query in queries:
            ddg_url = "https://html.duckduckgo.com/html/"
            for method, kwargs in (
                ("GET", {"params": {"q": query}}),
                ("POST", {"data": {"q": query}}),
            ):
                try:
                    if method == "GET":
                        response = await direct.get(ddg_url, headers=headers, **kwargs)
                    else:
                        response = await direct.post(ddg_url, headers=headers, **kwargs)
                    if response.status_code == 200:
                        collect_from_html(response.text)
                except httpx.HTTPError:
                    pass
                if len(found) >= max_ids:
                    break
            if len(found) >= max_ids:
                break

            bing_url = "https://www.bing.com/search"
            try:
                response = await direct.get(bing_url, params={"q": query}, headers=headers)
                if response.status_code == 200:
                    collect_from_html(response.text)
                    for match in re.finditer(
                        r'href="(https://www\.bing\.com/ck/a\?[^"]+)"', response.text
                    ):
                        try:
                            redirect = await direct.get(unescape(match.group(1)), headers=headers)
                            collect_from_html(str(redirect.url))
                            collect_from_html(redirect.text)
                        except httpx.HTTPError:
                            pass
            except httpx.HTTPError:
                pass
            if len(found) >= max_ids:
                break

    logger.info("linkedin_public_discovered", slug=slug, count=len(found))
    return found[:max_ids]


async def discover_activity_ids(
    router: LinkedInHttpRouter,
    slug: str,
    profile_type: str,
    *,
    max_ids: int,
    google_cse_api_key: str | None = None,
    google_cse_cx: str | None = None,
) -> list[str]:
    async def work(_slot, client, headers):
        return await _search_activity_ids(
            client,
            slug,
            profile_type,
            headers,
            max_ids=max_ids,
            google_cse_api_key=google_cse_api_key,
            google_cse_cx=google_cse_cx,
        )

    return await router.run_browser(work)


async def fetch_public_posts(
    profile: LinkedInProfile,
    since: datetime,
    *,
    router: LinkedInHttpRouter,
    max_posts: int,
    lookback_days: int = 30,
    google_cse_api_key: str | None = None,
    google_cse_cx: str | None = None,
) -> list[ContentMessage]:
    since = widen_public_since(since, lookback_days)
    slug = profile.profile_slug.lower()
    activity_ids: list[str] = []
    search_slug = slug

    if profile.linkedin_urn and profile.linkedin_urn.startswith("urn:li:activity:"):
        activity_ids.append(profile.linkedin_urn.rsplit(":", 1)[-1])
    if slug.startswith("activity-"):
        activity_ids.append(slug.removeprefix("activity-"))
        search_slug = ""

    async def work(_slot, client, headers):
        discovered: list[str] = []
        if search_slug:
            discovered = await _search_activity_ids(
                client,
                search_slug,
                profile.profile_type,
                headers,
                max_ids=max_posts * 3,
                google_cse_api_key=google_cse_api_key,
                google_cse_cx=google_cse_cx,
            )

        ids = list(activity_ids)
        for activity_id in discovered:
            if activity_id not in ids:
                ids.append(activity_id)

        label = profile.title or profile.profile_slug
        messages: list[ContentMessage] = []
        seen_posts: set[str] = set()
        author_key = search_slug or None

        if discovered and author_key:
            probed = await _probe_forward_posts(
                client,
                author_key,
                discovered[0],
                since,
                headers,
            )
            for activity_id, text, relative, post_url in probed:
                if activity_id not in ids:
                    ids.insert(0, activity_id)

        embed_failures = 0
        for activity_id in ids[: max_posts * 2]:
            if activity_id in seen_posts:
                continue
            text, post_url, relative, author_slug, absolute = await fetch_embed_post(
                client, activity_id, headers
            )
            if not text:
                embed_failures += 1
                continue
            if author_key and not _slug_matches(author_slug, author_key):
                continue
            if not is_within_since(relative, since, absolute=absolute):
                continue
            seen_posts.add(activity_id)
            created = post_created_at(relative, absolute)
            messages.append(
                ContentMessage(
                    text=text[:2000],
                    source=f"linkedin:{label}",
                    date=created,
                    message_id=f"activity:{activity_id}",
                    post_url=post_url,
                )
            )
            if len(messages) >= max_posts:
                break

        if not messages and ids and embed_failures >= max(3, len(ids) // 2):
            raise LinkedInBlockedError(
                f"found {len(ids)} ids but embeds failed ({embed_failures} attempts)"
            )

        if not ids:
            raise LinkedInBlockedError("no activity ids — LinkedIn scrape blocked, configure GOOGLE_CSE_*")

        logger.info(
            "linkedin_public_fetched",
            slug=profile.profile_slug,
            discovered=len(ids),
            matched=len(messages),
        )
        return messages

    return await router.run_browser(work)


async def resolve_profile_from_activity_url(
    activity_url: str,
    *,
    router: LinkedInHttpRouter,
) -> tuple[str | None, str | None]:
    ids = extract_activity_ids(activity_url)
    if not ids:
        return None, None
    activity_id = ids[0]

    async def work(_slot, client, headers):
        _, _, _, author_slug, _ = await fetch_embed_post(client, activity_id, headers)
        return author_slug

    author_slug = await router.run_browser(work)
    if not author_slug:
        return None, f"urn:li:activity:{activity_id}"
    return author_slug, f"urn:li:activity:{activity_id}"
