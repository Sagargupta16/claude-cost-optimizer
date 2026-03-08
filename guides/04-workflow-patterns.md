# Guide 04: Workflow Patterns

> **How you use Claude Code matters more than which model you use.** A disciplined workflow with Sonnet can be cheaper than a sloppy workflow with Haiku.

The biggest hidden cost in Claude Code is not the model — it is wasted turns. Every unnecessary clarification, every "actually, I meant...", every exploratory read of a file Claude did not need — these compound into real money. This guide covers workflow patterns that minimize waste.

---

## Table of Contents

- [Plan Before You Build](#plan-before-you-build)
- [Subagent Delegation Patterns](#subagent-delegation-patterns)
- [Commands for Repetitive Tasks](#commands-for-repetitive-tasks)
- [Batch Operations vs One-at-a-Time](#batch-operations-vs-one-at-a-time)
- [The "Ask Once, Implement Once" Pattern](#the-ask-once-implement-once-pattern)
- [Avoiding Clarification Loops](#avoiding-clarification-loops)
- [Structured Multi-Step Work with TodoWrite](#structured-multi-step-work-with-todowrite)
- [Using /compact at Natural Breakpoints](#using-compact-at-natural-breakpoints)
- [Git Commit Strategies](#git-commit-strategies)
- [When NOT to Use Claude Code](#when-not-to-use-claude-code)
- [Putting It All Together: The Optimal Session](#putting-it-all-together-the-optimal-session)

---

## Plan Before You Build

### The Problem

Without a plan, Claude Code tends to:
1. Start coding immediately with incomplete understanding
2. Hit a problem mid-implementation
3. Backtrack, re-read files, and try a different approach
4. Repeat steps 2-3 multiple times

Each iteration consumes tokens. A task that should take 3 turns takes 10.

### The Solution: Plan Mode

Use Claude Code's plan mode (`--plan` or shift+tab to toggle in interactive mode) to analyze before implementing:

```bash
# Bad: Jump straight to implementation
claude "refactor the auth module to use JWT instead of sessions"
# Result: 12 turns, multiple false starts, $1.80

# Good: Plan first, then implement
claude --plan "refactor the auth module to use JWT instead of sessions"
# Result: Plan in 2 turns ($0.30), implementation in 4 turns ($0.60), total $0.90
```

### What Plan Mode Does

In plan mode, Claude Code:
- Reads and analyzes relevant files
- Identifies the scope of changes needed
- Proposes a step-by-step implementation plan
- Does NOT make any changes to files

You review the plan, adjust if needed, then let Claude execute. This eliminates the costly trial-and-error cycle.

### When to Use Plan Mode

| Scenario | Use Plan Mode? | Why |
|----------|:--------------:|-----|
| Task touches 3+ files | **Yes** | Coordination between files benefits from upfront planning |
| You are unsure about the approach | **Yes** | Cheaper to explore options in plan mode than in code |
| Task is well-defined and single-file | No | Overhead of planning exceeds the benefit |
| Simple mechanical change | No | No planning needed for renames, formatting, etc. |
| New feature with vague requirements | **Yes** | Forces you to clarify requirements before burning tokens on code |

### The Plan-Then-Execute Workflow

```
Step 1: Plan (with plan mode or explicit instruction)
  "Analyze the codebase and propose a plan to add WebSocket support.
   List every file that needs to change and what the change is.
   Do not make any changes yet."

Step 2: Review (human reviews the plan, provides feedback)
  "Looks good, but skip the migration for now. Focus on the API layer."

Step 3: Execute (Claude implements the refined plan)
  "Proceed with the plan. Implement the changes."
```

**Estimated savings**: 15-25% per session by eliminating backtracking.

---

## Subagent Delegation Patterns

### What Are Subagents?

When Claude Code uses the Task tool, it spawns a **subagent** — an independent Claude instance with its own context window. The subagent does its work, returns a result, and its context is discarded. Only the result is added to the main conversation.

This is powerful for cost optimization because:
1. **Isolated context**: The subagent does not carry the full conversation history
2. **Cheaper models**: Subagents can use Haiku for simple subtasks
3. **Parallel work**: Multiple subagents can work simultaneously
4. **Context hygiene**: Large file reads in a subagent do not bloat the main context

### Pattern 1: Search and Report

Delegate file searches to a Haiku subagent instead of doing them in the main (expensive) context:

```
Main context (Opus, planning an architecture change):
  "Use a subagent to find all files that import from 'legacy/auth'
   and list them with their import statements."

Subagent (Haiku):
  - Runs Grep/Glob across the codebase
  - Returns a clean list of files and imports
  - Context discarded after returning results
```

**Why this saves money**: The Grep results (potentially thousands of lines) load into the cheap subagent's context, not the expensive Opus 4.6 context. The main context only receives the summarized result.

### Pattern 2: Parallel Implementation

Break a large task into independent subtasks and delegate each:

```
Main context (Sonnet, coordinating):
  "I need to add error handling to three services. Delegate each to a subagent:
   1. Subagent 1: Add error handling to UserService
   2. Subagent 2: Add error handling to PaymentService
   3. Subagent 3: Add error handling to NotificationService"

Each subagent:
  - Gets only the relevant file(s) in its context
  - Implements changes independently
  - Returns the result
```

**Why this saves money**: Each subagent has a small, focused context instead of one massive context containing all three services. Total tokens processed is lower.

### Pattern 3: Research Then Synthesize

Use a cheap subagent to gather information, then use the main context to reason about it:

```
Subagent 1 (Haiku): "Read package.json and list all dependencies with versions"
Subagent 2 (Haiku): "Find all API endpoints and their HTTP methods"
Subagent 3 (Haiku): "List all database models and their field counts"

Main context (Opus): "Given the project structure, dependency list, API surface,
and data model summary, design a caching strategy."
```

**Why this saves money**: Opus 4.6 only processes the summaries, not the raw files. The heavy reading is done by Haiku 4.5 at 1/5th the cost.

### CLAUDE.md Subagent Guidelines

Add this to your CLAUDE.md to encourage cost-efficient delegation:

```markdown
# Subagent Usage
- Always delegate file searches and grep operations to subagents
- Use subagents for independent implementation tasks that don't need shared context
- Prefer parallel subagents over sequential work in the main context
- Subagents should return concise summaries, not raw file contents
```

**Estimated savings**: 20-40% for sessions involving multi-file work.

---

## Commands for Repetitive Tasks

### The Problem

Every time you type a prompt, Claude Code must:
1. Parse your natural language request
2. Figure out what you want
3. Plan its approach
4. Execute

For tasks you do repeatedly (formatting, test running, deployment checks), steps 1-3 are pure overhead. You pay for Claude to "figure out" the same thing every time.

### The Solution: Custom Commands

Define the task once as a command, and Claude skips straight to execution:

```markdown
# .claude/commands/write-test.md
---
model: sonnet
---

Write unit tests for the file or function I specify.

Rules:
- Use the existing test framework (detect from package.json or existing tests)
- Follow the naming pattern of existing tests in the project
- Include: happy path, edge cases, error cases
- Use descriptive test names that explain the expected behavior
- Do not mock unless the dependency is external (API, database)
```

### Cost-Optimized Command Library

Here are commands designed for maximum cost efficiency:

**Simple tasks (Haiku):**

```markdown
# .claude/commands/format.md
---
model: haiku
---
Fix formatting issues in the specified files. Only fix indentation,
trailing whitespace, missing newlines, and bracket alignment.
Do not change any logic or behavior.
```

```markdown
# .claude/commands/find-usages.md
---
model: haiku
---
Find all usages of the specified function/class/variable across the codebase.
Return a list of file paths and line numbers. Do not modify any files.
```

```markdown
# .claude/commands/add-types.md
---
model: haiku
---
Add TypeScript type annotations to the specified file.
Infer types from usage patterns. Use existing type definitions when available.
Do not change any logic.
```

**Medium tasks (Sonnet):**

```markdown
# .claude/commands/fix-bug.md
---
model: sonnet
---
Fix the bug I describe. Steps:
1. Locate the relevant code
2. Identify the root cause
3. Implement the fix
4. Verify the fix doesn't break existing behavior
Keep changes minimal. Do not refactor unrelated code.
```

```markdown
# .claude/commands/create-component.md
---
model: sonnet
---
Create a React component based on my description.
Follow the project's existing component patterns (check src/components/ for examples).
Include: TypeScript types, props interface, basic error handling.
Do not add tests unless I ask.
```

### Why Commands Save Money

1. **Pre-set model**: Each command uses the cheapest appropriate model
2. **Clear instructions**: No tokens wasted on Claude interpreting vague requests
3. **Consistent behavior**: Same approach every time, no exploratory overhead
4. **Amortized prompt design**: You spend time writing the prompt once, and every invocation benefits

**Estimated savings**: 10-15% by eliminating prompt interpretation overhead.

---

## Batch Operations vs One-at-a-Time

### The Problem

Each Claude Code turn includes fixed overhead:
- System prompt (~1,500 tokens)
- CLAUDE.md content
- Conversation history
- Tool definitions

If you send 10 separate requests to rename 10 functions, you pay this overhead 10 times. If you send one request to rename all 10, you pay it once.

### The Batch Pattern

```bash
# Bad: 10 separate requests ($0.07 each x 10 = $0.70)
claude "rename getUserName to fetchUserName"
claude "rename getUserEmail to fetchUserEmail"
claude "rename getUserAge to fetchUserAge"
# ... 7 more times

# Good: 1 batched request ($0.15 total)
claude "rename all functions matching getUser* to fetchUser* across the codebase"
```

### When to Batch

| Scenario | Batch? | Why |
|----------|:------:|-----|
| Same operation on multiple files | **Yes** | Identical operation, different targets |
| Related changes across a module | **Yes** | Changes share context and rationale |
| Unrelated changes in different modules | No | Batching unrelated work confuses Claude |
| Changes that depend on each other's results | Sometimes | Batch if the dependency is simple, separate if complex |

### Batch-Friendly Task Patterns

```bash
# Batch: Add error handling to all API routes
claude "add try/catch error handling to all route handlers in src/routes/"

# Batch: Update all test files to use new assertion syntax
claude "migrate all test files from expect().toBe() to assert.equal()"

# Batch: Add TypeScript types to all utility functions
claude "add TypeScript type annotations to all functions in src/utils/"
```

### The Sweet Spot

Batch 3-10 related items per request. Beyond 10, Claude may lose track or make mistakes, requiring costly correction turns.

**Estimated savings**: 30-50% for repetitive multi-file operations.

---

## The "Ask Once, Implement Once" Pattern

### The Problem: Iterative Refinement Is Expensive

```
Turn 1: "Create a login form"
Turn 2: "Actually, add email validation"
Turn 3: "Oh, and add a 'remember me' checkbox"
Turn 4: "Can you also add password strength indicator?"
Turn 5: "Make it responsive"
Turn 6: "Add loading state during submission"

Total: 6 turns, $0.42 (Sonnet)
```

Each turn re-reads the growing conversation history and the modified file. By turn 6, Claude is processing all previous turns plus the file content.

### The Solution: Front-Load Requirements

```
Turn 1: "Create a login form with:
  - Email field with validation (format check)
  - Password field with strength indicator
  - 'Remember me' checkbox
  - Submit button with loading state
  - Responsive layout (mobile-first)
  - Error messages for invalid inputs"

Total: 1-2 turns, $0.12 (Sonnet)
```

**Savings: 71%** for the same output.

### How to Write Complete Requirements

Before sending a prompt, ask yourself:

1. **What is the output?** (component, function, config, etc.)
2. **What are the inputs?** (props, parameters, data sources)
3. **What are the constraints?** (styling framework, existing patterns, accessibility)
4. **What are the edge cases?** (error states, empty states, loading states)
5. **What should it NOT do?** (no tests, no storybook, no extra files)

Spend 60 seconds writing a complete prompt. It will save 5 minutes and $0.30 in unnecessary turns.

### The Pre-Prompt Checklist

Copy this checklist and fill it out before complex tasks:

```
Task: [what you want]
Files involved: [list known files, or "determine from codebase"]
Constraints:
  - Must follow existing patterns in [reference file]
  - Use [specific library/framework]
  - Do not modify [protected files]
Expected output:
  - [ ] Primary deliverable
  - [ ] Secondary deliverable (tests, docs, etc.)
Edge cases to handle:
  - [ ] Error states
  - [ ] Empty/null inputs
  - [ ] Loading states
Explicitly NOT needed:
  - [ ] Tests (will add later)
  - [ ] Documentation
  - [ ] Storybook stories
```

---

## Avoiding Clarification Loops

### The Cost of "What Did You Mean?"

When Claude asks a clarifying question, it costs you:
1. **Claude's question turn**: Input (full history) + Output (the question) -- you pay for this
2. **Your answer turn**: Input (full history + question + your answer) + Output (next action)
3. **Potential follow-up questions**: The cycle continues

A single clarification loop adds $0.03-$0.10 depending on context size. Three loops in a session is $0.09-$0.30 of pure waste.

### How to Eliminate Clarification Loops

**1. Be specific about file paths:**
```bash
# Bad (Claude will ask "which file?" or search the whole codebase)
claude "fix the auth bug"

# Good (Claude goes straight to the file)
claude "fix the null pointer in src/services/AuthService.ts line 47"
```

**2. Specify the approach when it matters:**
```bash
# Bad (Claude will ask or guess)
claude "add caching to the API"

# Good (no ambiguity)
claude "add Redis caching to GET /api/users with a 5-minute TTL.
Use the existing Redis client in src/lib/redis.ts"
```

**3. Include examples of desired output:**
```bash
# Bad
claude "create a type for API responses"

# Good
claude "create a TypeScript generic type for API responses like:
type ApiResponse<T> = { data: T; error: null } | { data: null; error: string }
Use this pattern for all API response types in src/types/"
```

**4. Use the "assume and proceed" instruction in CLAUDE.md:**
```markdown
# Decision Making
When multiple valid approaches exist, choose the simplest one and proceed.
Do not ask for clarification unless the request is genuinely ambiguous.
Prefer conventions already established in this codebase.
```

This single CLAUDE.md entry can eliminate 50%+ of clarification turns across all sessions.

---

## Structured Multi-Step Work with TodoWrite

### The Problem: Lost Context in Long Tasks

During complex tasks, Claude Code can lose track of what it has done and what remains. This leads to:
- Re-reading files it already read
- Repeating work it already completed
- Missing steps entirely
- Going in circles

### The Solution: TodoWrite

Claude Code's TodoWrite tool creates an explicit task list that persists across turns. Using it:
- Prevents duplicate work (Claude checks the list before each step)
- Ensures completeness (no steps are forgotten)
- Reduces context re-processing (the todo list is a compact summary of state)

### How to Trigger TodoWrite Usage

Add this to your CLAUDE.md:

```markdown
# Multi-Step Tasks
For any task involving 3+ steps:
1. Create a todo list before starting
2. Mark each step in_progress before working on it
3. Mark each step completed immediately after finishing
4. Never skip steps or work on multiple steps simultaneously
```

Or instruct Claude directly:

```bash
claude "Migrate from Express to Fastify. Use TodoWrite to track each step.
Plan all steps first, then execute them one at a time."
```

### Why TodoWrite Saves Money

Without TodoWrite:
```
Turn 1: Read files, start implementing (then forget what's left)
Turn 2: Re-read some files, continue (duplicated reads)
Turn 3: Realize a step was missed, backtrack
Turn 4: Re-read files from Turn 1 (context was lost)
Turn 5-8: More duplicated work
Total: 8 turns, heavy token waste
```

With TodoWrite:
```
Turn 1: Create todo list with 5 steps, start step 1
Turn 2: Complete step 1, start step 2
Turn 3: Complete step 2, start step 3
Turn 4: Complete steps 3-4
Turn 5: Complete step 5
Total: 5 turns, no wasted reads
```

**Estimated savings**: 15-30% on complex multi-step tasks.

---

## Using /compact at Natural Breakpoints

### How /compact Works

The `/compact` command tells Claude Code to compress the conversation history. It summarizes previous turns into a compact form, dramatically reducing the input tokens for subsequent turns.

### When to Compact

Think of `/compact` like saving your game and starting a new chapter. Use it at **natural breakpoints**:

```
Good times to /compact:
├── After finishing a feature and before starting a new one
├── After a planning phase, before implementation
├── After a long debugging session, before the fix
├── After reviewing code, before making changes
├── When conversation history exceeds ~30 turns
└── When you notice responses getting slower (sign of large context)

Bad times to /compact:
├── Mid-implementation (loses important context)
├── During a debugging session (need the full trail)
├── Right after reading several files (summaries lose detail)
└── When the next task directly references previous details
```

### The /compact Workflow

```
Phase 1: Planning (10 turns)
  - Discuss architecture
  - Review existing code
  - Agree on approach
  → /compact (preserves the plan, discards the back-and-forth)

Phase 2: Implementation (15 turns)
  - Build feature
  - Fix issues
  - Test
  → /compact (preserves what was built, discards the process)

Phase 3: Review and Polish (5 turns)
  - Code review
  - Final adjustments
  → Done (or /compact before starting next feature)
```

### Cost Impact

Without /compact, a 30-turn session has massive context by the end. Turn 30 processes the entire conversation history.

With /compact after every 10 turns:
- Turns 1-10: Normal growth
- /compact: History compressed from ~20K tokens to ~2K tokens
- Turns 11-20: Start with small context, normal growth
- /compact: Compressed again
- Turns 21-30: Start with small context

**Estimated savings**: 20-40% on long sessions (30+ turns).

---

## Git Commit Strategies

### The Problem: Committing After Every Change

Some developers configure Claude Code to auto-commit after every change. This seems convenient but is costly:

1. **Commit message generation** costs tokens (reading diff, writing message)
2. **Each commit is a separate turn** with full context overhead
3. **Noisy git history** makes future work harder (more tokens to understand history)

### Cost-Efficient Commit Patterns

**Pattern 1: Commit at logical boundaries**

```
Implement feature (5-8 turns)
  → Single commit: "Add user profile editing feature"

Not:
  Turn 1: "Add form component" → commit
  Turn 2: "Add validation" → commit
  Turn 3: "Add API call" → commit
  Turn 4: "Add error handling" → commit
  Turn 5: "Add loading state" → commit
  (5 commits, 5x commit overhead)
```

**Pattern 2: Let the developer commit**

Add to your CLAUDE.md:
```markdown
# Git
Do not create commits unless I explicitly ask.
I will handle git operations myself.
```

This eliminates all commit-related token costs. You commit manually when you are ready.

**Pattern 3: Batch commits with a command**

```markdown
# .claude/commands/commit.md
---
model: haiku
---
Create a single commit for all current changes.
Write a concise, conventional commit message.
Format: type(scope): description
```

Use Haiku for commit messages since they are simple summarization tasks.

### The Real Cost of Auto-Commit

```
50 changes/day x $0.02/commit (Sonnet) = $1.00/day = $22/month

With manual commits at logical boundaries:
10 commits/day x $0.01/commit (Haiku) = $0.10/day = $2.20/month

Savings: $19.80/month per developer
```

---

## When NOT to Use Claude Code

The most cost-effective Claude Code technique is knowing when not to use it at all.

### Tasks That Are Cheaper to Do Manually

| Task | Claude Code Cost | Manual Time | Verdict |
|------|:----------------:|:-----------:|---------|
| Change one line of code | $0.01-0.05 | 10 seconds | **Manual** |
| Rename a local variable (1 file) | $0.01-0.03 | 15 seconds (IDE rename) | **Manual** |
| Fix a typo | $0.01-0.03 | 5 seconds | **Manual** |
| Toggle a boolean config | $0.01-0.02 | 3 seconds | **Manual** |
| Delete a file | $0.01-0.02 | 2 seconds | **Manual** |
| Add a blank line | $0.01 | 1 second | **Manual** |

**Rule of thumb**: If you can do it faster than typing the prompt, do it manually. Claude Code's minimum cost per turn is ~$0.01 (Haiku). If the task takes under 30 seconds to do manually, it is not worth the token cost or the latency of waiting for a response.

### Tasks Better Suited to Other Tools

| Task | Better Tool | Why |
|------|-------------|-----|
| **Global find-and-replace** (literal string) | IDE search/replace | Deterministic, instant, free |
| **Formatting entire codebase** | Prettier/Black/rustfmt | Deterministic, faster, free |
| **Linting fixes** | ESLint --fix, Ruff | Purpose-built, free |
| **Dependency updates** | Dependabot, Renovate | Automated, handles changelogs |
| **Database migrations** | ORM migration tools | Safer, version-controlled |
| **Boilerplate generation** | CLI scaffolding (create-next-app, etc.) | Designed for the task, free |

### The Decision Matrix

```
Should I use Claude Code for this task?

1. Can I do it manually in under 30 seconds?
   → YES: Do it manually.

2. Is there a deterministic tool that does this perfectly?
   → YES: Use that tool.

3. Does this task require understanding code context or generating new logic?
   → YES: Use Claude Code (with the right model).
   → NO: Probably don't need Claude Code.
```

---

## Putting It All Together: The Optimal Session

Here is what a cost-optimized Claude Code session looks like in practice:

### Phase 1: Setup (1 turn)
- Start with Sonnet as default model
- CLAUDE.md is lean (<150 lines) and includes model routing guidelines
- .claudeignore excludes unnecessary files

### Phase 2: Plan (2-3 turns)
- Use plan mode or explicit "analyze and plan" instructions
- Review the plan, refine once
- `/compact` after planning phase

### Phase 3: Implement (5-15 turns)
- Execute the plan step by step
- Use TodoWrite for multi-step work
- Delegate file searches and simple subtasks to subagents
- Batch related changes into single turns
- Use commands for repetitive operations

### Phase 4: Review and Commit (1-2 turns)
- `/compact` before review if history is long
- Review changes
- Single commit at a logical boundary
- Use Haiku for the commit message

### Phase 5: Cleanup
- `/compact` before starting the next feature
- Or start a new session for a truly independent task

### Session Cost Comparison

| Approach | Turns | Avg Cost/Turn | Total |
|----------|:-----:|:-------------:|:-----:|
| Unoptimized (all Opus 4.6, no planning, no batching) | 25 | $0.12 | $3.00 |
| Partially optimized (Sonnet 4.6 default, some planning) | 18 | $0.08 | $1.44 |
| Fully optimized (right models, planning, batching, /compact) | 12 | $0.06 | $0.72 |

**Fully optimized is 76% cheaper** than the unoptimized approach, for the same end result. Even with Opus 4.6's lower pricing, disciplined workflows yield significant savings.

---

## Summary of Savings by Pattern

| Pattern | Estimated Savings | Effort to Adopt |
|---------|:-----------------:|:---------------:|
| Plan mode before implementation | 15-25% | None (built-in) |
| Subagent delegation | 20-40% | Low (CLAUDE.md update) |
| Custom commands for repetitive tasks | 10-15% | Medium (one-time setup) |
| Batch operations | 30-50% | None (habit change) |
| Front-loaded requirements | 20-40% | None (habit change) |
| Eliminate clarification loops | 5-15% | Low (better prompts) |
| TodoWrite for multi-step work | 15-30% | None (built-in) |
| /compact at breakpoints | 20-40% | None (built-in) |
| Smart commit strategy | 5-10% | Low (CLAUDE.md update) |
| Knowing when not to use Claude Code | 10-20% | None (judgment) |

> These savings compound. Applying all patterns together yields the 40-70% total reduction mentioned in the README.

---

## Next Steps

- Add the `/compact` habit to your workflow today (zero effort, immediate savings)
- Create 3-5 custom commands for your most common tasks
- Add subagent and model routing guidelines to your CLAUDE.md
- Read [Guide 05: Team Budgeting](05-team-budgeting.md) to scale these patterns across a team

---

*[Back to README](../README.md) | [Previous: Model Selection](03-model-selection.md) | [Next: Team Budgeting](05-team-budgeting.md)*
