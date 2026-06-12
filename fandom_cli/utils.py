"""Utilities: rate limiting, retry logic, URL helpers."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Any

import httpx

DEFAULT_USER_AGENT = (
    "FandomCLI/1.0 (https://github.com/kjx-talesofai/fandom-cli; research bot)"
)
DEFAULT_RATE_LIMIT_SECONDS = 1.0
MAX_RETRIES = 3
DEFAULT_FANDOM_PROXY_URL = os.getenv("FANDOM_PROXY_URL")
DEFAULT_CACHE_DIR = os.getenv(
    "FANDOM_CACHE_DIR",
    os.path.join(Path.home(), ".cache", "fandom-cli"),
)
DEFAULT_CACHE_TTL_SECONDS = int(os.getenv("FANDOM_CACHE_TTL_SECONDS", "86400"))


def _cache_key(url: str) -> str:
    """Derive a stable cache key from a URL."""
    return hashlib.sha256(url.encode()).hexdigest()


def _cache_path(url: str) -> Path:
    """Return the cache file path for a URL."""
    return Path(DEFAULT_CACHE_DIR) / f"{_cache_key(url)}.json"


def _cache_get(url: str) -> dict[str, Any] | None:
    """Return cached JSON payload if it exists and is still fresh."""
    if DEFAULT_CACHE_TTL_SECONDS <= 0:
        return None

    path = _cache_path(url)
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    cached_at = data.get("_cached_at")
    if cached_at is None or (time.time() - cached_at) > DEFAULT_CACHE_TTL_SECONDS:
        return None

    return data.get("_payload")


def _cache_put(url: str, payload: dict[str, Any]) -> None:
    """Write a JSON payload to the local cache."""
    if DEFAULT_CACHE_TTL_SECONDS <= 0:
        return

    Path(DEFAULT_CACHE_DIR).mkdir(parents=True, exist_ok=True)
    entry = {
        "_cached_at": time.time(),
        "_payload": payload,
    }
    path = _cache_path(url)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")
        tmp.rename(path)
    except Exception:
        pass





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


def _is_cloudflare_block(response: httpx.Response) -> bool:
    """Check if a 403 response is a Cloudflare block (not a real server 403)."""
    cf_mitigated = response.headers.get("cf-mitigated", "")
    server = response.headers.get("server", "")
    return cf_mitigated == "challenge" or server == "cloudflare"


def _fetch_via_proxy(url: str) -> dict[str, Any]:
    """Fetch Fandom API JSON through the Deno serverless proxy."""
    parsed = urllib.parse.urlparse(url)
    host_parts = parsed.netloc.split(".")
    if len(host_parts) < 3 or host_parts[-2:] != ["fandom", "com"]:
        raise RuntimeError(f"Unsupported Fandom host: {parsed.netloc}")

    proxy_url = DEFAULT_FANDOM_PROXY_URL
    if not proxy_url:
        raise RuntimeError(
            "FANDOM_PROXY_URL is not set; Cloudflare fallback cannot be used"
        )

    proxy_url = proxy_url.rstrip("/")
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    query = [("wikiname", host_parts[0]), *query]
    proxied_url = f"{proxy_url}/?{urllib.parse.urlencode(query, doseq=True)}"

    with httpx.Client(timeout=45.0) as client:
        response = client.get(proxied_url, headers={"User-Agent": DEFAULT_USER_AGENT})
        response.raise_for_status()
        return response.json()


def fetch_json(url: str, rate_limiter: RateLimiter | None = None) -> dict[str, Any]:
    """Fetch JSON from a URL with local cache, rate limiting, and Cloudflare proxy fallback.

    Cached results are stored on disk and honoured while their TTL has not
    expired (default 24 hours). Set ``FANDOM_CACHE_TTL_SECONDS`` to 0 to
    disable caching.

    The CLI tries Fandom directly first. If Cloudflare returns a managed
    challenge (403), it retries through the Deno proxy configured by
    FANDOM_PROXY_URL.

    If FANDOM_PROXY_URL is not set, the fallback raises a clear error.
    """
    # --- cache hit --------------------------------------------------------
    cached = _cache_get(url)
    if cached is not None:
        return cached

    # --- network ----------------------------------------------------------
    if rate_limiter is None:
        rate_limiter = RateLimiter()

    headers = {"User-Agent": DEFAULT_USER_AGENT}
    result: dict[str, Any] | None = None

    for attempt in range(MAX_RETRIES):
        rate_limiter.wait()
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                result = response.json()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code

            if status == 403 and _is_cloudflare_block(exc.response):
                try:
                    result = _fetch_via_proxy(url)
                except Exception as proxy_exc:
                    print(f"[fandom-cli] Fandom proxy failed: {proxy_exc}", file=sys.stderr)
                if result is not None:
                    break

            if status == 429 and attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            raise
        except httpx.RequestError:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            raise

        break

    if result is None:
        raise RuntimeError("Unexpected end of retry loop")

    # --- cache store ------------------------------------------------------
    _cache_put(url, result)
    return result
