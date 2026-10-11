# claude-rate

> **Rate your Claude / AI setup -- locally, in 5 seconds, no signup.**

`claude-rate` scans your project directory and grades your Claude Code (and adjacent AI tooling) configuration for cost-efficiency. Get a 0-100 score, an A+ to F letter grade, a per-category breakdown, copy-pasteable fix suggestions, and an estimated monthly spend on every active model tier.

Unlike the [web analyzer](https://sagargupta16.github.io/claude-cost-optimizer/analyzer) (which only sees what's on GitHub), `claude-rate` runs on the actual filesystem and inspects things the web tool can't:

- Real MCP server count from `.mcp.json`
- Hook configuration in `.claude/settings.json`
- `Read(...)` deny rules in a gitignored `.claude/settings.local.json`, checked against the lock files actually on disk
- Accidentally-committed secrets in `CLAUDE.md`, `.mcp.json`, or settings
- Untracked `.env` / credential files missing from `.gitignore`
- cost-mode skill installation, custom slash commands, subagents
- With `--user` and `--usage`: your user-level setup in `~/.claude` and your measured usage from local transcripts ([below](#your-whole-setup-and-your-real-usage))

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

## Your whole setup and your real usage

The project grade only sees one directory. Two flags grade the rest, all from local files:

```bash
claude-rate . --user --usage --fix
# one-shot, no install:
curl -sSL https://raw.githubusercontent.com/Sagargupta16/claude-cost-optimizer/main/tools/claude-rate/install.sh | sh -s -- . --user --usage --fix
```

- **`--user`** grades `~/.claude` (or `$CLAUDE_CONFIG_DIR`), which loads in every project: always-loaded instructions (`CLAUDE.md` plus `rules/` files without `paths:` frontmatter, which load at launch), the skill listing (every skill's description is in context each turn unless it sets `disable-model-invocation: true`), user and local MCP servers from `~/.claude.json`, cost controls in user settings, and user-level `Read(...)` deny rules. It reads counts and setting names only, never values.
- **`--usage [DAYS]`** reads your Claude Code transcripts (`~/.claude/projects/**/*.jsonl`, last 30 days by default) and grades what actually happened: the share of prompt tokens read from cache, median and p90 prompt size, and the share of list-price spend on legacy models. It reads only token counts and model names, dedupes the per-content-block records by message id, and prices each request the way Anthropic bills it (5-minute and 1-hour cache writes, the Haiku 5.5 prompt-length tier, Fast Mode at 2x). The dollar total is list price: on a Pro or Max plan you pay the plan price, so use it to compare models and habits.

Example against a sample `~/.claude` (14 skills, 5 user MCP servers, 6 sessions of synthetic transcripts):

```
Your Claude Code setup (user scope)
------------------------------------------------------------
  Global instructions      [################----]  20/25  ~2,345 tokens in 2 always-loaded file(s)
  Skill listing            [################----]  16/20  14 skill(s) in ~/.claude/skills and 0 enabled plugin(s), ~1,093 listing tokens
  MCP servers (user)       [###############-----]  15/20  5 user, 0 local (this project)
  Settings (user)          [########------------]   8/20  model=opus; cost controls: none
  Read deny rules (user)   [--------------------]   0/15  0 Read(...) rule(s) in user permissions.deny
  Score: 59/100  (C)
  * [Skill listing] Run /skill-doctor in a session: it lists what each skill costs and how often it is used. ...

Your measured usage (last 30 days)
------------------------------------------------------------
  Cache hit rate           [############--------]  30/50  86.1% of prompt tokens were cache reads
  Context size             [################----]  24/30  median prompt 67,154 tokens, p90 105,210; 15% of requests over 100K
  Model mix                [###############-----]  15/20  24% of list-price spend on legacy models
  Score: 69/100  (C)
  * [Model mix] 24% of list-price spend (40 requests) ran on legacy Opus 4.7 ($5/$25 per 1M). Opus 5.5 is $4/$20; pin it ...
  240 requests in 6 session file(s); list-price total $16.33, 21% of it output
    Opus 5.5           160 requests  $     12.29   75%
    Opus 4.7            40 requests  $      3.88   24%
    Haiku 5.5           40 requests  $      0.16    1%
```

| Scope | Category | Max | Full marks when |
|-------|----------|----:|-----------------|
| `--user` | Global instructions | 25 | Always-loaded user instructions stay small (they load in every session of every project) |
| `--user` | Skill listing | 20 | The skill and plugin descriptions in context each turn stay small |
| `--user` | MCP servers (user) | 20 | Few servers at user and local scope |
| `--user` | Settings (user) | 20 | A default model is pinned and a cost control Claude Code reads is set (`/effort` per model under `modelSettings`, `fastMode: false`, `availableModels` with `enforceAvailableModels`). A top-level `effortLevel` does not count: Opus 5.5 and later ignore it |
| `--user` | Read deny rules (user) | 15 | Deny rules for `.env`, dependencies and build output apply in every project |
| `--usage` | Cache hit rate | 50 | 95% or more of prompt tokens are cache reads |
| `--usage` | Context size | 30 | Median prompt under 50,000 tokens |
| `--usage` | Model mix | 20 | No list-price spend on legacy models |

## Example output (project)

```
claude-rate -- Claude / AI setup audit
============================================================
Project: /home/sagar/work/my-project
Verified against Anthropic pricing as of: 2026-10-09

  CLAUDE.md                [############--------]  12/20  250 lines primary (over the 200-line guidance); ~3,098 tokens total across 1 file(s)
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

Estimated monthly cost (30 turns/session, 3 sessions/day, 22 days; each turn reads the last one from cache)
  Fable 5.1      $ 2.10/session  ->  $ 138.64/month
  Fable 5        $ 2.94/session  ->  $ 193.87/month
  Opus 5.5       $ 0.95/session  ->  $  62.82/month
  Opus 5         $ 1.47/session  ->  $  96.93/month
  Opus 4.8       $ 1.47/session  ->  $  96.93/month
  Opus 4.7       $ 1.47/session  ->  $  96.93/month
  Opus 4.6       $ 1.13/session  ->  $  74.57/month
  Sonnet 5.5     $ 0.48/session  ->  $  31.41/month
  Sonnet 5       $ 0.59/session  ->  $  38.77/month
  Sonnet 4.6     $ 0.68/session  ->  $  44.74/month
  Haiku 5.5      $ 0.03/session  ->  $   1.94/month
  Haiku 4.5      $ 0.23/session  ->  $  14.91/month

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
  --user         Also grade your user-level setup (~/.claude)
  --usage [DAYS] Also grade measured usage from local transcripts (default 30 days)
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
claude-rate . --json | jq '.grade, .cost_estimate."sonnet-5-5".per_month'
# "D"
# 31.41
```

## Why a separate tool from the web analyzer?

The [web analyzer](https://sagargupta16.github.io/claude-cost-optimizer/analyzer) is aimed at **public repos** -- paste a GitHub URL, get a grade. But it can only see what's exposed via the GitHub Contents API. It can't:

- See your local `.claude/settings.local.json` (gitignored)
- Detect untracked secrets that haven't been pushed yet
- Check your Read deny rules against the lock files actually on disk
- Check whether you've installed the cost-mode skill locally

`claude-rate` runs where your code actually is. It's also faster (no network round-trip), works on private repos, and integrates with CI.

## Pricing data

All cost estimates use Anthropic's published rates **verified 2026-10-09**:

- Fable 5.1: $10/$50 per 1M tokens (1M context, most capable model); Fable 5: $10/$50 (legacy)
- Opus 5.5: $4/$20 per 1M tokens (1M context, released 2026-09-22) -- Anthropic's recommended starting model for most workloads, and 20% below Opus 5
- Opus 5 / 4.8 / 4.7 / 4.6: $5/$25 per 1M tokens (1M context, all legacy)
- Sonnet 5.5: $2/$10 per 1M tokens (1M context, released 2026-09-28) -- the current Sonnet flagship, same rate and tokenizer as Sonnet 5, but its cache read is $0.10 (cut on 2026-10-07), half Sonnet 5's $0.20
- Sonnet 5: $2/$10 per 1M tokens (1M context, legacy) -- the permanent standard rate; the increase to $3/$15 was cancelled
- Sonnet 4.6: $3/$15 per 1M tokens (1M context, legacy)
- Haiku 5.5 (`haiku-5-5`): $0.10/$0.50 per 1M tokens up to 100K prompt tokens, $0.50/$2.50 above (1M context, released 2026-10-07) -- the current Haiku and the first model priced by prompt length
- Haiku 4.5 (`haiku-4-5`): $1/$5 per 1M tokens (200K context, legacy)
- Cache hit: three multipliers -- 0.1x base input on most models (Haiku 5.5: $0.01/1M, or $0.05 over 100K), 0.05x on Opus 5.5 ($0.20/1M) and Sonnet 5.5 ($0.10/1M), 0.025x on Fable 5.1 ($0.25/1M); 5m write: 1.25x; 1h write: 2x
- Every model on the Claude 4.7+ tokenizer (Opus 4.7 and later, Fable, Sonnet 5 and 5.5, Haiku 5.5) includes a +30% tokenizer overhead: Anthropic's [pricing page](https://platform.claude.com/docs/en/about-claude/pricing) puts it at approximately 30% more tokens for the same text. Opus 4.6, Sonnet 4.6 and Haiku 4.5 use the previous tokenizer
- Each turn is billed the way Claude Code caches a conversation ([prompt caching docs](https://code.claude.com/docs/en/prompt-caching)): turn 1 writes the whole prompt at the 5-minute write rate (1.25x input), and every later turn reads the previous request from cache and writes only the new ~1,500-token exchange
- Haiku 5.5 is priced turn by turn, the way Anthropic bills each request on its own: a turn whose estimated prompt (after the tokenizer overhead) is over 100,000 tokens is priced at $0.50/$2.50 for input, cache and output alike. The example above stays under 100K on every turn

### Opus 5.5 cost gotchas

Opus 5.5 is 20% cheaper per token than Opus 5 ($4/$20 vs $5/$25), but re-baseline your costs after migrating:

- **Adaptive thinking is always on.** `thinking: {type: "disabled"}` and `budget_tokens` both return a 400, so effort is the only control. Code that disabled thinking on Opus 5 now pays for thinking tokens, billed as output at $20/1M.
- **`effort` defaults to `medium`** (Opus 5 defaulted to `high`; all five levels are supported). A request that omits effort now thinks less than it did on Opus 5.
- **Forced `tool_choice` (`any` / `tool`) returns a 400**, as do non-default sampling params and assistant prefill. Use `auto` with strict tool use or structured outputs.
- **`max_tokens` is a backstop, not a knob.** On Anthropic's repository-task benchmark a 16,384 cap ended about a quarter of Opus 5.5's attempts and 43% of Fable 5.1's ([cost guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence)); use 64,000 for agentic work.
- **Prompts written for an older model make the new one over-work.** In Anthropic's published runs, prompts written for Opus 4.8 cost 36% more per ticket on Opus 5 for no accuracy gain; audited, they were 14% cheaper and more accurate. Prune inherited instructions.
- **Minimum cacheable prompt is 512 tokens** on Opus 5.5 and Opus 5 (1,024 on Opus 4.8, 2,048 on Opus 4.7, 4,096 on Opus 4.6). A `cache_control` block below the floor is silently ignored: no error, no `cache_creation_input_tokens`, full input price.

### Sonnet 5.5 cost gotchas

Sonnet 5.5 costs the same as Sonnet 5 ($2/$10) and uses the same tokenizer, so migrating is free at the posted rate, and since 2026-10-07 cached reads cost half as much ($0.10 vs $0.20 per 1M, 0.05x base input). What still moves the bill:

- **Adaptive thinking is on by default** (effort `high`) and reasoning bills as output at $10/1M. `thinking: {type: "disabled"}` and `budget_tokens` return a 400; send `thinking: {type: "between_tools"}` at `high` effort or below to stop up-front thinking on routine turns.
- **Effort levels are recalibrated.** The same level does not produce the same amount of thinking as on Sonnet 5, so re-run your effort sweep. Anthropic's starting points: `high` in general, `medium` for well-specified agentic coding.
- **Forced `tool_choice` (`any` / `tool`) returns a 400**, as do non-default `temperature` / `top_p` / `top_k`. Use `auto` with strict tool use or structured outputs.
- **Minimum cacheable prompt is 512 tokens** (1,024 on Sonnet 5), so short system prompts that never cached on Sonnet 5 now do.
- **In Claude Code, `sonnet` is Sonnet 5.5 only on the Anthropic API.** On Bedrock, Google Cloud and Foundry it is Sonnet 4.5 ($3/$15, 200K context; deprecated, retirement scheduled for 2026-11-30), and on Claude Platform on AWS it is Sonnet 4.6 ($3/$15). Pin `claude-sonnet-5-5` (Bedrock: `anthropic.claude-sonnet-5-5`) or set `ANTHROPIC_DEFAULT_SONNET_MODEL`. Needs Claude Code v2.1.284 or later.

### Haiku 5.5 cost gotchas

Haiku 5.5 is 10x cheaper per token than Haiku 4.5 up to 100K prompt tokens and 2x above, but:

- **The 100K line is a cliff.** A request's prompt length counts all of its input tokens, including cache reads and writes, and a request over 100,000 tokens pays the higher prices for all of it, output included. A 100,000-token prompt costs $0.010 of input; a 100,001-token prompt costs $0.050 (5x). Short subagent and classification calls are where it wins.
- **~30% more tokens for the same text** than Haiku 4.5 (newer tokenizer), so per task it is roughly 7.7x cheaper at <=100K (10 / 1.3) and ~1.5x above (2 / 1.3).
- **Adaptive thinking is on by default** (effort `medium`). In Claude Code you cannot turn it off on Haiku 5.5.
- **Code carried over from Haiku 4.5 can return 400**: `budget_tokens`, non-default `temperature` / `top_p` / `top_k`, and assistant prefill are all rejected.
- **Minimum cacheable prompt is 512 tokens** (Haiku 4.5: 4,096).
- **In Claude Code, `haiku` is Haiku 5.5 only on the Anthropic API** (v2.1.293 or later). On Claude Platform on AWS, Bedrock, Google Cloud and Foundry it is Haiku 4.5 ($1/$5, 200K context). Set `ANTHROPIC_DEFAULT_HAIKU_MODEL` to pin it; that also sets the model for background functionality.

### Fast Mode

`speed: "fast"` (with the `fast-mode-2026-02-01` beta header) is **Opus 5.5, Opus 5 and Opus 4.8 only**, at a flat **2x** of each model's base: $8/$40 on Opus 5.5, $10/$50 on the other two. The older 6x tier no longer exists. Opus 4.7 returns an error on `speed: "fast"` with no fallback, and Opus 4.6 accepts the field but silently runs at standard speed and standard rates (`usage.speed` comes back `"standard"`). Claude API and Managed Agents only (Opus 5.5: Claude API only, as a research preview); cannot combine with Batch or Priority Tier, and switching speeds invalidates the prompt cache.

Sources:
- [platform.claude.com/docs/en/about-claude/pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- [platform.claude.com/docs/en/about-claude/models/overview](https://platform.claude.com/docs/en/about-claude/models/overview)
- [platform.claude.com/docs/en/models/opus-5-5/overview](https://platform.claude.com/docs/en/models/opus-5-5/overview)
- [platform.claude.com/docs/en/models/sonnet-5-5/overview](https://platform.claude.com/docs/en/models/sonnet-5-5/overview)
- [platform.claude.com/docs/en/models/haiku-5-5/overview](https://platform.claude.com/docs/en/models/haiku-5-5/overview)

## Limitations

- **Heuristic scoring.** Token estimates assume 30 turns/session, 3 sessions/day, 22 working days/month, ~1,500 new tokens and 500 output tokens per turn, with each turn reading the previous request from cache. Your actual usage may differ; treat the dollar numbers as order-of-magnitude.
- **Static analysis only.** It reads files; it doesn't trace actual API calls. Use [usage-analyzer](../usage-analyzer/) for measured per-session costs.
- **Stdlib only.** Intentional -- no `tiktoken`, no `requests`, runs anywhere Python 3.10+ runs. Token counts are estimated as characters / 4, then multiplied by the tokenizer overhead. Anthropic's [models overview](https://platform.claude.com/docs/en/about-claude/models/overview) puts the current tokenizer at about 2.5 characters per token (1M tokens is roughly 2.5M characters), so these counts can run low: treat them as a floor.

## License

MIT. Source: [github.com/Sagargupta16/claude-cost-optimizer](https://github.com/Sagargupta16/claude-cost-optimizer)
