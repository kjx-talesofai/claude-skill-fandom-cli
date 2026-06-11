---
name: fandom-cli
description: "Query Fandom wikis via MediaWiki API. Triggers: fandom wiki, wiki page, get wiki content, search wiki, wiki infobox, fandom character. Use when the user asks about game characters, items, lore, or any content from a Fandom-hosted wiki."
---

# Fandom CLI

Query any Fandom wiki via MediaWiki API. Fetches pages, infoboxes, categories, search results, and images.

## Preconditions

1. **fandom-cli installed** — `fandom --version` should succeed
2. **Internet connectivity** — Fandom's `api.php` endpoint must be reachable

If not installed, direct user to README.md for pip install instructions.

## Rate Limiting

**Hard rule: 1 request per second.** The CLI enforces this internally. Do not attempt to bypass or parallelize calls. Fandom's API goodwill depends on responsible use.

## Workflow

### 1. Determine the wiki subdomain

Extract the wiki name from user query:
- "Don't Starve Wilson" → `dontstarve`
- "Harry Potter character" → `harrypotter`
- "Resident Evil Leon" → `residentevil`

When unclear, ask the user: "Which Fandom wiki? (e.g. dontstarve, harrypotter, residentevil)"

### 2. Select command based on user intent

| User intent | Command |
|-------------|---------|
| Read page content | `fandom <wiki> page <title> --format markdown` |
| Get structured data (stats, attributes) | `fandom <wiki> infobox <title>` |
| Discover pages by type | `fandom <wiki> category <name> --limit N` |
| Search for a topic | `fandom <wiki> search <query> --limit N` |
| Get page images | `fandom <wiki> images <title> --entity-match --limit N` |
| Get page metadata | `fandom <wiki> metadata <title>` |

### 3. Handle output

- **`page --format markdown`**: Return raw markdown to user (best for reading)
- **`page --format json`**: Parse JSON, extract `html` or other fields as needed
- **`page --format text`**: Return plain text (most compact)
- **`infobox`**: Returns JSON key-value pairs. Present in structured format
- **`category`**: Returns list of pages with titles and URLs. Present as bulleted list
- **`search`**: Returns ranked results with snippets. Present top matches
- **`images`**: Returns image URLs and filenames. Can render markdown images or list URLs
- **`metadata`**: Returns pageid, URL, categories. Use for verification or linking

### 4. Error handling

| Error | Cause | Action |
|-------|-------|--------|
| "Page not found" | Title doesn't exist | Try search: `fandom <wiki> search <partial title>` |
| "No infobox found" | Page lacks portable-infobox | Fall back to `page --format markdown` |
| Empty category | Category has no direct pages (only subcats) | Try broader category or search |
| API Error [429] | Rate limited | Wait and retry (CLI auto-retries 3x) |
| Empty search | No matches | Broaden query or check wiki subdomain |

## Constraints

- **Always use kebab-case wiki names**: `dontstarve` not `Don't Starve`
- **Quote titles with spaces**: `fandom page dontstarve "Dark Sword"`
- **Page titles are case-sensitive** in the URL but MediaWiki is usually forgiving
- **Special characters**: The CLI auto-encodes `'` and spaces, but quote the shell argument
- **Category prefix optional**: `fandom category dontstarve Characters` works same as `Category:Characters`
- **No concurrent calls**: Rate limiter is global per process; do not spawn parallel fandom processes
- **Image URLs are CDN links**: Validity is not guaranteed long-term; use promptly

## Anti-abuse

This tool relies on Fandom's free API. When using it:
- Do not script bulk downloads of 100+ pages
- Do not run multiple instances simultaneously
- Respect the 1 req/s limit (enforced)
- If a wiki blocks API access, stop and notify user

## Fallback

If `fandom-cli` fails or is unavailable:
1. Check if `pip install fandom-cli` resolves it
2. For simple lookups, suggest visiting the wiki directly: `https://{wiki}.fandom.com/wiki/{title}`
3. For structured data, note that infobox formats vary by wiki and may need manual inspection
