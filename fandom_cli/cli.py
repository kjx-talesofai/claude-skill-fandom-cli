"""Fandom CLI — typer-based command-line interface."""

from __future__ import annotations

import json
import sys
from typing import Any

import typer
from typing_extensions import Annotated

from fandom_cli import __version__
from fandom_cli.api import get_page_content, get_page_metadata, list_category_members, search_pages
from fandom_cli.parser import extract_images, extract_infobox, html_to_markdown, html_to_text
from fandom_cli.utils import RateLimiter

app = typer.Typer(
    name="fandom",
    help="Query Fandom and other MediaWiki wikis via API.",
    no_args_is_help=True,
)

# Global rate limiter — shared across all commands in a single invocation
# This ensures even if a user runs multiple subcommands, we still respect the limit
_rate_limiter = RateLimiter()


def _handle_api_error(data: dict[str, Any]) -> None:
    """Check for MediaWiki API errors and raise if found."""
    if "error" in data:
        code = data["error"].get("code", "unknown")
        info = data["error"].get("info", "Unknown error")
        typer.echo(f"API Error [{code}]: {info}", err=True)
        raise typer.Exit(1)


@app.command()
def page(
    wiki: Annotated[str, typer.Argument(help="Wiki: Fandom subdomain (e.g. 'dontstarve'), non-Fandom host (e.g. '1d6chan.miraheze.org'), or full API base URL")],
    title: Annotated[str, typer.Argument(help="Page title, e.g. 'Wilson'")],
    format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Output format: markdown, json, or text",
        ),
    ] = "markdown",
) -> None:
    """Fetch a wiki page's content."""
    if format not in ("markdown", "json", "text"):
        typer.echo(f"Invalid format: {format}. Use: markdown, json, text", err=True)
        raise typer.Exit(1)

    data = get_page_content(wiki, title, _rate_limiter)
    _handle_api_error(data)

    parsed = data.get("parse", {})
    html = parsed.get("text", {}).get("*", "")

    if format == "json":
        # Return structured data with HTML included
        output = {
            "title": parsed.get("title", title),
            "pageid": parsed.get("pageid"),
            "displaytitle": parsed.get("displaytitle"),
            "categories": [c.get("*") for c in parsed.get("categories", [])],
            "images": parsed.get("images", []),
            "html": html,
        }
        typer.echo(json.dumps(output, indent=2, ensure_ascii=False))
    elif format == "markdown":
        md = html_to_markdown(html)
        typer.echo(md)
    else:  # text
        text = html_to_text(html)
        typer.echo(text)


@app.command()
def infobox(
    wiki: Annotated[str, typer.Argument(help="Wiki: Fandom subdomain (e.g. 'dontstarve'), non-Fandom host (e.g. '1d6chan.miraheze.org'), or full API base URL")],
    title: Annotated[str, typer.Argument(help="Page title, e.g. 'Wilson'")],
) -> None:
    """Extract structured infobox data from a page."""
    data = get_page_content(wiki, title, _rate_limiter)
    _handle_api_error(data)

    html = data.get("parse", {}).get("text", {}).get("*", "")
    box = extract_infobox(html)

    if not box:
        typer.echo(f"No infobox found on page '{title}'", err=True)
        raise typer.Exit(1)

    typer.echo(json.dumps(box, indent=2, ensure_ascii=False))


@app.command()
def category(
    wiki: Annotated[str, typer.Argument(help="Wiki: Fandom subdomain (e.g. 'dontstarve'), non-Fandom host (e.g. '1d6chan.miraheze.org'), or full API base URL")],
    name: Annotated[str, typer.Argument(help="Category name, e.g. 'Characters'")],
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Max results (max 500)"),
    ] = 50,
    offset: Annotated[
        str | None,
        typer.Option("--offset", "-o", help="Continue token from previous request"),
    ] = None,
) -> None:
    """List pages in a category."""
    data = list_category_members(wiki, name, limit, offset, _rate_limiter)
    _handle_api_error(data)

    pages = data.get("query", {}).get("pages", {})
    continue_token = data.get("continue", {}).get("gcmcontinue")

    results = []
    for page_id, page_info in pages.items():
        result: dict[str, Any] = {
            "pageid": page_id,
            "title": page_info.get("title"),
            "url": page_info.get("fullurl"),
        }
        # Page image if available
        thumbnail = page_info.get("thumbnail", {})
        if thumbnail:
            result["image"] = thumbnail.get("original")
        results.append(result)

    output = {
        "category": name if name.startswith("Category:") else f"Category:{name}",
        "count": len(results),
        "pages": results,
    }
    if continue_token:
        output["continue"] = continue_token

    typer.echo(json.dumps(output, indent=2, ensure_ascii=False))


@app.command()
def search(
    wiki: Annotated[str, typer.Argument(help="Wiki: Fandom subdomain (e.g. 'dontstarve'), non-Fandom host (e.g. '1d6chan.miraheze.org'), or full API base URL")],
    query: Annotated[str, typer.Argument(help="Search query")],
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Max results (max 50)"),
    ] = 20,
) -> None:
    """Search pages in a wiki."""
    data = search_pages(wiki, query, limit, rate_limiter=_rate_limiter)
    _handle_api_error(data)

    search_results = data.get("query", {}).get("search", [])
    continue_info = data.get("continue", {})

    results = []
    for item in search_results:
        results.append(
            {
                "pageid": item.get("pageid"),
                "title": item.get("title"),
                "snippet": item.get("snippet", "").replace("<span class=\"searchmatch\">", "**").replace("</span>", "**"),
                "wordcount": item.get("wordcount"),
                "timestamp": item.get("timestamp"),
            }
        )

    output = {
        "query": query,
        "count": len(results),
        "results": results,
    }
    if "sroffset" in continue_info:
        output["continue_offset"] = continue_info["sroffset"]

    typer.echo(json.dumps(output, indent=2, ensure_ascii=False))


@app.command()
def images(
    wiki: Annotated[str, typer.Argument(help="Wiki: Fandom subdomain (e.g. 'dontstarve'), non-Fandom host (e.g. '1d6chan.miraheze.org'), or full API base URL")],
    title: Annotated[str, typer.Argument(help="Page title, e.g. 'Wilson'")],
    entity_match: Annotated[
        bool,
        typer.Option(
            "--entity-match",
            "-e",
            help="Filter to images related to the entity name",
        ),
    ] = False,
    limit: Annotated[
        int | None,
        typer.Option("--limit", "-l", help="Max images to return"),
    ] = None,
) -> None:
    """Extract images from a page."""
    data = get_page_content(wiki, title, _rate_limiter)
    _handle_api_error(data)

    html = data.get("parse", {}).get("text", {}).get("*", "")
    entity_name = title if entity_match else None
    images_list = extract_images(html, entity_name=entity_name, limit=limit)

    output = {
        "title": title,
        "count": len(images_list),
        "images": images_list,
    }
    typer.echo(json.dumps(output, indent=2, ensure_ascii=False))


@app.command()
def metadata(
    wiki: Annotated[str, typer.Argument(help="Wiki: Fandom subdomain (e.g. 'dontstarve'), non-Fandom host (e.g. '1d6chan.miraheze.org'), or full API base URL")],
    title: Annotated[str, typer.Argument(help="Page title, e.g. 'Wilson'")],
) -> None:
    """Get page metadata (pageid, URL, categories)."""
    data = get_page_metadata(wiki, title, _rate_limiter)
    _handle_api_error(data)

    pages = data.get("query", {}).get("pages", {})
    if not pages:
        typer.echo(f"Page '{title}' not found", err=True)
        raise typer.Exit(1)

    page_info = next(iter(pages.values()))
    categories = [
        {"title": c.get("title"), "sortkey": c.get("sortkey")}
        for c in page_info.get("categories", [])
    ]

    output = {
        "pageid": page_info.get("pageid"),
        "title": page_info.get("title"),
        "canonicalurl": page_info.get("canonicalurl"),
        "fullurl": page_info.get("fullurl"),
        "touched": page_info.get("touched"),
        "length": page_info.get("length"),
        "categories": categories,
    }
    typer.echo(json.dumps(output, indent=2, ensure_ascii=False))


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
