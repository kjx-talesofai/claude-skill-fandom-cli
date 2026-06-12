# Fandom CLI

A **Claude Code** / **Cohub** skill for querying any Fandom wiki via MediaWiki API.
Fetch pages, extract infoboxes, search, browse categories, and collect images —
without scraping HTML or fighting Cloudflare.

## Quick Start

```bash
git clone https://github.com/kjx-talesofai/claude-skill-fandom-cli.git
cd claude-skill-fandom-cli

# Install dependencies (Python 3.10+)
pip install typer httpx beautifulsoup4 markdownify

# Run directly as a Python module (always works)
python -m fandom_cli.cli page dontstarve Wilson --format markdown
```

### Convenience wrapper (optional, one-time)

To use the shorter `fandom` command without typing `python -m fandom_cli.cli`:

```bash
# In Cohub / workspace:
cat > /workspace/bin/fandom << 'EOF'
#!/bin/bash
cd "$(dirname "$(readlink -f "$0")")/../.agents/skills/fandom-cli" && exec python3 -m fandom_cli.cli "$@"
EOF
chmod +x /workspace/bin/fandom

# Or symlink the module invocation:
# echo '#!/bin/bash' > /workspace/bin/fandom
# echo 'exec python3 -m fandom_cli.cli "$@"' >> /workspace/bin/fandom
# chmod +x /workspace/bin/fandom
```

Then use anywhere:
```bash
fandom search genshin-impact Zhongli --limit 5
```

## Cloudflare fallback

When Fandom returns a Cloudflare challenge (403), the CLI automatically retries
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
