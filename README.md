# Fandom CLI

Query any Fandom wiki via MediaWiki API — an agent-friendly command-line tool.

Fandom hosts thousands of game, anime, and pop-culture wikis. This CLI wraps the MediaWiki `api.php` endpoint to fetch pages, extract infoboxes, search, list categories, and collect images — all without scraping HTML or fighting Cloudflare.

## Installation

```bash
pip install fandom-cli
```

Or install from source:

```bash
git clone https://github.com/kjx-talesofai/fandom-cli.git
cd fandom-cli
pip install -e .
```

Requires Python 3.10+.

## Quick Start

```bash
# Fetch a page as Markdown
fandom page dontstarve Wilson --format markdown

# Extract structured infobox data
fandom infobox dontstarve Wilson

# List pages in a category
fandom category dontstarve Characters --limit 20

# Search pages
fandom search dontstarve "shadow weapon" --limit 10

# Get page images (filtered to entity-related)
fandom images dontstarve Wilson --entity-match --limit 5

# Get page metadata
fandom metadata dontstarve Wilson
```

## Commands

| Command | Description | Example |
|---------|-------------|---------|
| `page` | Fetch page content | `fandom page <wiki> <title> --format markdown\|json\|text` |
| `infobox` | Extract structured infobox | `fandom infobox <wiki> <title>` |
| `category` | List pages in a category | `fandom category <wiki> <name> --limit N --offset TOKEN` |
| `search` | Search pages by query | `fandom search <wiki> <query> --limit N` |
| `images` | Extract images from a page | `fandom images <wiki> <title> --entity-match --limit N` |
| `metadata` | Get page metadata | `fandom metadata <wiki> <title>` |

## Output Formats

**Markdown** (default for `page`) — clean article text, suitable for reading or feeding to LLMs.

**JSON** — structured data with HTML, categories, and images included. Use `--format json`.

**Text** — plain text extraction, most compact. Use `--format text`.

## How It Works

Fandom wikis run on MediaWiki, which provides a native `api.php` endpoint returning JSON. Unlike Fandom's HTML pages (protected by Cloudflare challenges), the API endpoint is designed for machine access and typically remains open.

This CLI:
1. Calls `https://{wiki}.fandom.com/api.php` with standard MediaWiki actions
2. Parses the returned HTML using BeautifulSoup
3. Extracts infoboxes, images, and article text
4. Converts to Markdown or JSON for easy consumption

## Rate Limiting & Anti-Abuse

**Fandom provides free API access. Please use it responsibly.**

This CLI enforces the following limits to protect Fandom's infrastructure:

- **1 request per second** — hard-coded, cannot be disabled
- **Serial execution only** — no concurrent requests
- **Automatic retry with backoff** on HTTP 429 (rate limit) errors

**Please do NOT:**
- Use this tool to scrape entire wikis (1000+ pages)
- Run multiple CLI instances in parallel
- Distribute it in abuse-prone environments
- Hammer the same wiki repeatedly

Fandom's goodwill enables this tool to exist. If abused, they may restrict API access for everyone.

## Limitations

- **Fandom-only**: Works on Fandom-hosted wikis. Gray-zone wikis (e.g. Chinese Huiji) with WAF-blocked APIs are not supported.
- **Infobox variance**: Different wikis use different infobox structures. The parser handles the common `portable-infobox` format; custom templates may need adaptation.
- **Image URL longevity**: Fandom CDN URLs are not guaranteed to persist indefinitely.
- **API dependency**: If Fandom ever restricts `api.php`, this tool will stop working.

## Credits

[Jiaxin Kou 寇佳新](https://github.com/kjx-talesofai) · [Neta Art 捏Ta](https://www.neta.art)

Thanks to [OpenCode](https://opencode.ai) for the excellent CLI agent.

---

MIT License © 2026 Jiaxin Kou 寇佳新
