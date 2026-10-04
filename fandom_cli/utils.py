"""Utilities: rate limiting, retry logic, URL helpers, proxy handling."""

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

PROXY_ENV_VAR = "FANDOM_PROXY_URL"


def get_proxy_url() -> str:
    """Return the configured serverless proxy URL, or "" when unset.

    Read on every call so callers and tests can set FANDOM_PROXY_URL after this
    module has been imported.
    """
    return (os.getenv(PROXY_ENV_VAR) or DEFAULT_FANDOM_PROXY_URL or "").strip()


def _normalize_no_proxy(value: str) -> str:
    """Return a no_proxy list httpx can parse.

    Some agent runtimes export the loopback bypass list with a bracketed IPv6
    literal (``[::1]``). httpx parses every entry as a URL while building its
    client mounts and aborts with ``InvalidURL: Invalid port: ':1]'`` before a
    request is sent. Rewrite ``[::1]`` to its bare form; drop a bracketed entry
    that also carries a port, since the bare form would be ambiguous.
    """
    entries: list[str] = []
    seen: set[str] = set()

    def add(entry: str) -> None:
        if entry and entry not in seen:
            seen.add(entry)
            entries.append(entry)

    for raw in value.split(","):
        entry = raw.strip()
        if not entry:
            continue
        if entry.startswith("["):
            close = entry.find("]")
            if close == -1:
                continue
            host = entry[1:close]
            if not entry[close + 1 :]:
                add(host)
            continue
        if "]" in entry:
            continue
        add(entry)
    return ",".join(entries)


def _socks_dependency_missing() -> bool:
    """True when httpx cannot honour a SOCKS proxy (optional ``socksio`` absent)."""
    try:
        import socksio  # noqa: F401
    except ImportError:
        return True
    return False


def normalize_proxy_env() -> None:
    """Make the proxy environment safe for httpx (idempotent).

    Two shapes abort httpx client construction before any request is sent:

    - a bracketed IPv6 entry in ``no_proxy`` (``[::1]``);
    - a SOCKS ``ALL_PROXY`` while the optional ``socksio`` dependency is absent.

    The first is rewritten, the second dropped so the http(s) proxy or a direct
    connection carries the request instead of the process aborting.
    """
    for name in ("no_proxy", "NO_PROXY"):
        value = os.environ.get(name)
        if value and "[" in value:
            os.environ[name] = _normalize_no_proxy(value)

    if _socks_dependency_missing():
        for name in ("ALL_PROXY", "all_proxy"):
            value = os.environ.get(name, "")
            if value.lower().startswith("socks"):
                os.environ.pop(name, None)


def new_client(**kwargs: Any) -> httpx.Client:
    """Create an httpx client after sanitising the proxy environment."""
    normalize_proxy_env()
    return httpx.Client(**kwargs)


# Sanitise once at import: every client in this module goes through new_client().
normalize_proxy_env()


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
    """Build a MediaWiki API URL.

    Supports three forms:
    - Fandom subdomain:  ``dontstarve`` → https://dontstarve.fandom.com/api.php
    - Non-Fandom host:   ``1d6chan.miraheze.org`` → https://1d6chan.miraheze.org/w/api.php
    - Full URL base:     ``https://custom.wiki/api.php`` → use as-is
    """
    if "://" in wiki:
        base = wiki.rstrip("/")
    elif "." in wiki and "fandom.com" not in wiki:
        base = f"https://{wiki}/w/api.php"
    else:
        base = f"https://{wiki}.fandom.com/api.php"
    query = urllib.parse.urlencode(params, doseq=True)
    return f"{base}?{query}"


def _is_cloudflare_block(response: httpx.Response) -> bool:
    """Check if a 403 response is a Cloudflare block (not a real server 403)."""
    cf_mitigated = response.headers.get("cf-mitigated", "")
    server = response.headers.get("server", "")
    return cf_mitigated == "challenge" or server == "cloudflare"


def _fetch_via_proxy(url: str, proxy_url: str | None = None) -> dict[str, Any]:
    """Fetch API JSON through the Deno serverless proxy.

    For Fandom wikis, uses the wiki-specific proxy format (/?wikiname=...).
    For all other hosts, uses the generic proxy endpoint (/proxy?url=...).
    """
    proxy_url = (proxy_url or get_proxy_url()).rstrip("/")
    if not proxy_url:
        raise RuntimeError(
            "FANDOM_PROXY_URL is not set; proxy fallback cannot be used"
        )

    parsed = urllib.parse.urlparse(url)
    host_parts = parsed.netloc.split(".")

    # Fandom wikis → use /?wikiname=... endpoint (legacy, keeps cache compatibility)
    if len(host_parts) >= 3 and host_parts[-2:] == ["fandom", "com"]:
        query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        query = [("wikiname", host_parts[0]), *query]
        proxied_url = f"{proxy_url}/?{urllib.parse.urlencode(query, doseq=True)}"
    else:
        # Generic proxy for non-Fandom wikis (Miraheze, self-hosted, etc.)
        proxied_url = f"{proxy_url}/proxy?url={urllib.parse.quote(url, safe='')}"

    with new_client(timeout=45.0) as client:
        response = client.get(proxied_url, headers={"User-Agent": DEFAULT_USER_AGENT})
        response.raise_for_status()
        return response.json()


def fetch_json(url: str, rate_limiter: RateLimiter | None = None) -> dict[str, Any]:
    """Fetch JSON from a URL with local cache, rate limiting, and Cloudflare proxy fallback.

    Cached results are stored on disk and honoured while their TTL has not
    expired (default 24 hours). Set ``FANDOM_CACHE_TTL_SECONDS`` to 0 to
    disable caching.

    When FANDOM_PROXY_URL is set the request goes through the Deno proxy first
    and falls back to the wiki directly if the proxy errors. When it is unset the
    CLI talks to the wiki directly, which may hit a Cloudflare challenge (403); a
    detected challenge is retried through the proxy if one is available.
    """
    # --- cache hit --------------------------------------------------------
    cached = _cache_get(url)
    if cached is not None:
        return cached

    # --- network ----------------------------------------------------------
    if rate_limiter is None:
        rate_limiter = RateLimiter()

    headers = {"User-Agent": DEFAULT_USER_AGENT}
    proxy_url = get_proxy_url()
    result: dict[str, Any] | None = None

    # --- proxy first ------------------------------------------------------
    # Many wikis answer Cloudflare challenges on ordinary networks, so the
    # serverless proxy is the dependable route whenever it is configured.
    if proxy_url:
        rate_limiter.wait()
        try:
            result = _fetch_via_proxy(url, proxy_url)
        except Exception as proxy_exc:
            print(
                f"[fandom-cli] Proxy fetch failed ({proxy_exc}); trying the wiki directly",
                file=sys.stderr,
            )

    # --- direct -----------------------------------------------------------
    if result is None:
        for attempt in range(MAX_RETRIES):
            rate_limiter.wait()
            try:
                with new_client(timeout=30.0) as client:
                    response = client.get(url, headers=headers)
                    response.raise_for_status()
                    result = response.json()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code

                if status == 403 and _is_cloudflare_block(exc.response) and proxy_url:
                    try:
                        result = _fetch_via_proxy(url, proxy_url)
                    except Exception as proxy_exc:
                        print(
                            f"[fandom-cli] Fandom proxy failed: {proxy_exc}",
                            file=sys.stderr,
                        )
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
