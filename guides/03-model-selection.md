# Guide 03: Model Selection

> **The single highest-impact optimization.** Choosing the right model per task can reduce your Claude Code bill by 30-60% with zero loss in output quality.

Most developers default to the most capable model for everything. This is like hiring a senior architect to change a lightbulb. Claude Fable 5 is extraordinary — but for renaming a variable, it is a $50/M-output-token lightbulb-changer (and Opus 4.8 a $25 one). With the 4.7-generation tokenizer using up to 35% more tokens for the same text, the effective cost penalty for over-using top-tier models is even higher than posted pricing suggests.

---

## Table of Contents

- [Model Lineup and Pricing](#model-lineup-and-pricing)
- [The 80/20 Rule of Model Selection](#the-8020-rule-of-model-selection)
- [Task Complexity Decision Tree](#task-complexity-decision-tree)
- [Task Categories with Recommended Models](#task-categories-with-recommended-models)
- [How to Set the Model](#how-to-set-the-model)
- [Cost-Per-Task Examples](#cost-per-task-examples)
- [The Common Mistake: Opus for Everything](#the-common-mistake-opus-for-everything)
- [Advanced: Dynamic Model Routing](#advanced-dynamic-model-routing)
- [Quick Reference Card](#quick-reference-card)

---

## Model Lineup and Pricing

### Current Pricing (verified 2026-06-12, per 1M tokens)

| Model | Input Cost | Output Cost | Cache Hit | 5m Cache Write | 1h Cache Write | Relative Cost | Context Window | Max Output |
|-------|:----------:|:-----------:|:---------:|:--------------:|:--------------:|:-------------:|:--------------:|:----------:|
| **Fable 5** (most capable) | $10.00 | $50.00 | $1.00 | $12.50 | $20.00 | 2x baseline | 1M | 128K |
| **Opus 4.8** (Opus flagship) | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1x (baseline) | 1M | 128K |
| **Opus 4.7** | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1x (baseline) | 1M | 128K |
| **Opus 4.6** | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1x (baseline) | 1M | 128K |
| **Opus 4.5** | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1x (baseline) | 200K | 64K |
| **Opus 4.1** | $15.00 | $75.00 | $1.50 | $18.75 | $30.00 | 3x baseline | 200K | 32K |
| **Sonnet 5** (Sonnet flagship) | $3.00 | $15.00 | $0.30 | $3.75 | $6.00 | ~1.67x cheaper | 1M | 128K |
| **Sonnet 4.6** | $3.00 | $15.00 | $0.30 | $3.75 | $6.00 | ~1.67x cheaper | 1M | 64K |
| **Sonnet 4.5** | $3.00 | $15.00 | $0.30 | $3.75 | $6.00 | ~1.67x cheaper | 200K | 64K |
| **Haiku 4.5** | $1.00 | $5.00 | $0.10 | $1.25 | $2.00 | 5x cheaper | 200K | 64K |

> **Fable 5** (GA 2026-06-09): Anthropic's most capable widely released model -- a new Mythos-class tier **above** Opus at **$10/$50, 2x Opus 4.8**. 1M context at standard rates, 128K max output, always-on adaptive thinking (control depth with `effort`), Batch supported ($5/$25), no Fast Mode, 30-day data retention required. Safety classifiers can decline a request (HTTP 200 + `stop_reason: "refusal"`; pre-output refusals are free; beta `fallbacks` retries another model server-side). **Cost guidance**: reach for Fable 5 only when the task genuinely needs frontier-plus capability -- the hardest reasoning, the longest autonomous runs. For everything else Opus 4.8 at half the price is the efficient frontier. **Mythos 5** is the same model minus the classifiers, limited to approved [Project Glasswing](https://anthropic.com/glasswing) customers.
>
> **Two things to know about Opus 4.8**:
> 1. **Same pricing as Opus 4.7 / 4.6 / 4.5** ($5/$25) — no price premium for the upgrade.
> 2. **New tokenizer** (Opus 4.7 and later) uses up to **35% more tokens** for the same text. So the *effective* cost is higher than the posted rates. A task that cost $1.00 on Opus 4.6 may cost $1.10-$1.35 on Opus 4.8 for the same prompt and output.
>
> **Opus 4.7 status**: Previous-generation (legacy). Earliest retirement 2027-04-16. Same price as 4.8. **Both 4.8 and 4.7 support Fast Mode** (beta). Pick 4.7 if you have prompts pinned to that snapshot or already tuned against it.
>
> **Opus 4.6 status**: Active (legacy). Earliest retirement 2027-02-05. Same price as 4.8/4.7. Supports Fast Mode (beta), but **Opus 4.6 Fast Mode is deprecated** as of the 4.8 launch. Pick 4.6 if you want a stable snapshot or your prompts already perform well on it.
>
> **Opus 4.5 (200K-only)**: Active until at least 2026-11-24. Same price as 4.6/4.7/4.8 but smaller context window and no Fast Mode. Generally migrate to 4.8 unless your code is pinned to this snapshot.
>
> **Sonnet 5** (`claude-sonnet-5`, GA 2026-06-30): the current Sonnet flagship -- best combination of speed and intelligence, adaptive thinking (`effort` defaults to high on the Claude API and Claude Code), 1M context at standard rates, 128K max output, no Fast Mode. Uses the newer tokenizer (~30% more tokens for the same text). **Introductory pricing $2/$10 per MTok through 2026-08-31**, then standard **$3/$15** (table above shows standard rates). New default for most production work; Sonnet 4.6 is now legacy.
>
> **Sonnet 4.5 (200K-only)**: Active until at least 2026-09-29. Same price as Sonnet 4.6 but smaller context window. Migrate to Sonnet 5 if you need 1M.
>
> **Opus 4.1**: Still available at older pricing ($15/$75) — **3x more expensive** than current Opus tiers. Deprecated 2026-06-05, retires 2026-08-05. No reason to use it unless you have a specific compatibility need — migrate to 4.8.

> **Claude Mythos Preview** ([Project Glasswing](https://anthropic.com/glasswing)): superseded by Mythos 5 -- **retires 2026-06-30**. It was the invitation-only research preview ($25/$125) for defensive cybersecurity through Glasswing partners. Its successor Mythos 5 drops to $10/$50 (same as Fable 5) and remains Glasswing-only; the prediction that Mythos-class capabilities would reach a widely released model came true as **Fable 5**, which is GA for everyone.

### What These Numbers Mean in Practice

A typical Claude Code turn involves roughly **2,000-5,000 input tokens** and **500-3,000 output tokens**. Here is what a single turn costs across models:

| Scenario | Input Tokens | Output Tokens | Opus 4.8* | Sonnet 4.6 | Haiku 4.5 |
|----------|:------------:|:-------------:|:---------:|:----------:|:---------:|
| Quick fix (small) | 2,000 | 500 | $0.023 | $0.014 | $0.005 |
| Component creation (medium) | 5,000 | 2,000 | $0.075 | $0.045 | $0.015 |
| Architecture analysis (large) | 10,000 | 5,000 | $0.175 | $0.105 | $0.035 |
| Multi-file refactor (XL) | 20,000 | 10,000 | $0.350 | $0.210 | $0.070 |

> *Opus 4.8 costs shown at posted rate. Multiply by ~1.2-1.35 to account for the new tokenizer's higher token counts on the same text.

> **Key insight**: Output tokens cost 5x more than input tokens across all models. Tasks that generate a lot of code (scaffolding, boilerplate, test suites) are where model selection has the most impact.

### Prompt Caching and Real-World Costs

Claude Code uses prompt caching, which reduces the cost of repeated input tokens by 90%. After the first turn of a session, cached content (system prompt, CLAUDE.md, stable conversation history) costs far less. This means:

- **First turn** of a session is the most expensive
- **Subsequent turns** benefit heavily from caching
- **Model selection still matters** because output tokens are never cached, and output is where most cost accumulates in code-generation tasks

---

## The 80/20 Rule of Model Selection

> **80% of your Claude Code tasks can be handled by a cheaper model.** The remaining 20% genuinely benefit from Opus.

Here is a breakdown of a typical developer's daily Claude Code usage:

```
Typical daily task distribution:
├── 40%  Simple tasks (formatting, renames, lookups, simple edits)     → Haiku
├── 40%  Medium tasks (components, bug fixes, tests, docs)             → Sonnet
└── 20%  Complex tasks (architecture, multi-file refactors, debugging) → Opus
```

### Cost Impact of the 80/20 Rule

Assume 50 tasks per day with an average cost of $0.10/task on Opus 4.8:

| Strategy | Daily Cost | Monthly Cost (22 days) | Savings |
|----------|:----------:|:----------------------:|:-------:|
| **All Opus 4.8** | $5.00 | $110.00 | — |
| **80/20 split** (Haiku/Sonnet for 80%) | $2.00 | $44.00 | **60%** |
| **Optimized split** (40/40/20) | $1.70 | $37.40 | **66%** |

With Opus 4.8's same pricing as 4.7/4.6 ($5/$25), the absolute dollar savings are smaller than they used to be versus Opus 4.1 ($15/$75) — but a 60-66% reduction still adds up fast across a team. Model selection remains the single biggest lever you have, and the new tokenizer overhead makes it even more valuable to skip Opus when you don't need it.

---

## Task Complexity Decision Tree

Use this decision tree to quickly decide which model to use:

```
START: What is the task?
│
├── Does it require understanding complex architecture or
│   reasoning about multi-file interactions?
│   ├── YES → Is it a planning/analysis task (no code output)?
│   │         ├── YES → Opus 4.8 (plan mode)
│   │         └── NO  → Opus 4.8
│   └── NO ↓
│
├── Does it require generating new code with non-trivial logic?
│   ├── YES → Is the logic self-contained in 1-2 files?
│   │         ├── YES → Sonnet
│   │         └── NO  → Sonnet (consider Opus if > 5 files)
│   └── NO ↓
│
├── Is it a mechanical/repetitive change?
│   (formatting, renaming, simple find-replace, adding imports)
│   ├── YES → Haiku
│   └── NO ↓
│
├── Is it a lookup or question about the codebase?
│   ├── YES → Haiku (for simple questions) / Sonnet (for analysis)
│   └── NO ↓
│
└── Default → Sonnet (the safest general-purpose choice)
```

### The "Two Question" Shortcut

If the decision tree feels heavy, just ask two questions:

1. **Does this task require reasoning about how multiple components interact?** If yes: Opus. If no: continue.
2. **Does this task require generating non-trivial new logic?** If yes: Sonnet. If no: Haiku.

---

## Task Categories with Recommended Models

### Simple Tasks: Use Haiku 4.5

**Cost per task: $0.003-$0.02**

Haiku handles these tasks with the same quality as more expensive models. There is no benefit to using Sonnet or Opus here.

| Task | Example | Why Haiku Works |
|------|---------|-----------------|
| **Code formatting** | "Fix the indentation in `utils.py`" | Mechanical transformation, no reasoning needed |
| **Variable/function renaming** | "Rename `getData` to `fetchUserProfile`" | Simple find-and-replace with scope awareness |
| **Import management** | "Add missing imports to this file" | Pattern matching against existing code |
| **Simple type annotations** | "Add TypeScript types to these function params" | Inferring types from usage patterns |
| **Comment updates** | "Update the JSDoc for this function" | Reading function signature, writing description |
| **Config file changes** | "Add `cors: true` to the server config" | Small edits to structured files |
| **Git operations** | "Create a commit message for these changes" | Summarizing diffs |
| **File lookups** | "What files import from `utils/auth`?" | Grep-based search, no deep reasoning |
| **Simple error fixes** | "Fix this missing semicolon / closing bracket" | Syntax-level corrections |
| **Moving/copying files** | "Move `Header.tsx` to `components/layout/`" | File system operations with import updates |

**How to invoke**:
```bash
claude --model haiku "rename getUserData to fetchUserProfile in src/api/"
```

### Medium Tasks: Use Sonnet 4.6

**Cost per task: $0.02-$0.15**

Sonnet is the sweet spot for most development work. It handles logic, generates quality code, and understands context well.

| Task | Example | Why Sonnet Works |
|------|---------|------------------|
| **Component creation** | "Create a pagination component with prev/next" | Generates well-structured code with standard patterns |
| **Bug fixes** | "Fix the race condition in the auth flow" | Understands cause-and-effect in code, traces logic |
| **Test writing** | "Write unit tests for the CartService class" | Follows testing patterns, covers edge cases |
| **API endpoint creation** | "Add a PUT endpoint for updating user profiles" | Follows existing patterns in the codebase |
| **Database queries** | "Write a query to get users with expired subs" | Understands schema relationships |
| **Documentation** | "Write API docs for the payment module" | Reads code, generates structured documentation |
| **Code review** | "Review this PR diff for issues" | Identifies common anti-patterns and bugs |
| **Refactoring (single file)** | "Extract the validation logic into its own function" | Restructures code while preserving behavior |
| **Error handling** | "Add proper error handling to the API layer" | Understands failure modes, generates try/catch patterns |
| **State management** | "Add Redux slice for the notification feature" | Follows established state patterns in the project |

**How to invoke**:
```bash
claude --model sonnet "write unit tests for src/services/CartService.ts"
```

### Complex Tasks: Use Opus 4.8

**Cost per task: $0.05-$0.50+** (higher in practice due to 4.8's new tokenizer)

Reserve Opus for tasks where deep reasoning, multi-file coordination, or architectural understanding provides genuine value. With Opus 4.8's pricing at $5/$25 (same as 4.7/4.6, down from 4.1's $15/$75), the cost penalty for using it is smaller than it used to be — but it is still ~1.67x more than Sonnet and 5x more than Haiku at posted rates, and the new tokenizer adds another 20-35% of effective cost on top. Defaulting to Opus for every task remains wasteful.

**Why Opus 4.8 over 4.7**: Anthropic reports a step-change improvement in agentic coding. 4.8 also catches its own logical faults during planning, verifies outputs before reporting, and takes instructions more literally. For long autonomous runs (audit, multi-file refactor, migration), 4.8's self-verification often pays for itself by avoiding expensive retry loops.

**Thinking modes differ**:
- **Opus 4.8** uses **adaptive thinking** (no separate extended-thinking budget). Effort defaults to `high` on all surfaces (the Claude Code default was `xhigh` on 4.7).
- **Opus 4.7** uses **adaptive thinking** (no separate extended-thinking budget) plus an `xhigh` effort level.
- **Opus 4.6** uses **extended thinking** — you can configure a reasoning token budget.
- If you have prompts or harnesses tuned against extended thinking's explicit budget knobs, they won't carry over to 4.8.

**Benchmarks published by Anthropic for Opus 4.6** (the numbers were even higher for Mythos Preview, the tier that Fable 5 / Mythos 5 now succeed — included below for reference):

| Benchmark | Opus 4.6 | Mythos Preview (retired tier) |
|-----------|:--------:|:----------------------------:|
| SWE-bench Verified | 80.8% | 93.9% |
| SWE-bench Pro | 53.4% | 77.8% |
| Terminal-Bench 2.0 | 65.4% | 82.0% |
| CyberGym (vuln reproduction) | 66.6% | 83.1% |

> Mythos-class capability is now generally available as **Fable 5** ($10/$50). Anthropic has not published a per-benchmark scorecard for Fable 5 on these exact suites at the time of writing -- when official numbers land, this table should be extended.

| Task | Example | Why Opus Is Worth It |
|------|---------|----------------------|
| **Architecture design** | "Design the module structure for a plugin system" | Requires reasoning about abstractions, trade-offs, extensibility |
| **Multi-file refactoring** | "Migrate from REST to GraphQL across 15 files" | Needs to hold the full picture, coordinate changes, avoid breakage |
| **Complex debugging** | "Find why checkout fails intermittently under load" | Requires reasoning across multiple systems, race conditions, state |
| **Performance optimization** | "Identify and fix the N+1 queries in the API" | Needs to trace data flow through multiple layers |
| **Security auditing** | "Review the auth system for vulnerabilities" | Requires deep understanding of attack vectors, subtle bugs |
| **Migration planning** | "Plan the migration from Webpack to Vite" | Needs to understand build system internals, dependency implications |
| **Design pattern implementation** | "Implement CQRS for the order processing system" | Complex pattern with many interacting components |
| **System integration** | "Integrate Stripe webhooks with our event system" | Multiple systems, error handling, idempotency concerns |
| **Algorithm development** | "Implement a rate limiter with sliding window" | Algorithmic reasoning, edge cases, correctness proofs |
| **Legacy code understanding** | "Explain how the billing engine works end-to-end" | Reading and synthesizing across a large, undocumented codebase |

**How to invoke**:
```bash
claude --model opus "design a plugin architecture for our CLI tool"
```

**Want a specific Opus snapshot explicitly?** Use the dated/aliased ID:
- Opus 4.8: `--model claude-opus-4-8` (Anthropic API), `anthropic.claude-opus-4-8` (Bedrock Messages API), `us.anthropic.claude-opus-4-8` (Bedrock legacy InvokeModel/Converse)
- Opus 4.7: `--model claude-opus-4-7` (Anthropic API), `anthropic.claude-opus-4-7` (Bedrock)
- Opus 4.6: `--model claude-opus-4-6` (Anthropic API), `anthropic.claude-opus-4-6-v1` (Bedrock legacy InvokeModel/Converse)
- Opus 4.5: `--model claude-opus-4-5-20251101`
- Opus 4.1: `--model claude-opus-4-1-20250805`

The `opus` alias maps to 4.8 by default on current Claude Code releases.

---

## How to Set the Model

### Method 1: The `--model` Flag (Per-Task)

The most direct approach. Override the model for a single invocation:

```bash
# Use Haiku for a quick rename
claude --model haiku "rename processData to transformPayload in src/"

# Use Sonnet for a component
claude --model sonnet "create a modal dialog component"

# Use Opus for architecture work
claude --model opus "design the caching layer for our API"
```

**Best for**: Ad-hoc tasks where you know the complexity upfront.

### Method 2: Default Model in Settings (Session Default)

Set a default model in your Claude Code settings (`~/.claude/settings.json` or project-level `.claude/settings.json`):

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "model": "sonnet"
}
```

Then override with `--model` only when needed. This way, your baseline cost is Sonnet-level, and you opt into Opus explicitly.

**Best for**: Establishing a cost-efficient baseline across all sessions.

### Method 3: Command Frontmatter (Per-Command)

Define the model inside a Claude Code custom command (`.claude/commands/*.md`):

```markdown
---
model: haiku
---

Fix formatting issues in the files I specify. Do not change logic or behavior.
Only fix indentation, trailing whitespace, and missing newlines.
```

This ensures the command always uses the specified model regardless of your session default.

**Best for**: Repetitive tasks that should always use a specific model.

### Method 4: Subagent Model Configuration

When using the Task tool to delegate work to a subagent, the subagent uses its own model configuration. You can instruct the main agent to delegate specific tasks to cheaper subagents:

```
Use a subagent to find all files that import from 'utils/deprecated'.
The subagent should use Haiku since this is a simple search task.
```

You can also configure subagent model preferences in your CLAUDE.md:

```markdown
# Subagent Guidelines
- Use Haiku for: file searches, simple edits, formatting
- Use Sonnet for: code generation, test writing, bug fixes
- Use Opus only for: architecture decisions, complex multi-file work
```

**Best for**: Automated delegation where different subtasks have different complexity levels.

---

## Cost-Per-Task Examples

These are real-world estimates based on typical token usage patterns. All costs assume prompt caching is active (not the first turn of a session).

### Example 1: Rename a Function

**Task**: Rename `getUserData` to `fetchUserProfile` across 8 files.

| | Haiku 4.5 | Sonnet 4.6 | Opus 4.8 |
|-|:---------:|:----------:|:--------:|
| Input tokens | ~3,000 | ~3,000 | ~3,000 |
| Output tokens | ~1,200 | ~1,200 | ~1,200 |
| **Cost** | **$0.009** | **$0.027** | **$0.045** |
| Quality | Identical | Identical | Identical |

**Verdict**: Haiku. Saves $0.036 per rename vs Opus. Over 10 renames/day, that is $0.36/day saved. The gap is narrower than it used to be with old Opus pricing, but Haiku is still 5x cheaper for tasks where quality is identical.

### Example 2: Write Unit Tests for a Service

**Task**: Write comprehensive unit tests for `PaymentService` (5 methods, ~200 lines).

| | Haiku 4.5 | Sonnet 4.6 | Opus 4.8 |
|-|:---------:|:----------:|:--------:|
| Input tokens | ~8,000 | ~8,000 | ~8,000 |
| Output tokens | ~4,000 | ~4,000 | ~4,000 |
| **Cost** | **$0.028** | **$0.084** | **$0.140** |
| Quality | Good (may miss edge cases) | Very good | Excellent (not worth 1.67x more) |

**Verdict**: Sonnet. Saves $0.056 vs Opus with negligible quality difference for standard test writing.

### Example 3: Debug a Race Condition

**Task**: Investigate and fix intermittent auth failures in a distributed system spanning 12 files.

| | Haiku 4.5 | Sonnet 4.6 | Opus 4.8 |
|-|:---------:|:----------:|:--------:|
| Turns needed | ~15 (struggles) | ~8 | ~4 |
| Total input tokens | ~120,000 | ~80,000 | ~60,000 |
| Total output tokens | ~30,000 | ~25,000 | ~20,000 |
| **Total cost** | **$0.270** | **$0.615** | **$0.800** |
| Quality | Poor (likely fails) | Decent | High (finds root cause) |
| Time | 25 min | 15 min | 8 min |

**Verdict**: Opus. While the cost gap between Opus and Sonnet is now much narrower ($0.80 vs $0.615), Opus solves it in fewer turns and developer time saved justifies the modest premium.

### Example 4: Create a CRUD API Endpoint

**Task**: Add a new `/api/projects` endpoint with GET, POST, PUT, DELETE.

| | Haiku 4.5 | Sonnet 4.6 | Opus 4.8 |
|-|:---------:|:----------:|:--------:|
| Input tokens | ~6,000 | ~6,000 | ~6,000 |
| Output tokens | ~3,500 | ~3,500 | ~3,500 |
| **Cost** | **$0.024** | **$0.071** | **$0.118** |
| Quality | Adequate (follows patterns) | Good | Excellent (overkill) |

**Verdict**: Sonnet. Standard CRUD follows patterns that Sonnet handles well.

### Example 5: Plan a Database Migration

**Task**: Design the migration strategy from MongoDB to PostgreSQL for a 20-collection database with complex relationships.

| | Haiku 4.5 | Sonnet 4.6 | Opus 4.8 |
|-|:---------:|:----------:|:--------:|
| Input tokens | ~15,000 | ~15,000 | ~15,000 |
| Output tokens | ~8,000 | ~8,000 | ~8,000 |
| **Cost** | **$0.055** | **$0.165** | **$0.275** |
| Quality | Superficial plan | Good plan | Thorough, catches edge cases |

**Verdict**: Opus. Migration planning is high-stakes. A missed edge case can cost days of developer time. The extra $0.11 vs Sonnet is negligible compared to the cost of a botched migration.

---

## The Common Mistake: Opus for Everything

### The "Premium Default" Anti-Pattern

Many developers set Opus as their default model and never change it. Their reasoning: "I want the best output, and the cost is acceptable."

With Opus 4.8's pricing ($5/$25, unchanged from 4.7/4.6, down from 4.1's $15/$75), this anti-pattern is less financially devastating than it used to be — but it is still wasteful, and 4.8's new tokenizer (up to 35% more tokens per turn) quietly widens the gap back out:

**1. Quality is often identical across models for simple tasks.**

For formatting, renaming, import management, config changes, and other mechanical tasks, Haiku produces output that is indistinguishable from Opus. You are paying 5x more for the same result.

**2. The cost still compounds.**

```
Scenario: 50 tasks/day, 22 working days/month

All Opus 4.8: 50 tasks x $0.10 avg x 22 days = $110/month (+35% tokenizer = ~$148)
Smart split:  (20 x $0.005) + (20 x $0.03) + (10 x $0.10) x 22 = $37/month

Annual difference: $876
Team of 5 annual difference: $4,380
```

While the savings are more modest than they were at old Opus pricing, $4,380/year for a 5-person team is still worth capturing — especially since it requires no loss in output quality.

**3. More expensive does not mean faster for simple tasks.**

Opus does not rename a variable faster than Haiku. The latency is often higher because Opus generates more thorough (but unnecessary) reasoning for simple tasks.

### How to Break the Habit

1. **Set Sonnet as your default model.** This is the best general-purpose starting point.
2. **Create Haiku commands** for your most frequent simple tasks (formatting, renaming, lookups).
3. **Explicitly opt into Opus** with `--model opus` only when you are doing architecture, complex debugging, or multi-file planning.
4. **Review your usage weekly.** Look at which tasks used Opus and ask: "Did that task genuinely need Opus?"

---

## Advanced: Dynamic Model Routing

### CLAUDE.md-Based Routing Guidelines

Add model routing guidance to your CLAUDE.md so Claude Code itself helps you pick the right model when delegating to subagents:

```markdown
# Model Routing
When delegating subtasks:
- Haiku: file searches, grep operations, simple edits, formatting, git operations
- Sonnet: code generation, test writing, bug fixes, documentation, single-file refactors
- Opus: architecture decisions, multi-file refactors, complex debugging, security reviews
```

### Cost-Aware Command Library

Build a library of commands with pre-assigned models:

```
.claude/commands/
├── format.md          (model: haiku)
├── rename.md          (model: haiku)
├── find-usages.md     (model: haiku)
├── write-test.md      (model: sonnet)
├── fix-bug.md         (model: sonnet)
├── create-component.md (model: sonnet)
├── review-arch.md     (model: opus)
├── plan-refactor.md   (model: opus)
└── security-audit.md  (model: opus)
```

This way, model selection is built into your workflow. You do not have to think about it each time.

### The Escalation Pattern

Start with the cheapest model and escalate only if needed:

1. **Try Haiku first.** If the output is good, you are done.
2. **If Haiku struggles**, retry with Sonnet.
3. **If Sonnet struggles**, retry with Opus.

This sounds like it wastes tokens on failed attempts, but in practice, most tasks succeed on the first try with the cheaper model, and the few that need escalation still cost less overall than defaulting to Opus.

---

## Quick Reference Card

```
HAIKU 4.5 ($1/$5 per 1M tokens)
├── Formatting and linting fixes
├── Variable and function renaming
├── Import management
├── Config file edits
├── File searches and lookups
├── Git commit messages
├── Simple type annotations
└── Mechanical find-and-replace

SONNET 4.6 ($3/$15 per 1M tokens)
├── Component and module creation
├── Bug fixes (single file or simple multi-file)
├── Unit and integration test writing
├── API endpoint creation
├── Documentation generation
├── Code review
├── Single-file refactoring
└── Error handling implementation

OPUS 4.8 ($5/$25 per 1M tokens, +~35% tokenizer overhead)
├── Architecture design and planning
├── Multi-file refactoring (5+ files)
├── Complex debugging (race conditions, memory leaks)
├── Long autonomous agentic runs (self-verifies outputs)
├── Performance optimization (N+1 queries, bottlenecks)
├── Security auditing
├── Migration planning
├── System integration design
└── Legacy code comprehension

FABLE 5 ($10/$50 per 1M tokens -- 2x Opus, most capable widely released model)
├── The absolute hardest reasoning problems Opus 4.8 can't crack
├── The longest autonomous agentic runs (single turns can run many minutes)
├── Mythos-class capability without a Glasswing invitation
└── Note: always-on thinking, no Fast Mode, safety classifiers may refuse
    (pre-output refusals are free; use the beta fallbacks param to retry)

OPUS 4.7 ($5/$25 per 1M tokens -- previous-generation, also supports Fast Mode 6x)
└── Only if you have prompts pinned to that snapshot or already tuned against it

OPUS 4.6 ($5/$25 per 1M tokens -- legacy, Fast Mode 6x but deprecated)
└── Only if you have prompts tuned to the older tokenizer or want a stable snapshot

OPUS 4.8 FAST MODE ($10/$50 per 1M tokens -- 2x premium, beta, Claude API + Managed Agents only)
OPUS 4.7 / 4.6 FAST MODE ($30/$150 per 1M tokens -- 6x premium, beta; 4.6 deprecated)
└── Only when output latency directly impacts revenue / UX
    (live demos, real-time agentic loops, urgent debugging)
    NOT for routine interactive coding
```

---

## Next Steps

- Set Sonnet as your default model today
- Create 2-3 Haiku commands for your most common simple tasks
- Read [Guide 04: Workflow Patterns](04-workflow-patterns.md) for additional cost-saving strategies
- Use the [Token Estimator](../tools/token-estimator/README.md) to measure costs before and after switching models

---

*[Back to README](../README.md) | [Previous: Context Optimization](02-context-optimization.md) | [Next: Workflow Patterns](04-workflow-patterns.md)*
