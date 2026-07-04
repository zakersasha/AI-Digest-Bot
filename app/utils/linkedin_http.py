from collections.abc import Awaitable, Callable
from typing import TypeVar

import asyncio
import httpx

from app.utils.http_proxy import create_httpx_client, proxy_host
from app.utils.linkedin_block import LinkedInBlockedError
from app.utils.linkedin_slots import LinkedInSlot, browser_headers, pick_user_agent
from app.utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")

BROWSER_REQUEST_DELAY_SEC = 1.0

_RETRYABLE_STATUS = frozenset({429, 403, 500, 502, 503, 504})


class _PacingAsyncClient:
    """Pauses before each HTTP call during public LinkedIn scraping."""

    def __init__(self, client: httpx.AsyncClient, delay: float = BROWSER_REQUEST_DELAY_SEC) -> None:
        self._client = client
        self._delay = delay

    async def get(self, *args, **kwargs):
        await asyncio.sleep(self._delay)
        return await self._client.get(*args, **kwargs)

    async def post(self, *args, **kwargs):
        await asyncio.sleep(self._delay)
        return await self._client.post(*args, **kwargs)


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _RETRYABLE_STATUS
    return isinstance(exc, (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError))


class LinkedInHttpRouter:
    def __init__(self, slots: list[LinkedInSlot], *, timeout: float = 30.0) -> None:
        if not slots:
            raise ValueError("At least one LinkedIn slot is required")
        self._slots = slots
        self._timeout = timeout
        self._next_start = 0

    @property
    def slots(self) -> list[LinkedInSlot]:
        return self._slots

    def _pick_start(self) -> int:
        idx = self._next_start
        self._next_start = (idx + 1) % len(self._slots)
        return idx

    async def run_browser(
        self,
        coro_fn: Callable[[LinkedInSlot, httpx.AsyncClient, dict[str, str]], Awaitable[T]],
    ) -> T:
        return await self._run(coro_fn, with_headers=True)

    async def run_api(
        self,
        coro_fn: Callable[[LinkedInSlot, httpx.AsyncClient], Awaitable[T]],
    ) -> T:
        async def wrapped(slot: LinkedInSlot, client: httpx.AsyncClient, _headers: dict[str, str]) -> T:
            return await coro_fn(slot, client)

        return await self._run(wrapped, with_headers=False)

    async def _run(
        self,
        coro_fn: Callable[[LinkedInSlot, httpx.AsyncClient, dict[str, str]], Awaitable[T]],
        *,
        with_headers: bool,
    ) -> T:
        last_exc: Exception | None = None
        n = len(self._slots)
        start = self._pick_start()
        used_user_agents: set[str] = set()

        for offset in range(n):
            slot_idx = (start + offset) % n
            slot = self._slots[slot_idx]
            headers: dict[str, str] = {}
            if with_headers:
                user_agent = pick_user_agent(exclude=frozenset(used_user_agents) if used_user_agents else None)
                used_user_agents.add(user_agent)
                headers = browser_headers(user_agent)

            logger.debug(
                "linkedin_request_slot",
                slot=slot.index,
                proxy_host=proxy_host(slot.proxy_url) if slot.proxy_url else None,
                browser=with_headers,
                user_agent=headers.get("User-Agent", "")[:48] if headers else None,
            )

            try:
                async with create_httpx_client(slot.proxy_url, self._timeout) as client:
                    http = _PacingAsyncClient(client) if with_headers else client
                    return await coro_fn(slot, http, headers)
            except LinkedInBlockedError as exc:
                if offset == n - 1:
                    logger.warning(
                        "linkedin_slot_blocked",
                        slot=slot.index,
                        error=str(exc),
                        proxy_host=proxy_host(slot.proxy_url) if slot.proxy_url else None,
                    )
                    raise
                last_exc = exc
                next_slot = self._slots[(slot_idx + 1) % n].index
                logger.warning(
                    "linkedin_slot_blocked_retry",
                    slot=slot.index,
                    next_slot=next_slot,
                    proxy_host=proxy_host(slot.proxy_url) if slot.proxy_url else None,
                )
            except Exception as exc:
                if not _is_retryable(exc) or offset == n - 1:
                    logger.warning(
                        "linkedin_slot_failed",
                        slot=slot.index,
                        error=str(exc),
                        retryable=_is_retryable(exc),
                        proxy_host=proxy_host(slot.proxy_url) if slot.proxy_url else None,
                    )
                    raise
                last_exc = exc
                next_slot = self._slots[(slot_idx + 1) % n].index
                logger.warning(
                    "linkedin_slot_retry",
                    slot=slot.index,
                    next_slot=next_slot,
                    error=str(exc),
                    proxy_host=proxy_host(slot.proxy_url) if slot.proxy_url else None,
                )

        if last_exc:
            raise last_exc
        raise RuntimeError("linkedin slots exhausted")
