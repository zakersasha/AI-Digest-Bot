#!/usr/bin/env python3
"""
Standalone LinkedIn public profile post parser.

pip install httpx
python scripts/parse_linkedin_profile.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html import unescape
from urllib.parse import unquote, urlparse

import httpx

# --- настройки ---
PROFILE_URL = "https://www.linkedin.com/in/elenaverna/"
PROXY = "http://proxy_user:97vAN1S@92.112.181.200:3128"

DAYS = 30
MAX_POSTS = 20
VERBOSE = True
# Google CSE — ищет посты без обращения к linkedin.com (100 запросов/день бесплатно)
GOOGLE_CSE_API_KEY = ""  # или os.environ / .env
GOOGLE_CSE_CX = ""
PROXY_2 = ""  # второй прокси для ротации
# -----------------

UTC = timezone.utc

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

ACTIVITY_PATTERNS = (
    re.compile(r"urn:li:activity:(\d+)", re.I),
    re.compile(r"activity%3A(\d{10,})", re.I),
    re.compile(r"activity%2D(\d{10,})", re.I),
    re.compile(r"activity[:-](\d{10,})", re.I),
    re.compile(r"/feed/update/urn:li:activity:(\d+)", re.I),
)

PROFILE_PATH_RE = re.compile(
    r"^/?in/(?P<slug>[a-zA-Z0-9\-_%]+)/?",
    re.IGNORECASE,
)


@dataclass
class Profile:
    slug: str
    url: str


@dataclass
class Post:
    text: str
    url: str
    date: datetime
    activity_id: str


def parse_profile_url(raw: str) -> Profile:
    text = raw.strip()
    if not text.startswith("http"):
        slug = text.lstrip("@/").lower()
        if not slug:
            raise ValueError("empty profile slug")
        return Profile(slug=slug, url=f"https://www.linkedin.com/in/{slug}")

    parsed = urlparse(text)
    host = (parsed.netloc or "").lower().removeprefix("www.")
    if host != "linkedin.com":
        raise ValueError(f"not a linkedin.com URL: {raw}")
    match = PROFILE_PATH_RE.match(parsed.path or "")
    if not match:
        raise ValueError(f"expected /in/username URL, got: {raw}")
    slug = unquote(match.group("slug")).lower().rstrip("/")
    return Profile(slug=slug, url=f"https://www.linkedin.com/in/{slug}")


def extract_activity_ids(text: str) -> list[str]:
    decoded = unescape(text)
    url_decoded = unquote(decoded)
    blob = f"{text}\n{decoded}\n{url_decoded}"
    found: set[str] = set()
    for pattern in ACTIVITY_PATTERNS:
        found.update(pattern.findall(blob))
    for match in re.finditer(r"uddg=([^&\"]+)", blob):
        link = unquote(match.group(1))
        for pattern in ACTIVITY_PATTERNS:
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
            return unquote(match.group(1)).lower()
    return None


def extract_meta_description(html: str) -> str:
    for pattern in (
        r'<meta[^>]+property="og:description"[^>]+content="([^"]*)"',
        r'<meta[^>]+content="([^"]*)"[^>]+property="og:description"',
        r'<meta[^>]+name="description"[^>]+content="([^"]*)"',
    ):
        match = re.search(pattern, html, re.I | re.S)
        if match and match.group(1).strip():
            return unescape(match.group(1).strip())
    return ""


class LinkedInBlocked(Exception):
    pass


def is_linkedin_blocked(status_code: int, html: str) -> bool:
    if status_code in (401, 403, 429, 999):
        return True
    sample = (html or "")[:80_000].lower()
    markers = ("authwall", "session_redirect", "sign in to linkedin", "checkpoint")
    return any(m in sample for m in markers)


def extract_relative_time(html: str) -> str | None:
    match = re.search(r"<time[^>]*>(.*?)</time>", html, re.I | re.S)
    if not match:
        return None
    text = re.sub(r"<[^>]+>", "", match.group(1))
    text = unescape(text).strip()
    return text or None


def fetch_embed_post(client: httpx.Client, activity_id: str) -> tuple[str, str, str | None, str | None]:
    url = f"https://www.linkedin.com/embed/feed/update/urn:li:activity:{activity_id}"
    try:
        response = client.get(url, headers=BROWSER_HEADERS)
    except httpx.HTTPError:
        return "", "", None, None
    if is_linkedin_blocked(response.status_code, response.text):
        if VERBOSE:
            print(f"[embed] {activity_id} -> BLOCKED HTTP {response.status_code}", file=sys.stderr)
        raise LinkedInBlocked(f"embed {activity_id} status={response.status_code}")
    if response.status_code != 200 or len(response.text) < 1000:
        if VERBOSE:
            print(
                f"[embed] {activity_id} -> HTTP {response.status_code}, len={len(response.text)}",
                file=sys.stderr,
            )
        return "", "", None, None
    html = response.text
    text = extract_meta_description(html)
    if not text:
        return "", "", None, None
    post_url = f"https://www.linkedin.com/feed/update/urn:li:activity:{activity_id}"
    return text, post_url, extract_relative_time(html), extract_author_slug(html)


def scrape_profile_pages(client: httpx.Client, slug: str, *, max_ids: int) -> list[str]:
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
            response = client.get(url, headers=BROWSER_HEADERS)
        except httpx.HTTPError:
            continue
        if response.status_code != 200:
            if VERBOSE:
                label = "BLOCKED" if is_linkedin_blocked(response.status_code, response.text) else "HTTP"
                print(f"[scrape] {url} -> {label} {response.status_code}", file=sys.stderr)
            continue
        ids = extract_activity_ids(response.text)
        if VERBOSE:
            print(f"[scrape] {url} -> {len(ids)} ids", file=sys.stderr)
        for activity_id in ids:
            if activity_id in seen:
                continue
            seen.add(activity_id)
            found.append(activity_id)
            if len(found) >= max_ids:
                return found
    return found


def google_cse_search(client: httpx.Client, slug: str, *, max_ids: int) -> list[str]:
    api_key = GOOGLE_CSE_API_KEY or os.getenv("GOOGLE_CSE_API_KEY", "")
    cx = GOOGLE_CSE_CX or os.getenv("GOOGLE_CSE_CX", "")
    if not api_key or not cx:
        return []

    found: list[str] = []
    seen: set[str] = set()
    queries = [
        f"site:linkedin.com/posts/{slug}",
        f"site:linkedin.com/in/{slug}",
    ]
    for query in queries:
        start = 1
        while len(found) < max_ids and start <= 31:
            try:
                response = client.get(
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
                if VERBOSE:
                    print(f"[cse] request failed: {exc}", file=sys.stderr)
                break
            if response.status_code != 200:
                if VERBOSE:
                    print(f"[cse] HTTP {response.status_code}: {response.text[:200]}", file=sys.stderr)
                break
            items = response.json().get("items", [])
            if not items:
                break
            for item in items:
                for activity_id in extract_activity_ids(item.get("link", "")):
                    if activity_id in seen:
                        continue
                    seen.add(activity_id)
                    found.append(activity_id)
                    if len(found) >= max_ids:
                        break
            start += 10
    if VERBOSE:
        print(f"[cse] {len(found)} ids from Google CSE", file=sys.stderr)
    return found[:max_ids]


def search_engines_direct(slug: str, *, max_ids: int) -> list[str]:
    """DDG/Bing без прокси — через заблокированный прокси не работают."""
    queries = [
        f"site:linkedin.com/posts/{slug}",
        f"site:linkedin.com/in/{slug} posts",
    ]
    found: list[str] = []
    seen: set[str] = set()

    def collect(html: str) -> None:
        for activity_id in extract_activity_ids(html):
            if activity_id in seen:
                continue
            seen.add(activity_id)
            found.append(activity_id)

    with httpx.Client(timeout=30.0, follow_redirects=True, trust_env=False) as direct:
        for query in queries:
            if len(found) >= max_ids:
                break
            try:
                response = direct.get(
                    "https://html.duckduckgo.com/html/",
                    params={"q": query},
                    headers=BROWSER_HEADERS,
                )
                if response.status_code == 200:
                    collect(response.text)
            except httpx.HTTPError:
                pass
            try:
                response = direct.get(
                    "https://www.bing.com/search",
                    params={"q": query},
                    headers=BROWSER_HEADERS,
                )
                if response.status_code == 200:
                    collect(response.text)
            except httpx.HTTPError:
                pass

    if VERBOSE:
        print(f"[search] {len(found)} ids from DDG/Bing (direct)", file=sys.stderr)
    return found[:max_ids]


def discover_activity_ids(li_client: httpx.Client, slug: str, *, max_ids: int) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()

    def merge(ids: list[str]) -> None:
        for activity_id in ids:
            if activity_id in seen:
                continue
            seen.add(activity_id)
            found.append(activity_id)

    with httpx.Client(timeout=30.0, trust_env=False) as direct:
        merge(google_cse_search(direct, slug, max_ids=max_ids))

    if len(found) < max_ids:
        merge(scrape_profile_pages(li_client, slug, max_ids=max_ids - len(found)))

    if len(found) < max_ids:
        merge(search_engines_direct(slug, max_ids=max_ids - len(found)))

    return found[:max_ids]


def fetch_posts(li_client: httpx.Client, profile: Profile, since: datetime) -> list[Post]:
    activity_ids = discover_activity_ids(li_client, profile.slug, max_ids=MAX_POSTS * 3)
    if VERBOSE:
        print(f"[total] {len(activity_ids)} activity ids", file=sys.stderr)

    posts: list[Post] = []
    seen: set[str] = set()
    embed_failures = 0

    for activity_id in activity_ids:
        if activity_id in seen:
            continue
        try:
            text, post_url, relative, author_slug = fetch_embed_post(li_client, activity_id)
        except LinkedInBlocked:
            raise
        if not text:
            embed_failures += 1
            continue
        if author_slug and author_slug != profile.slug:
            continue
        if not is_within_since(relative, since):
            continue
        seen.add(activity_id)
        created = datetime.now(tz=UTC)
        delta = parse_relative_age(relative) if relative else None
        if delta:
            created = datetime.now(tz=UTC) - delta
        posts.append(Post(text=text[:2000], url=post_url, date=created, activity_id=activity_id))
        if len(posts) >= MAX_POSTS:
            break

    if not posts and activity_ids and embed_failures >= max(3, len(activity_ids) // 2):
        raise LinkedInBlocked(f"found {len(activity_ids)} ids, embeds failed")

    if not posts and not activity_ids:
        cse_ok = bool(GOOGLE_CSE_API_KEY or os.getenv("GOOGLE_CSE_API_KEY"))
        if not cse_ok:
            print(
                "HINT: LinkedIn scrape blocked (999). Set GOOGLE_CSE_API_KEY + GOOGLE_CSE_CX "
                "or change proxy.",
                file=sys.stderr,
            )
        raise LinkedInBlocked("no activity ids discovered")

    return posts


def _proxy_list() -> list[str]:
    proxies = [p.strip() for p in (PROXY, PROXY_2) if p and p.strip()]
    return proxies or [""]


def main() -> None:
    proxies = _proxy_list()
    if not proxies or not proxies[0]:
        print("ERROR: задайте PROXY в начале файла", file=sys.stderr)
        raise SystemExit(2)

    profile = parse_profile_url(PROFILE_URL)
    since = datetime.now(tz=UTC) - timedelta(days=DAYS)

    if VERBOSE:
        print(f"Profile: {profile.url}", file=sys.stderr)
        print(f"Proxies: {[urlparse(p).hostname if p else 'direct' for p in proxies]}", file=sys.stderr)
        print(f"Since:   {since.date()}", file=sys.stderr)

    posts: list[Post] = []
    last_block: LinkedInBlocked | None = None

    for proxy in proxies:
        if VERBOSE and proxy:
            print(f"--- trying proxy {urlparse(proxy).hostname} ---", file=sys.stderr)
        try:
            with httpx.Client(
                proxy=proxy or None,
                timeout=30.0,
                follow_redirects=True,
                http2=False,
                trust_env=False,
            ) as li_client:
                posts = fetch_posts(li_client, profile, since)
            last_block = None
            break
        except LinkedInBlocked as exc:
            last_block = exc
            if VERBOSE:
                print(f"proxy blocked: {exc}", file=sys.stderr)
            time.sleep(1)

    if last_block:
        print(f"BLOCKED: LinkedIn authwall / HTTP 999 — {last_block}", file=sys.stderr)
        print("Смените прокси, настройте Google CSE, или подождите несколько часов.", file=sys.stderr)
        raise SystemExit(3)

    print(json.dumps(
        {
            "profile": profile.url,
            "count": len(posts),
            "posts": [
                {
                    "text": p.text,
                    "url": p.url,
                    "date": p.date.isoformat(),
                    "activity_id": p.activity_id,
                }
                for p in posts
            ],
        },
        ensure_ascii=False,
        indent=2,
    ))

    if not posts:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
