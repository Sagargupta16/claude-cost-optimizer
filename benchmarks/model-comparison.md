# Model Comparison Benchmarks

> Opus 4.7 vs Sonnet 4.6 vs Haiku 4.5 across five common task types. Find the best cost-to-quality ratio for each kind of work.

## Pricing Reference

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Relative Cost |
|-------|:---------------------:|:----------------------:|:-------------:|
| Opus 4.7 (current) | $5.00 | $25.00 | 1x (baseline) |
| Opus 4.6 (legacy) | $5.00 | $25.00 | 1x (baseline) |
| Sonnet 4.6 | $3.00 | $15.00 | ~1.7x cheaper |
| Haiku 4.5 | $1.00 | $5.00 | 5x cheaper |

> **Historical note**: The numbers in the task-type sections below were measured on Opus 4.6. On Opus 4.7, expect ~20-35% higher token counts for identical prompts (new tokenizer), which translates to 20-35% higher absolute costs for the same task. Quality is generally better on 4.7 — Anthropic reports a step-change improvement in agentic coding. Fresh benchmark runs with 4.7 are welcome contributions.

## How to Read This

Each task type was performed with all three models under the same conditions:

- Same codebase (React + TypeScript, ~50 files)
- Same CLAUDE.md (Standard template, ~100 lines, ~700 tokens)
- Same prompt wording
- Quality rated 1-5 (5 = perfect, no follow-ups needed; 1 = unusable or required complete redo)

**Recommendation key:**
- **Best Value** — the model with the best quality-per-dollar ratio for this task type
- **Best Quality** — the model that produces the best output regardless of cost
- **Avoid** — the model is not a good fit for this task type

---

## Task Type 1: Simple Formatting and Renaming

**Task**: Rename the variable `userData` to `userProfile` across 8 files, update all imports, and fix a minor indentation inconsistency in 3 files.

| Metric | Opus (4.6 measured) | Sonnet 4.6 | Haiku 4.5 |
|--------|:------:|:--------:|:---------:|
| Turns to complete | 2 | 2 | 2 |
| Input tokens (total) | 24,200 | 24,200 | 24,200 |
| Output tokens (total) | 3,800 | 3,900 | 4,100 |
| **Estimated cost** | **$0.22** | **$0.13** | **$0.05** |
| Quality (1-5) | 5 | 5 | 5 |
| Follow-ups needed | 0 | 0 | 0 |

### Analysis

All three models handle mechanical refactoring equally well. Token counts are nearly identical because the task is straightforward — there is no complex reasoning to differentiate the models.

| | Recommendation |
|---------|----------------|
| **Best Value** | Haiku 4.5 — 5x cheaper than Opus, identical quality |
| **Best Quality** | Tie — all models score 5/5 |
| **Avoid** | Opus 4.7 — paying $0.22 for a task Haiku does for $0.05 is wasteful |

> **Rule of thumb**: If a task can be described as "find X, replace with Y" or "apply this mechanical change," Haiku is always the right choice.

---

## Task Type 2: Component Creation

**Task**: Create a new `DataTable` component with sortable columns, pagination, loading skeleton, empty state, and TypeScript generics for row data. Include CSS modules and prop documentation.

| Metric | Opus (4.6 measured) | Sonnet 4.6 | Haiku 4.5 |
|--------|:------:|:--------:|:---------:|
| Turns to complete | 3 | 4 | 7 |
| Input tokens (total) | 48,600 | 52,100 | 71,400 |
| Output tokens (total) | 12,800 | 11,400 | 14,200 |
| **Estimated cost** | **$0.56** | **$0.33** | **$0.14** |
| Quality (1-5) | 5 | 4 | 3 |
| Follow-ups needed | 0 | 1 (minor type fix) | 3 (generic types wrong, pagination logic off, missing loading state) |

### Analysis

This task involves moderate complexity — TypeScript generics, multiple interactive states, and integration with project patterns. The models diverge clearly.

- **Opus** gets generics right on the first try and produces well-structured code with thoughtful edge case handling. Zero follow-ups.
- **Sonnet** produces good code but makes a minor TypeScript error in the generic constraint (`extends object` instead of the project's `extends Record<string, unknown>` convention). One quick follow-up.
- **Haiku** struggles with TypeScript generics, produces a simpler pagination implementation that does not handle edge cases (page count of 0, single-page data sets), and omits the loading skeleton. Three follow-up turns inflate its total token count, eroding some of the per-token cost advantage.

| | Recommendation |
|---------|----------------|
| **Best Value** | Sonnet 4.6 — 1.7x cheaper than Opus, nearly equal quality (4/5), one minor fix |
| **Best Quality** | Opus 4.7 — perfect output, zero iterations needed |
| **Avoid** | Haiku 4.5 for complex components — follow-up turns erode cost savings and quality suffers |

> **Rule of thumb**: For components with complex types, state logic, or multiple interaction patterns, Sonnet is the sweet spot. Use Opus when the cost of getting it wrong (rework time) exceeds the $0.23 premium.

---

## Task Type 3: Bug Investigation

**Task**: Users report that the dashboard loads slowly after login. The developer suspects an N+1 query or unnecessary re-renders. Investigate, identify the root cause, and propose a fix.

| Metric | Opus (4.6 measured) | Sonnet 4.6 | Haiku 4.5 |
|--------|:------:|:--------:|:---------:|
| Turns to complete | 4 | 6 | 9 |
| Input tokens (total) | 68,200 | 86,400 | 112,500 |
| Output tokens (total) | 9,600 | 11,800 | 15,200 |
| **Estimated cost** | **$0.58** | **$0.44** | **$0.19** |
| Quality (1-5) | 5 | 4 | 2 |
| Follow-ups needed | 0 | 1 (missed secondary cause) | 4 (chased wrong hypothesis twice) |

### Analysis

Bug investigation is where model intelligence matters most. The task requires reading code, forming hypotheses, and narrowing down from multiple potential causes.

- **Opus** reads the dashboard component, the data fetching hook, and the API route, then correctly identifies both causes: (1) an N+1 query in the API route where user preferences are fetched per-item, and (2) an unnecessary `useEffect` re-render triggered by an unstable object reference. Four focused turns, no wasted investigation.
- **Sonnet** identifies the N+1 query but misses the re-render issue initially. After the developer confirms the N+1 fix helps but does not fully resolve the slowness, Sonnet investigates further and finds the re-render problem. Good result, slightly more turns.
- **Haiku** fixates on the wrong hypothesis twice — first suspects a missing `useMemo`, then suspects a slow CSS animation — before the developer manually steers it toward the data fetching layer. Even then, it identifies only the N+1 query and misses the re-render issue entirely. Low quality output for a debugging task.

| | Recommendation |
|---------|----------------|
| **Best Value** | Sonnet 4.6 — finds the primary issue quickly, reasonable cost, acceptable that it needs a nudge for the secondary issue |
| **Best Quality** | Opus 4.7 — finds both causes in a single investigation pass |
| **Avoid** | Haiku 4.5 for debugging — low accuracy means more developer time spent steering, which defeats the purpose |

> **Rule of thumb**: For bug investigation, model intelligence directly translates to fewer turns and better hypotheses. Opus pays for itself if the bug is complex. Sonnet is good for straightforward bugs. Haiku is only suitable for "the error message tells you exactly what's wrong" situations.

---

## Task Type 4: Architecture Planning

**Task**: Design the data model and API structure for a new "Teams" feature — team creation, member management, role-based permissions, and invitation flow. Output a plan with entity schemas, API endpoints, and migration strategy.

| Metric | Opus (4.6 measured) | Sonnet 4.6 | Haiku 4.5 |
|--------|:------:|:--------:|:---------:|
| Turns to complete | 3 | 4 | 6 |
| Input tokens (total) | 52,400 | 58,100 | 74,800 |
| Output tokens (total) | 14,800 | 12,600 | 10,200 |
| **Estimated cost** | **$0.63** | **$0.36** | **$0.13** |
| Quality (1-5) | 5 | 4 | 2 |
| Follow-ups needed | 0 | 1 (edge case in permission model) | 3 (missing invitation flow, weak permission model, no migration strategy) |

### Analysis

Architecture planning requires the model to reason about system design, anticipate edge cases, and produce a coherent plan that holds together across multiple concerns.

- **Opus** produces a comprehensive plan covering: entity schemas with proper foreign keys and indexes, RESTful API endpoints with authentication middleware, a role-permission matrix with inheritance, the full invitation flow (create, send email, accept, expire), and a 3-step migration strategy that handles existing users. The plan addresses edge cases like "what happens if a user is invited to a team they already belong to" and "how to handle the last admin leaving a team."
- **Sonnet** covers all major areas but uses a flat permission model (role string) instead of a flexible permission matrix. After one follow-up asking about granular permissions, it revises to a proper RBAC design. Migration strategy is solid. Missing the "last admin" edge case.
- **Haiku** provides a minimal entity schema and basic CRUD endpoints. Missing: invitation flow (just says "add invitation endpoint"), no permission inheritance, no migration strategy, no edge case handling. Requires significant developer augmentation to be usable.

| | Recommendation |
|---------|----------------|
| **Best Value** | Sonnet 4.6 — covers 90% of what Opus produces at 57% of the cost |
| **Best Quality** | Opus 4.7 — the plan is production-ready without modification |
| **Avoid** | Haiku 4.5 — output requires so much developer augmentation that it saves neither time nor money |

> **Rule of thumb**: For architecture and design tasks, Opus produces plans you can hand directly to a developer (or to Claude for implementation). Sonnet produces good first drafts that need minor refinement. Haiku produces outlines, not plans.

---

## Task Type 5: Code Review

**Task**: Review a 200-line pull request that adds a caching layer to the API client. Check for correctness, performance issues, security concerns, test coverage, and adherence to project patterns.

| Metric | Opus (4.6 measured) | Sonnet 4.6 | Haiku 4.5 |
|--------|:------:|:--------:|:---------:|
| Turns to complete | 2 | 2 | 3 |
| Input tokens (total) | 36,800 | 36,800 | 42,100 |
| Output tokens (total) | 6,200 | 5,400 | 4,800 |
| **Estimated cost** | **$0.34** | **$0.19** | **$0.07** |
| Quality (1-5) | 5 | 4 | 3 |
| Issues found | 7 (3 critical, 2 moderate, 2 minor) | 5 (2 critical, 2 moderate, 1 minor) | 3 (1 critical, 1 moderate, 1 minor) |

### Detailed Findings by Model

| Finding | Severity | Opus (4.6 measured) | Sonnet 4.6 | Haiku 4.5 |
|---------|:--------:|:------:|:--------:|:---------:|
| Cache key collision risk (objects with same JSON but different key order) | Critical | Found | Found | Missed |
| Missing cache invalidation on write operations | Critical | Found | Found | Found |
| No TTL expiration — stale data served indefinitely | Critical | Found | Missed | Missed |
| Cache size unbounded — potential memory leak | Moderate | Found | Found | Found |
| Error in cache miss path — swallows network errors | Moderate | Found | Found | Missed |
| Inconsistent naming (`cacheData` vs `cachedData`) | Minor | Found | Missed | Missed |
| Missing JSDoc on public API methods | Minor | Found | Found | Found |

### Analysis

- **Opus** catches all 7 issues including the subtle TTL problem and the cache key collision risk (which requires understanding that `JSON.stringify({a:1, b:2})` and `JSON.stringify({b:2, a:1})` produce different strings). High-quality review that a senior developer would produce.
- **Sonnet** catches 5 of 7 issues. Misses the TTL concern and the naming inconsistency. Still a strong review that catches the most impactful problems.
- **Haiku** catches only 3 issues and misses both critical cache correctness problems (key collision and TTL). The review reads more like a surface-level scan — catches obvious issues but misses subtle logic bugs.

| | Recommendation |
|---------|----------------|
| **Best Value** | Sonnet 4.6 — catches the high-impact issues at 56% of Opus's cost |
| **Best Quality** | Opus 4.7 — catches subtle correctness issues that could become production bugs |
| **Avoid** | Haiku 4.5 for security/correctness review — missing critical issues makes it counterproductive |

> **Rule of thumb**: Use Opus for code reviews involving security, caching, concurrency, or financial logic. Use Sonnet for general code review. Haiku can review formatting and style compliance, but not logic.

---

## Summary: Model Selection Matrix

| Task Type | Haiku 4.5 | Sonnet 4.6 | Opus 4.7 | Recommendation |
|-----------|:---------:|:--------:|:------:|----------------|
| Formatting / renaming | 5/5 — $0.05 | 5/5 — $0.13 | 5/5 — $0.22 | **Use Haiku** |
| Component creation | 3/5 — $0.14 | 4/5 — $0.33 | 5/5 — $0.56 | **Use Sonnet** (Opus for complex types) |
| Bug investigation | 2/5 — $0.19 | 4/5 — $0.44 | 5/5 — $0.58 | **Use Sonnet** (Opus for hard bugs) |
| Architecture planning | 2/5 — $0.13 | 4/5 — $0.36 | 5/5 — $0.63 | **Use Sonnet** (Opus for critical design) |
| Code review | 3/5 — $0.07 | 4/5 — $0.19 | 5/5 — $0.34 | **Use Sonnet** (Opus for security review) |

### Cost Efficiency Ratios

Another way to look at it — quality points per dollar:

| Task Type | Haiku (quality/$) | Sonnet (quality/$) | Opus (quality/$) |
|-----------|:-----------------:|:------------------:|:-----------------:|
| Formatting / renaming | **100.0** | 38.5 | 22.7 |
| Component creation | 21.4 | **12.1** | 8.9 |
| Bug investigation | 10.5 | **9.1** | 8.6 |
| Architecture planning | 15.4 | **11.1** | 7.9 |
| Code review | 42.9 | **21.1** | 14.7 |

> Higher is better. Haiku dominates for simple tasks. Sonnet wins for everything else on a quality-per-dollar basis. Opus is now much closer in cost to Sonnet, making it a more viable choice when quality matters — the cost premium over Sonnet is only ~1.7x (down from 5x previously).

---

## Decision Tree

```
Is the task mechanical (rename, format, simple find-and-replace)?
├── Yes → Use Haiku 4.5
└── No
    ├── Does the task involve security, financial logic, or complex architecture?
    │   ├── Yes → Use Opus 4.7
    │   └── No
    │       ├── Is the task straightforward with clear requirements?
    │       │   ├── Yes → Use Haiku 4.5
    │       │   └── No → Use Sonnet 4.6
    │       └── Are you on a tight budget?
    │           ├── Yes → Use Sonnet 4.6 (with plan mode to reduce iterations)
    │           └── No → Use Opus 4.7 (now only ~1.7x more than Sonnet)
```

### Practical Model Switching

In Claude Code, switch models per-task:

```bash
# Start a session with Haiku for quick tasks
claude --model haiku

# Switch mid-session for a harder task (use /model command)
/model sonnet

# Or start separate sessions per model
claude --model opus  # for architecture planning
claude --model haiku # for formatting cleanup afterward
```

### Monthly Cost Projection by Strategy

Assuming 80 tasks per month with the distribution: 30% simple, 25% component/feature, 20% bugs, 15% planning, 10% review:

| Strategy | Monthly Cost | Quality |
|----------|:------------:|:-------:|
| Always Opus | $36.00 | Excellent |
| Always Sonnet | $22.60 | Good |
| Always Haiku | $9.16 | Poor (for complex tasks) |
| **Smart routing** (Haiku for simple, Sonnet for medium, Opus for critical) | **$23.90** | **Good to Excellent** |

> Smart model routing saves **34%** versus always-Opus while maintaining high quality where it matters. Note that with current pricing, Opus is only ~1.7x more expensive than Sonnet, so the cost gap between strategies is narrower than it used to be. The main benefit of smart routing is using Haiku for simple tasks where all models perform equally.
