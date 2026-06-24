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
slug = "adilsarfrazdev"
query = f"site:linkedin.com/posts/{slug}"

_PATTERNS = (
    re.compile(r"urn:li:activity:(\d+)", re.I),
    re.compile(r"activity[:-](\d{10,})", re.I),
)


def extract_activity_ids(text: str) -> list[str]:
    found: set[str] = set()
    for p in _PATTERNS:
        found.update(p.findall(text))
    for m in re.finditer(r"uddg=([^&\"]+)", text):
        link = unquote(m.group(1))
        for p in _PATTERNS:
            found.update(p.findall(link))
    return sorted(found, reverse=True)


def check(name: str, html: str) -> None:
    ids = extract_activity_ids(html)
    li = html.lower().count("linkedin.com")
    print(name, "linkedin refs", li, "activity ids", ids[:5], "total", len(ids))


with httpx.Client(follow_redirects=True, timeout=30, headers=HEADERS) as c:
    for name, url, kwargs in [
        ("bing", "https://www.bing.com/search", {"params": {"q": query}}),
        ("google", "https://www.google.com/search", {"params": {"q": query, "num": 20}}),
        ("brave", "https://search.brave.com/search", {"params": {"q": query}}),
        ("ddg-get", "https://html.duckduckgo.com/html/", {"params": {"q": query}}),
    ]:
        r = c.get(url, **kwargs)
        check(f"{name} {r.status_code}", r.text)
        if "bing" in name:
            for m in re.finditer(r'href="(https://www\.bing\.com/ck/a\?[^"]+)"', r.text):
                try:
                    r2 = c.get(unescape(m.group(1)))
                    check(" bing-redirect", str(r2.url) + r2.text[:500])
                except Exception as e:
                    print(" redirect err", e)
                break
        if "brave" in name:
            for m in re.finditer(r"https?://[^\s\"<>]*linkedin[^\s\"<>]*", r.text):
                u = unescape(m.group(0))
                if "posts" in u or "activity" in u or "/in/" in u:
                    print("  url:", u[:160])
