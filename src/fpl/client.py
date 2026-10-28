"""A polite client for the unofficial FPL API: throttled, retried, with a descriptive User-Agent."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import requests
from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# Status codes worth retrying: rate limiting and server-side trouble.
# The FPL API returns 503 while "the game is being updated" around deadlines.
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class RetryableHTTPError(Exception):
    """A response that might succeed if we wait and try again."""


class FPLClient:
    def __init__(
        self,
        base_url: str,
        user_agent: str,
        delay: float = 0.5,
        timeout: float = 30,
        max_attempts: int = 5,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.base_url = base_url if base_url.endswith("/") else base_url + "/"
        self.delay = delay
        self.timeout = timeout
        self.max_attempts = max_attempts
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = user_agent
        self._sleep = sleep
        self._last_call: float | None = None

    def url(self, path: str) -> str:
        """Build the full URL. FPL paths must end with a slash or the request fails."""
        path = path.lstrip("/")
        if not path.endswith("/"):
            path += "/"
        return self.base_url + path

    def get(self, path: str) -> Any:
        """GET an endpoint and return its parsed JSON, retrying with exponential back-off."""
        retrying = Retrying(
            stop=stop_after_attempt(self.max_attempts),
            wait=wait_exponential(multiplier=2, min=2, max=60),
            retry=retry_if_exception_type(
                (requests.ConnectionError, requests.Timeout, RetryableHTTPError)
            ),
            sleep=self._sleep,
            reraise=True,
        )
        return retrying(self._get_once, self.url(path))

    def _get_once(self, url: str) -> Any:
        self._throttle()
        response = self.session.get(url, timeout=self.timeout)
        if response.status_code in RETRYABLE_STATUS:
            raise RetryableHTTPError(f"{response.status_code} from {url}")
        response.raise_for_status()
        return response.json()

    def _throttle(self) -> None:
        """Keep at least `delay` seconds between consecutive requests."""
        if self._last_call is not None:
            wait = self.delay - (time.monotonic() - self._last_call)
            if wait > 0:
                self._sleep(wait)
        self._last_call = time.monotonic()
