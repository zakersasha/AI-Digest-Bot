import re
from html import unescape

import httpx

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36"}
BASE = 7473651270688595968
slug = "adilsarfrazdev"


def check(aid: int) -> bool:
    url = f"https://www.linkedin.com/embed/feed/update/urn:li:activity:{aid}"
    r = httpx.get(url, timeout=15, headers=HEADERS)
    if r.status_code != 200 or len(r.text) < 5000:
        return False
    if slug.lower() not in r.text.lower() and f"/in/{slug}" not in r.text.lower():
        return False
    m = re.search(r'property="og:description" content="([^"]+)"', r.text)
    text = unescape(m.group(1))[:80] if m else "?"
    print("HIT", aid, text)
    return True


hits = 0
for delta in range(0, 5000, 100):
    if check(BASE + delta):
        hits += 1
print("done hits", hits)
