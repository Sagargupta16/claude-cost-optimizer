# claude-rate

> **Rate your Claude / AI setup -- locally, in 5 seconds, no signup.**

`claude-rate` scans your project directory and grades your Claude Code (and adjacent AI tooling) configuration for cost-efficiency. Get a 0-100 score, an A+ to F letter grade, a per-category breakdown, copy-pasteable fix suggestions, and an estimated monthly spend on every active model tier.

Unlike the web analyzer in [../../site/](../../site/) (which only sees what's on GitHub, and isn't live on the deployed site yet), `claude-rate` runs on the actual filesystem and inspects things the web tool can't:

- Real MCP server count from `.mcp.json`
- Hook configuration in `.claude/settings.json`
- Coverage gaps in `.claudeignore` vs files actually present on disk
- Accidentally-committed secrets in `CLAUDE.md`, `.mcp.json`, or settings
- Untracked `.env` / credential files missing from `.gitignore`
- cost-mode skill installation, custom slash commands, subagents

## Quick start

Pick whichever runner fits your shell:

### curl one-shot (no Node, no install)

```bash
curl -sSL https://raw.githubusercontent.com/Sagargupta16/claude-cost-optimizer/main/tools/claude-rate/install.sh | sh -s -- .
```

### curl, persistent install

```bash
curl -sSL https://raw.githubusercontent.com/Sagargupta16/claude-cost-optimizer/main/tools/claude-rate/install.sh | sh -s -- --install
# then anywhere:
claude-rate .
```

### Direct Python (cloned repo)

```bash
python tools/claude-rate/rate.py /path/to/project
```

No external dependencies. Pure Python 3.10+ stdlib.

## Example output

```
claude-rate -- Claude / AI setup audit
============================================================
Project: /home/sagar/work/my-project
Verified against Anthropic pricing as of: 2026-06-06

  CLAUDE.md                [###############-----]  15/20  3,648 chars primary (near hard limit); 3,648 chars total across 1 file(s)
  .claudeignore            [--------------------]   0/15  not found
    ! No .claudeignore file. Claude will index node_modules, dist, lock files, and other large generated content.
  .claude/settings.json    [--------------------]   0/15  no settings.json
    ! No .claude/settings.json. Default model and permissions are not project-pinned.
  MCP servers              [####################]  15/15  no MCP servers configured (lowest overhead)
  Hooks                    [--------------------]   0/10  no hooks configured
  Security & hygiene       [####################]  10/10  no leaked secrets, gitignore present
  Optimizer tooling        [##########----------]   8/15  cost-mode skill installed, plugin marketplace metadata

Total: 48/100  (D)

Estimated monthly cost (30 turns/session, 3 sessions/day, 22 days, 70% cache hit)
  Opus 4.8       $ 2.62/session  ->  $ 172.67/month
  Opus 4.7       $ 2.62/session  ->  $ 172.67/month
  Opus 4.6       $ 1.94/session  ->  $ 127.91/month
  Sonnet 4.6     $ 1.16/session  ->  $  76.74/month
  Haiku 4.5      $ 0.39/session  ->  $  25.58/month

Badge URL:  https://img.shields.io/badge/Claude%20Cost%20Grade-D-orange
Markdown:  ![Claude Cost Grade](https://img.shields.io/badge/Claude%20Cost%20Grade-D-orange)

Run with --fix to see 6 copy-pasteable fix suggestion(s).
```

## What gets scored

| Category | Max | What's checked |
|----------|----:|----------------|
| **CLAUDE.md** | 20 | Primary file size (4K hard limit, content beyond is silently truncated), plus total instruction budget across `CLAUDE.md` + `.claude/CLAUDE.md` (~12K total budget) |
| **.claudeignore** | 15 | Existence, entry count, AND coverage gaps -- if you have `node_modules/` on disk but it's not in `.claudeignore`, that's flagged with a copy-paste fix |
| **.claude/settings.json** | 15 | Default model pinned, budget cap configured, permissions array defined |
| **MCP servers** | 15 | Total count across `.mcp.json` and `settings.json`. Each adds ~1.5K tokens to every turn |
| **Hooks** | 10 | Count of configured hooks (PreToolUse, PostToolUse, Stop, etc.) for budget tracking and cost logging |
| **Security & hygiene** | 10 | `.env` / credentials presence vs `.gitignore` coverage, plus a regex scan for leaked API keys (`sk-...`, `AKIA...`, `ghp_...`) in tracked files |
| **Optimizer tooling** | 15 | Bonus: cost-mode skill installed, custom slash commands, subagents, plugin marketplace metadata |
| **Total** | **100** | |

| Grade | Score | Color |
|:-----:|:-----:|:-----:|
| A+ | 95-100 | brightgreen |
| A | 85-94 | green |
| B | 70-84 | yellowgreen |
| C | 55-69 | yellow |
| D | 40-54 | orange |
| F | 0-39 | red |

## Flags

```
positional arguments:
  path           Project directory (default: current dir)

options:
  --json         Emit machine-readable JSON
  --fix          Show copy-pasteable fix suggestions
  --strict       Exit with status 1 if grade is below B (CI-friendly)
  --version      Print version
```

### CI usage

Add a quality gate to your CI:

```yaml
# .github/workflows/claude-rate.yml
name: claude-rate
on: [pull_request]
jobs:
  rate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: |
          curl -sSL https://raw.githubusercontent.com/Sagargupta16/claude-cost-optimizer/main/tools/claude-rate/install.sh \
            | sh -s -- . --strict --fix
```

`--strict` exits with status 1 if your grade drops below B, breaking the build until the configuration is fixed.

### Programmatic / JSON

```bash
claude-rate . --json | jq '.grade, .cost_estimate."sonnet-4-6".per_month'
# "B"
# 76.74
```

## Why a separate tool from the web analyzer?

The web analyzer (built in [../../site/](../../site/), not yet live on the deployed site) is aimed at **public repos** -- paste a GitHub URL, get a grade. But it can only see what's exposed via the GitHub Contents API. It can't:

- See your local `.claude/settings.local.json` (gitignored)
- Detect untracked secrets that haven't been pushed yet
- Verify `.claudeignore` matches your actual on-disk file tree
- Check whether you've installed the cost-mode skill locally

`claude-rate` runs where your code actually is. It's also faster (no network round-trip), works on private repos, and integrates with CI.

## Pricing data

All cost estimates use Anthropic's published rates **verified 2026-06-06**:

- Opus 4.8 / 4.7 / 4.6: $5/$25 per 1M tokens (1M context)
- Sonnet 4.6: $3/$15 per 1M tokens (1M context)
- Haiku 4.5: $1/$5 per 1M tokens (200K context)
- Cache hit: 0.1x base input price; 5m write: 1.25x; 1h write: 2x
- Opus 4.8 / 4.7 cost estimates include the +35% tokenizer overhead

Sources:
- [platform.claude.com/docs/en/about-claude/pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- [platform.claude.com/docs/en/about-claude/models/overview](https://platform.claude.com/docs/en/about-claude/models/overview)

## Limitations

- **Heuristic scoring.** Token estimates assume 30 turns/session, 3 sessions/day, 22 working days/month, 70% cache hit rate. Your actual usage may differ; treat the dollar numbers as order-of-magnitude.
- **Static analysis only.** It reads files; it doesn't trace actual API calls. Use [usage-analyzer](../usage-analyzer/) for measured per-session costs.
- **Stdlib only.** Intentional -- no `tiktoken`, no `requests`, runs anywhere Python 3.10+ runs. Token counts are estimated from character count (~4 chars/token), which is accurate within ~10% for English + code.

## License

MIT. Source: [github.com/Sagargupta16/claude-cost-optimizer](https://github.com/Sagargupta16/claude-cost-optimizer)
