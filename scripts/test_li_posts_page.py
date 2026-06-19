import re
from html import unescape

import httpx

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
}

slug = "adilsarfrazdev"
urls = [
    f"https://www.linkedin.com/posts/{slug}_",
    f"https://www.linkedin.com/in/{slug}/detail/recent-activity/",
    f"https://www.linkedin.com/in/{slug}/recent-activity/all/?feedView=all",
]
for url in urls:
    r = httpx.get(url, follow_redirects=True, timeout=25, headers=HEADERS)
    ids = sorted(set(re.findall(r"activity[:-](\d{10,})", r.text)))
    print(url, "->", r.status_code, r.url, "ids", len(ids), ids[:5])
