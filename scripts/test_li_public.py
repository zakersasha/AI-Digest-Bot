"""Quick probe for LinkedIn public post discovery (dev only)."""
import re
from html import unescape

import httpx

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch(url: str) -> tuple[int, str]:
    r = httpx.get(url, follow_redirects=True, timeout=25, headers=HEADERS)
    return r.status_code, r.text


def activity_ids(html: str) -> list[str]:
    patterns = [
        r"urn:li:activity:(\d+)",
        r"activity[:-](\d{10,})",
        r"/feed/update/urn:li:activity:(\d+)",
        r"/posts/[^\"']+activity-(\d+)-",
    ]
    found: set[str] = set()
    for pat in patterns:
        found.update(re.findall(pat, html))
    return sorted(found)


def parse_embed(activity_id: str) -> None:
    url = f"https://www.linkedin.com/embed/feed/update/urn:li:activity:{activity_id}"
    status, html = fetch(url)
    print("embed", activity_id, "status", status, "len", len(html))
    for meta in re.findall(r'<meta[^>]+property="og:description"[^>]+>', html):
        print(" og:", meta[:250])
    for meta in re.findall(r'<meta[^>]+property="og:[^"]+"[^>]+>', html):
        if "time" in meta.lower() or "date" in meta.lower() or "published" in meta.lower():
            print(" time meta:", meta[:250])
    for meta in re.findall(r'<meta[^>]+name="description"[^>]+>', html):
        print(" desc:", meta[:250])
    for pat in [r'"publishedAt":(\d+)', r'"createdAt":(\d+)', r'data-published="([^"]+)"', r'time datetime="([^"]+)"']:
        m = re.search(pat, html)
        if m:
            print(" ts pat", pat, m.group(1))
    m = re.search(r'"commentary":\{"text":"(.*?)"', html)
    if m:
        print(" commentary:", unescape(m.group(1))[:300])


def main() -> None:
    slug = "adilsarfrazdev"
    urls = [
        f"https://www.linkedin.com/in/{slug}/recent-activity/all/",
        f"https://www.linkedin.com/in/{slug}/recent-activity/shares/",
        f"https://www.linkedin.com/mwlite/in/{slug}/recent-activity/all",
        f"https://www.linkedin.com/in/{slug}/",
        "https://www.linkedin.com/embed/feed/update/urn:li:activity:7473651270688595968",
    ]
    for url in urls:
        status, html = fetch(url)
        ids = activity_ids(html)
        print("===", url)
        print("status", status, "len", len(html), "activities", ids[:5])

    parse_embed("7473651270688595968")

    q = f"site:linkedin.com/posts/{slug}"
    ddg = f"https://html.duckduckgo.com/html/?q={httpx.QueryParams({'q': q})}"
    status, html = fetch(ddg)
    print("=== duckduckgo", status, "activities", activity_ids(html)[:10])
    for m in re.finditer(r"uddg=([^&]+)", html):
        link = unescape(m.group(1))
        if "linkedin.com" in link:
            print(" link:", link[:120])

    mwlite = f"https://www.linkedin.com/mwlite/in/{slug}/recent-activity/all"
    status, html = fetch(mwlite)
    print("=== mwlite", status, "len", len(html))
    for pat in ["urn:li:activity", "urn%3Ali%3Aactivity", "activity-", "feed/update", "7473651270688595968"]:
        print(" count", pat, html.count(pat))
    idx = html.find("urn")
    if idx >= 0:
        print(" first urn", html[idx : idx + 100])

    for vanity_url in (
        "https://www.linkedin.com/embed/public-profile-card?vanityName=adilsarfrazdev",
        "https://www.linkedin.com/embed/profile/public-profile-card?vanityName=adilsarfrazdev",
    ):
        status, html = fetch(vanity_url)
        persons = re.findall(r"urn:li:person:[^\s\"&]+", html)
        print("=== profile embed", vanity_url.split("?")[0].split("/")[-1], status, persons[:3])


if __name__ == "__main__":
    main()
