# Guide 03: Model Selection

> **The single highest-impact optimization.** Choosing the right model per task can reduce your Claude Code bill by 30-60% with zero loss in output quality.

Most developers default to the most capable model for everything. This is like hiring a senior architect to change a lightbulb. Claude Opus 4.6 is extraordinary — but for renaming a variable, it is a $25/M-output-token lightbulb-changer.

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

### Current Pricing (March 2026, per 1M tokens)

| Model | Input Cost | Output Cost | Cache Hit | Relative Cost | Context Window |
|-------|:----------:|:-----------:|:---------:|:-------------:|:--------------:|
| **Opus 4.6** | $5.00 | $25.00 | $0.50 | 1x (baseline) | 1M |
| **Sonnet 4.6** | $3.00 | $15.00 | $0.30 | ~1.67x cheaper | 1M |
| **Haiku 4.5** | $1.00 | $5.00 | $0.10 | 5x cheaper | 200K |

> **Note**: Opus 4.6 is now significantly more affordable than previous generations (down from $15/$75 to $5/$25). This narrows the gap between models, but smart model selection still yields meaningful savings.

### What These Numbers Mean in Practice

A typical Claude Code turn involves roughly **2,000-5,000 input tokens** and **500-3,000 output tokens**. Here is what a single turn costs across models:

| Scenario | Input Tokens | Output Tokens | Opus 4.6 | Sonnet 4.6 | Haiku 4.5 |
|----------|:------------:|:-------------:|:--------:|:----------:|:---------:|
| Quick fix (small) | 2,000 | 500 | $0.023 | $0.014 | $0.005 |
| Component creation (medium) | 5,000 | 2,000 | $0.075 | $0.045 | $0.015 |
| Architecture analysis (large) | 10,000 | 5,000 | $0.175 | $0.105 | $0.035 |
| Multi-file refactor (XL) | 20,000 | 10,000 | $0.350 | $0.210 | $0.070 |

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

Assume 50 tasks per day with an average cost of $0.10/task on Opus 4.6:

| Strategy | Daily Cost | Monthly Cost (22 days) | Savings |
|----------|:----------:|:----------------------:|:-------:|
| **All Opus 4.6** | $5.00 | $110.00 | — |
| **80/20 split** (Haiku/Sonnet for 80%) | $2.00 | $44.00 | **60%** |
| **Optimized split** (40/40/20) | $1.70 | $37.40 | **66%** |

With Opus 4.6's lower pricing, the absolute dollar savings are smaller than they used to be — but a 60-66% reduction still adds up fast across a team. Model selection remains the single biggest lever you have.

---

## Task Complexity Decision Tree

Use this decision tree to quickly decide which model to use:

```
START: What is the task?
│
├── Does it require understanding complex architecture or
│   reasoning about multi-file interactions?
│   ├── YES → Is it a planning/analysis task (no code output)?
│   │         ├── YES → Opus (plan mode)
│   │         └── NO  → Opus
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

### Complex Tasks: Use Opus 4.6

**Cost per task: $0.05-$0.50+**

Reserve Opus for tasks where deep reasoning, multi-file coordination, or architectural understanding provides genuine value. With Opus 4.6's more affordable pricing, the cost penalty for using it is smaller — but it is still ~1.67x more than Sonnet and 5x more than Haiku, so defaulting to it for every task is still wasteful.

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
  "model": "sonnet",
  "preferences": {
    "defaultModel": "sonnet"
  }
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

| | Haiku 4.5 | Sonnet 4.6 | Opus 4.6 |
|-|:---------:|:----------:|:--------:|
| Input tokens | ~3,000 | ~3,000 | ~3,000 |
| Output tokens | ~1,200 | ~1,200 | ~1,200 |
| **Cost** | **$0.009** | **$0.027** | **$0.045** |
| Quality | Identical | Identical | Identical |

**Verdict**: Haiku. Saves $0.036 per rename vs Opus. Over 10 renames/day, that is $0.36/day saved. The gap is narrower than it used to be with old Opus pricing, but Haiku is still 5x cheaper for tasks where quality is identical.

### Example 2: Write Unit Tests for a Service

**Task**: Write comprehensive unit tests for `PaymentService` (5 methods, ~200 lines).

| | Haiku 4.5 | Sonnet 4.6 | Opus 4.6 |
|-|:---------:|:----------:|:--------:|
| Input tokens | ~8,000 | ~8,000 | ~8,000 |
| Output tokens | ~4,000 | ~4,000 | ~4,000 |
| **Cost** | **$0.028** | **$0.084** | **$0.140** |
| Quality | Good (may miss edge cases) | Very good | Excellent (not worth 1.67x more) |

**Verdict**: Sonnet. Saves $0.056 vs Opus with negligible quality difference for standard test writing.

### Example 3: Debug a Race Condition

**Task**: Investigate and fix intermittent auth failures in a distributed system spanning 12 files.

| | Haiku 4.5 | Sonnet 4.6 | Opus 4.6 |
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

| | Haiku 4.5 | Sonnet 4.6 | Opus 4.6 |
|-|:---------:|:----------:|:--------:|
| Input tokens | ~6,000 | ~6,000 | ~6,000 |
| Output tokens | ~3,500 | ~3,500 | ~3,500 |
| **Cost** | **$0.024** | **$0.071** | **$0.118** |
| Quality | Adequate (follows patterns) | Good | Excellent (overkill) |

**Verdict**: Sonnet. Standard CRUD follows patterns that Sonnet handles well.

### Example 5: Plan a Database Migration

**Task**: Design the migration strategy from MongoDB to PostgreSQL for a 20-collection database with complex relationships.

| | Haiku 4.5 | Sonnet 4.6 | Opus 4.6 |
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

With Opus 4.6's more affordable pricing ($5/$25 vs the old $15/$75), this anti-pattern is less financially devastating than it used to be — but it is still wasteful:

**1. Quality is often identical across models for simple tasks.**

For formatting, renaming, import management, config changes, and other mechanical tasks, Haiku produces output that is indistinguishable from Opus. You are paying 5x more for the same result.

**2. The cost still compounds.**

```
Scenario: 50 tasks/day, 22 working days/month

All Opus 4.6: 50 tasks x $0.10 avg x 22 days = $110/month
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

OPUS 4.6 ($5/$25 per 1M tokens)
├── Architecture design and planning
├── Multi-file refactoring (5+ files)
├── Complex debugging (race conditions, memory leaks)
├── Performance optimization (N+1 queries, bottlenecks)
├── Security auditing
├── Migration planning
├── System integration design
└── Legacy code comprehension
```

---

## Next Steps

- Set Sonnet as your default model today
- Create 2-3 Haiku commands for your most common simple tasks
- Read [Guide 04: Workflow Patterns](04-workflow-patterns.md) for additional cost-saving strategies
- Use the [Token Estimator](../tools/token-estimator/README.md) to measure costs before and after switching models

---

*[Back to README](../README.md) | [Previous: Context Optimization](02-context-optimization.md) | [Next: Workflow Patterns](04-workflow-patterns.md)*
