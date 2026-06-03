from urllib.parse import urlparse

import httpx


def proxy_host(proxy_url: str) -> str:
    try:
        return urlparse(proxy_url).hostname or "unknown"
    except Exception:
        return "unknown"


def create_httpx_client(proxy_url: str | None, timeout: float) -> httpx.AsyncClient:
    """HTTP(S) client for OpenAI; http2 disabled — many proxies break it."""
    kwargs: dict = {
        "timeout": timeout,
        "follow_redirects": True,
        "http2": False,
        "trust_env": False,
    }
    if proxy_url:
        kwargs["proxy"] = proxy_url
    return httpx.AsyncClient(**kwargs)
