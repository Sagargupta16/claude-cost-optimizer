# claude-rate

> **Rate your Claude / AI setup -- locally, in 5 seconds, no signup.**

`claude-rate` scans your project directory and grades your Claude Code (and adjacent AI tooling) configuration for cost-efficiency. Get a 0-100 score, an A+ to F letter grade, a per-category breakdown, copy-pasteable fix suggestions, and an estimated monthly spend on every active model tier.

Unlike the web analyzer in [../../site/](../../site/) (which only sees what's on GitHub, and isn't live on the deployed site yet), `claude-rate` runs on the actual filesystem and inspects things the web tool can't:

- Real MCP server count from `.mcp.json`
- Hook configuration in `.claude/settings.json`
- `Read(...)` deny rules in a gitignored `.claude/settings.local.json`, checked against the lock files actually on disk
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
Verified against Anthropic pricing as of: 2026-09-28

  CLAUDE.md                [############--------]  12/20  250 lines primary (over the 200-line guidance); ~3,223 tokens total across 1 file(s)
    ! 250 lines -- over Anthropic's 200-line guidance for CLAUDE.md. Longer files consume more context and reduce adherence. Move workflow-specific instructions into skills or path-scoped .claude/rules/ so they load on demand.
  File-read exclusions     [################----]  12/15  6 Read deny rule(s); lock files covered
    ! `.claudeignore` is not read by Claude Code -- it appears nowhere in Claude Code's documentation. Move its patterns into permissions.deny as Read(...) rules.
  .claude/settings.json    [#####---------------]   4/15  found at .claude/settings.json; permissions defined
  MCP servers              [####################]  15/15  no MCP servers configured (lowest overhead)
  Hooks                    [--------------------]   0/10  no hooks configured
  Security & hygiene       [##############------]   7/10  minor gaps
    ! No .gitignore at all -- secrets and build artifacts will be tracked.
  Optimizer tooling        [--------------------]   0/15  none of: cost-mode skill, custom commands, subagents, plugin metadata

Total: 50/100  (D)

Estimated monthly cost (30 turns/session, 3 sessions/day, 22 days, 70% cache hit)
  Fable 5.1      $ 4.75/session  ->  $ 313.39/month
  Fable 5        $ 5.37/session  ->  $ 354.57/month
  Opus 5.5       $ 2.06/session  ->  $ 135.88/month
  Opus 5         $ 2.79/session  ->  $ 184.10/month
  Opus 4.8       $ 2.79/session  ->  $ 184.10/month
  Opus 4.7       $ 2.79/session  ->  $ 184.10/month
  Opus 4.6       $ 2.07/session  ->  $ 136.37/month
  Sonnet 5       $ 1.07/session  ->  $  70.91/month
  Sonnet 4.6     $ 1.24/session  ->  $  81.82/month
  Haiku 4.5      $ 0.41/session  ->  $  27.27/month

Badge URL:  https://img.shields.io/badge/Claude%20Cost%20Grade-D-orange
Markdown:  ![Claude Cost Grade](https://img.shields.io/badge/Claude%20Cost%20Grade-D-orange)

Run with --fix to see 9 copy-pasteable fix suggestion(s).
```

With `--fix`, the File-read exclusions entry prints the `.claudeignore` patterns converted to rules you can paste:

```
  * [File-read exclusions] Merge its patterns into permissions.deny in .claude/settings.json, then delete .claudeignore:
    {
      "permissions": {
        "deny": [
          "Read(./node_modules/**)",
          "Read(*.min.js)",
          "Read(./docs/generated/x.md)"
        ]
      }
    }
```

## What gets scored

| Category | Max | What's checked |
|----------|----:|----------------|
| **CLAUDE.md** | 20 | Primary file (root `CLAUDE.md`, else `.claude/CLAUDE.md`) line count: up to 100 lines 12, up to 200 10, up to 300 6, up to 500 3, more 1. Plus estimated tokens (chars / 4) across both files: up to 2,000 8, up to 4,000 6, up to 8,000 4, up to 16,000 2, more 0. CLAUDE.md loads in full at launch, so over 200 lines is flagged against Anthropic's 200-line guidance |
| **File-read exclusions** | 15 | `Read(...)` rules in `permissions.deny` (`.claude/settings.json`, else `.claude/settings.local.json`): 10+ rules 13, 5-9 10, 1-4 6, none 0. +2 when every lock file at the root (`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `poetry.lock`, `Cargo.lock`, `uv.lock`) is covered by a rule containing its name, `*.lock` or `*lock*`. A `.claudeignore` scores nothing -- Claude Code does not read it -- and `--fix` converts its patterns to Read rules |
| **.claude/settings.json** | 15 | Default model pinned (6); a cost control Claude Code reads -- `effortLevel` low/medium, `fastMode: false`, `alwaysThinkingEnabled: false`, `enforceAvailableModels` with `availableModels`, or `autoCompactEnabled: true` (5); permissions defined (4) |
| **MCP servers** | 15 | Total count across `.mcp.json` and `settings.json`: none 15, 1-3 13, 4-5 10, 6-8 6, 9-12 3, more 0. With tool search on (the default) each server adds its tool names and server instructions to context; full tool schemas load up front only when tool search is off |
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
claude-rate . --json | jq '.grade, .cost_estimate."sonnet-5".per_month'
# "B"
# 99.77
```

## Why a separate tool from the web analyzer?

The web analyzer (built in [../../site/](../../site/), not yet live on the deployed site) is aimed at **public repos** -- paste a GitHub URL, get a grade. But it can only see what's exposed via the GitHub Contents API. It can't:

- See your local `.claude/settings.local.json` (gitignored)
- Detect untracked secrets that haven't been pushed yet
- Check your Read deny rules against the lock files actually on disk
- Check whether you've installed the cost-mode skill locally

`claude-rate` runs where your code actually is. It's also faster (no network round-trip), works on private repos, and integrates with CI.

## Pricing data

All cost estimates use Anthropic's published rates **verified 2026-09-28**:

- Fable 5.1: $10/$50 per 1M tokens (1M context, most capable model); Fable 5: $10/$50 (legacy)
- Opus 5.5: $4/$20 per 1M tokens (1M context, released 2026-09-22) -- Anthropic's recommended starting model for most workloads, and 20% below Opus 5
- Opus 5 / 4.8 / 4.7 / 4.6: $5/$25 per 1M tokens (1M context, all legacy)
- Sonnet 5: $2/$10 per 1M tokens (1M context) -- the permanent standard rate; the increase to $3/$15 was cancelled
- Sonnet 4.6: $3/$15 per 1M tokens (1M context, legacy)
- Haiku 4.5: $1/$5 per 1M tokens (200K context)
- Cache hit: three multipliers -- 0.1x base input on most models, 0.05x on Opus 5.5 ($0.20/1M), 0.025x on Fable 5.1 ($0.25/1M); 5m write: 1.25x; 1h write: 2x
- Opus 5.5 / 5 / 4.8 / 4.7 cost estimates include the +35% tokenizer overhead; Fable 5.1, Fable 5 and Sonnet 5 include +30%

### Opus 5.5 cost gotchas

Opus 5.5 is 20% cheaper per token than Opus 5 ($4/$20 vs $5/$25), but re-baseline your costs after migrating:

- **Adaptive thinking is always on.** `thinking: {type: "disabled"}` and `budget_tokens` both return a 400, so effort is the only control. Code that disabled thinking on Opus 5 now pays for thinking tokens, billed as output at $20/1M.
- **`effort` defaults to `medium`** (Opus 5 defaulted to `high`; all five levels are supported). A request that omits effort now thinks less than it did on Opus 5.
- **Forced `tool_choice` (`any` / `tool`) returns a 400**, as do non-default sampling params and assistant prefill. Use `auto` with strict tool use or structured outputs.
- **`max_tokens` is a backstop, not a knob.** In Anthropic's published runs a 16,384 cap ended 15% of Opus 5's coding attempts unsolved; use 64,000 for agentic work.
- **Prompts written for an older model make the new one over-work.** In Anthropic's published runs, prompts written for Opus 4.8 cost 36% more per ticket on Opus 5 for no accuracy gain; audited, they were 14% cheaper and more accurate. Prune inherited instructions.
- **Minimum cacheable prompt is 512 tokens** on Opus 5.5 and Opus 5 (1,024 on Opus 4.8, 2,048 on Opus 4.7, 4,096 on Opus 4.6). A `cache_control` block below the floor is silently ignored: no error, no `cache_creation_input_tokens`, full input price.

### Fast Mode

`speed: "fast"` (with the `fast-mode-2026-02-01` beta header) is **Opus 5.5, Opus 5 and Opus 4.8 only**, at a flat **2x** of each model's base: $8/$40 on Opus 5.5, $10/$50 on the other two. The older 6x tier no longer exists. Opus 4.7 returns an error on `speed: "fast"` with no fallback, and Opus 4.6 accepts the field but silently runs at standard speed and standard rates (`usage.speed` comes back `"standard"`). Claude API and Managed Agents only (Opus 5.5: Claude API only, as a research preview); cannot combine with Batch or Priority Tier, and switching speeds invalidates the prompt cache.

Sources:
- [platform.claude.com/docs/en/about-claude/pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- [platform.claude.com/docs/en/about-claude/models/overview](https://platform.claude.com/docs/en/about-claude/models/overview)
- [platform.claude.com/docs/en/models/opus-5-5/overview](https://platform.claude.com/docs/en/models/opus-5-5/overview)

## Limitations

- **Heuristic scoring.** Token estimates assume 30 turns/session, 3 sessions/day, 22 working days/month, 70% cache hit rate. Your actual usage may differ; treat the dollar numbers as order-of-magnitude.
- **Static analysis only.** It reads files; it doesn't trace actual API calls. Use [usage-analyzer](../usage-analyzer/) for measured per-session costs.
- **Stdlib only.** Intentional -- no `tiktoken`, no `requests`, runs anywhere Python 3.10+ runs. Token counts are estimated from character count (~4 chars/token), which is accurate within ~10% for English + code.

## License

MIT. Source: [github.com/Sagargupta16/claude-cost-optimizer](https://github.com/Sagargupta16/claude-cost-optimizer)
