# Fandom CLI

A **Claude Code** / **Cohub** skill for querying Fandom wikis (and other MediaWiki-based wikis) via API.
Fetch pages, extract infoboxes, search, browse categories, and collect images —
without scraping HTML or fighting Cloudflare.

## Quick Start

```bash
git clone https://github.com/kjx-talesofai/claude-skill-fandom-cli.git
cd claude-skill-fandom-cli

# Install dependencies (Python 3.10+)
pip install typer httpx beautifulsoup4 markdownify

# Run directly as a Python module (always works from the skill directory)
python -m fandom_cli page dontstarve Wilson --format markdown
```

## Installation (choose one)

### 🥇 `pip install -e .` — recommended, works everywhere

```bash
cd claude-skill-fandom-cli
pip install -e .
```

After this, the `fandom` command is globally available, and `python -m fandom_cli` runs
from any directory:

```bash
fandom search genshin-impact Zhongli --limit 5
python -m fandom_cli page dontstarve Wilson --format markdown
```

### 🥈 PYTHONPATH — lightweight, no pip install required

```bash
export PYTHONPATH="/path/to/claude-skill-fandom-cli:$PYTHONPATH"
python -m fandom_cli page dontstarve Wilson --format markdown
```

### 🥉 Run from skill directory — zero config, always works

```bash
cd /path/to/claude-skill-fandom-cli
python -m fandom_cli page dontstarve Wilson --format markdown
```

### Externally-managed Python (Debian/Ubuntu)

If you see `error: externally-managed-environment`:

```bash
# Option A: pip with override
pip install -e . --break-system-packages

# Option B: use PYTHONPATH instead (no pip at all)
export PYTHONPATH="$(pwd):$PYTHONPATH"

# Option C: create a venv
python3 -m venv .venv && source .venv/bin/activate && pip install -e .
```

### Cohub-specific: PATH wrapper

Inside a Cohub sandbox, you can create a shorthand `fandom` command:

```bash
cat > /workspace/bin/fandom << 'SCRIPT'
#!/bin/bash
SKILL_DIR="/workspace/.agents/skills/fandom-cli"
cd "$SKILL_DIR" && exec python3 -m fandom_cli.cli "$@"
SCRIPT
chmod +x /workspace/bin/fandom
```

Then `fandom search dontstarve Wilson` works from anywhere in the sandbox.

> **Note:** This wrapper only works in Cohub sandboxes where `/workspace/.agents/skills/`
> is the standard skill directory. For local environments, use `pip install -e .` instead.

## Cloudflare fallback

When a wiki returns a Cloudflare challenge (403), the CLI automatically retries
through a serverless proxy. Set the proxy URL via environment variable:

```bash
export FANDOM_PROXY_URL="https://your-proxy.example.com"
```

See [`reference/DENO_DEPLOY.md`](reference/DENO_DEPLOY.md) for setup instructions
(Deno Deploy registration, deployment, and proxy code).

## Local cache

Successful API responses are cached on disk for 24 hours by default. Repeated
queries for the same URL return instantly without network round-trips.

| Env var | Default | Description |
|---------|---------|-------------|
| `FANDOM_CACHE_DIR` | `~/.cache/fandom-cli` | Cache directory |
| `FANDOM_CACHE_TTL_SECONDS` | `86400` (24h) | Cache TTL; set to `0` to disable |

## Documentation

- [`SKILL.md`](SKILL.md) — Agent execution guide (loaded by Claude / Cohub)
- [`reference/DENO_DEPLOY.md`](reference/DENO_DEPLOY.md) — Deno proxy setup

## Anti-Abuse

This tool relies on Fandom's free API. It enforces **1 request per second**
(cannot be disabled) and serial execution only. Please do not scrape entire
wikis or run multiple instances in parallel.

---

MIT License
