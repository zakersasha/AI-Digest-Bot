from dataclasses import dataclass

from app.config import Settings, effective_telethon_proxy_url


@dataclass(frozen=True)
class OpenAISlot:
    index: int
    api_key: str
    proxy_url: str | None


def _non_empty(value: str | None) -> str | None:
    if value and value.strip():
        return value.strip()
    return None


def build_openai_slots(settings: Settings) -> list[OpenAISlot]:
    """Build paired OpenAI key + proxy slots (primary and optional secondary)."""
    keys = [
        _non_empty(settings.openai_api_key),
        _non_empty(settings.openai_api_key_2),
    ]
    keys = [k for k in keys if k]

    proxies = [
        _non_empty(settings.openai_proxy_url),
        _non_empty(settings.openai_proxy_url_2),
    ]
    fallback_proxy = effective_telethon_proxy_url(settings)

    slots: list[OpenAISlot] = []
    for i, api_key in enumerate(keys):
        proxy_url = proxies[i] if i < len(proxies) else None
        if not proxy_url and i == 0 and fallback_proxy:
            proxy_url = fallback_proxy
        elif not proxy_url and slots:
            proxy_url = slots[-1].proxy_url
        slots.append(OpenAISlot(index=i, api_key=api_key, proxy_url=proxy_url))

    return slots
