# Fandom CLI

A **Claude Code** skill for querying any Fandom wiki via MediaWiki API. Fetch pages, extract infoboxes, search, browse categories, and collect images — without scraping HTML or fighting Cloudflare.

## Quick Start

```bash
git clone https://github.com/kjx-talesofai/fandom-cli.git
cd fandom-cli

# Install dependencies (Python 3.10+)
pip install typer httpx beautifulsoup4 markdownify

# Run
python -m fandom_cli.cli page dontstarve Wilson --format markdown
```

## Documentation

- [`SKILL.md`](SKILL.md) — Agent execution guide (loaded by Claude when triggered)

## Anti-Abuse

This tool relies on Fandom's free API. It enforces **1 request per second** (cannot be disabled) and serial execution only. Please do not scrape entire wikis or run multiple instances in parallel.

## Credits

[Jiaxin Kou 寇佳新](https://github.com/kjx-talesofai) · [Neta Art 捏Ta](https://www.neta.art)

---

MIT License © 2026 Jiaxin Kou 寇佳新
