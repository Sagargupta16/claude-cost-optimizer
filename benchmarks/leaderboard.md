# Community Benchmark Leaderboard

> Real-world cost data submitted by the community. Submit your own results using the [leaderboard entry template](../.github/ISSUE_TEMPLATE/leaderboard-entry.md).

## How to Read This Table

- **Cost** is the estimated total session cost for completing the task
- **Tokens** is total tokens (input + output) consumed
- **Optimizations** lists the techniques applied
- All costs use April 2026 pricing (Opus 4.7 and 4.6 at $5/$25, Sonnet 4.6 at $3/$15, Haiku 4.5 at $1/$5 per MTok). Entries labeled "Opus 4.6" were measured before Opus 4.7 launched (2026-04-16); 4.7 should produce similar cost ranges, with ~20-35% higher token counts due to its new tokenizer.

---

## Component Creation

| Task | Model | Turns | Tokens | Cost | Optimizations | Submitted By |
|------|-------|:-----:|:------:|:----:|---------------|:------------:|
| React form with validation (150 LOC) | Sonnet 4.6 | 8 | 45,000 | $0.18 | Plan mode, focused prompt | @maintainer |
| React dashboard with charts (400 LOC) | Sonnet 4.6 | 15 | 120,000 | $0.54 | Subagent for research, batch edits | @maintainer |
| DataTable with sortable columns and pagination (250 LOC) | Sonnet 4.6 | 4 | 52,100 | $0.33 | Trimmed CLAUDE.md (~100 lines), plan mode | @maintainer |

## Bug Fixing

| Task | Model | Turns | Tokens | Cost | Optimizations | Submitted By |
|------|-------|:-----:|:------:|:----:|---------------|:------------:|
| Search filter state reset on navigation (Zustand) | Sonnet 4.6 | 5 | 69,400 | $0.29 | Plan mode (investigate before editing) | @maintainer |
| N+1 query in dashboard API route | Opus 4.6 | 4 | 77,800 | $0.58 | Plan mode, targeted file reads | @maintainer |
| Slow dashboard load -- re-render + N+1 query | Sonnet 4.6 | 6 | 98,200 | $0.44 | Plan mode, one nudge for secondary cause | @maintainer |

## Test Writing

| Task | Model | Turns | Tokens | Cost | Optimizations | Submitted By |
|------|-------|:-----:|:------:|:----:|---------------|:------------:|
| Unit tests for PaymentProcessor (4 flows) | Sonnet 4.6 | 6 | 61,000 | $0.42 | Subagent delegation, conventions in prompt | @maintainer |
| Integration tests for REST API (8 endpoints) | Sonnet 4.6 | 10 | 95,000 | $0.51 | Subagent per endpoint group, shared fixture prompt | @maintainer |

## Refactoring

| Task | Model | Turns | Tokens | Cost | Optimizations | Submitted By |
|------|-------|:-----:|:------:|:----:|---------------|:------------:|
| Split 800-line UserService into 4 modules | Sonnet 4.6 | 12 | 141,200 | $0.85 | Plan mode + subagents + commands | @maintainer |
| Extract shared validation logic into utils (6 files) | Haiku 4.5 | 5 | 48,000 | $0.07 | Mechanical extraction, Haiku for simple moves | @maintainer |
| Migrate class components to hooks (3 components) | Sonnet 4.6 | 8 | 78,000 | $0.38 | Plan mode, one component per subagent | @maintainer |

## Code Review

| Task | Model | Turns | Tokens | Cost | Optimizations | Submitted By |
|------|-------|:-----:|:------:|:----:|---------------|:------------:|
| Review 200-line caching layer PR | Opus 4.6 | 2 | 43,000 | $0.34 | Single-pass review, security focus | @maintainer |
| Review 200-line caching layer PR | Sonnet 4.6 | 2 | 42,200 | $0.19 | Single-pass review | @maintainer |
| Review 150-line auth middleware PR | Sonnet 4.6 | 3 | 52,000 | $0.24 | Plan mode for threat modeling first | @maintainer |

---

## Contributing

To submit your own benchmark:

1. Open a new issue using the [Leaderboard Entry](../.github/ISSUE_TEMPLATE/leaderboard-entry.md) template.
2. Fill in your task details, token counts, and cost.
3. A maintainer will verify and add your entry to the table.

### Guidelines

- Use `/usage` in Claude Code to get accurate token counts.
- Calculate costs from the [pricing table](model-comparison.md#pricing-reference).
- Be specific about the task -- "React component" is too vague; "React form with validation (150 LOC)" is useful.
- Note which optimizations you applied so others can replicate your results.
