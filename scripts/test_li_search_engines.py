import re
import httpx

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36"}
slug = "adilsarfrazdev"
q = f"site:linkedin.com/posts/{slug}"
pat = re.compile(r"activity[:-](\d{10,})", re.I)

for name, url, kw in [
    ("yandex", "https://yandex.com/search/", {"params": {"text": q}}),
    ("mojeek", "https://www.mojeek.com/search", {"params": {"q": q}}),
    ("ecosia", "https://www.ecosia.org/search", {"params": {"q": q}}),
    ("ddg-lite", "https://lite.duckduckgo.com/lite/", {"params": {"q": q}}),
]:
    r = httpx.get(url, headers=HEADERS, timeout=30, **kw)
    ids = pat.findall(r.text)
    print(name, r.status_code, "linkedin", r.text.lower().count("linkedin.com"), "ids", ids[:5])
