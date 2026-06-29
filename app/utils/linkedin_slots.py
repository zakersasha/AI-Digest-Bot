import random
from dataclasses import dataclass

from app.config import Settings, effective_telethon_proxy_url

# Realistic desktop browsers — rotated per LinkedIn scrape session.
_BROWSER_USER_AGENTS: tuple[str, ...] = (
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
        "Gecko/20100101 Firefox/125.0"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) "
        "Gecko/20100101 Firefox/125.0"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15"
    ),
)


@dataclass(frozen=True)
class LinkedInSlot:
    index: int
    proxy_url: str | None


def user_agent_pool_size() -> int:
    return len(_BROWSER_USER_AGENTS)


def pick_user_agent(*, exclude: frozenset[str] | None = None) -> str:
    pool = [ua for ua in _BROWSER_USER_AGENTS if exclude is None or ua not in exclude]
    if not pool:
        pool = list(_BROWSER_USER_AGENTS)
    return random.choice(pool)


def browser_headers(user_agent: str) -> dict[str, str]:
    return {
        "User-Agent": user_agent,
        "Accept-Language": "en-US,en;q=0.9",
    }


def _non_empty(value: str | None) -> str | None:
    if value and value.strip():
        return value.strip()
    return None


def build_linkedin_slots(settings: Settings) -> list[LinkedInSlot]:
    """Two proxy slots: OPENAI_PROXY_URL and OPENAI_PROXY_URL_2."""
    proxies = [
        _non_empty(settings.openai_proxy_url),
        _non_empty(settings.openai_proxy_url_2),
    ]
    linkedin_override = _non_empty(settings.linkedin_proxy_url)
    if linkedin_override:
        proxies[0] = linkedin_override

    fallback_proxy = effective_telethon_proxy_url(settings)

    slots: list[LinkedInSlot] = []
    for i in range(2):
        proxy_url = proxies[i] if i < len(proxies) else None
        if not proxy_url and i == 0 and fallback_proxy:
            proxy_url = fallback_proxy
        elif not proxy_url and slots:
            proxy_url = slots[-1].proxy_url
        slots.append(LinkedInSlot(index=i, proxy_url=proxy_url))

    return slots
