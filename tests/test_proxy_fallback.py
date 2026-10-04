"""Regression tests for proxy handling (offline, no network).

The bug these cover: some agent runtimes (DeepSeek Harness among them) export a
loopback bypass list as ``no_proxy=localhost,127.0.0.1,::1,[::1]``. httpx parses
every ``no_proxy`` entry as a URL during client construction and dies with
``InvalidURL: Invalid port: ':1]'`` — before any request is made.

Run with: ``pytest -q``
"""

import os

import httpx
import pytest

from fandom_cli import utils


@pytest.fixture(autouse=True)
def _fast_and_cacheless(monkeypatch):
    """No rate-limit sleeps and no cache reads/writes inside tests."""

    class _NoWaitLimiter:
        def wait(self) -> None:
            return None

    monkeypatch.setattr(utils, "RateLimiter", _NoWaitLimiter)
    monkeypatch.setattr(utils, "DEFAULT_CACHE_TTL_SECONDS", 0)


def _mock_client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_new_client_survives_bracketed_ipv6_in_no_proxy(monkeypatch):
    hostile = "localhost,127.0.0.1,::1,[::1]"
    monkeypatch.setenv("no_proxy", hostile)
    monkeypatch.setenv("NO_PROXY", hostile)

    client = utils.new_client(timeout=5)  # raised InvalidURL before the fix
    client.close()

    assert "[" not in os.environ["no_proxy"]
    # `::1` and `[::1]` are both exported by these runtimes; dedupe collapses them.
    assert os.environ["no_proxy"] == "localhost,127.0.0.1,::1"


def test_normalize_no_proxy_rewrites_and_drops_entries():
    assert utils._normalize_no_proxy("localhost,[::1]") == "localhost,::1"
    assert (
        utils._normalize_no_proxy("localhost,[::1]:8080,example.com")
        == "localhost,example.com"
    )
    assert utils._normalize_no_proxy(" , ,") == ""


def test_socks_all_proxy_dropped_without_socksio(monkeypatch):
    monkeypatch.setenv("ALL_PROXY", "socks5://127.0.0.1:7897")
    monkeypatch.setenv("all_proxy", "socks5://127.0.0.1:7897")
    monkeypatch.setattr(utils, "_socks_dependency_missing", lambda: True)

    utils.normalize_proxy_env()

    assert "ALL_PROXY" not in os.environ
    assert "all_proxy" not in os.environ


def test_socks_all_proxy_kept_when_socksio_available(monkeypatch):
    monkeypatch.setenv("ALL_PROXY", "socks5://127.0.0.1:7897")
    monkeypatch.setattr(utils, "_socks_dependency_missing", lambda: False)

    utils.normalize_proxy_env()

    assert os.environ["ALL_PROXY"] == "socks5://127.0.0.1:7897"


def test_get_proxy_url_reads_env_at_call_time(monkeypatch):
    monkeypatch.setenv("FANDOM_PROXY_URL", "https://proxy.example")
    assert utils.get_proxy_url() == "https://proxy.example"

    monkeypatch.delenv("FANDOM_PROXY_URL")
    monkeypatch.setattr(utils, "DEFAULT_FANDOM_PROXY_URL", None)
    assert utils.get_proxy_url() == ""


def test_proxy_is_used_first_when_configured(monkeypatch):
    monkeypatch.setenv("FANDOM_PROXY_URL", "https://proxy.example")
    calls = []

    def fake_proxy(url, proxy_url=None):
        calls.append(proxy_url)
        return {"via": "proxy"}

    monkeypatch.setattr(utils, "_fetch_via_proxy", fake_proxy)

    def explode(*args, **kwargs):
        raise AssertionError("direct request should not be made when proxy works")

    monkeypatch.setattr(utils, "new_client", explode)

    result = utils.fetch_json("https://dontstarve.fandom.com/api.php?action=query")
    assert result == {"via": "proxy"}
    assert calls == ["https://proxy.example"]


def test_direct_request_when_no_proxy_configured(monkeypatch):
    monkeypatch.delenv("FANDOM_PROXY_URL", raising=False)
    monkeypatch.setattr(utils, "DEFAULT_FANDOM_PROXY_URL", None)
    monkeypatch.setattr(
        utils, "_fetch_via_proxy", lambda *a, **k: pytest.fail("proxy must not be used")
    )

    def handler(request):
        return httpx.Response(200, json={"via": "direct"})

    monkeypatch.setattr(utils, "new_client", lambda **kwargs: _mock_client(handler))

    result = utils.fetch_json("https://dontstarve.fandom.com/api.php?action=query")
    assert result == {"via": "direct"}


def test_falls_back_to_direct_when_proxy_errors(monkeypatch):
    monkeypatch.setenv("FANDOM_PROXY_URL", "https://proxy.example")

    def broken_proxy(url, proxy_url=None):
        raise RuntimeError("proxy down")

    monkeypatch.setattr(utils, "_fetch_via_proxy", broken_proxy)

    def handler(request):
        return httpx.Response(200, json={"via": "direct"})

    monkeypatch.setattr(utils, "new_client", lambda **kwargs: _mock_client(handler))

    result = utils.fetch_json("https://dontstarve.fandom.com/api.php?action=query")
    assert result == {"via": "direct"}


def test_cloudflare_403_retries_through_proxy(monkeypatch):
    monkeypatch.setenv("FANDOM_PROXY_URL", "https://proxy.example")
    attempts = []

    def flaky_proxy(url, proxy_url=None):
        attempts.append(proxy_url)
        if len(attempts) == 1:
            raise RuntimeError("proxy transient failure")
        return {"via": "proxy"}

    monkeypatch.setattr(utils, "_fetch_via_proxy", flaky_proxy)

    def handler(request):
        return httpx.Response(
            403, headers={"server": "cloudflare"}, json={"error": "challenge"}
        )

    monkeypatch.setattr(utils, "new_client", lambda **kwargs: _mock_client(handler))

    result = utils.fetch_json("https://dontstarve.fandom.com/api.php?action=query")
    assert result == {"via": "proxy"}
    assert len(attempts) == 2
