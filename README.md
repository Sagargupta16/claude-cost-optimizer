# Claude Cost Optimizer

![GitHub stars](https://img.shields.io/github/stars/Sagargupta16/claude-cost-optimizer?style=flat-square&cacheSeconds=86400)
![GitHub forks](https://img.shields.io/github/forks/Sagargupta16/claude-cost-optimizer?style=flat-square&cacheSeconds=86400)
![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)
![Last Commit](https://img.shields.io/github/last-commit/Sagargupta16/claude-cost-optimizer?style=flat-square&cacheSeconds=86400)

> **Save 30-90% on Claude Code costs** with an installable skill, CLI tools, and 12 deep-dive guides.
>
> **30-60% is the typical result** for a mixed real workload. **Up to 90% is the ceiling** when you stack every lever -- prompt caching, Batch API, model routing, and context discipline -- against an unoptimized all-Opus baseline. Every number is sourced: see [How far can you actually go?](#how-far-can-you-actually-go).

## Install

**Claude Code (official plugin system):**

```bash
/plugin marketplace add Sagargupta16/claude-cost-optimizer
/plugin install cost-mode@claude-cost-optimizer
```

**Multi-agent (Cursor, Cline, Codex, 40+ agents):**

```bash
npx skills add Sagargupta16/claude-cost-optimizer
```

Then activate in any session:

```
/cost-mode              # Standard (40-60% output token reduction)
/cost-mode lite         # Professional brevity (20-40% output reduction)
/cost-mode strict       # Telegraphic, max savings (60-70% output reduction)
/cost-mode off          # Resume normal behavior
```

---

## What cost-mode Does

| Feature | How It Saves Tokens |
|---------|-------------------|
| **Strips filler** | Drops pleasantries, hedging, restating your question, trailing summaries |
| **Suggests cheaper models** | "Haiku handles this -- `/model haiku`" for simple tasks |
| **Suggests CLI tools** | "Use `prettier`/`eslint --fix` directly" instead of burning LLM tokens |
| **Session awareness** | Reminds to `/compact` after 20+ turns, fresh sessions for new tasks |
| **Minimal code gen** | Diffs over rewrites, no obvious comments, no speculative error handling |
| **Auto-deactivates** | Full clarity for security warnings, destructive ops, and when you're confused |

Technical accuracy is never sacrificed. Code in commits and PRs is written normally.

[Full skill documentation](skills/cost-mode/README.md)

---

## Rate your setup

### Locally, in 5 seconds (recommended)

`claude-rate` runs on your filesystem -- no signup, no GitHub upload, no network round-trip. Pick whichever runner fits your shell:

```bash
# curl one-shot (no Node, no install)
curl -sSL https://raw.githubusercontent.com/Sagargupta16/claude-cost-optimizer/main/tools/claude-rate/install.sh | sh -s -- .

# curl, persistent install
curl -sSL https://raw.githubusercontent.com/Sagargupta16/claude-cost-optimizer/main/tools/claude-rate/install.sh | sh -s -- --install
```

Add `--fix` to print copy-pasteable fix commands, `--strict` to fail CI when the grade drops below B, or `--json` for machine-readable output. See [tools/claude-rate/README.md](tools/claude-rate/README.md) for the full breakdown.

The local rater works on private and uncommitted repos and inspects things the web analyzer can't reach: `settings.local.json`, whether your `Read(...)` deny rules cover the lock files actually on disk, and secrets in your working tree. The [web analyzer](https://sagargupta16.github.io/claude-cost-optimizer/analyzer) applies the same 7-category rubric (CLAUDE.md, file-read exclusions, settings, MCP, hooks, security, skills/agents/commands) to any public repo.

### Public repos -- web tools

| Tool | What It Does |
|------|-------------|
| **[Repo Analyzer](https://sagargupta16.github.io/claude-cost-optimizer/analyzer)** | Paste a GitHub URL to get a cost audit, grade (A+ to F), and recommendations |
| **[Cost Calculator](https://sagargupta16.github.io/claude-cost-optimizer/calculator)** | Estimate monthly spend with interactive charts: per-turn cost curve, savings breakdown, model comparison |
| **[Badge Checker](https://sagargupta16.github.io/claude-cost-optimizer/badge)** | Score your setup and get a shields.io badge for your repo |

---

## Before vs After

Worked example, 30-turn session, priced at legacy Opus 5 rates (identical math on Opus 4.8 -- same $5/$25). On Opus 5.5, the current Opus flagship ($4/$20, cache hits at 0.05x), every line item is cheaper, so both columns come out lower. The dollar figures are arithmetic from the posted rates, not a metered bill. The MCP share of the drop assumes MCP tool search is off (full tool schemas loaded up front); under the default tool search only tool names and server instructions enter context, so that part of the saving is smaller:

```
BEFORE (no optimization):                 AFTER (5 minutes of setup):
  CLAUDE.md:        6,200 chars           CLAUDE.md:        2,800 chars
  Read deny rules:  none                  Read deny rules:  12 patterns
  MCP servers:      6 active                  MCP servers:      2 active
  System prompt:    ~15,000 tokens/turn       System prompt:    ~5,500 tokens/turn
  Session cost:     $2.85                     Session cost:     $1.12
  Monthly (3x/day): $188.10                   Monthly (3x/day): $73.92

  Savings: $114.18/month (61%)
```

---

## How Far Can You Actually Go?

Short answer: **30-60% is what a typical mixed workload saves. Up to ~90% is the ceiling** when every lever stacks against a naive all-Opus, no-cache, verbose baseline. The headline numbers below are each real and sourced -- but each one applies only to the *favorable slice* of your spend, so the compound rarely holds across an entire real workload. Treat 90% as a ceiling, not a promise.

| Lever | Published savings | Applies to | Source |
|-------|:-----------------:|------------|--------|
| **Prompt caching** | **up to 90%** cost (**95%** on Opus 5.5 and Sonnet 5.5, **97.5%** on Fable 5.1), 85% latency | cached input only (0.1x input price; 0.05x on Opus 5.5 / Sonnet 5.5; 0.025x on Fable 5.1 / Mythos 5.1) | [Anthropic: Prompt caching](https://claude.com/blog/prompt-caching), [pricing docs](https://platform.claude.com/docs/en/about-claude/pricing) |
| **Batch API** | flat **50%** off input **and** output, stacks with caching | any async (24h) work | [Anthropic: Message Batches API](https://claude.com/blog/message-batches-api), [batch docs](https://platform.claude.com/docs/en/build-with-claude/batch-processing) |
| **Model routing** | **up to 97.5%** per token (Opus 5.5->Haiku 5.5 is 40x at <=100K prompt tokens, 8x above; legacy Haiku 4.5 was 4x); RouteLLM up to 85% at 95% quality | tasks a cheaper model handles well | [RouteLLM (arXiv 2406.18665)](https://arxiv.org/pdf/2406.18665), [LMSYS](https://lmsys.org/blog/2024-07-01-routellm/) |
| **Context management** | **84%** fewer tokens in a 100-turn eval | long agentic sessions | [Anthropic: Context management](https://claude.com/blog/context-management) |
| **Subscription vs API** | **~90%+** for heavy users (Pro $20 / Max $100-200 flat; Max also includes $100-200/mo of API credits, which do not cover Claude Code) | power users vs pay-as-you-go | [ksred cost tracker](https://www.ksred.com/claude-code-pricing-guide-which-plan-actually-saves-you-money/) (n=1) |

### The honest read

- **"up to 90%" is a ceiling, not a typical result.** Anthropic itself publishes 90% for caching *alone*, and the levers genuinely multiply against an unoptimized baseline. But each 90% is a best case on its favorable slice (cached input for caching; conversational traffic for routing), so a whole mixed workload lands well below the sum.
- **The stacked total has no source.** Each lever above is individually sourced; the combined figure is not, and this repo holds no controlled multi-lever measurement. For a number that applies to your workload, run [claude-rate](#rate-your-setup) on your own repo and price only the levers you can apply.
- **The cost-mode skill on its own delivers 30-60%** -- it does output-token reduction and model-routing hints, not batch/caching/subscription. The 90% ceiling needs the full playbook in the [guides](#guides), not just the skill.
- **Caching and batch are the firmest floors** (first-party Anthropic pricing; batch is a documented flat 50% that provably stacks with caching). Routing and subscription savings are the most workload-sensitive.

> Prices verified against the [pricing reference](#pricing-reference) below (2026-10-09). Cache hit = 0.1x base input on every model **except Fable 5.1 and Mythos 5.1 (0.025x) and Opus 5.5 and Sonnet 5.5 (0.05x)**; Batch = 50% off both input and output.

---

## Quick Start (5 Minutes, No Skill Needed)

Even without installing the skill, these 5 changes cut costs immediately:

| # | Strategy | Savings | Guide |
|---|----------|:-------:|-------|
| 1 | **Keep CLAUDE.md under 200 lines** -- it loads in full every session; Anthropic's guidance is that longer files "consume more context and reduce adherence". Move workflow-specific instructions into skills or path-scoped `.claude/rules/` | No published figure | [Context Optimization](guides/02-context-optimization.md) |
| 2 | **Use Haiku for simple tasks** (`--model haiku`) -- Haiku 5.5 is $0.10/$0.50 up to 100K prompt tokens, $0.50/$2.50 above: 40x cheaper per token than Opus 5.5 below 100K, 8x above | 20-40% | [Model Selection](guides/03-model-selection.md) |
| 3 | **Use Plan Mode before coding** (Shift+Tab) -- prevents wasted iterative cycles | 15-25% | [Workflow Patterns](guides/04-workflow-patterns.md) |
| 4 | **Add `Read(...)` deny rules** to `permissions.deny` in `.claude/settings.json` -- keep Claude's file tools out of node_modules, dist, lock files (`.claudeignore` is not a Claude Code feature) | No published figure | [Context Optimization](guides/02-context-optimization.md) |
| 5 | **Delegate to subagents** -- isolate expensive searches from main context | 20-40% | [Workflow Patterns](guides/04-workflow-patterns.md) |

Full walkthrough: **[Getting Started in 5 Minutes](guides/00-getting-started.md)**

---

## Skills Roadmap

cost-mode is the first skill. More are planned:

| Skill | Status | What It Does | Cost Impact |
|-------|:------:|-------------|:-----------:|
| **cost-mode** | Live | Concise responses, model routing suggestions, session awareness | 30-60% (skill alone) |
| **deny-rules-gen** | Planned | Generates `permissions.deny` `Read(...)` rules for your project's tech stack | No published figure |
| **context-compress** | Planned | Rewrites your CLAUDE.md to be shorter while keeping all essential info | 10-20% input reduction |
| **cache-optimizer** | Planned | Detects cache-busting patterns and suggests fixes to maximize prompt cache hits | 10-25% input reduction |
| **budget-guard** | Planned | Per-session and per-day spending limits with warnings before you blow past them | Prevents overspend |

Want to build one? Skills are just `SKILL.md` files -- see [CONTRIBUTING.md](CONTRIBUTING.md) and the [skills/cost-mode/](skills/cost-mode/) directory for the pattern.

---

## Guides

12 deep-dive guides covering every optimization area:

| Guide | What You'll Learn |
|-------|-------------------|
| [00 - Getting Started](guides/00-getting-started.md) | Zero to optimized in 5 minutes -- the essential setup |
| [01 - Understanding Costs](guides/01-understanding-costs.md) | How billing works, what costs the most, where money goes |
| [02 - Context Optimization](guides/02-context-optimization.md) | Reduce input tokens: CLAUDE.md, Read deny rules, file reads |
| [03 - Model Selection](guides/03-model-selection.md) | When to use Opus vs Sonnet vs Haiku (with decision tree) |
| [04 - Workflow Patterns](guides/04-workflow-patterns.md) | Plan mode, subagents, commands, batch operations |
| [05 - Team Budgeting](guides/05-team-budgeting.md) | Per-developer budgets, cost tracking, ROI calculation |
| [06 - Access Methods & Pricing](guides/06-access-methods-pricing.md) | Compare API vs Bedrock vs Vertex AI vs Claude Code pricing |
| [07 - MCP & Agent Cost Impact](guides/07-mcp-agent-costs.md) | MCP server overhead, subagent costs, Agent SDK patterns |
| [08 - Prompt Caching Deep Dive](guides/08-prompt-caching.md) | Cache mechanics, TTL economics, maximizing hit rates, ROI math |
| [09 - Subscription Plan Value](guides/09-subscription-value.md) | Choose the right plan, maximize allowance, upgrade/downgrade signals |
| [10 - Three-Tier Task Routing](guides/10-task-routing.md) | Skip the LLM for Tier 0 tasks, route cheap tasks to Haiku, save Opus for complex work |
| [11 - Speed vs Cost](guides/11-speed-vs-cost.md) | Make Claude faster without burning money -- free latency levers first, Fast Mode economics last |

Also: [Visual Diagrams](guides/diagrams.md) (Mermaid flowcharts) | [One-Page Cheatsheet](cheatsheet.md)

---

## Templates

Copy-paste configs that are already optimized:

**CLAUDE.md**: [Minimal](templates/CLAUDE.md/minimal.md) | [Standard](templates/CLAUDE.md/standard.md) | [Comprehensive](templates/CLAUDE.md/comprehensive.md) | [Monorepo](templates/CLAUDE.md/monorepo.md)

**By Stack**: [React+Vite](templates/CLAUDE.md/by-stack/react-vite.md) | [Next.js](templates/CLAUDE.md/by-stack/nextjs.md) | [FastAPI](templates/CLAUDE.md/by-stack/fastapi-python.md) | [MERN](templates/CLAUDE.md/by-stack/mern.md) | [Terraform](templates/CLAUDE.md/by-stack/terraform-aws.md) | [Go](templates/CLAUDE.md/by-stack/go.md) | [Rust](templates/CLAUDE.md/by-stack/rust.md) | [Django](templates/CLAUDE.md/by-stack/django.md) | [Rails](templates/CLAUDE.md/by-stack/rails.md) | [Spring Boot](templates/CLAUDE.md/by-stack/java-spring.md)

**Settings**: [Cost-Conscious](templates/settings/cost-conscious.json) | [Balanced](templates/settings/balanced.json) | [Performance-First](templates/settings/performance-first.json)

**Commands**: [/cost-check](templates/commands/cost-check.md) | [/budget-mode](templates/commands/budget-mode.md) | [/quick-fix](templates/commands/quick-fix.md) | [/optimize](tools/optimize-command/optimize.md)

---

## CLI Tools

The 8 tools in `tools/`, plus the budget hooks in `hooks/`. [Full tools documentation](tools/README.md)

| Tool | What It Does |
|------|-------------|
| [claude-rate](tools/claude-rate/) | Grade your local setup on the 7-category rubric (recommended entry point) |
| [Token Estimator](tools/token-estimator/) | Estimate token count and cost for any file |
| [Usage Analyzer](tools/usage-analyzer/) | Find cost hotspots across your sessions |
| [Badge Generator](tools/badge-generator/) | Grade your project config (A+ to F) from the CLI |
| [MCP Cost Server](tools/mcp-cost-server/) | In-session cost estimation via MCP |
| [VS Code Extension](tools/vscode-extension/) | Token count and cost in the status bar |
| [GitHub Action](tools/actions/claude-cost-audit/) | Automated cost audit on PRs |
| [/optimize Command](tools/optimize-command/) | Claude Code custom command that audits the current project |
| [Budget Hooks](hooks/) | Track tool calls, log costs, warn at thresholds |

---

## Pricing Reference

Verified 2026-10-09 against Anthropic's [pricing](https://platform.claude.com/docs/en/about-claude/pricing), [models overview](https://platform.claude.com/docs/en/about-claude/models/overview), [Opus 5.5 overview](https://platform.claude.com/docs/en/models/opus-5-5/overview), [Sonnet 5.5 overview](https://platform.claude.com/docs/en/models/sonnet-5-5/overview), [Haiku 5.5 overview](https://platform.claude.com/docs/en/models/haiku-5-5/overview), and [model deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations) pages.

| Model | Input / 1M | Output / 1M | Cache Hit / 1M | 5m Cache Write / 1M | 1h Cache Write / 1M | Context | Max Output | Min cacheable prompt |
|-------|:----------:|:-----------:|:---------------:|:-------------------:|:-------------------:|:-------:|:----------:|:--------------------:|
| **Fable 5.1** (highest capability) | $10.00 | $50.00 | **$0.25** | $12.50 | $20.00 | 1M | 128K | 512 |
| Mythos 5.1 (verification required) | $10.00 | $50.00 | **$0.25** | $12.50 | $20.00 | 1M | 128K | 512 |
| **Fable 5** (legacy) | $10.00 | $50.00 | $1.00 | $12.50 | $20.00 | 1M | 128K | 512 |
| Mythos 5 (limited, [Glasswing](https://anthropic.com/glasswing)) | $10.00 | $50.00 | $1.00 | $12.50 | $20.00 | 1M | 128K | 512 |
| **Opus 5.5** (Opus flagship, recommended default) | $4.00 | $20.00 | **$0.20** | $5.00 | $8.00 | 1M | 128K | **512** |
| Opus 5 (legacy) | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1M | 128K | 512 |
| Opus 4.8 (legacy) | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1M | 128K | 1,024 |
| Opus 4.7 | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1M | 128K | 2,048 |
| Opus 4.6 | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1M | 128K | 4,096 |
| Opus 4.5 | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 200K | 64K | 4,096 |
| Opus 4.1 (retired 2026-08-05, still on Bedrock + Google Cloud) | $15.00 | $75.00 | $1.50 | $18.75 | $30.00 | 200K | 32K | 1,024 |
| **Sonnet 5.5** (Sonnet flagship) | $2.00 | $10.00 | **$0.10** | $2.50 | $4.00 | 1M | 128K | **512** |
| Sonnet 5 (legacy) | $2.00 | $10.00 | $0.20 | $2.50 | $4.00 | 1M | 128K | 1,024 |
| Sonnet 4.6 | $3.00 | $15.00 | $0.30 | $3.75 | $6.00 | 1M | 64K | 1,024 |
| Sonnet 4.5 (deprecated, retirement scheduled for 2026-11-30) | $3.00 | $15.00 | $0.30 | $3.75 | $6.00 | 200K | 64K | 1,024 |
| **Haiku 5.5** (prompt <= 100K tokens) | **$0.10** | **$0.50** | **$0.01** | $0.125 | $0.20 | 1M | 128K | **512** |
| Haiku 5.5 (prompt > 100K tokens) | $0.50 | $2.50 | $0.05 | $0.625 | $1.00 | 1M | 128K | 512 |
| Haiku 4.5 (legacy) | $1.00 | $5.00 | $0.10 | $1.25 | $2.00 | 200K | 64K | 4,096 |
| Mythos Preview (deprecated, no retirement date) | $25.00 | $125.00 | $2.50 | $31.25 | $50.00 | 1M | -- | 2,048 |

Mythos 5.1's rates come from the pricing page; its context window, max output and cache floor are not listed there. The [Fable 5.1 model page](https://platform.claude.com/docs/en/models/fable-5-1/overview) states Mythos 5.1 "shares Claude Fable 5.1's specifications and pricing", and the [prompt-caching page](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) lists it at the 512-token floor. Mythos 5.1 (`claude-mythos-5-1`, Bedrock `anthropic.claude-mythos-5-1`) is now "Verification required": available to organizations verified through Anthropic's verification programs such as the Cyber Verification Program, on the Claude API, Bedrock, Google Cloud and Microsoft Foundry (not Claude Platform on AWS).

**Opus 5.5** (`claude-opus-5-5`, released 2026-09-22) is the current Opus flagship, and Anthropic's models overview now says to "start with Claude Opus 5.5 for most workloads". It costs **$4/$20 -- 20% below the $5/$25 of Opus 5 and Opus 4.8**, the first Opus release to lower the rate, and cache hits read at **$0.20, 0.05x base input (95% off)**. It is not a drop-in swap of the model string -- see [what actually changes](#migrating-to-opus-55) first. **Opus 5** (`claude-opus-5`, GA 2026-07-24) is now legacy at $5/$25. **1M context** on Fable 5.1, Mythos 5.1, Fable 5, Mythos 5, Opus 5.5, Opus 5, Opus 4.8, Opus 4.7, Opus 4.6, Sonnet 5.5, Sonnet 5, and Sonnet 4.6 bills at **standard rates** across the full window (no long-context premium); Haiku 5.5 also has 1M context but is the exception, billing any prompt over 100K tokens at its higher tier. **Sonnet 5.5** (`claude-sonnet-5-5`, released 2026-09-28) is the current Sonnet flagship at **$2/$10, the same as Sonnet 5**, with the same cache writes, batch ($1/$5) and tokenizer, and since 2026-10-07 its cache hits read at **$0.10, 0.05x base input (95% off)** -- half Sonnet 5's $0.20 -- so moving to it never costs more at the posted rate; it still rejects some Sonnet 5 request shapes -- see [what changes](#migrating-to-sonnet-55). **Sonnet 5** (`claude-sonnet-5`, GA 2026-06-30), now legacy, is **$2/$10 per MTok permanently** -- the launch rate was labelled introductory through 2026-08-31, but Anthropic made it standard and cancelled the increase to $3/$15, so Sonnet 5 costs half as much as Opus 5.5 (and 60% less than legacy Opus 5). **Haiku 5.5** (`claude-haiku-5-5`, Bedrock `anthropic.claude-haiku-5-5`, released 2026-10-07) is the current Haiku and the first model priced by prompt length: **$0.10/$0.50 up to 100K prompt tokens, $0.50/$2.50 above**, so a 100,001-token prompt pays 5x the input and output rate of a 100,000-token one -- see [what changes](#migrating-to-haiku-55). **Haiku 4.5** is now legacy at $1/$5. **Batch API**: 50% off both input and output, and it stacks with caching -- Opus 5.5 batch is **$2/$10** (Opus 5: $2.50/$12.50), with up to 300K output via the `output-300k-2026-03-24` beta. **Fast Mode** (research preview, **Opus 5.5, Opus 5 and Opus 4.8 only**): **2x** each model's own base rate -- **$8/$40 on Opus 5.5**, $10/$50 on Opus 5 and 4.8 -- up to 2.5x output tokens/sec. **Regional endpoints** (Bedrock / Vertex AI / Claude API `inference_geo: "us"` for 4.6+ models): +10%. **Subscriptions**: Pro $20/mo (or **$200/yr ≈ $16.67/mo**, ~17% off), Max 5x $100/mo, Max 20x $200/mo. Since 2026-10-07 Max and Team include **monthly API credits**: $100 on Max 5x, $200 on Max 20x, and on Team $20 per Standard seat and $100 per Premium seat, pooled per month and capped at $500. They cover the Claude API (Claude Console only, not Bedrock, Google Cloud, Foundry or Claude Platform on AWS), Claude Managed Agents, the Claude Agent SDK and the playground -- **not Claude Code** or extra usage in the Claude apps -- and expire at the end of each billing cycle with no rollover. New subscribers can claim after 7 days; Free, Pro and Enterprise are not eligible. **Web search**: $10 per 1,000 searches plus token costs. **Web fetch**: free beyond token costs. **Code execution**: free with web search/fetch; otherwise 1,550 free hours/month then $0.05/hour per container. **Bash tool**: +325 input tokens on Opus 5 / 4.8 / 4.7 (+244 on Opus 4.6 and earlier). **Text editor tool**: +700 input tokens.

> **Minimum cacheable prompt is a real cost lever.** A `cache_control` block below the model's threshold is silently ignored -- you pay full input price every turn and see no error. Opus 5.5, Opus 5, Sonnet 5.5 and Haiku 5.5 all sit at **512 tokens**, half the 1,024 threshold of Opus 4.8 and Sonnet 5 and an eighth of Haiku 4.5's 4,096, so system prompts and CLAUDE.md files that never cached on those start caching on Opus 5.x, Sonnet 5.5 and Haiku 5.5. Haiku 4.5, Opus 4.6, and Opus 4.5, all now legacy, sit at 4,096, the worst floor in the lineup.
>
> **Opus 5.5 / 5 / 4.8 / 4.7 tokenizer caveat**: The tokenizer introduced with Opus 4.7 may use **up to 35% more tokens** for the same fixed text. Effective per-task cost is higher than posted pricing suggests -- factor this into budgets, especially when comparing against Opus 4.6 / Sonnet 4.6. Haiku 5.5 uses the same newer tokenizer: about **30% more tokens than Haiku 4.5** for the same text.
>
> **Fast Mode (research preview)**: Now **Opus 5.5, Opus 5 and Opus 4.8 only**, via the `fast-mode-2026-02-01` beta header (`speed: "fast"`). All three are **2x** their own base rate: **$8/$40 per MTok on Opus 5.5**, $10/$50 on Opus 5 and Opus 4.8. Up to 2.5x more output tokens/second; the speed gain is on output tokens/sec, not time-to-first-token. **Opus 4.7 now returns an error** on `speed: "fast"` with no fallback, and **Opus 4.6 silently runs at standard speed and standard rates** (`usage.speed` comes back `"standard"`) -- if you were paying 6x for Fast Mode on either, that option is gone. Claude API + Managed Agents only: not on Claude Platform on AWS, Bedrock, Vertex AI, Microsoft Foundry, Batch API, or Priority Tier. Switching speeds invalidates prompt cache. [Join the waitlist](https://claude.com/fast-mode).
>
> **Claude Code's `sonnet` alias depends on your provider**: it is Sonnet 5.5 only on the Anthropic API; on Bedrock, Google Cloud and Microsoft Foundry it resolves to Sonnet 4.5 ($3/$15, 200K context -- 1.5x the price of Sonnet 5.5 for a smaller window, and now deprecated), and on Claude Platform on AWS to Sonnet 4.6 ($3/$15, 1M). Pin it with `--model claude-sonnet-5-5` (Bedrock: `anthropic.claude-sonnet-5-5`) or `ANTHROPIC_DEFAULT_SONNET_MODEL`; Sonnet 5.5 needs Claude Code v2.1.284 or later. **The `haiku` alias works the same way**: Haiku 5.5 on the Anthropic API (Claude Code v2.1.293+), legacy Haiku 4.5 ($1/$5, 200K) on Claude Platform on AWS, Bedrock, Google Cloud and Foundry. Pin it with `ANTHROPIC_DEFAULT_HAIKU_MODEL`, which also sets the model for background functionality.
>
> **Fable 5 / Mythos 5** (GA 2026-06-09): Anthropic's Mythos-class tier above Opus, at **$10/$50** -- 2x legacy Opus 5's price and 2.5x Opus 5.5's. Same specs for both: 1M context at standard rates, 128K max output, always-on adaptive thinking (control depth with `effort`; `thinking: disabled` not supported), 4.7-generation tokenizer. **Fable 5 is GA everywhere** (Claude API, Claude Platform on AWS, Bedrock, Vertex AI, Microsoft Foundry) and includes safety classifiers that can decline requests -- a refusal returns HTTP 200 with `stop_reason: "refusal"`, **pre-output refusals are not billed**, and the beta `fallbacks` parameter plus fallback credit make retrying on another model cheap. **Mythos 5** is the same model without the classifiers, limited to approved [Project Glasswing](https://anthropic.com/glasswing) customers. No Fast Mode on either; Batch API supported ($5/$25). Requires 30-day data retention (no zero-data-retention option).
>
> **Mythos Preview**: superseded by Mythos 5 and **deprecated** -- still functional, no longer recommended, and no retirement date is published. The invite-only defensive-cybersecurity research preview under Project Glasswing.
>
> **Looking for older model IDs and pricing?** See the [Legacy & Retired Models](#legacy--retired-models) section below for migration context.

### Migrating to Opus 5.5

Opus 5.5 is 20% cheaper than Opus 5, but the bill does not simply fall 20%. These changes move it in both directions or break the request:

| Change | Why it matters for cost |
|--------|-------------------------|
| **$4/$20, cache hit $0.20** | Down from $5/$25 and $0.50. Cache hits are 0.05x base input (95% off) instead of 0.1x. Batch $2/$10, Fast Mode $8/$40. |
| **Thinking is always on** | `thinking: {type: "disabled"}` and `thinking: {type: "enabled", budget_tokens}` both return **400**. Code that disabled thinking on Opus 5 now pays for thinking tokens, billed as **output** at $20/1M, that it did not pay for before. |
| **Default effort drops to `medium`** | Opus 5 defaulted to `high`. A request that omits effort now thinks less than it did on Opus 5. Effort is the only depth control; all five levels are supported. |
| **Forced tool use returns 400** | `tool_choice` `any`/`tool` is rejected -- use `auto` plus strict tool use or structured outputs. The tool-use system prompt is 286 tokens. |
| **Sampling params and prefill return 400; no Priority Tier** | Non-default `temperature`/`top_p`/`top_k` and assistant prefill fail. Opus 4.8 keeps Priority Tier; Opus 5.5 has none. |
| **Thinking blocks are tied to the model and conversation** | Text between tool calls now comes back in `thinking` blocks (empty at the default display setting). On the Claude API and Google Cloud, `computer_20251124` is rejected -- use `computer_toolset_20260801`. |

Re-baseline cost after migrating rather than assuming the 20%: the lower rate pulls the bill down, and thinking you used to disable pushes it up. Audit your prompts at the same time -- in Anthropic's published runs, prompts written for Opus 4.8 cost 36% more per ticket on Opus 5 for no accuracy gain, and once audited they were 14% cheaper and more accurate ([cost and intelligence guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence)). Full details: [Anthropic's Opus 5.5 migration guide](https://platform.claude.com/docs/en/models/opus-5-5/migration-guide).

### Migrating to Sonnet 5.5

Sonnet 5.5 has Sonnet 5's $2/$10 and tokenizer, and since 2026-10-07 reads cache hits at half Sonnet 5's price, so the posted rate never goes up. Each change below either returns a 400 when Sonnet 5 code is carried over or shifts what you pay:

| Change | Why it matters for cost |
|--------|-------------------------|
| **Same $2/$10, same tokenizer, cheaper cache hits** | Cache hit **$0.10** (0.05x base input, 95% off; Sonnet 5: $0.20), 5m write $2.50, 1h write $4.00, Batch $1/$5. The same text gives the same token count, so migrating never costs more at the posted rate, and each 1M cached tokens saves $1.90 against uncached input instead of $1.80. No Fast Mode. |
| **Min cacheable prompt drops to 512 tokens** | Sonnet 5 needed 1,024, so short system prompts that never cached on Sonnet 5 now do. The tool-use system prompt is 286 tokens (Sonnet 5: 354), a small per-request input saving. |
| **Thinking is on by default and cannot be disabled** | Adaptive thinking is on at default effort `high`, and reasoning tokens bill as **output** at $10/1M. `thinking: {type: "disabled"}` and manual `budget_tokens` return **400**; the lowest setting is `thinking: {type: "between_tools"}`, which turns off up-front thinking and is accepted only at `low`, `medium` and `high` effort. |
| **Effort levels are recalibrated** | The same level does not produce the same amount of thinking as on Sonnet 5, so re-run your effort sweep instead of carrying a setting over. Anthropic's starting points: `high` in general, `medium` for well-specified agentic coding and multistep tool use. |
| **Forced tool use and sampling params return 400** | `tool_choice` `any`/`tool` is rejected -- use `auto` plus strict tool use or structured outputs. Non-default `temperature`/`top_p`/`top_k` fail. |
| **Thinking blocks are tied to the model and conversation** | Keep conversations append-only: replaying a Sonnet 5.5 thinking block after editing earlier history can return 400. On the Claude API and Google Cloud, `computer_20251124` is rejected -- use `computer_toolset_20260801`. The advisor tool rejects Opus 4.8, Opus 4.7 and Sonnet 5 as advisors for a Sonnet 5.5 executor. |
| **Tools and instructions can change mid-conversation** | Mid-conversation tool changes (beta), mid-conversation system messages and per-message effort (beta) work on Sonnet 5.5 and not on Sonnet 5, so changing them no longer costs you the prompt cache. |

Full details: [What's new in Sonnet 5.5](https://platform.claude.com/docs/en/models/sonnet-5-5/whats-new-sonnet-5-5).

### Migrating to Haiku 5.5

Haiku 5.5 replaces Haiku 4.5, now legacy, and is the first Claude model priced by prompt length. Each change below either moves what you pay or returns a 400 when Haiku 4.5 code is carried over:

| Change | Why it matters for cost |
|--------|-------------------------|
| **Two price tiers, split at 100K prompt tokens** | Up to 100,000 prompt tokens: $0.10/$0.50, cache hit $0.01, 5m write $0.125, 1h write $0.20, Batch $0.05/$0.25. Above: $0.50/$2.50, cache hit $0.05, 5m write $0.625, 1h write $1.00, Batch $0.25/$1.25. Prompt length counts every input token, cache reads and writes included, and each request is priced on its own: one over the line pays the higher input and output rates even when most of its prompt is a cache hit. A 100,000-token prompt costs $0.010 of input; a 100,001-token prompt costs $0.050 (5x). |
| **10x cheaper per token than Haiku 4.5 below 100K, 2x above** | The newer tokenizer turns the same text into ~30% more tokens, so per task that is roughly 7.7x cheaper below 100K (10 / 1.3) and ~1.5x above (2 / 1.3). Against Sonnet 5.5 it is 20x cheaper below 100K and 4x above; against Opus 5.5, 40x and 8x. |
| **1M context, 128K output, 512-token cache floor** | Haiku 4.5 was 200K / 64K with a 4,096 floor, so short system prompts that never cached on Haiku 4.5 now do. Batch output goes to 300K with `output-300k-2026-03-24`. The 1M window does not bill at one rate: everything past 100K prompt tokens pays the higher tier. |
| **Adaptive thinking is on by default** | Default effort is `medium`, and reasoning bills as output. On the API, `thinking: {type: "disabled"}` still works at `high` effort or below; in Claude Code you cannot turn thinking off on Haiku 5.5. Manual `budget_tokens` returns **400**. |
| **Sampling params and prefill return 400** | Non-default `temperature`/`top_p`/`top_k` and assistant prefill fail -- end `messages` with a user turn. Forced tool use still works; the tool-use system prompt is 286 tokens (`auto`/`none`) / 406 (`any`/`tool`). No Fast Mode. |
| **Thinking blocks are tied to the conversation** | Changing earlier turns invalidates thinking blocks, so keep conversations append-only. Responses can begin with `thinking` blocks -- select blocks by `type`. On the Claude API and Google Cloud, `computer_20250124` is rejected -- use `computer_toolset_20260801`. Safety classifiers can decline (`stop_reason: "refusal"`) with no server-side fallback. |

Keep Haiku prompts under 100K: short subagent, classification, extraction and routing calls are where Haiku 5.5 wins. Full details: [What's new in Haiku 5.5](https://platform.claude.com/docs/en/models/haiku-5-5/whats-new-haiku-5-5).

### Migrating to Opus 5

Opus 5 is now legacy; if you are moving off Opus 4.8 today, go straight to [Opus 5.5](#migrating-to-opus-55). The notes below still apply to anyone pinned on Opus 5. Opus 5 is the same price as Opus 4.8, but it is not a drop-in swap of the model string. Four things change your bill or break your request:

| Change | Why it matters for cost |
|--------|-------------------------|
| **Thinking is ON by default** | Omit `thinking` and Opus 5 thinks adaptively. Reasoning tokens bill as **output** at $25/1M, and `max_tokens` is a hard cap on thinking **plus** text -- an unchanged `max_tokens: 4096` now gets eaten by thinking before your answer is written. Raise it to 64K+ if you run `xhigh`/`max` effort. |
| **`thinking: {type: "disabled"}` is effort-gated** | Legal only at effort `high` or below. Pairing it with `xhigh` or `max` returns a **400**, so a config that worked on 4.8 can hard-fail. |
| **Min cacheable prompt drops to 512 tokens** | Prompts too short to cache on 4.8 (1,024) now cache on 5. Free savings if you re-check your `cache_control` placement. |
| **Cybersecurity classifiers ship on Opus 5** | Security-adjacent work can hit `stop_reason: "refusal"`. Set the server-side `fallbacks` param (beta `server-side-fallback-2026-07-01`) to auto-retry on Opus 4.8 inside the same call rather than paying for a failed round-trip. |

Two prompt-level cleanups worth doing at the same time: Opus 5 writes **longer** output than 4.8 by default, so re-tune your verbosity instructions; and it self-verifies, so any "double-check your work before answering" instruction you carried over from an older model is now paying twice for the same behavior. New beta `mid-conversation-tool-changes-2026-07-01` also lets you change tool definitions between turns without invalidating the prompt cache -- previously a cache-busting move.

Full details: [Anthropic's Opus 5 migration guide](https://platform.claude.com/docs/en/models/opus-5/migration-guide).

---

## Legacy & Retired Models

> Reference only -- **don't use these for new work.** Kept for migration context if you're unwinding code that still pins old model IDs.

**Recently retired** (requests now fail):

| Model | Retired on | Migrate to |
|-------|:----------:|-----------|
| Claude Opus 3 (`claude-3-opus-20240229`) | 2026-01-05 | Opus 5.5 |
| Claude Sonnet 3.7 (`claude-3-7-sonnet-20250219`) | 2026-02-19 | Sonnet 5.5 |
| Claude Haiku 3.5 (`claude-3-5-haiku-20241022`) | 2026-02-19 (still on Bedrock + Vertex AI) | Haiku 5.5 |
| Claude Haiku 3 (`claude-3-haiku-20240307`) | 2026-04-20 | Haiku 5.5 |
| Claude Sonnet 4 (`claude-sonnet-4-20250514`) | 2026-06-15 | Sonnet 5.5 |
| Claude Opus 4 (`claude-opus-4-20250514`) | 2026-06-15 | Opus 5.5 |
| Claude Opus 4.1 (`claude-opus-4-1-20250805`) | 2026-08-05 (still on Bedrock + Google Cloud) | Opus 5.5 |
| Claude Sonnet 3.5 v1 / v2, Sonnet 3, Claude 2.x, Claude 1.x, Instant 1.x | 2024-2025 | See deprecations page |

**Deprecated**: two models. Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`) was deprecated (announced 2026-09-30), with **retirement scheduled for 2026-11-30** on the Claude API -- migrate to Sonnet 5.5. Claude Mythos Preview (`claude-mythos-preview`) is still functional, no longer recommended, and Anthropic publishes **no retirement date** for it -- migrate to Mythos 5 (Glasswing). Every other model that has not retired reads **Active** -- Haiku 4.5 (now legacy, not deprecated) and Opus 4.5 included. Their published retirement dates are "not sooner than" dates; the nearest is Haiku 4.5, not sooner than 2026-10-15.

**Older snapshots still callable** (not retired, but not the headline tier):

| Snapshot | Pricing | Context | Earliest retirement | Why use |
|----------|:-------:|:-------:|:-------------------:|---------|
| Opus 5 | $5/$25 | 1M | 2027-07-24 | Previous flagship -- pin if you need thinking disabled or forced `tool_choice`, both of which Opus 5.5 rejects |
| Opus 4.8 | $5/$25 | 1M | 2027-05-28 | Older flagship -- pin if prompts are tuned to it, if you need thinking off at `xhigh`/`max` (Opus 5 rejects that combination), or if you need Priority Tier (Opus 5.5 has none). Also the fallback target for Opus 5 cyber refusals |
| Opus 4.7 | $5/$25 | 1M | 2027-04-16 | Pinned workloads. No Fast Mode -- `speed: "fast"` now errors |
| Opus 4.6 | $5/$25 | 1M | 2027-02-05 | Pinned workloads / older tokenizer. `speed: "fast"` silently runs standard |
| Opus 4.5 | $5/$25 | 200K | 2026-11-24 | Pinned workloads only |
| Sonnet 5 | $2/$10 | 1M | 2027-06-30 | Previous Sonnet flagship, same price as Sonnet 5.5 -- pin if you need thinking disabled or forced `tool_choice`, both of which Sonnet 5.5 rejects |
| Sonnet 4.6 | $3/$15 | 1M | 2027-02-17 | Pinned workloads -- migrate to Sonnet 5.5 |
| Sonnet 4.5 | $3/$15 | 200K | Scheduled for 2026-11-30 (deprecated) | Deprecated -- migrate to Sonnet 5.5. Still what the `sonnet` alias resolves to on Bedrock, Google Cloud and Foundry |
| Haiku 4.5 | $1/$5 | 200K | 2026-10-15 | Legacy -- Haiku 5.5 is 10x cheaper per token up to 100K prompt tokens. Still what the `haiku` alias resolves to on Claude Platform on AWS, Bedrock, Google Cloud and Foundry |

> Authoritative source: [platform.claude.com/docs/en/about-claude/model-deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations).
>
> The cheatsheet has a [more detailed legacy table](cheatsheet.md#legacy--retired-models-reference-only) including last-known pricing for every retired tier.

---

## Benchmarks & Case Studies

- [Task Comparison](benchmarks/task-comparison.md) -- same task, optimized vs not
- [Model Comparison](benchmarks/model-comparison.md) -- Opus vs Sonnet vs Haiku
- [Context Size Impact](benchmarks/context-size-impact.md) -- how CLAUDE.md size affects cost
- [Community Leaderboard](benchmarks/leaderboard.md) -- crowdsourced cost-per-task data
- [Case Studies](case-studies/README.md) -- submission template and format; no stories published yet, contributions welcome

---

## Community

- **[GitHub Discussions](https://github.com/Sagargupta16/claude-cost-optimizer/discussions)** -- ask questions, share strategies
- **[Contributing](CONTRIBUTING.md)** -- from starring the repo to building new skills
- **[Issue Templates](https://github.com/Sagargupta16/claude-cost-optimizer/issues/new/choose)** -- tips, benchmarks, case studies

### Complementary Projects

Stars read on GitHub 2026-09-28. The savings column is each project's **own claim**, not something this repo has measured; `--` means the project publishes no savings figure.

| Project | Stars | What It Does | Savings (project's own claim) |
|---------|:-----:|-------------|:-------:|
| [caveman](https://github.com/JuliusBrussee/caveman) | 108k | Brevity skill plus proxy -- strips filler from responses | Claims "cuts 65% of tokens" |
| [claude-mem](https://github.com/thedotmack/claude-mem) | 95k | Persistent compressed context across sessions | -- |
| [rtk](https://github.com/rtk-ai/rtk) | 82k | CLI proxy that compresses common dev-command output before Claude reads it | Claims "60-90%" on common dev commands |
| [claude-code-router](https://github.com/musistudio/claude-code-router) | 37k | Routes Claude Code requests across models | -- |
| [ccusage](https://github.com/ccusage/ccusage) | 18.7k | `npx ccusage` usage and cost reports from your local logs | -- |
| [Claude-Code-Usage-Monitor](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor) | 8.7k | Real-time usage monitor with predictions | -- |
| [claudetop](https://github.com/liorwn/claudetop) | 212 | htop-style cost and cache monitor | -- |

---

## FAQ

<details>
<summary>How much does Claude Code actually cost?</summary>

With Pro ($20/mo or $200/yr ≈ $16.67/mo with annual billing -- 17% off), Max 5x ($100/mo), or Max 20x ($200/mo), you get included usage. For enterprise deployments, Anthropic's own average is about **$13 per developer per active day** and **$150-250 per developer per month**, with 90% of users under $30 per active day ([Claude Code costs docs](https://code.claude.com/docs/en/costs)); run `/usage` in Claude Code to see your own session cost. Opus 5, 4.8, 4.7, and 4.6 at $5/$25 are 3x cheaper per token than Opus 4.1 ($15/$75), and Opus 5.5 at $4/$20 is cheaper still -- but the tokenizer introduced with Opus 4.7 (shared by Opus 5.5) can use up to 35% more tokens, so the effective gap for the $5/$25 models is closer to ~2x.
</details>

<details>
<summary>Does this apply to the Claude API too?</summary>

Context optimization, model selection, and prompt engineering apply to both. The skill and commands are Claude Code-specific.
</details>

<details>
<summary>Will optimization reduce output quality?</summary>

No. These strategies eliminate waste (duplicate context, unnecessary file reads, expensive models for simple tasks). Quality stays the same or improves -- less noise means better reasoning.
</details>

<details>
<summary>What's the biggest single change I can make?</summary>

Install cost-mode (`npx skills add Sagargupta16/claude-cost-optimizer`) and switch to Haiku for routine tasks. Combined: 50-70% savings.
</details>

---

## Star History

If this repo helped you save money, consider giving it a star!

<a href="https://www.star-history.com/?repos=Sagargupta16%2Fclaude-cost-optimizer&type=timeline&legend=bottom-right">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=Sagargupta16/claude-cost-optimizer&type=timeline&theme=dark&legend=bottom-right" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=Sagargupta16/claude-cost-optimizer&type=timeline&legend=bottom-right" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=Sagargupta16/claude-cost-optimizer&type=timeline&legend=bottom-right" />
 </picture>
</a>

---

## More AI Developer Tools

If you found this useful, check out my other AI/Claude tools:

| Project | Description |
|---------|-------------|
| [claude-code-recipes](https://github.com/Sagargupta16/claude-code-recipes) | 47 copy-paste recipes for Claude Code - commands, subagents, hooks, skills |
| [claude-skills](https://github.com/Sagargupta16/claude-skills) | Custom Claude Code plugin marketplace with dev-workflow, FARM stack, and more |
| [agent-recipes](https://github.com/Sagargupta16/agent-recipes) | AI agent workflows for real-world dev tasks - code review, testing, security |
| [ai-git-hooks](https://github.com/Sagargupta16/ai-git-hooks) | AI-powered git hooks - auto-review diffs, generate commit messages, security scanning |
| [mcp-toolkit](https://github.com/Sagargupta16/mcp-toolkit) | Production-ready middleware for MCP servers - auth, caching, rate limiting |

---

## License

[MIT](LICENSE) - use these strategies, templates, and tools however you want.
