"""HTML parsing: infobox extraction, image filtering, markdown conversion."""

from __future__ import annotations

import re
from typing import Any

import markdownify
from bs4 import BeautifulSoup


def _clean_text(text: str | None) -> str:
    """Strip whitespace and collapse multiple spaces."""
    if text is None:
        return ""
    return re.sub(r"\s+", " ", text.strip())


def extract_infobox(html: str) -> dict[str, str]:
    """Extract key-value pairs from a Fandom portable-infobox.

    Tries data-source attribute first, falls back to label text matching.
    """
    soup = BeautifulSoup(html, "html.parser")
    infobox = soup.find("aside", class_="portable-infobox")
    if not infobox:
        return {}

    result: dict[str, str] = {}

    # Title
    title_tag = infobox.find("h2", class_="pi-title")
    if title_tag:
        result["Box title"] = _clean_text(title_tag.get_text())

    # Data items — some wikis use <section>, others use <div>
    for item in infobox.find_all(["section", "div"], class_="pi-data"):
        key = item.get("data-source", "").strip()
        label_tag = item.find("h3", class_="pi-data-label")
        value_tag = item.find("div", class_="pi-data-value")

        if not key and label_tag:
            key = _clean_text(label_tag.get_text())

        if key and value_tag:
            # Clean up HTML tags and nbsp from value
            value_html = str(value_tag)
            # Remove the wrapper div tags
            value = BeautifulSoup(value_html, "html.parser").get_text(separator=" ")
            value = value.replace("\xa0", " ")
            result[_clean_text(key)] = _clean_text(value)

    # Also look for grouped sections (pi-group) that contain pi-data divs
    for group in infobox.find_all("section", class_="pi-group"):
        for item in group.find_all("div", class_="pi-data"):
            key = item.get("data-source", "").strip()
            label_tag = item.find("h3", class_="pi-data-label")
            value_tag = item.find("div", class_="pi-data-value")

            if not key and label_tag:
                key = _clean_text(label_tag.get_text())

            if key and value_tag:
                value = BeautifulSoup(str(value_tag), "html.parser").get_text(separator=" ")
                value = value.replace("\xa0", " ")
                result[_clean_text(key)] = _clean_text(value)

    return result


def _extract_real_filename(url: str) -> str:
    """Extract the real filename from a Fandom CDN URL.

    Fandom URLs look like:
    https://static.wikia.nocookie.net/.../filename.png/revision/latest
    """
    parts = url.split("/")
    for i, part in enumerate(parts):
        if part == "revision" and i > 0:
            return parts[i - 1]
    return parts[-1]


def _is_placeholder(filename: str) -> bool:
    """Check if an image is a placeholder or icon that should be skipped."""
    lower = filename.lower()
    placeholders = {
        "placeholder",
        "undefined",
        "unknown",
        "blank",
        "null",
        "none",
    }
    return any(p in lower for p in placeholders)


def _is_navbox_icon(filename: str) -> bool:
    """Heuristic: navigation box icons are usually very small generic icons."""
    lower = filename.lower()
    navbox_indicators = {
        "tab",
        "nav",
        "icon_",
        "button",
        "arrow",
        "bullet",
        "checkbox",
    }
    return any(ind in lower for ind in navbox_indicators)


def extract_images(
    html: str,
    entity_name: str | None = None,
    limit: int | None = None,
) -> list[dict[str, str]]:
    """Extract image URLs from page HTML.

    Args:
        html: Raw HTML string.
        entity_name: If provided, filter to images whose filename contains
            the entity name (case-insensitive).
        limit: Max number of images to return.

    Returns:
        List of dicts with keys: url, filename, alt.
    """
    soup = BeautifulSoup(html, "html.parser")
    images: list[dict[str, str]] = []

    for img in soup.find_all("img"):
        src = img.get("src", "")
        if not src or "wikia.nocookie.net" not in src:
            continue

        filename = _extract_real_filename(src)

        # Skip placeholders and navbox icons
        if _is_placeholder(filename) or _is_navbox_icon(filename):
            continue

        # Skip very small images (likely UI elements)
        width = img.get("width", "")
        height = img.get("height", "")
        try:
            if width and int(width) < 32:
                continue
            if height and int(height) < 32:
                continue
        except ValueError:
            pass

        # Entity match filter
        if entity_name:
            entity_lower = entity_name.lower().replace(" ", "_")
            filename_lower = filename.lower()
            # Also check alt text
            alt = img.get("alt", "")
            alt_lower = alt.lower().replace(" ", "_")
            if entity_lower not in filename_lower and entity_lower not in alt_lower:
                continue

        images.append(
            {
                "url": src.split("/revision/")[0],  # Strip revision suffix
                "filename": filename,
                "alt": img.get("alt", ""),
            }
        )

    # Deduplicate by URL
    seen = set()
    deduped = []
    for img in images:
        if img["url"] not in seen:
            seen.add(img["url"])
            deduped.append(img)

    # Sort: prefer idle/down/build images, then inventory, then icon
    def _sort_key(img: dict[str, str]) -> int:
        fn = img["filename"].lower()
        if "idle" in fn or "down" in fn:
            return 0
        if "build" in fn:
            return 1
        if "inventory" in fn:
            return 2
        if "icon" in fn:
            return 3
        return 4

    deduped.sort(key=_sort_key)

    if limit:
        deduped = deduped[:limit]

    return deduped


def html_to_markdown(html: str) -> str:
    """Convert HTML to clean Markdown.

    Removes infobox, navigation boxes, and other non-content elements first.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove elements that don't belong in article text
    for selector in [
        "aside.portable-infobox",
        "nav",  # Navigation boxes
        ".navbox",  # Table-based navboxes
        ".mw-parser-output > table",  # Often layout tables
        ".mw-editsection",  # Edit links
        "script",
        "style",
    ]:
        for elem in soup.select(selector):
            elem.decompose()

    # Convert to markdown
    md = markdownify.markdownify(str(soup), heading_style="ATX", strip=["a"])

    # Clean up common artifacts
    md = re.sub(r"\n{3,}", "\n\n", md)  # Collapse multiple blank lines
    md = re.sub(r"^\s*\|.*\|\s*$", "", md, flags=re.MULTILINE)  # Table artifacts
    md = md.strip()

    return md


def html_to_text(html: str) -> str:
    """Convert HTML to plain text."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove non-content elements
    for selector in [
        "aside.portable-infobox",
        "nav",
        ".navbox",
        ".mw-editsection",
        "script",
        "style",
    ]:
        for elem in soup.select(selector):
            elem.decompose()

    text = soup.get_text(separator="\n")
    # Clean up
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)
