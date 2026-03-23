# Claude Cost Optimizer
[![Stars](https://img.shields.io/github/stars/Sagargupta16/claude-cost-optimizer?style=flat)](https://github.com/Sagargupta16/claude-cost-optimizer/stargazers) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![Last Updated](https://img.shields.io/badge/updated-March_2026-brightgreen)](https://github.com/Sagargupta16/claude-cost-optimizer/commits/main)

> **Save 30-60% on Claude Code costs** with proven strategies, real benchmarks, and copy-paste configs.

Claude Code is powerful — but costs add up fast. A single afternoon of heavy coding can burn through $20-50 in tokens. Most of this spend is **avoidable** with the right setup.

This repo is a collection of **battle-tested strategies** for reducing Claude Code costs without sacrificing quality. Every technique includes expected savings percentages based on real-world benchmarks.

---

## Quick Wins (Start Here)

Apply these 5 changes right now and cut costs immediately:

| # | Strategy | Expected Savings | Effort | Guide |
|---|----------|:----------------:|:------:|-------|
| 1 | **Keep CLAUDE.md under 150 lines** — every line loads on every turn | 10-20% | 5 min | [Context Optimization](guides/02-context-optimization.md) |
| 2 | **Use Haiku for simple tasks** (`--model haiku`) — 5x cheaper than Opus | 20-40% | 1 min | [Model Selection](guides/03-model-selection.md) |
| 3 | **Use Plan Mode before coding** — prevents wasted iterative cycles | 15-25% | 0 min | [Workflow Patterns](guides/04-workflow-patterns.md) |
| 4 | **Add `.claudeignore`** — stop Claude from reading `node_modules`, `dist`, lock files | 5-15% | 2 min | [Context Optimization](guides/02-context-optimization.md) |
| 5 | **Delegate to subagents** — isolate expensive searches from main context | 20-40% | 5 min | [Workflow Patterns](guides/04-workflow-patterns.md) |

> Combined impact: **30-60% reduction** in monthly Claude Code spend.

---

## Table of Contents

- [Quick Wins](#quick-wins-start-here)
- [How Claude Billing Works](#how-claude-billing-works)
- [Guides](#guides)
- [Benchmarks](#benchmarks)
- [Templates](#templates)
- [Tools](#tools)
- [Cheatsheet](#cheatsheet)
- [Contributing](#contributing)
- [FAQ](#faq)

---

## How Claude Billing Works

Understanding the billing model is the foundation of optimization.

### Token Pricing (as of March 2026)

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Cache Hit (per 1M) | Context Window | Max Output |
|-------|:---------------------:|:----------------------:|:-------------------:|:--------------:|:----------:|
| **Opus 4.6** | $5.00 | $25.00 | $0.50 | 1M | 128K |
| **Opus 4.6 (1M, >200K input)** | $10.00 (2x) | $37.50 (1.5x) | $1.00 | 1M | 128K |
| **Opus 4.6 Fast Mode** | $30.00 (6x) | $150.00 (6x) | -- | 1M (included) | 128K |
| **Sonnet 4.6** | $3.00 | $15.00 | $0.30 | 1M | 64K |
| **Haiku 4.5** | $1.00 | $5.00 | $0.10 | 200K | 64K |

> **New in 2.1+**: `--max-budget-usd <amount>` caps spending per session. `--fallback-model <model>` auto-switches to a cheaper model when the primary is overloaded.

> **Plans**: Pro $20/mo, Max 5x $100/mo, Max 20x $200/mo. **Batch API**: 50% discount. **Cache write**: 1.25x (5-min TTL), 2x (1-hour TTL).

### Off-Peak 2x Usage Events

Anthropic periodically runs promotional events that **double usage limits** during off-peak hours (e.g., "Spring Break for Claude Code" in March 2026). Watch the [Anthropic blog](https://www.anthropic.com/news) and Claude Code release notes for announcements.

During these events, **peak hours** (normal limits) are typically **8 AM - 2 PM ET** (5-11 AM PT). Everything outside that window + all weekends = **2x usage**.

| Time Zone | Peak (Normal Limits) | 2x Usage Window |
|-----------|---------------------|-----------------|
| US West (PT) | 5-11 AM | 11 AM - 5 AM + weekends |
| US East (ET) | 8 AM - 2 PM | 2 PM - 8 AM + weekends |
| UK (BST) | 1-7 PM | 7 PM - 1 PM + weekends |
| Central Europe (CET) | 2-8 PM | 8 PM - 2 PM + weekends |
| India (IST) | 6:30 PM - 12:30 AM | Entire workday is 2x |
| China/Singapore (SGT) | 9 PM - 3 AM | Entire workday is 2x |
| Japan/Korea (JST) | 10 PM - 4 AM | Entire workday is 2x |
| Australia (AEDT) | 12-6 AM | Entire workday is 2x |

> **Key insight**: If you're outside the US, your entire workday likely falls in the 2x window. Even US-based users get 2x from afternoon through night. Watch for these promotions -- they effectively halve your cost per unit of work.

### What Counts as Tokens

```
Every Claude Code turn = Input Tokens + Output Tokens

Input Tokens (you pay for):
├── System prompt (Claude Code's built-in instructions)
├── CLAUDE.md file (loaded every turn)
├── Conversation history (grows with each turn)
├── File contents (from Read/Grep/Glob results)
├── Tool call results
├── MCP server tool schemas (each server adds ~500-2000 tokens)
└── MCP server responses

Output Tokens (you pay more for):
├── Claude's text responses
├── Tool calls (Read, Edit, Bash, etc.)
├── Code generation
└── Plan mode analysis
```

### The Key Insight

> **Input tokens are charged every turn.** If your CLAUDE.md is 300 lines and you have 50 turns in a session, you're paying for those 300 lines x 50 times. Cutting it to 100 lines saves you 2/3 of that recurring cost.

### Prompt Caching

Claude Code uses **prompt caching** to reduce costs. Cached input tokens cost significantly less (e.g., $0.50/MTok vs $5.00/MTok on Opus 4.6 — a 90% discount). Content that stays the same between turns (like CLAUDE.md and system prompt) gets cached automatically.

**What this means**: The first turn is expensive, subsequent turns benefit from caching. Avoid breaking the cache by keeping stable content (CLAUDE.md, file reads) consistent between turns.

---

## Guides

Deep-dive guides for each optimization area:

| Guide | What You'll Learn |
|-------|-------------------|
| [01 - Understanding Costs](guides/01-understanding-costs.md) | How billing works, what costs the most, where money goes |
| [02 - Context Optimization](guides/02-context-optimization.md) | Reduce input tokens: CLAUDE.md, .claudeignore, file reads |
| [03 - Model Selection](guides/03-model-selection.md) | When to use Opus vs Sonnet vs Haiku (with decision tree) |
| [04 - Workflow Patterns](guides/04-workflow-patterns.md) | Plan mode, subagents, commands, batch operations |
| [05 - Team Budgeting](guides/05-team-budgeting.md) | Per-developer budgets, cost tracking, ROI calculation |
| [06 - Access Methods & Pricing](guides/06-access-methods-pricing.md) | Compare API vs Bedrock vs Vertex AI vs Claude Code pricing |
| [07 - MCP & Agent Cost Impact](guides/07-mcp-agent-costs.md) | MCP server overhead, subagent costs, Agent SDK patterns |

---

## Benchmarks

Real-world cost measurements for common development tasks:

| Benchmark | What's Compared |
|-----------|-----------------|
| [Task Comparison](benchmarks/task-comparison.md) | Same task with/without optimization — before vs after |
| [Model Comparison](benchmarks/model-comparison.md) | Opus vs Sonnet vs Haiku for different task types |
| [Context Size Impact](benchmarks/context-size-impact.md) | How CLAUDE.md size and file reads affect total cost |

> All benchmarks include methodology, raw numbers, and reproducible steps.

---

## Templates

Copy-paste configs that are already optimized. Drop these into your project:

### CLAUDE.md Templates

| Template | Lines | Best For | Link |
|----------|:-----:|----------|------|
| Minimal | <50 | Maximum savings, solo projects | [minimal.md](templates/CLAUDE.md/minimal.md) |
| Standard | ~100 | Balanced cost/quality | [standard.md](templates/CLAUDE.md/standard.md) |
| Comprehensive | ~150 | Full-featured, team projects | [comprehensive.md](templates/CLAUDE.md/comprehensive.md) |
| Monorepo | ~120 | Multi-package workspaces | [monorepo.md](templates/CLAUDE.md/monorepo.md) |

### Stack-Specific Templates

| Stack | Link |
|-------|------|
| React + Vite | [react-vite.md](templates/CLAUDE.md/by-stack/react-vite.md) |
| Next.js | [nextjs.md](templates/CLAUDE.md/by-stack/nextjs.md) |
| FastAPI + Python | [fastapi-python.md](templates/CLAUDE.md/by-stack/fastapi-python.md) |
| MERN Stack | [mern.md](templates/CLAUDE.md/by-stack/mern.md) |
| Terraform + AWS | [terraform-aws.md](templates/CLAUDE.md/by-stack/terraform-aws.md) |

### Settings Configs

| Config | Philosophy | Link |
|--------|-----------|------|
| Cost-Conscious | Aggressive savings, Haiku default | [cost-conscious.json](templates/settings/cost-conscious.json) |
| Balanced | Sonnet default, smart routing | [balanced.json](templates/settings/balanced.json) |
| Performance-First | Opus for complex, speed priority | [performance-first.json](templates/settings/performance-first.json) |

### Claude Commands

| Command | Purpose | Link |
|---------|---------|------|
| `/cost-check` | Check current session usage | [cost-check.md](templates/commands/cost-check.md) |
| `/budget-mode` | Force cost-conscious behavior | [budget-mode.md](templates/commands/budget-mode.md) |
| `/quick-fix` | Minimal-token bug fix | [quick-fix.md](templates/commands/quick-fix.md) |

---

## Tools

### Token Estimator

Estimate how many tokens a file or prompt will cost before sending it to Claude:

```bash
python tools/token-estimator/estimate.py path/to/file.py
# Output: ~1,247 tokens | Estimated cost: $0.004 (Sonnet input)

python tools/token-estimator/estimate.py path/to/CLAUDE.md --per-turn 50
# Output: ~890 tokens per turn | 50 turns = 44,500 tokens | $0.13 (Sonnet)
```

[Token Estimator Documentation](tools/token-estimator/README.md)

### Usage Analyzer

Analyze your Claude Code usage patterns to find cost hotspots:

```bash
python tools/usage-analyzer/analyze.py ~/.claude/projects/
# Output: Cost breakdown by project, session, and action type
```

[Usage Analyzer Documentation](tools/usage-analyzer/README.md)

---

## Cheatsheet

One-page reference: **[cheatsheet.md](cheatsheet.md)**

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

Ways to contribute:
- **Share a tip**: Open an issue using the [Tip Submission](.github/ISSUE_TEMPLATE/tip-submission.md) template
- **Add a benchmark**: Run a test and submit results using the [Benchmark Result](.github/ISSUE_TEMPLATE/benchmark-result.md) template
- **Add a template**: Submit a CLAUDE.md template for a new stack
- **Improve guides**: Fix errors, add examples, clarify explanations
- **Build a tool**: Add utilities that help track or reduce costs

---

## FAQ

### How much does Claude Code actually cost?

With the Pro plan ($20/mo), Max 5x ($100/mo), or Max 20x ($200/mo), you get included usage. After that, costs depend on your model and token usage. Heavy users report $3-15/day without optimization. With optimization, most drop to $1-5/day. Note that Opus 4.6 is now priced at $5/$25 — the same price Sonnet used to be — making top-tier model usage much more affordable.

### Does this apply to Claude API too?

Many strategies (context optimization, model selection, prompt engineering) apply to both Claude Code and the API. The templates and commands are Claude Code-specific.

### Will these optimizations reduce output quality?

No. The strategies focus on eliminating **waste** — duplicate context, unnecessary file reads, using expensive models for simple tasks. Quality stays the same or improves (because Claude has less noise to process).

### How do I track my spending?

Use the `/usage` command in Claude Code to see current session stats. For historical tracking, use our [Usage Analyzer](tools/usage-analyzer/README.md) tool.

### What's the biggest single change I can make?

Switch to **Haiku for routine tasks** (formatting, simple fixes, file lookups). It's 5x cheaper than Opus and handles 70% of common coding tasks well. With Opus 4.6 now at $5/$25 (the same price Sonnet used to be), even the top model is much more accessible — but Haiku at $1/$5 still adds up to meaningful savings at scale.

---

## Star History

If this repo helped you save money, consider giving it a star! It helps others find these resources.

---

## License

[MIT](LICENSE) — use these strategies, templates, and tools however you want.
