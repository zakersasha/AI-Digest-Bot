from dataclasses import dataclass

from app.config import Settings, effective_telethon_proxy_url


@dataclass(frozen=True)
class LinkedInSlot:
    index: int
    proxy_url: str | None
    user_agent: str


_LINKEDIN_USER_AGENTS = (
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    ),
)


def _non_empty(value: str | None) -> str | None:
    if value and value.strip():
        return value.strip()
    return None


def browser_headers(slot: LinkedInSlot) -> dict[str, str]:
    return {
        "User-Agent": slot.user_agent,
        "Accept-Language": "en-US,en;q=0.9",
    }


def build_linkedin_slots(settings: Settings) -> list[LinkedInSlot]:
    """Two slots: OPENAI_PROXY_URL + UA #1, OPENAI_PROXY_URL_2 + UA #2."""
    proxies = [
        _non_empty(settings.openai_proxy_url),
        _non_empty(settings.openai_proxy_url_2),
    ]
    linkedin_override = _non_empty(settings.linkedin_proxy_url)
    if linkedin_override:
        proxies[0] = linkedin_override

    fallback_proxy = effective_telethon_proxy_url(settings)

    slots: list[LinkedInSlot] = []
    for i, user_agent in enumerate(_LINKEDIN_USER_AGENTS):
        proxy_url = proxies[i] if i < len(proxies) else None
        if not proxy_url and i == 0 and fallback_proxy:
            proxy_url = fallback_proxy
        elif not proxy_url and slots:
            proxy_url = slots[-1].proxy_url
        slots.append(LinkedInSlot(index=i, proxy_url=proxy_url, user_agent=user_agent))

    return slots
