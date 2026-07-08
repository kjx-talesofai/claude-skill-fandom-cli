# Fandom CLI

A **Claude Code** / **Cohub** skill for querying Fandom wikis (and other MediaWiki-based wikis) via API.
Fetch pages, extract infoboxes, search, browse categories, and collect images —
without scraping HTML or fighting Cloudflare.

## Quick Start

```bash
git clone https://github.com/kjx-talesofai/claude-skill-fandom-cli.git
cd claude-skill-fandom-cli

# Install into a sandbox-local venv outside the workspace (Python 3.10+)
python3 -m venv ~/venvs/fandom-cli
PIP_USER=false ~/venvs/fandom-cli/bin/pip install -e .
mkdir -p ~/.local/bin
ln -sf ~/venvs/fandom-cli/bin/fandom ~/.local/bin/fandom
export PATH="$HOME/.local/bin:$PATH"

fandom page dontstarve Wilson --format markdown
```

## Installation (choose one)

### 🥇 Sandbox-local venv — recommended for Cohub

```bash
cd claude-skill-fandom-cli
python3 -m venv ~/venvs/fandom-cli
PIP_USER=false ~/venvs/fandom-cli/bin/pip install --upgrade pip
PIP_USER=false ~/venvs/fandom-cli/bin/pip install -e .
mkdir -p ~/.local/bin
ln -sf ~/venvs/fandom-cli/bin/fandom ~/.local/bin/fandom
export PATH="$HOME/.local/bin:$PATH"
```

After this, the `fandom` command is available through `~/.local/bin/fandom`, and `python -m fandom_cli` runs from the venv:

```bash
fandom search genshin-impact Zhongli --limit 5
~/venvs/fandom-cli/bin/python -m fandom_cli page dontstarve Wilson --format markdown
```

### 🥈 PYTHONPATH — lightweight, no pip install required

```bash
export PYTHONPATH="/path/to/claude-skill-fandom-cli:$PYTHONPATH"
python -m fandom_cli page dontstarve Wilson --format markdown
```

### 🥉 Run from skill directory — after dependencies are installed

```bash
cd /path/to/claude-skill-fandom-cli
~/venvs/fandom-cli/bin/python -m fandom_cli page dontstarve Wilson --format markdown
```

### Externally-managed Python (Debian/Ubuntu)

If you see `error: externally-managed-environment`, do not use system pip. Create the sandbox-local venv instead:

```bash
python3 -m venv ~/venvs/fandom-cli
PIP_USER=false ~/venvs/fandom-cli/bin/pip install -e .
```

Alternatively, install dependencies into that venv and run with `PYTHONPATH`:

```bash
PIP_USER=false ~/venvs/fandom-cli/bin/pip install typer httpx beautifulsoup4 markdownify
export PYTHONPATH="$(pwd):$PYTHONPATH"
~/venvs/fandom-cli/bin/python -m fandom_cli page dontstarve Wilson --format markdown
```

### Cohub-specific: PATH wrapper

Inside a Cohub sandbox, keep runtime dependencies outside the workspace and expose the CLI through `~/.local/bin`:

```bash
SKILL_DIR="/workspace/.agents/skills/fandom-cli"
python3 -m venv ~/venvs/fandom-cli
PIP_USER=false ~/venvs/fandom-cli/bin/pip install -e "$SKILL_DIR"
mkdir -p ~/.local/bin
ln -sf ~/venvs/fandom-cli/bin/fandom ~/.local/bin/fandom
export PATH="$HOME/.local/bin:$PATH"
```

Then `fandom search dontstarve Wilson` works from anywhere in the sandbox.

> **Note:** Do not create a `.venv` inside `/workspace/.agents/skills/fandom-cli`; venvs and Python binaries belong under `~/venvs/`.

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
