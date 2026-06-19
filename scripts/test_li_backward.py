import re
from html import unescape

import httpx

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36"}
BASE = 7473651270688595968
slug = "adilsarfrazdev"


def hit(aid: int) -> bool:
    r = httpx.get(
        f"https://www.linkedin.com/embed/feed/update/urn:li:activity:{aid}",
        timeout=12,
        headers=HEADERS,
    )
    if r.status_code != 200 or len(r.text) < 5000:
        return False
    if f"/in/{slug}" not in r.text.lower():
        return False
    m = re.search(r'property="og:description" content="([^"]+)"', r.text)
    print("HIT", aid, unescape(m.group(1))[:60] if m else "")
    return True


for step in (1, 10, 100, 1000, 10000, 100000):
    found = 0
    for delta in range(1, 2001):
        if hit(BASE - delta * step):
            found += 1
            if found >= 2:
                break
    print("step", step, "found", found)
