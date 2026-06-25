---
name: fandom-cli
description: "Query Fandom wikis via MediaWiki API. Triggers: fandom, wiki page, infobox, search."
---

# Fandom CLI

Query any Fandom wiki via MediaWiki API. Fetches pages, infoboxes, categories, search results, and images.

## Preconditions

1. **fandom CLI available** — try commands in this order:
   ```bash
   fandom --help                          # installed via pip install -e .
   python -m fandom_cli --help            # module in PYTHONPATH or pip-installed
   python -m fandom_cli.cli --help        # fallback: cd to skill directory first
   ```
   If none of the above work, set up the module:
   ```bash
   # Recommended: pip install (works on any machine)
   cd /path/to/fandom-cli && pip install -e . --break-system-packages

   # Lightweight: add to PYTHONPATH (no pip needed)
   export PYTHONPATH="/path/to/fandom-cli:$PYTHONPATH"

   # Cohub sandbox only: create a PATH wrapper
   cat > /workspace/bin/fandom << 'SCRIPT'
   #!/bin/bash
   cd /workspace/.agents/skills/fandom-cli && exec python3 -m fandom_cli.cli "$@"
   SCRIPT
   chmod +x /workspace/bin/fandom
   ```
   If dependencies are missing, see README.md.
2. **Internet connectivity** — Fandom's `api.php` endpoint must be reachable
3. **Cloudflare fallback configured** — set `FANDOM_PROXY_URL` if you expect blocked requests

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
| Read page content | `fandom page <wiki> <title> --format markdown` |
| Get structured data (stats, attributes) | `fandom infobox <wiki> <title>` |
| Discover pages by type | `fandom category <wiki> <name> --limit N` |
| Search for a topic | `fandom search <wiki> <query> --limit N` |
| Get page images | `fandom images <wiki> <title> --entity-match --limit N` |
| Get page metadata | `fandom metadata <wiki> <title>` |

> **Note:** If the `fandom` command is unavailable, try `python -m fandom_cli` first.
> If that also fails, `cd` to the skill directory and run `python -m fandom_cli.cli`.
> See README.md for full installation options.

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
| "Page not found" | Title doesn't exist | Try search: `fandom search <wiki> <partial title>` |
| "No infobox found" | Page lacks portable-infobox | Fall back to `fandom page <wiki> <title> --format markdown` |
| Empty category | Category has no direct pages (only subcats) | Try broader category or search |
| API Error [429] | Rate limited | Wait and retry (CLI auto-retries 3x) |
| Empty search | No matches | Broaden query or check wiki subdomain |

## Constraints

- **Invocation**: Try `fandom` first. Fallback cascade: `python -m fandom_cli` → `python -m fandom_cli.cli` (from skill dir).
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

## Local cache

Successful API responses are cached on disk for 24 hours by default. Set `FANDOM_CACHE_TTL_SECONDS=0` to disable. See README.md for configuration details.

## Installation Troubleshooting

### "ModuleNotFoundError: No module named 'fandom_cli'"

The module isn't in Python's search path. Fix:
```bash
# Option A: pip install (works on any machine)
cd /path/to/fandom-cli && pip install -e . --break-system-packages

# Option B: add to PYTHONPATH (no pip needed)
export PYTHONPATH="/path/to/fandom-cli:$PYTHONPATH"

# Option C: run from the skill directory (zero config)
cd /path/to/fandom-cli && python -m fandom_cli.cli ...
```

### "externally-managed-environment"

Use `--break-system-packages` with pip, or use PYTHONPATH (Option B above).

## Cloudflare Fallback

If `fandom-cli` hits Cloudflare protection, it will first try the serverless proxy configured by `FANDOM_PROXY_URL`.

See `reference/DENO_DEPLOY.md` for Deno registration, deployment steps, and proxy code.

If `FANDOM_PROXY_URL` is missing or unavailable:
1. Check whether the proxy URL is configured correctly
2. Try again later if the request is rate limited or temporarily blocked
3. For simple lookups, suggest visiting the wiki directly: `https://{wiki}.fandom.com/wiki/{title}`
4. For structured data, note that infobox formats vary by wiki and may need manual inspection
