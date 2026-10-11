# Guide 04: Workflow Patterns

> **How you use Claude Code matters more than which model you use.** A disciplined workflow with Sonnet can be cheaper than a sloppy workflow with Haiku.

The biggest hidden cost in Claude Code is not the model -- it is wasted turns. Every unnecessary clarification, every "actually, I meant...", every exploratory read of a file Claude did not need -- these compound into real money. This guide covers workflow patterns that minimize waste.

> **How the dollar figures in this guide are computed.** Session and per-turn costs use this repo's calculator defaults (3,500-token system prompt, 100-line CLAUDE.md at 7 tokens per line, 2 MCP servers at 1,500 tokens each, one 2,000-token file read, 500 output tokens per turn, history growing 1,500 tokens per turn), billed the way Claude Code bills: each request reads the whole previous request from cache and writes only the new exchange at the 5-minute rate (1.25x input), with no pause longer than the cache TTL ([formula](01-understanding-costs.md#estimated-session-cost)). At those defaults a 30-turn session is $0.74 on Opus 5.5 and $0.37 on Sonnet 5.5. Turn counts in the examples are illustrative, not measured.

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

Use Claude Code's plan mode to analyze before implementing. In an interactive session, press **Shift+Tab** to cycle to plan mode before implementation starts (Anthropic's costs page lists this as a cost lever). To start a session already in plan mode, pass `--permission-mode plan` (there is no `--plan` flag):

```bash
# Bad: Jump straight to implementation
claude "refactor the auth module to use JWT instead of sessions"
# Result: 12 turns, multiple false starts: $0.29 on Opus 5.5

# Good: Plan first, then implement (or press Shift+Tab inside a running session)
claude --permission-mode plan "refactor the auth module to use JWT instead of sessions"
# Result: plan in 2 turns ($0.08), implementation in 4 more ($0.08), total $0.16
```

(Computed at the calculator defaults above. The 12 and 6 turn counts are illustrative.)

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

**Estimated savings: no published figure.** Plan mode appends its instructions as messages, so toggling it keeps the prompt cache; opusplan is the exception, since each toggle switches model and rebuilds the cache ([prompt-caching page](https://code.claude.com/docs/en/prompt-caching)).

---

## Subagent Delegation Patterns

### What Are Subagents?

When Claude Code uses the Task tool, it spawns a **subagent** -- an independent Claude instance with its own context window. The subagent does its work, returns a result, and its context is discarded. Only the result is added to the main conversation.

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

**Why this saves money**: The Grep results (potentially thousands of lines) load into the cheap subagent's context, not the expensive Opus 5.5 context. The main context only receives the summarized result. Haiku 5.5 is priced by prompt length -- $0.10/$0.50 per 1M up to 100K prompt tokens, $0.50/$2.50 above, with cache reads and writes counting toward the 100K -- so a search subagent that returns file names and line numbers instead of file contents stays in the cheap tier, 40x below Opus 5.5 per token.

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

**Why this saves money**: Opus 5.5 only processes the summaries, not the raw files. The heavy reading is done by Haiku 5.5 at 1/40 of Opus 5.5's per-token rate while each subagent's prompt stays at or under 100K tokens (1/8 above).

### CLAUDE.md Subagent Guidelines

Add this to your CLAUDE.md to encourage cost-efficient delegation:

```markdown
# Subagent Usage
- Always delegate file searches and grep operations to subagents
- Use subagents for independent implementation tasks that don't need shared context
- Prefer parallel subagents over sequential work in the main context
- Subagents should return concise summaries, not raw file contents
```

To pin the cheap model rather than asking for it, set `model: haiku` in the subagent's definition frontmatter -- Anthropic's costs page (code.claude.com/docs/en/costs) recommends exactly that for simple subagent tasks. On the Anthropic API `haiku` is Haiku 5.5 (Claude Code v2.1.293+); on Bedrock, Google Cloud, Microsoft Foundry and Claude Platform on AWS it is still legacy Haiku 4.5, so set `ANTHROPIC_DEFAULT_HAIKU_MODEL` there (Bedrock: `anthropic.claude-haiku-5-5`). Two Haiku 5.5 properties suit subagents: short subagent calls stay in the cheap under-100K tier, and its 512-token cache floor (Haiku 4.5: 4,096) means a subagent's short system prompt actually caches instead of paying full input price on every call. The same page warns about the opposite end: agent teams use about **7x the tokens** of a standard session when teammates run in plan mode, so fan out deliberately.

Delegation is not cheap by default: the built-in Explore subagent runs on the main conversation's model, not Haiku. To explore on Haiku, define your own `Explore` with `model: haiku`, or set `CLAUDE_CODE_SUBAGENT_MODEL=haiku` plus `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` (v2.1.257+). Since v2.1.292 the Agent tool also takes an `effort` parameter ([sub-agents docs](https://code.claude.com/docs/en/sub-agents), [changelog](https://code.claude.com/docs/en/changelog)).

**Measured elsewhere:** in Anthropic's [cost-optimization cookbook](https://platform.claude.com/cookbook/cost-optimization-cost-optimization), moving the work into a subagent cut one agent loop's cost 78% ($1.7945 to $0.3978). No Claude Code measurement exists, and subagents add their own requests: Anthropic measured multi-agent systems at about 15x the tokens of a chat ([multi-agent research post](https://www.anthropic.com/engineering/multi-agent-research-system)). Subagents save when they read far more than they return and run on a cheaper model.

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

**Estimated savings: no published figure.** Commands and skills load their instructions only when invoked, as messages, so they keep the prompt cache ([prompt-caching page](https://code.claude.com/docs/en/prompt-caching)). A skill's description is the exception: it sits in the skill listing on every turn whether or not the skill runs. `/skill-doctor` (Claude Code v2.1.252+) reports what each skill costs and how often it is used, and says where to turn off the ones you never invoke ([skills docs](https://code.claude.com/docs/en/skills)).

### Hooks: Filter Output Before Claude Reads It

A command controls what Claude is asked; a hook controls what Claude reads back. Anthropic's costs page gives the example of a `PreToolUse` hook that filters test output down to the failures, which it says cuts tens of thousands of tokens to hundreds. The same idea applies to any noisy command (builds, linters, installs): let the hook strip the passing lines so only the signal enters context. Anthropic publishes the token range, not a session-level percentage, so measure your own before and after with `/usage`.

Filtering matters more on Haiku 5.5 subagents: unfiltered test or build output can push a subagent's prompt past 100K tokens, and then the whole request bills at $0.50/$2.50 instead of $0.10/$0.50. Trimmed output keeps short subagent calls in the cheap tier, and a short, stable system prompt above Haiku 5.5's 512-token floor keeps caching.

---

## Batch Operations vs One-at-a-Time

### The Problem

Each Claude Code turn includes fixed overhead:
- System prompt (3,500 tokens is this repo's modelling assumption; Claude Code's real system prompt plus its tool definitions is larger)
- CLAUDE.md content
- Conversation history
- Tool definitions (MCP tools are deferred by default under tool search: only their names and server instructions load until Claude uses one)

If you send 10 separate requests to rename 10 functions, you pay this overhead 10 times. If you send one request to rename all 10, you pay it once.

### The Batch Pattern

```bash
# Bad: 10 separate requests ($0.028 each x 10 = $0.28 on Sonnet 5.5)
claude "rename getUserName to fetchUserName"
claude "rename getUserEmail to fetchUserEmail"
claude "rename getUserAge to fetchUserAge"
# ... 7 more times

# Good: 1 batched request (one session: $0.048 if it takes 3 turns, $0.12 even at 10)
claude "rename all functions matching getUser* to fetchUser* across the codebase"
```

(Computed at the calculator defaults at the top of this guide. Each separate `claude` run is a new session that writes its whole 9,200-token prompt to the cache again, unless it can reuse the cached system prompt, which happens only within the TTL and only if its git status snapshot matches ([prompt-caching page](https://code.claude.com/docs/en/prompt-caching)); one session writes it once and reads it after that.)

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

Batch related items into one request, up to about 10. Beyond that, Claude may lose track or make mistakes, requiring costly correction turns (a rule of thumb, not a measured limit).

**Worked example:** each turn you avoid saves one cache read of the whole context plus that turn's output. At a 50K-token context on Opus 5.5 that is $0.01 per avoided turn in cache reads ($0.005 on Sonnet 5.5), so twelve one-file turns collapsed into one save about $0.11 before output (computed: 50,000 x $0.20/1M = $0.01, x 11 avoided turns; Sonnet 5.5 reads at $0.10/1M, [Anthropic pricing page](https://platform.claude.com/docs/en/about-claude/pricing)).

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

Total: 6 turns, $0.078 (Sonnet 5.5)
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

Total: 2 turns, $0.038 (Sonnet 5.5)
```

**Savings: 52%** for the same output (computed at the calculator defaults at the top of this guide: $0.038 vs $0.078; the turn counts are illustrative).

### How to Write Complete Requirements

Before sending a prompt, ask yourself:

1. **What is the output?** (component, function, config, etc.)
2. **What are the inputs?** (props, parameters, data sources)
3. **What are the constraints?** (styling framework, existing patterns, accessibility)
4. **What are the edge cases?** (error states, empty states, loading states)
5. **What should it NOT do?** (no tests, no storybook, no extra files)

Spend 60 seconds writing a complete prompt. It saves the extra turns: $0.04 per task in the example above on Sonnet 5.5, twice that on Opus 5.5, and more in a longer session, where every extra turn reads a bigger context.

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

A single clarification loop adds at least one extra request: a cache read of the whole context, plus the new exchange and its output. At a 50K-token context that is $0.01 of cache read on Opus 5.5 ($0.005 on Sonnet 5.5) before output and thinking, and $0.04 at 200K. The bigger risk is the wait: if you take longer than the cache TTL to answer (five minutes on an API key), the next request re-writes the whole context instead, $0.25 at 50K on Opus 5.5 (computed: 50,000 x $0.20/1M read vs 50,000 x $5/1M write, [Anthropic pricing page](https://platform.claude.com/docs/en/about-claude/pricing)).

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

This single CLAUDE.md entry removes the clarification turns it answers in advance; no published figure says how many.

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

**Estimated savings: no published figure.**

---

## Using /compact at Natural Breakpoints

### How /compact Works

The `/compact` command tells Claude Code to compress the conversation history. It summarizes previous turns into a compact form, dramatically reducing the input tokens for subsequent turns.

- **Automatic trigger** (Anthropic's docs): Claude Code auto-compacts when the context nears the window, at about **967K tokens** by default on 1M-window models (Fable, Sonnet 5 and later, Haiku 5.5, Opus 4.7 and later). `/autocompact` sets the point anywhere from 100K to 1M and is saved per model since v2.1.288 (2026-10-02); subagents get their own `autoCompactWindow` since v2.1.296 (2026-10-09) ([model-config page](https://code.claude.com/docs/en/model-config), [changelog](https://code.claude.com/docs/en/changelog)).

Based on community research into Claude Code's observed behavior (not documented by Anthropic), here are more specifics:

- **What is preserved**: After compaction, the **4 most recent messages** are preserved verbatim. Everything older is replaced with a summary.
- **What the summary contains**: The generated summary includes tool mentions from the session, up to 3 recent user requests, up to 8 key files that were referenced, and an inference of the current work being done. This is designed to retain enough context for Claude to continue working without losing track of the task.
- **Manual /compact is still valuable**: Even though auto-compaction exists, running `/compact` manually before the threshold gives you more control over the timing. You can also provide a focus hint (e.g., `/compact Focus on the auth refactor`) to influence what the summary prioritizes.

### What /clear, /compact and /rewind Cost

From Anthropic's prompt-caching page for Claude Code (code.claude.com/docs/en/prompt-caching):

| Command | What it costs | Cache effect |
|---------|---------------|--------------|
| `/clear` | Nothing | Starts fresh; the next turn builds a new cache |
| `/compact` | A summarization request that reads the prefix from cache while it is warm, so a fraction of the context size. After a break longer than the cache TTL it reprocesses the full history uncached | Compaction rebuilds the conversation layer, so later turns re-cache it |
| `/rewind` | Returns to an already-cached prefix | Keeps the cache |

So compact **before** a break, not after one. The TTL is one hour for the main conversation on a Claude subscription within plan usage, and five minutes on an API key, a cloud provider, or once you draw on usage credits (set it with `promptCacheTtl` or `CLAUDE_CODE_PROMPT_CACHE_TTL`, Claude Code v2.1.242+). `/usage` shows a `Prompt cache (main)` line with hit share and whether the cache is warm (v2.1.251+).

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
- /compact: History compressed from 15K tokens (10 turns x 1,500 at the calculator defaults) to a 2K summary
- Turns 11-20: Start with small context, normal growth
- /compact: Compressed again
- Turns 21-30: Start with small context

**Computed:** at the calculator defaults at the top of this guide, those two compactions make the 30-turn session about 6% *more* expensive on Opus 5.5 or Sonnet 5.5 ($0.785 vs $0.739 on Opus 5.5): the history they remove was already billing at the cache-read rate, and each 2K summary bills as output. On an 80-turn session, compacting every 20 turns saves about 20% ($2.01 vs $2.51 on Opus 5.5). Compact long sessions, and compact for focus; on short ones it does not pay.

**Measured elsewhere:** compaction cut cost 32% and pruning stale tool results 39% on Anthropic's long triage run, and saved nothing on short loops ([cost-optimization guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence)). In Anthropic's [cookbook](https://platform.claude.com/cookbook/cost-optimization-cost-optimization) loop, compaction cut 16% and jagged pruning 29%.

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
Implement feature (6 turns)
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
50 changes/day x $0.0123/commit (Sonnet 5.5) = $0.62/day = $13.54/month

With manual commits at logical boundaries:
10 commits/day x $0.0041/commit (Haiku 5.5) = $0.04/day = $0.91/month

Savings: $12.63/month per developer
```

Computed at the calculator defaults at the top of this guide, 22 working days. A Sonnet 5.5 commit turn is the average turn of a 30-turn session ($0.37 / 30). A Haiku 5.5 commit through a `model: haiku` command switches model mid-session, so Haiku writes the whole context to its own cache first: 30,950 tokens (the average prompt) x $0.125/1M + 500 output x $0.50/1M = $0.0041. That is still below the Sonnet 5.5 turn, which pays $10/1M for its output and $2.50/1M to write the new exchange, while Haiku 5.5 writes the whole context for $0.125/1M as long as the prompt stays under 100K. On legacy Haiku 4.5 the same switch costs $0.041 per commit ($1.25/1M write), more than staying on Sonnet 5.5: $9.06/month for the manual-commit line.

---

## When NOT to Use Claude Code

The most cost-effective Claude Code technique is knowing when not to use it at all.

### Tasks That Are Cheaper to Do Manually

| Task | Claude Code Cost (one Sonnet 5.5 turn) | Manual Time | Verdict |
|------|:--------------------------------------:|:-----------:|---------|
| Change one line of code | $0.012 | 10 seconds | **Manual** |
| Rename a local variable (1 file) | $0.012 | 15 seconds (IDE rename) | **Manual** |
| Fix a typo | $0.012 | 5 seconds | **Manual** |
| Toggle a boolean config | $0.012 | 3 seconds | **Manual** |
| Delete a file | $0.012 | 2 seconds | **Manual** |
| Add a blank line | $0.012 | 1 second | **Manual** |

> Computed at the calculator defaults at the top of this guide: each of these is one turn, priced as the average turn of a 30-turn Sonnet 5.5 session ($0.37 / 30 = $0.012). As the first turn of a fresh session it is $0.028, because that turn writes the whole 9,200-token prompt to the cache; on Opus 5.5 a fresh one-turn session is $0.056 (9,200 x $5/1M + 500 x $20/1M). Manual times are illustrative.

**Rule of thumb**: If you can do it faster than typing the prompt, do it manually. Claude Code's minimum cost per turn is about $0.0014 on Haiku 5.5 ($0.014 on legacy Haiku 4.5): a one-turn session at the calculator defaults at the top of this guide writes a 9,200-token prompt to the cache and returns 500 output tokens. If the task takes under 30 seconds to do manually, it is not worth the token cost or the latency of waiting for a response.

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

Here is what a cost-optimized Claude Code session looks like in practice. The phases add up to the 12 turns priced in the comparison below; the turn counts are illustrative.

### Phase 1: Setup (1 turn)
- Start with Sonnet as default model
- CLAUDE.md is lean (<150 lines) and includes model routing guidelines
- `permissions.deny` `Read(...)` rules in `.claude/settings.json` keep Claude out of build output, dependencies and lock files (`.claudeignore` is not a Claude Code feature -- move any patterns you have there into Read rules)

### Phase 2: Plan (2 turns)
- Use plan mode or explicit "analyze and plan" instructions
- Review the plan, refine once
- Skip `/compact` on a session this short: it costs more than it saves (see [Cost Impact](#cost-impact)); compact after planning only when a long implementation follows

### Phase 3: Implement (7 turns)
- Execute the plan step by step
- Use TodoWrite for multi-step work
- Delegate file searches and simple subtasks to subagents
- Batch related changes into single turns
- Use commands for repetitive operations

### Phase 4: Review and Commit (2 turns)
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
| Unoptimized (all Opus 5.5, no planning, no batching) | 25 | $0.024 | $0.60 |
| Partially optimized (Sonnet 5.5 default, some planning) | 18 | $0.012 | $0.21 |
| Fully optimized (Sonnet 5.5, planning and batching cut it to 12 turns) | 12 | $0.012 | $0.14 |

**Fully optimized is 76% cheaper** than the unoptimized approach, for the same end result (computed at the calculator defaults at the top of this guide: $0.143 vs $0.603; on legacy Opus 5 the unoptimized session is $0.91 and the gap is 84%). About two-thirds of the saving is the model price, Sonnet 5.5 at half Opus 5.5's rate; the rest is the turn count, which is illustrative. `/compact` is left out: one compaction at turn 6 would make this 12-turn session 19% dearer (computed, see [Cost Impact](#cost-impact)).

One Opus-specific caveat for the per-turn numbers above: on Opus 5.5 adaptive thinking is always on and reasoning tokens bill as output at $20/MTok; effort (default `medium`) is the only control. And prompts written for an older model make the new one over-work: in Anthropic's published run, prompts written for Opus 4.8 cost 36% more per ticket on Opus 5 for no accuracy gain, and audited they were 14% cheaper and more accurate. Opus 5 also self-verifies on its own, so a carried-over "double-check your work" instruction pays twice. Re-audit CLAUDE.md when you change models, or your per-turn cost ($0.024 on Opus 5.5 at the calculator defaults) drifts upward on its own.

---

## Summary of Savings by Pattern

| Pattern | Savings (source) | Effort to Adopt |
|---------|:----------------:|:---------------:|
| Plan mode before implementation | No published figure | None (built-in) |
| Subagent delegation | No Claude Code figure (cookbook loop: 78%) | Low (CLAUDE.md update) |
| Custom commands for repetitive tasks | No published figure (commands load only when invoked and keep the cache) | Medium (one-time setup) |
| Batch operations | $0.01 per avoided turn at 50K context (Opus 5.5) | None (habit change) |
| Front-loaded requirements | No published figure | None (habit change) |
| Eliminate clarification loops | No published figure | Low (better prompts) |
| TodoWrite for multi-step work | No published figure | None (built-in) |
| /compact at breakpoints | 32% (Anthropic long triage run; nothing on short loops) | None (built-in) |
| Smart commit strategy | No published figure | Low (CLAUDE.md update) |
| Knowing when not to use Claude Code | No published figure | None (judgment) |

> No published measurement covers these workflow patterns, alone or combined. The measured levers are in the README's [How far can you actually go?](../README.md#how-far-can-you-actually-go): cache pricing, Batch (50% off), effort (Opus 5.5 at medium costs about 70% of high on SWE-bench Pro, per Anthropic's [cost-optimization guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence)), and model routing.

---

## Next Steps

- Add the `/compact` habit to your workflow today for long sessions (zero effort; on short ones it costs more than it saves)
- Create a custom command for each of your three most common tasks
- Add subagent and model routing guidelines to your CLAUDE.md
- Read [Guide 05: Team Budgeting](05-team-budgeting.md) to scale these patterns across a team

---

*[Back to README](../README.md) | [Previous: Model Selection](03-model-selection.md) | [Next: Team Budgeting](05-team-budgeting.md)*
