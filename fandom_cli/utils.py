"""Utilities: rate limiting, retry logic, URL helpers."""

from __future__ import annotations

import time
import urllib.parse
from typing import Any

import httpx

DEFAULT_USER_AGENT = (
    "FandomCLI/1.0 (https://github.com/kjx-talesofai/fandom-cli; research bot)"
)
DEFAULT_RATE_LIMIT_SECONDS = 1.0
MAX_RETRIES = 3


class RateLimiter:
    """Enforces a minimum delay between successive requests."""

    def __init__(self, delay: float = DEFAULT_RATE_LIMIT_SECONDS) -> None:
        self.delay = delay
        self._last_request_time: float | None = None

    def wait(self) -> None:
        """Sleep if needed to respect the rate limit."""
        if self._last_request_time is not None:
            elapsed = time.monotonic() - self._last_request_time
            remaining = self.delay - elapsed
            if remaining > 0:
                time.sleep(remaining)
        self._last_request_time = time.monotonic()


def encode_page_title(title: str) -> str:
    """Encode a wiki page title for use in a URL.

    MediaWiki uses underscores instead of spaces, then URL-encodes special chars.
    """
    return urllib.parse.quote(title.replace(" ", "_"), safe="")


def build_api_url(wiki: str, params: dict[str, Any]) -> str:
    """Build a MediaWiki API URL for a given Fandom wiki."""
    base = f"https://{wiki}.fandom.com/api.php"
    query = urllib.parse.urlencode(params, doseq=True)
    return f"{base}?{query}"


def fetch_json(url: str, rate_limiter: RateLimiter | None = None) -> dict[str, Any]:
    """Fetch JSON from a URL with rate limiting and retry logic.

    Args:
        url: The URL to fetch.
        rate_limiter: Optional RateLimiter instance.

    Returns:
        Parsed JSON response.

    Raises:
        httpx.HTTPStatusError: On non-2xx status after retries.
        httpx.RequestError: On network failure after retries.
    """
    if rate_limiter is None:
        rate_limiter = RateLimiter()

    headers = {"User-Agent": DEFAULT_USER_AGENT}

    for attempt in range(MAX_RETRIES):
        rate_limiter.wait()
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 429 and attempt < MAX_RETRIES - 1:
                # Too many requests — exponential backoff
                backoff = 2 ** attempt
                time.sleep(backoff)
                continue
            raise
        except httpx.RequestError:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            raise

    # Should never reach here, but keep type checker happy
    raise RuntimeError("Unexpected end of retry loop")
