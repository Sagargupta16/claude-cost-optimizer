# Claude Cost Optimizer

> **Save 40-70% on Claude Code costs** with proven strategies, real benchmarks, and copy-paste configs.

Claude Code is powerful — but costs add up fast. A single afternoon of heavy coding can burn through $20-50 in tokens. Most of this spend is **avoidable** with the right setup.

This repo is a collection of **battle-tested strategies** for reducing Claude Code costs without sacrificing quality. Every technique includes expected savings percentages based on real-world benchmarks.

---

## Quick Wins (Start Here)

Apply these 5 changes right now and cut costs immediately:

| # | Strategy | Expected Savings | Effort | Guide |
|---|----------|:----------------:|:------:|-------|
| 1 | **Keep CLAUDE.md under 150 lines** — every line loads on every turn | 10-20% | 5 min | [Context Optimization](guides/02-context-optimization.md) |
| 2 | **Use Haiku for simple tasks** (`--model haiku`) — 60x cheaper than Opus | 30-50% | 1 min | [Model Selection](guides/03-model-selection.md) |
| 3 | **Use Plan Mode before coding** — prevents wasted iterative cycles | 15-25% | 0 min | [Workflow Patterns](guides/04-workflow-patterns.md) |
| 4 | **Add `.claudeignore`** — stop Claude from reading `node_modules`, `dist`, lock files | 5-15% | 2 min | [Context Optimization](guides/02-context-optimization.md) |
| 5 | **Delegate to subagents** — isolate expensive searches from main context | 20-40% | 5 min | [Workflow Patterns](guides/04-workflow-patterns.md) |

> Combined impact: **40-70% reduction** in monthly Claude Code spend.

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

### Token Pricing (as of 2025)

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Context Window |
|-------|:---------------------:|:----------------------:|:--------------:|
| **Opus 4** | $15.00 | $75.00 | 200K |
| **Sonnet 4** | $3.00 | $15.00 | 200K |
| **Haiku 3.5** | $0.80 | $4.00 | 200K |

### What Counts as Tokens

```
Every Claude Code turn = Input Tokens + Output Tokens

Input Tokens (you pay for):
├── System prompt (Claude Code's built-in instructions)
├── CLAUDE.md file (loaded every turn)
├── Conversation history (grows with each turn)
├── File contents (from Read/Grep/Glob results)
├── Tool call results
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

Claude Code uses **prompt caching** to reduce costs. Cached input tokens cost 90% less. Content that stays the same between turns (like CLAUDE.md and system prompt) gets cached automatically.

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

With the Pro plan ($20/month or $100/month for Max), you get included usage. After that, costs depend on your model and token usage. Heavy users report $5-30/day without optimization. With optimization, most drop to $2-10/day.

### Does this apply to Claude API too?

Many strategies (context optimization, model selection, prompt engineering) apply to both Claude Code and the API. The templates and commands are Claude Code-specific.

### Will these optimizations reduce output quality?

No. The strategies focus on eliminating **waste** — duplicate context, unnecessary file reads, using expensive models for simple tasks. Quality stays the same or improves (because Claude has less noise to process).

### How do I track my spending?

Use the `/usage` command in Claude Code to see current session stats. For historical tracking, use our [Usage Analyzer](tools/usage-analyzer/README.md) tool.

### What's the biggest single change I can make?

Switch to **Haiku for routine tasks** (formatting, simple fixes, file lookups). It's 60x cheaper than Opus and handles 70% of common coding tasks well.

---

## Star History

If this repo helped you save money, consider giving it a star! It helps others find these resources.

---

## License

[MIT](LICENSE) — use these strategies, templates, and tools however you want.
