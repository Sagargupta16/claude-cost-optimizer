# Claude Cost Optimizer

![GitHub stars](https://img.shields.io/github/stars/Sagargupta16/claude-cost-optimizer?style=flat-square)
![GitHub forks](https://img.shields.io/github/forks/Sagargupta16/claude-cost-optimizer?style=flat-square)
![License](https://img.shields.io/github/license/Sagargupta16/claude-cost-optimizer?style=flat-square)
![Last Commit](https://img.shields.io/github/last-commit/Sagargupta16/claude-cost-optimizer?style=flat-square)

> **Save 30-60% on Claude Code costs** with an installable skill, web tools, and 11 deep-dive guides.

## Install

**Claude Code (official plugin system):**

```bash
/plugin marketplace add Sagargupta16/claude-cost-optimizer
/plugin install cost-mode@sagargupta16-claude-cost-optimizer
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
# npx (any Node project)
npx -y @sagargupta16/claude-rate .

# curl one-shot (no Node, no install)
curl -sSL https://raw.githubusercontent.com/Sagargupta16/claude-cost-optimizer/main/tools/claude-rate/install.sh | sh -s -- .

# curl, persistent install
curl -sSL https://raw.githubusercontent.com/Sagargupta16/claude-cost-optimizer/main/tools/claude-rate/install.sh | sh -s -- --install
```

Add `--fix` to print copy-pasteable fix commands, `--strict` to fail CI when the grade drops below B, or `--json` for machine-readable output. See [tools/claude-rate/README.md](tools/claude-rate/README.md) for the full breakdown.

The local rater inspects things the web analyzer can't: real MCP server count from `.mcp.json`, hooks, `.claudeignore` coverage gaps vs files actually on disk, accidentally-committed secrets, and cost-mode skill installation status.

### Public repos -- web tools

No install needed -- use these in your browser for any public GitHub repo:

| Tool | What It Does |
|------|-------------|
| **[Repo Analyzer](https://sagargupta16.github.io/claude-cost-optimizer/analyzer)** | Paste a GitHub URL to get a cost audit, grade (A+ to F), and recommendations |
| **[Cost Calculator](https://sagargupta16.github.io/claude-cost-optimizer/calculator)** | Estimate monthly spend based on your model, sessions, and config |
| **[Badge Checker](https://sagargupta16.github.io/claude-cost-optimizer/badge)** | Score your setup and get a shields.io badge for your repo |

---

## Before vs After

Real project, 30-turn session, Opus 4.7:

```
BEFORE (no optimization):                 AFTER (5 minutes of setup):
  CLAUDE.md:        6,200 chars (truncated)  CLAUDE.md:        2,800 chars (under limit)
  .claudeignore:    missing                   .claudeignore:    12 patterns
  MCP servers:      6 active                  MCP servers:      2 active
  System prompt:    ~15,000 tokens/turn       System prompt:    ~5,500 tokens/turn
  Session cost:     $2.85                     Session cost:     $1.12
  Monthly (3x/day): $188.10                   Monthly (3x/day): $73.92

  Savings: $114.18/month (61%)
```

---

## Quick Start (5 Minutes, No Skill Needed)

Even without installing the skill, these 5 changes cut costs immediately:

| # | Strategy | Savings | Guide |
|---|----------|:-------:|-------|
| 1 | **Keep CLAUDE.md under 4,000 characters** -- content beyond 4K is silently truncated | 10-20% | [Context Optimization](guides/02-context-optimization.md) |
| 2 | **Use Haiku for simple tasks** (`--model haiku`) -- 5x cheaper than Opus | 20-40% | [Model Selection](guides/03-model-selection.md) |
| 3 | **Use Plan Mode before coding** -- prevents wasted iterative cycles | 15-25% | [Workflow Patterns](guides/04-workflow-patterns.md) |
| 4 | **Add `.claudeignore`** -- stop Claude from reading node_modules, dist, lock files | 5-15% | [Context Optimization](guides/02-context-optimization.md) |
| 5 | **Delegate to subagents** -- isolate expensive searches from main context | 20-40% | [Workflow Patterns](guides/04-workflow-patterns.md) |

Full walkthrough: **[Getting Started in 5 Minutes](guides/00-getting-started.md)**

---

## Skills Roadmap

cost-mode is the first skill. More are planned:

| Skill | Status | What It Does | Cost Impact |
|-------|:------:|-------------|:-----------:|
| **cost-mode** | Live | Concise responses, model routing suggestions, session awareness | 30-60% cost savings |
| **claudeignore-gen** | Planned | Auto-generates .claudeignore based on your project's tech stack | 5-15% input reduction |
| **context-compress** | Planned | Rewrites your CLAUDE.md to be shorter while keeping all essential info | 10-20% input reduction |
| **cache-optimizer** | Planned | Detects cache-busting patterns and suggests fixes to maximize prompt cache hits | 10-25% input reduction |
| **budget-guard** | Planned | Per-session and per-day spending limits with warnings before you blow past them | Prevents overspend |

Want to build one? Skills are just `SKILL.md` files -- see [CONTRIBUTING.md](CONTRIBUTING.md) and the [skills/cost-mode/](skills/cost-mode/) directory for the pattern.

---

## Guides

11 deep-dive guides covering every optimization area:

| Guide | What You'll Learn |
|-------|-------------------|
| [00 - Getting Started](guides/00-getting-started.md) | Zero to optimized in 5 minutes -- the essential setup |
| [01 - Understanding Costs](guides/01-understanding-costs.md) | How billing works, what costs the most, where money goes |
| [02 - Context Optimization](guides/02-context-optimization.md) | Reduce input tokens: CLAUDE.md, .claudeignore, file reads |
| [03 - Model Selection](guides/03-model-selection.md) | When to use Opus vs Sonnet vs Haiku (with decision tree) |
| [04 - Workflow Patterns](guides/04-workflow-patterns.md) | Plan mode, subagents, commands, batch operations |
| [05 - Team Budgeting](guides/05-team-budgeting.md) | Per-developer budgets, cost tracking, ROI calculation |
| [06 - Access Methods & Pricing](guides/06-access-methods-pricing.md) | Compare API vs Bedrock vs Vertex AI vs Claude Code pricing |
| [07 - MCP & Agent Cost Impact](guides/07-mcp-agent-costs.md) | MCP server overhead, subagent costs, Agent SDK patterns |
| [08 - Prompt Caching Deep Dive](guides/08-prompt-caching.md) | Cache mechanics, TTL economics, maximizing hit rates, ROI math |
| [09 - Subscription Plan Value](guides/09-subscription-value.md) | Choose the right plan, maximize allowance, upgrade/downgrade signals |
| [10 - Three-Tier Task Routing](guides/10-task-routing.md) | Skip the LLM for Tier 0 tasks, route cheap tasks to Haiku, save Opus for complex work |

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

7 tools for measuring, tracking, and reducing costs. [Full tools documentation](tools/README.md)

| Tool | What It Does |
|------|-------------|
| [Token Estimator](tools/token-estimator/) | Estimate token count and cost for any file |
| [Usage Analyzer](tools/usage-analyzer/) | Find cost hotspots across your sessions |
| [Badge Generator](tools/badge-generator/) | Grade your project config (A+ to F) from the CLI |
| [MCP Cost Server](tools/mcp-cost-server/) | In-session cost estimation via MCP |
| [VS Code Extension](tools/vscode-extension/) | Token count and cost in the status bar |
| [GitHub Action](tools/actions/claude-cost-audit/) | Automated cost audit on PRs |
| [Budget Hooks](hooks/) | Track tool calls, log costs, warn at thresholds |

---

## Pricing Reference (verified 2026-05-22)

| Model | Input / 1M | Output / 1M | Cache Hit / 1M | 5m Cache Write / 1M | 1h Cache Write / 1M | Context | Max Output |
|-------|:----------:|:-----------:|:---------------:|:-------------------:|:-------------------:|:-------:|:----------:|
| **Opus 4.7** (current) | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1M | 128K |
| Opus 4.6 | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1M | 128K |
| Opus 4.5 | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 200K | 64K |
| Opus 4.1 | $15.00 | $75.00 | $1.50 | $18.75 | $30.00 | 200K | 32K |
| Sonnet 4.6 | $3.00 | $15.00 | $0.30 | $3.75 | $6.00 | 1M | 64K |
| Sonnet 4.5 | $3.00 | $15.00 | $0.30 | $3.75 | $6.00 | 200K | 64K |
| Haiku 4.5 | $1.00 | $5.00 | $0.10 | $1.25 | $2.00 | 200K | 64K |
| Mythos Preview (invite-only, [Glasswing](https://anthropic.com/glasswing)) | $25.00 | $125.00 | $2.50 | $31.25 | $50.00 | 1M | -- |

**1M context** on Opus 4.7, Opus 4.6, and Sonnet 4.6 bills at **standard rates** across the full window (no long-context premium). **Batch API**: 50% off both input and output. **Fast Mode** (Opus 4.7 and 4.6, beta): 6x standard rates, up to 2.5x output tokens/sec. **Regional endpoints** (Bedrock / Vertex AI / Claude API `inference_geo: "us"` for 4.6+ models): +10%. **Subscriptions**: Pro $20/mo (or **$200/yr ≈ $16.67/mo**, ~17% off), Max 5x $100/mo, Max 20x $200/mo. **Web search**: $10 per 1,000 searches plus token costs. **Web fetch**: free beyond token costs. **Code execution**: free with web search/fetch; otherwise 1,550 free hours/month then $0.05/hour per container. **Bash tool**: +245 input tokens. **Text editor tool**: +700 input tokens.

> **Opus 4.7 tokenizer caveat**: The new tokenizer may use **up to 35% more tokens** for the same fixed text. Effective per-task cost is higher than posted pricing suggests — factor this into budgets, especially when comparing to Opus 4.6 / Sonnet 4.6.
>
> **Fast Mode (beta)**: Available on **both Opus 4.7 and Opus 4.6** via the `fast-mode-2026-02-01` beta header (`speed: "fast"`). 6x standard rates ($30/$150 per MTok). Up to 2.5x more output tokens/second; speed gain is on output tokens/sec, not time-to-first-token. Not available on Claude Platform on AWS, Batch API, or Priority Tier. Switching speeds invalidates prompt cache. [Join the waitlist](https://claude.com/fast-mode).
>
> **Mythos Preview**: Research preview for defensive cybersecurity (vulnerability discovery, binary analysis). Invite-only via Project Glasswing (AWS, Apple, Cisco, CrowdStrike, Google, JPMorganChase, Microsoft, NVIDIA, Palo Alto Networks, 40+ critical-infra orgs). Not a general-purpose dev model.
>
> **Looking for older model IDs and pricing?** See the [Legacy & Retired Models](#legacy--retired-models) section below for migration context.

---

## Legacy & Retired Models

> Reference only -- **don't use these for new work.** Kept for migration context if you're unwinding code that still pins old model IDs.

**Recently retired** (requests now fail):

| Model | Retired on | Migrate to |
|-------|:----------:|-----------|
| Claude Opus 3 (`claude-3-opus-20240229`) | 2026-01-05 | Opus 4.7 |
| Claude Sonnet 3.7 (`claude-3-7-sonnet-20250219`) | 2026-02-19 | Sonnet 4.6 |
| Claude Haiku 3.5 (`claude-3-5-haiku-20241022`) | 2026-02-19 (still on Bedrock + Vertex AI) | Haiku 4.5 |
| Claude Haiku 3 (`claude-3-haiku-20240307`) | 2026-04-20 | Haiku 4.5 |
| Claude Sonnet 3.5 v1 / v2, Sonnet 3, Claude 2.x, Claude 1.x, Instant 1.x | 2024-2025 | See deprecations page |

**Deprecated, retiring soon**:

| Model | Retirement date | Migrate to |
|-------|:---------------:|-----------|
| Claude Sonnet 4 (`claude-sonnet-4-20250514`) | **2026-06-15** | Sonnet 4.6 |
| Claude Opus 4 (`claude-opus-4-20250514`) | **2026-06-15** | Opus 4.7 |

**Older snapshots still callable** (not retired, but not the headline tier):

| Snapshot | Pricing | Context | Why use |
|----------|:-------:|:-------:|---------|
| Opus 4.5 | $5/$25 | 200K | Pinned workloads only |
| Opus 4.1 | $15/$75 | 200K | Compatibility only -- 3x more expensive |
| Sonnet 4.5 | $3/$15 | 200K | Pinned workloads only |

> Authoritative source: [platform.claude.com/docs/en/about-claude/model-deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations).
>
> The cheatsheet has a [more detailed legacy table](cheatsheet.md#legacy--retired-models-reference-only) including last-known pricing for every retired tier.

---

## Benchmarks & Case Studies

- [Task Comparison](benchmarks/task-comparison.md) -- same task, optimized vs not
- [Model Comparison](benchmarks/model-comparison.md) -- Opus vs Sonnet vs Haiku
- [Context Size Impact](benchmarks/context-size-impact.md) -- how CLAUDE.md size affects cost
- [Community Leaderboard](benchmarks/leaderboard.md) -- crowdsourced cost-per-task data
- [Case Studies](case-studies/README.md) -- real-world optimization stories

---

## Community

- **[GitHub Discussions](https://github.com/Sagargupta16/claude-cost-optimizer/discussions)** -- ask questions, share strategies
- **[Contributing](CONTRIBUTING.md)** -- from starring the repo to building new skills
- **[Issue Templates](https://github.com/Sagargupta16/claude-cost-optimizer/issues/new/choose)** -- tips, benchmarks, case studies

### Complementary Projects

| Project | What It Does | Savings |
|---------|-------------|:-------:|
| [caveman](https://github.com/JuliusBrussee/caveman) | Brevity skill -- strips filler from responses | 50-75% output |
| [claude-mem](https://github.com/thedotmack/claude-mem) | Compresses session context for handoff | Input reduction |
| [claudetop](https://github.com/liorwn/claudetop) | htop-style monitoring with cost tracking | Visibility |

---

## FAQ

<details>
<summary>How much does Claude Code actually cost?</summary>

With Pro ($20/mo or $200/yr ≈ $16.67/mo with annual billing — 17% off), Max 5x ($100/mo), or Max 20x ($200/mo), you get included usage. Heavy users report $3-15/day without optimization, $1-5/day with it. Opus 4.7 and Opus 4.6 at $5/$25 are 3x cheaper per token than Opus 4.1 ($15/$75) — but Opus 4.7's new tokenizer can use up to 35% more tokens, so the effective gap is closer to ~2x.
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
| [claude-code-recipes](https://github.com/Sagargupta16/claude-code-recipes) | 50+ copy-paste recipes for Claude Code - commands, subagents, hooks, skills |
| [claude-skills](https://github.com/Sagargupta16/claude-skills) | Custom Claude Code plugin marketplace with dev-workflow, FARM stack, and more |
| [agent-recipes](https://github.com/Sagargupta16/agent-recipes) | AI agent workflows for real-world dev tasks - code review, testing, security |
| [ai-git-hooks](https://github.com/Sagargupta16/ai-git-hooks) | AI-powered git hooks - auto-review diffs, generate commit messages, security scanning |
| [mcp-toolkit](https://github.com/Sagargupta16/mcp-toolkit) | Production-ready middleware for MCP servers - auth, caching, rate limiting |

---

## License

[MIT](LICENSE) - use these strategies, templates, and tools however you want.
