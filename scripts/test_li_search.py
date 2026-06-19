import re
from html import unescape
from urllib.parse import unquote

import httpx

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
}


def activity_ids(html: str) -> list[str]:
    found: set[str] = set()
    for pat in (
        r"urn:li:activity:(\d+)",
        r"activity[:-](\d{10,})",
        r"/feed/update/urn:li:activity:(\d+)",
    ):
        found.update(re.findall(pat, html))
    return sorted(found)


def search_ddg(query: str) -> list[str]:
    url = "https://html.duckduckgo.com/html/"
    r = httpx.get(url, params={"q": query}, headers=HEADERS, timeout=25)
    print(" ddg status", r.status_code, "len", len(r.text))
    return activity_ids(r.text)


def search_bing(query: str) -> list[str]:
    url = "https://www.bing.com/search"
    r = httpx.get(url, params={"q": query}, headers=HEADERS, timeout=25)
    return activity_ids(r.text)


slug = "adilsarfrazdev"
for engine, fn in [("ddg", search_ddg), ("bing", search_bing)]:
    for q in [
        f"site:linkedin.com/posts/{slug}",
        f"site:linkedin.com/in/{slug}/recent-activity",
        f"site:linkedin.com/feed/update {slug}",
    ]:
        ids = fn(q)
        print(engine, q[:50], "->", len(ids), ids[:5], "latest747365", "7473651270688595968" in ids)
