"""MediaWiki API wrappers for Fandom wikis."""

from __future__ import annotations

from typing import Any

from fandom_cli.utils import RateLimiter, build_api_url, fetch_json


def get_page_content(
    wiki: str,
    title: str,
    rate_limiter: RateLimiter | None = None,
) -> dict[str, Any]:
    """Fetch raw page content via action=parse.

    Returns the full API response dict. The parsed HTML is under
    response['parse']['text']['*'].
    """
    url = build_api_url(
        wiki,
        {
            "action": "parse",
            "page": title,
            "prop": "text|categories|images|displaytitle",
            "format": "json",
        },
    )
    return fetch_json(url, rate_limiter)


def get_page_metadata(
    wiki: str,
    title: str,
    rate_limiter: RateLimiter | None = None,
) -> dict[str, Any]:
    """Fetch page metadata (pageid, title, url, categories) via action=query."""
    url = build_api_url(
        wiki,
        {
            "action": "query",
            "titles": title,
            "prop": "info|categories",
            "inprop": "url|displaytitle",
            "cllimit": 50,
            "format": "json",
        },
    )
    return fetch_json(url, rate_limiter)


def list_category_members(
    wiki: str,
    category: str,
    limit: int = 50,
    offset: str | None = None,
    rate_limiter: RateLimiter | None = None,
) -> dict[str, Any]:
    """List pages in a category using generator=categorymembers.

    Args:
        wiki: Wiki subdomain (e.g. "dontstarve").
        category: Category name, with or without "Category:" prefix.
        limit: Max results per request (max 500 for bots).
        offset: Continue token from previous request.
    """
    if not category.startswith("Category:"):
        category = f"Category:{category}"

    params: dict[str, Any] = {
        "action": "query",
        "generator": "categorymembers",
        "gcmtitle": category,
        "gcmnamespace": 0,
        "gcmlimit": min(limit, 500),
        "prop": "pageimages|info",
        "piprop": "original",
        "inprop": "url",
        "format": "json",
    }
    if offset:
        params["gcmcontinue"] = offset

    url = build_api_url(wiki, params)
    return fetch_json(url, rate_limiter)


def search_pages(
    wiki: str,
    query: str,
    limit: int = 20,
    offset: int | None = None,
    rate_limiter: RateLimiter | None = None,
) -> dict[str, Any]:
    """Search pages using action=query&list=search."""
    params: dict[str, Any] = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": min(limit, 50),
        "format": "json",
    }
    if offset is not None:
        params["sroffset"] = offset

    url = build_api_url(wiki, params)
    return fetch_json(url, rate_limiter)
