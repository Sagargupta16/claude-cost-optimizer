# Task Comparison Benchmarks

> The same development tasks performed with and without optimization strategies. All estimates use Sonnet 4 unless otherwise noted.

## How to Read This

Each scenario shows the **same task** done two ways:

- **Unoptimized** — default Claude Code behavior, large CLAUDE.md (~300 lines), no workflow strategies, single model.
- **Optimized** — using strategies from this repo: trimmed CLAUDE.md (~100 lines), plan mode, subagents, model selection, custom commands.

Token counts are per-session totals (all turns combined). Costs are calculated from published pricing. See [benchmarks/README.md](README.md) for full methodology.

---

## Scenario 1: Adding a React Component

**Task**: Create a new `UserProfileCard` component with TypeScript, props interface, styling (CSS modules), and a Storybook story. Project uses React 18, TypeScript, CSS Modules, and Storybook 7.

### Unoptimized Approach

The developer types a single prompt: "Create a UserProfileCard component with avatar, name, bio, and follow button. Use our project patterns." Claude reads multiple existing components to learn patterns, reads the entire CLAUDE.md (300 lines), and generates everything in one long context.

| Metric | Value |
|--------|-------|
| Turns | 6 |
| Input tokens (total across all turns) | 82,400 |
| Output tokens (total) | 8,200 |
| CLAUDE.md tokens loaded per turn | ~2,100 |
| Files read by Claude | 7 (3 existing components, styles, types, storybook config, package.json) |
| **Estimated cost (Sonnet 4)** | **$0.37** |
| Quality | Correct but used wrong CSS naming convention, needed 2 follow-up turns to fix |

**Breakdown of waste:**
- CLAUDE.md loaded 6 times at 2,100 tokens = 12,600 tokens of context overhead
- Read 3 existing components (2,400 tokens) that could have been summarized in CLAUDE.md conventions
- 2 follow-up turns to fix style issues that a better CLAUDE.md would have prevented

### Optimized Approach

CLAUDE.md (~100 lines) includes a "Component Patterns" section specifying CSS module naming convention, file structure, and props pattern. Developer uses plan mode first: "Plan a UserProfileCard component with avatar, name, bio, and follow button." Reviews the plan, then: "Execute the plan."

| Metric | Value |
|--------|-------|
| Turns | 4 (1 plan + 1 approval + 1 execution + 1 minor tweak) |
| Input tokens (total across all turns) | 38,500 |
| Output tokens (total) | 6,800 |
| CLAUDE.md tokens loaded per turn | ~700 |
| Files read by Claude | 2 (types file, one example component for reference) |
| **Estimated cost (Sonnet 4)** | **$0.22** |
| Quality | Correct on first execution — plan caught the CSS naming question upfront |

### Comparison

| Metric | Unoptimized | Optimized | Savings |
|--------|:-----------:|:---------:|:-------:|
| Turns | 6 | 4 | 33% fewer |
| Total input tokens | 82,400 | 38,500 | 53% |
| Total output tokens | 8,200 | 6,800 | 17% |
| Estimated cost | $0.37 | $0.22 | **41%** |
| Quality fix-ups needed | 2 | 0 | -- |

**Key savings driver**: Smaller CLAUDE.md eliminated 9,800 tokens of per-turn overhead. Plan mode prevented 2 wasted fix-up turns. Documenting conventions in CLAUDE.md removed the need to read 3 example files.

---

## Scenario 2: Fixing a Bug

**Task**: Users report that the search filter resets when navigating between pages. The bug is in the state management layer. Project uses React + Zustand.

### Unoptimized Approach (Iterative)

Developer tells Claude: "The search filter resets when users navigate between pages. Fix it." Claude starts reading files, hypothesizing, editing code, running tests, hitting errors, reading more files, and iterating.

| Metric | Value |
|--------|-------|
| Turns | 11 |
| Input tokens (total) | 148,000 |
| Output tokens (total) | 12,400 |
| CLAUDE.md tokens loaded per turn | ~2,100 |
| Files read by Claude | 14 (search component, store, router, 4 page components, tests, configs, etc.) |
| **Estimated cost (Sonnet 4)** | **$0.63** |
| Quality | Fixed the bug, but introduced a minor regression in filter clear behavior (caught later) |

**What went wrong:**
- Claude investigated 6 files that were unrelated to the bug before finding the root cause
- 3 turns were spent on a wrong hypothesis (thought the bug was in the router, actually in the store)
- Large CLAUDE.md loaded 11 times contributed 23,100 tokens of overhead
- No plan phase meant Claude jumped straight into editing before understanding the problem

### Optimized Approach (Plan Mode First)

Developer uses plan mode: "Investigate why the search filter resets when navigating between pages. The state is managed with Zustand. Do not edit any files — just identify the root cause and propose a fix." After receiving the plan, developer confirms the correct hypothesis and says: "Execute option 2 from your plan."

| Metric | Value |
|--------|-------|
| Turns | 5 (2 investigation + 1 plan review + 1 fix + 1 test verification) |
| Input tokens (total) | 62,300 |
| Output tokens (total) | 7,100 |
| CLAUDE.md tokens loaded per turn | ~700 |
| Files read by Claude | 5 (search component, store, 2 page components, test file) |
| **Estimated cost (Sonnet 4)** | **$0.29** |
| Quality | Clean fix, no regressions, test added for the specific case |

### Comparison

| Metric | Unoptimized | Optimized | Savings |
|--------|:-----------:|:---------:|:-------:|
| Turns | 11 | 5 | 55% fewer |
| Total input tokens | 148,000 | 62,300 | 58% |
| Total output tokens | 12,400 | 7,100 | 43% |
| Estimated cost | $0.63 | $0.29 | **54%** |
| Regressions introduced | 1 | 0 | -- |

**Key savings driver**: Plan mode prevented 6 wasted investigation turns. Constraining Claude to "do not edit" during investigation avoided the costly read-edit-test-undo loop. Smaller CLAUDE.md saved 15,400 tokens across all turns.

---

## Scenario 3: Writing Tests

**Task**: Write unit tests for a `PaymentProcessor` class that handles Stripe integration. Need tests for successful payment, card declined, network error, and refund flows. Project uses Jest + TypeScript.

### Unoptimized Approach (Main Context)

Developer tells Claude in the main session: "Write comprehensive unit tests for the PaymentProcessor class in src/services/payment.ts." Claude reads the file, its dependencies, existing test patterns, and generates all tests in the main conversation context.

| Metric | Value |
|--------|-------|
| Turns | 8 |
| Input tokens (total) | 124,600 |
| Output tokens (total) | 18,500 |
| CLAUDE.md tokens loaded per turn | ~2,100 |
| Files read by Claude | 9 (PaymentProcessor, Stripe types, 3 existing test files for patterns, jest config, tsconfig, mock helpers, error types) |
| **Estimated cost (Sonnet 4)** | **$0.65** |
| Quality | Tests pass but mock structure differs from project convention — 2 turns spent on revision |

**What went wrong:**
- Reading 3 existing test files for pattern learning consumed 8,700 tokens
- Each subsequent turn re-loaded all that context (conversation history grows)
- 2 revision turns at the end were expensive because the full conversation history was in context
- Main context became bloated — by turn 8, input was ~25,000 tokens per turn

### Optimized Approach (Subagent Delegation)

Developer uses a subagent command for test generation. The `/test` custom command prompt tells Claude: "Delegate the test writing to a subagent. Include this context: test framework is Jest, use `vi.mock()` pattern for mocking, follow AAA pattern (Arrange/Act/Assert), use `describe`/`it` blocks." The subagent runs in an isolated context, generates the test file, and returns just the result.

| Metric | Value |
|--------|-------|
| Turns in main context | 2 (1 delegation + 1 review of result) |
| Turns in subagent | 4 |
| Input tokens (main context total) | 18,200 |
| Input tokens (subagent total) | 42,800 |
| Output tokens (main + subagent total) | 16,100 |
| CLAUDE.md tokens loaded per turn (main) | ~700 |
| Files read by Claude | 4 (PaymentProcessor, Stripe types, 1 example test, mock helpers) |
| **Estimated cost (Sonnet 4)** | **$0.42** |
| Quality | Tests pass and follow project conventions — mock pattern was specified in the delegation prompt |

### Comparison

| Metric | Unoptimized | Optimized | Savings |
|--------|:-----------:|:---------:|:-------:|
| Effective turns | 8 | 6 (2 main + 4 subagent) | 25% fewer |
| Total input tokens | 124,600 | 61,000 | 51% |
| Total output tokens | 18,500 | 16,100 | 13% |
| Estimated cost | $0.65 | $0.42 | **35%** |
| Convention violations | 2 (required revision) | 0 | -- |

**Key savings driver**: Subagent isolation prevented test-generation context from bloating the main conversation. The subagent started with a clean context window, so each of its turns was cheap. Convention info in the delegation prompt eliminated pattern-learning file reads.

---

## Scenario 4: Refactoring a Module

**Task**: Refactor the `UserService` module from a monolithic 800-line file into separate concerns: `UserRepository` (data access), `UserValidator` (validation logic), `UserNotifier` (email/notification), and a slim `UserService` (orchestration). Maintain all existing tests.

### Unoptimized Approach (Ad-Hoc)

Developer tells Claude: "Refactor src/services/user-service.ts. It's too big. Split it into repository, validator, notifier, and service layers." Claude reads the file, starts editing, discovers dependencies, reads more files, makes changes, runs tests, fixes failures — all in one long session.

| Metric | Value |
|--------|-------|
| Turns | 18 |
| Input tokens (total) | 312,000 |
| Output tokens (total) | 34,600 |
| CLAUDE.md tokens loaded per turn | ~2,100 |
| Files read by Claude | 16 (user service, tests, 6 dependent modules, types, configs, etc.) |
| **Estimated cost (Sonnet 4)** | **$1.46** |
| Quality | Refactoring complete, 3 test failures fixed after initial pass, one circular dependency resolved in extra turns |

**What went wrong:**
- By turn 12, each turn had ~28,000 input tokens from conversation history alone
- 4 turns were spent discovering and fixing a circular dependency that plan mode would have caught
- Claude re-read the original 800-line file 3 times because earlier reads scrolled out of context
- Turns 14-18 each cost $0.10+ due to massive context accumulation

### Optimized Approach (Commands + Plan Mode)

Developer uses plan mode: "Analyze src/services/user-service.ts and plan a refactoring into UserRepository, UserValidator, UserNotifier, and UserService. Identify all dependencies and potential circular dependencies. Output a step-by-step execution plan." After reviewing, the developer runs a custom `/refactor` command that executes each step as a separate subagent task, keeping the main context slim.

| Metric | Value |
|--------|-------|
| Turns in main context | 4 (1 plan + 1 review + 1 orchestration + 1 test verification) |
| Turns in subagents | 8 (2 per new module) |
| Input tokens (main context total) | 42,800 |
| Input tokens (subagent total) | 98,400 |
| Output tokens (main + subagent total) | 28,200 |
| CLAUDE.md tokens loaded per turn (main) | ~700 |
| Files read by Claude | 10 (more targeted reads per subagent) |
| **Estimated cost (Sonnet 4)** | **$0.85** |
| Quality | Clean refactoring, all tests pass on first run, no circular dependencies (caught in plan) |

### Comparison

| Metric | Unoptimized | Optimized | Savings |
|--------|:-----------:|:---------:|:-------:|
| Effective turns | 18 | 12 (4 main + 8 subagent) | 33% fewer |
| Total input tokens | 312,000 | 141,200 | 55% |
| Total output tokens | 34,600 | 28,200 | 19% |
| Estimated cost | $1.46 | $0.85 | **42%** |
| Post-hoc fixes needed | 4 | 0 | -- |

**Key savings driver**: Plan mode caught the circular dependency before any code was written, saving 4 fix-up turns. Subagent delegation kept each module extraction in a fresh context window — no accumulated bloat. The main context stayed under 15,000 tokens per turn throughout.

---

## Summary Table

| Scenario | Unoptimized Cost | Optimized Cost | Savings | Primary Strategy |
|----------|:----------------:|:--------------:|:-------:|------------------|
| Adding a React component | $0.37 | $0.22 | **41%** | Smaller CLAUDE.md + plan mode |
| Fixing a bug | $0.63 | $0.29 | **54%** | Plan mode (investigate before editing) |
| Writing tests | $0.65 | $0.42 | **35%** | Subagent delegation |
| Refactoring a module | $1.46 | $0.85 | **42%** | Plan mode + subagents + commands |
| **Total (4 tasks)** | **$3.11** | **$1.78** | **43%** | Combined strategies |

### Extrapolated Monthly Impact

Assuming a developer performs roughly similar tasks 5 times per week:

| Metric | Unoptimized | Optimized | Savings |
|--------|:-----------:|:---------:|:-------:|
| Weekly cost (20 tasks) | $15.55 | $8.90 | $6.65/week |
| Monthly cost (80 tasks) | $62.20 | $35.60 | **$26.60/month** |
| Annual cost (960 tasks) | $746.40 | $427.20 | **$319.20/year** |

> These estimates assume Sonnet 4 pricing for all tasks. Mixing in Haiku for simple tasks (scenarios 1 and 2) would increase savings to 55-65%. See [Model Comparison](model-comparison.md) for model-specific analysis.

---

## Reproducing These Benchmarks

To reproduce any scenario:

1. Use a medium-sized project (~50 files, ~15K lines) in the relevant stack.
2. Use the Standard template (~100 lines) from `templates/CLAUDE.md/standard.md` as the optimized CLAUDE.md.
3. For the unoptimized baseline, use a CLAUDE.md with ~300 lines (include redundant sections, verbose descriptions, and duplicated information).
4. Run the task and record token counts from `/usage`.
5. Submit your results via the [Benchmark Result](../.github/ISSUE_TEMPLATE/benchmark-result.md) template.
