# Guide 10: Three-Tier Task Routing

> **The cheapest token is the one you never send.** Before reaching for Claude, ask: does this task actually need an LLM?

This guide introduces a three-tier routing framework that goes beyond model selection. The key insight: many common development tasks can be handled without an API call at all, and most of the rest don't need your most expensive model.

---

## The Three Tiers

```
Tier 0: No LLM needed          $0.000    <1ms
Tier 1: Haiku / Sonnet          $0.005    ~1s
Tier 2: Opus + multi-turn       $0.050    ~5s
```

Most developers operate entirely in Tier 2. Moving 30-50% of your tasks to Tier 0 or Tier 1 is where the biggest savings come from.

---

## Tier 0: Skip the LLM Entirely

These tasks have deterministic solutions. Using Claude for them is like using a calculator app to add 2+2 -- it works, but you're paying for the round trip.

### Tasks That Don't Need an LLM

| Task | Use Instead | Why |
|------|------------|-----|
| Format code | `prettier`, `black`, `gofmt`, `rustfmt` | Deterministic, zero cost |
| Lint fixes | `eslint --fix`, `ruff --fix` | Auto-fixable rules don't need reasoning |
| Sort imports | `isort`, `organize-imports-cli` | Alphabetical ordering is not AI |
| Remove unused imports | `autoflake`, `eslint --fix` | Static analysis is sufficient |
| Rename across files | `sed`, `ripgrep + sed`, IDE refactor | Find-and-replace, no reasoning needed |
| Convert var to const/let | `eslint --fix` with `prefer-const` | Mechanical transform |
| Add missing semicolons | Formatter config | Style enforcement, not intelligence |
| Generate .gitignore | `gitignore.io` or templates | Well-known patterns per stack |
| Check types | `tsc --noEmit`, `mypy`, `pyright` | Compilers catch type errors for free |
| Run tests | `pytest`, `jest`, `go test` | You don't need Claude to run tests |
| Git operations | `git` CLI directly | Commits, branches, rebases are deterministic |

### Implementing Tier 0 with Hooks

You can use Claude Code hooks to intercept tool calls and handle simple patterns without burning tokens. See the [model-routing hook example](#model-routing-hook) below.

### Implementing Tier 0 with Custom Commands

Create commands that use shell scripts instead of Claude reasoning:

```markdown
<!-- .claude/commands/format.md -->
Run these commands and report the output:
- `npx prettier --write "src/**/*.{ts,tsx}"`
- `npx eslint --fix "src/**/*.{ts,tsx}"`
Do not analyze the code yourself. Just run the tools and summarize what changed.
```

This uses Claude only as a command runner (minimal output tokens) rather than a code analyzer.

---

## Tier 1: Cheap Model for Simple Tasks

Tasks that need some reasoning but not deep analysis. Haiku at $1/$5 per 1M tokens handles these well.

### Tier 1 Tasks

| Task | Why Haiku works | Cost vs Opus |
|------|----------------|:------------:|
| Write a single unit test | Pattern-based, one file | 5x cheaper |
| Add error handling to a function | Wrap in try/catch, type errors | 5x cheaper |
| Write a docstring/JSDoc | Read function, describe it | 5x cheaper |
| Create a simple component | Boilerplate + props | 5x cheaper |
| Explain what a function does | Reading comprehension | 5x cheaper |
| Fix a typo in code | Find and replace with context | 5x cheaper |
| Add TypeScript types to JS | Mechanical inference | 5x cheaper |
| Generate a config file | Template with project-specific values | 5x cheaper |
| Write a commit message | Summarize a diff | 5x cheaper |
| Translate error message | Simple text transformation | 5x cheaper |

### How to Stay in Tier 1

Switch models before the task:

```
/model haiku
write tests for src/utils/parser.ts
```

Or use pre-assigned custom commands:

```markdown
<!-- .claude/commands/test.md -->
Write unit tests for $ARGUMENTS. Use the existing test patterns in this project.
Focus on edge cases and error paths. Keep tests concise.
```

Then delegate to haiku: `claude --model haiku -p "/test src/utils/parser.ts"`

---

## Tier 2: Full Power for Complex Work

Tasks that require deep reasoning, multi-file awareness, or architectural understanding. This is where Opus earns its cost.

### Tier 2 Tasks

| Task | Why Opus is worth it |
|------|---------------------|
| Debug a race condition | Needs to trace async flows across files |
| Plan a multi-file refactor | Must understand dependency graph |
| Security audit | Requires threat modeling, not just pattern matching |
| Architecture review | Needs to evaluate tradeoffs holistically |
| Migrate between frameworks | Must understand both old and new patterns |
| Fix a production incident | Needs to reason about state, timing, side effects |
| Optimize N+1 queries | Must trace data flow through layers |
| Design a new system | Requires weighing alternatives with context |

### When to Escalate from Tier 1 to Tier 2

Signs that you need to bump up:

- Haiku's output is wrong or incomplete
- The task touches 3+ files
- You need Claude to reason about tradeoffs (not just generate code)
- The task requires understanding code it hasn't read yet
- You're on your 3rd attempt at explaining what you want

Don't escalate preemptively. Try the cheaper model first -- it works more often than you'd expect.

---

## Decision Flowchart

```
Is the task deterministic?
(formatting, linting, sorting, renaming, git ops)
│
├── YES → Tier 0: Use a CLI tool. Cost: $0
│
└── NO → Does it need deep reasoning?
         (multi-file, architecture, debugging complex state)
         │
         ├── NO → Tier 1: Haiku ($1/$5) or Sonnet ($3/$15)
         │         Single file? Haiku.
         │         Multi-file but straightforward? Sonnet.
         │
         └── YES → Tier 2: Opus ($5/$25)
                   Use Plan Mode first to reduce wasted turns.
```

---

## Cost Impact: Real Numbers

A developer who runs 90 tasks/day (3 sessions x 30 turns):

| Routing Strategy | Distribution | Daily Cost | Monthly Cost |
|-----------------|:------------|:----------:|:------------:|
| **All Opus** | 100% Tier 2 | $8.55 | $188.10 |
| **Manual model switching** | 30% Haiku, 70% Opus | $6.27 | $137.94 |
| **Three-tier routing** | 20% Tier 0, 40% Tier 1, 40% Tier 2 | $3.76 | $82.72 |

**Savings with three-tier routing: $105/month (56%)**

The biggest win is Tier 0. Every task you handle with a CLI tool instead of an API call is effectively free.

---

## Model-Routing Hook

This hook logs a cost estimate for each tool call, helping you understand where tokens go. Add it to your hooks config to build awareness of your spending patterns.

```bash
#!/bin/bash
# hooks/cost-logger.sh
# Logs estimated cost per tool call to a session file.
# Use with PreToolUse hook to build cost awareness.

TOOL="${HOOK_TOOL_NAME:-unknown}"
LOG_DIR="${TMPDIR:-/tmp}/claude-cost-log"
mkdir -p "$LOG_DIR"
SESSION_LOG="$LOG_DIR/session-$(date +%Y%m%d).log"

# Estimate tokens by tool type
case "$TOOL" in
  Read|Glob|Grep)
    EST_INPUT=2000
    EST_OUTPUT=100
    ;;
  Edit|Write)
    EST_INPUT=3000
    EST_OUTPUT=1500
    ;;
  Bash)
    EST_INPUT=2000
    EST_OUTPUT=500
    ;;
  *)
    EST_INPUT=1000
    EST_OUTPUT=500
    ;;
esac

# Log the estimate (using Opus pricing as worst-case)
COST=$(echo "scale=4; ($EST_INPUT * 5 + $EST_OUTPUT * 25) / 1000000" | bc 2>/dev/null || echo "0.01")
echo "$(date +%H:%M:%S) $TOOL input:~${EST_INPUT} output:~${EST_OUTPUT} ~\$${COST}" >> "$SESSION_LOG"

# Count total calls this session
COUNT=$(wc -l < "$SESSION_LOG" 2>/dev/null || echo 0)

# Warn at thresholds
if [ "$COUNT" -eq 50 ]; then
  echo '{"result": "50 tool calls this session. Consider starting fresh if switching tasks."}'
elif [ "$COUNT" -eq 100 ]; then
  echo '{"result": "100 tool calls. Session history is getting expensive. Run /compact or start new session."}'
fi

exit 0
```

### Hook Configuration

Add to your `settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": ".*",
        "hooks": ["bash hooks/cost-logger.sh"]
      }
    ]
  }
}
```

### Reading the Log

After a session, review where your tokens went:

```bash
cat /tmp/claude-cost-log/session-$(date +%Y%m%d).log
# 09:15:23 Read input:~2000 output:~100 ~$0.0125
# 09:15:25 Edit input:~3000 output:~1500 ~$0.0525
# 09:15:30 Bash input:~2000 output:~500 ~$0.0225
# ...
```

This builds intuition for which operations are cheap vs expensive, helping you naturally shift toward lower tiers.

---

## Quick Reference

```
TIER 0 -- $0 (skip the LLM)
├── Formatting:    prettier, black, gofmt
├── Linting:       eslint --fix, ruff --fix
├── Imports:       isort, organize-imports
├── Renaming:      sed, IDE refactor
├── Type checking: tsc, mypy, pyright
├── Tests:         jest, pytest (just running them)
└── Git:           commit, branch, rebase

TIER 1 -- Haiku $1/$5 or Sonnet $3/$15
├── Single unit test writing
├── Docstrings and comments
├── Simple component creation
├── Error handling addition
├── Config file generation
├── Type annotation addition
└── Code explanation

TIER 2 -- Opus $5/$25
├── Architecture design
├── Multi-file refactoring
├── Complex debugging
├── Security auditing
├── Performance optimization
├── Framework migration
└── System design
```

---

## Further Reading

- [Guide 03: Model Selection](03-model-selection.md) -- detailed model comparison and per-task cost tables
- [Guide 04: Workflow Patterns](04-workflow-patterns.md) -- plan mode, subagents, and session management
- [Hooks Documentation](../hooks/README.md) -- full hook system reference
- [Cheatsheet](../cheatsheet.md) -- one-page quick reference
