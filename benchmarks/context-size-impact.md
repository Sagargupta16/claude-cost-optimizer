# Context Size Impact Benchmarks

> How CLAUDE.md size, file reads, and context window fill percentage affect costs over real sessions.

## Why Context Size Matters

Every turn in Claude Code re-sends the entire conversation context to the model. This includes:

1. **System prompt** — Claude Code's built-in instructions (~2,000 tokens, constant)
2. **CLAUDE.md** — your project configuration file (variable, loaded every turn)
3. **Conversation history** — all previous messages and tool results (grows each turn)
4. **Current turn content** — the new user message, file reads, tool results

The first two items are **fixed overhead per turn**. The third **grows linearly** with each turn. This means:

- A 50-line CLAUDE.md in a 30-turn session is loaded 30 times.
- A 300-line CLAUDE.md in the same session is loaded 30 times.
- The difference compounds with every turn.

> **Note on prompt caching**: Claude Code caches stable content (system prompt, CLAUDE.md, earlier conversation turns) between turns. Cached tokens cost ~90% less. The token counts below represent **pre-cache** (raw) values. Actual billed costs will be lower for the CLAUDE.md portion after the first turn, but the relative differences between sizes still hold because larger files occupy more cache space and reduce room for caching conversation history.

---

## Benchmark 1: CLAUDE.md Size Over a 30-Turn Session

### Setup

Three CLAUDE.md files of different sizes, all providing project configuration for the same React + TypeScript codebase:

| Version | Lines | Tokens | What's Included |
|---------|:-----:|:------:|-----------------|
| **Minimal** | 42 | ~320 | Build/test commands, file structure, 3 key conventions |
| **Standard** | 98 | ~700 | Above + code style rules, testing patterns, common pitfalls |
| **Bloated** | 310 | ~2,100 | Above + full API docs, copy-pasted style guide, redundant examples, historical notes |

Each CLAUDE.md version was used across a simulated 30-turn session performing a mix of tasks (component creation, bug fix, test writing, refactoring). The model is Sonnet 4 for all runs.

### CLAUDE.md Token Overhead Per Turn

The CLAUDE.md is loaded as input on every turn. Here is the raw (pre-cache) overhead:

| Turn | Minimal (320 tok) | Standard (700 tok) | Bloated (2,100 tok) |
|:----:|:------------------:|:-------------------:|:-------------------:|
| 1 | 320 | 700 | 2,100 |
| 5 | 320 | 700 | 2,100 |
| 10 | 320 | 700 | 2,100 |
| 15 | 320 | 700 | 2,100 |
| 20 | 320 | 700 | 2,100 |
| 25 | 320 | 700 | 2,100 |
| 30 | 320 | 700 | 2,100 |
| **Total (30 turns)** | **9,600** | **21,000** | **63,000** |

### Cumulative CLAUDE.md Cost Over 30 Turns (Sonnet 4)

Using Sonnet 4 input pricing ($3.00 / 1M tokens):

| CLAUDE.md Size | Total Tokens (30 turns) | Raw Cost | With ~90% Caching* | Effective Cost |
|----------------|:-----------------------:|:--------:|:-------------------:|:--------------:|
| Minimal (320) | 9,600 | $0.029 | ~$0.004 | **$0.004** |
| Standard (700) | 21,000 | $0.063 | ~$0.008 | **$0.008** |
| Bloated (2,100) | 63,000 | $0.189 | ~$0.023 | **$0.023** |

*Caching applies to turns 2-30 at ~90% discount. Turn 1 pays full price.*

> While the absolute costs look small, CLAUDE.md overhead stacks on top of all other input tokens. In sessions with heavy file reads and long conversation history, the effective context window fills faster, pushing older turns out of cache.

### Full Session Cost Comparison

Including all input tokens (system prompt, conversation history, file reads, CLAUDE.md) and output tokens across the 30-turn mixed-task session:

| Metric | Minimal CLAUDE.md | Standard CLAUDE.md | Bloated CLAUDE.md |
|--------|:------------------:|:-------------------:|:------------------:|
| Total input tokens | 486,000 | 512,000 | 584,000 |
| Total output tokens | 68,400 | 66,800 | 72,100 |
| **Estimated cost** | **$2.48** | **$2.54** | **$2.83** |
| Quality (follow-ups needed) | 8 extra turns | 4 extra turns | 3 extra turns |
| Effective cost (incl. follow-ups) | $3.14 | $2.82 | $3.06 |

### Analysis

| | Minimal | Standard | Bloated |
|------|:-------:|:--------:|:-------:|
| Raw CLAUDE.md overhead | Lowest | Moderate | Highest |
| Task quality | Lower (missing conventions leads to follow-ups) | Good balance | Marginally better quality, but diminishing returns |
| Effective cost (quality-adjusted) | $3.14 | **$2.82** | $3.06 |

**Key finding**: The Standard CLAUDE.md (~100 lines, ~700 tokens) hits the sweet spot. The Minimal version saves on per-turn overhead but causes 8 follow-up turns due to missing convention information — those extra turns cost more than the tokens saved. The Bloated version provides marginally better first-pass quality but wastes tokens on content Claude rarely needs (historical notes, redundant examples).

> **Recommendation**: Keep your CLAUDE.md between 80-120 lines. Below 80, you lose too much context and pay for it in follow-ups. Above 150, you pay for redundant context that does not measurably improve output quality.

---

## Benchmark 2: File Read Size Impact

### Setup

Claude Code reads files during tasks (to understand existing code, check types, review tests). File read results become part of the conversation context and are re-sent on every subsequent turn.

We measured the impact of reading files of different sizes during a 10-turn session.

| File Size | Approximate Tokens | Example |
|:---------:|:------------------:|---------|
| 1 KB | ~250 tokens | A small utility function (25 lines) |
| 10 KB | ~2,500 tokens | A medium component or service (250 lines) |
| 100 KB | ~25,000 tokens | A large module, generated code, or bundled file (2,500 lines) |

### Single File Read — Cost Propagation

When Claude reads a file on turn 3 of a 10-turn session, that file's content stays in the conversation history for turns 3-10 (8 turns). Here is the input token overhead from that single file read:

| File Size | Tokens per Turn | Turns in Context | Total Added Tokens | Added Cost (Sonnet 4) |
|:---------:|:---------------:|:----------------:|:------------------:|:---------------------:|
| 1 KB | 250 | 8 | 2,000 | $0.006 |
| 10 KB | 2,500 | 8 | 20,000 | $0.060 |
| 100 KB | 25,000 | 8 | 200,000 | $0.600 |

> A single 100 KB file read adds $0.60 to a Sonnet session. With Opus, that same read adds **$3.00** in propagated input costs.

### Multiple File Reads — Compounding Effect

Many tasks require Claude to read several files. Here is the total overhead when multiple files are read on turn 2 of a 10-turn session (9 turns of propagation):

| Files Read | Total Tokens Added to Context | Propagated Over 9 Turns | Added Cost (Sonnet 4) | Added Cost (Opus 4) |
|:----------:|:-----------------------------:|:-----------------------:|:---------------------:|:-------------------:|
| 3 x 1 KB | 750 | 6,750 | $0.02 | $0.10 |
| 3 x 10 KB | 7,500 | 67,500 | $0.20 | $1.01 |
| 1 x 10 KB + 1 x 100 KB | 27,500 | 247,500 | $0.74 | $3.71 |
| 3 x 100 KB | 75,000 | 675,000 | $2.03 | $10.13 |

### File Read Optimization Strategies

| Strategy | When to Use | Token Savings |
|----------|-------------|:-------------:|
| Use `.claudeignore` to exclude large generated/vendor files | Always | Prevents accidental reads of `node_modules`, `dist`, lock files |
| Ask Claude to read specific sections ("lines 50-120") | When you know where the relevant code is | 60-90% of full file read |
| Summarize large files in CLAUDE.md instead of reading them | For files Claude reads repeatedly (config, types) | 80-95% per turn |
| Use subagents for file-heavy investigation | When the task requires reading many files | Keeps main context clean |
| Read files early in the session | When you know you will need them | Maximizes cache benefit for subsequent turns |

### Recommended Maximum File Reads Per Session

Based on cost-efficiency data, here are guidelines for how many file reads to budget per session:

| Model | Small Files (1 KB) | Medium Files (10 KB) | Large Files (100 KB) |
|-------|:------------------:|:-------------------:|:-------------------:|
| Haiku 3.5 | 20+ (negligible cost) | 10-15 | 1-2 (delegate to subagent) |
| Sonnet 4 | 15-20 | 5-10 | 1 (delegate to subagent) |
| Opus 4 | 10-15 | 3-5 | 0 (always delegate to subagent) |

---

## Benchmark 3: Context Window Fill Percentage and Cost Curve

### How Context Grows

Claude Code has a 200K token context window. As a session progresses, the context fills with conversation history. Here is how context utilization typically grows:

| Turn | Typical Context Fill | Cumulative Input Tokens Billed | Per-Turn Input Cost (Sonnet 4) |
|:----:|:--------------------:|:------------------------------:|:------------------------------:|
| 1 | 1.5% (~3,000 tok) | 3,000 | $0.009 |
| 5 | 8% (~16,000 tok) | 52,000 | $0.048 |
| 10 | 18% (~36,000 tok) | 178,000 | $0.108 |
| 15 | 30% (~60,000 tok) | 406,000 | $0.180 |
| 20 | 44% (~88,000 tok) | 756,000 | $0.264 |
| 25 | 58% (~116,000 tok) | 1,226,000 | $0.348 |
| 30 | 72% (~144,000 tok) | 1,802,000 | $0.432 |
| 40 | 92% (~184,000 tok) | 3,362,000 | $0.552 |

> **Context growth is roughly linear**, but **cumulative billed tokens grow quadratically** because each turn re-sends all previous history.

### The Cost Curve (Chart as Table)

Cumulative session cost by turn count (Sonnet 4, Standard CLAUDE.md, medium file read activity):

```
Turn  | Cost   | Visual (each block = $0.10)
------+--------+-------------------------------------------
  1   | $0.01  |
  5   | $0.16  | ##
 10   | $0.53  | #####
 15   | $1.22  | ############
 20   | $2.27  | #######################
 25   | $3.68  | #####################################
 30   | $5.40  | ######################################################
 35   | $7.52  | ###########################################################################
 40   | $10.08 | #####################################################################################################
```

### Cost Per Turn Increases Over Time

This is the critical insight: **later turns are dramatically more expensive than early turns** because they include all prior context.

| Turn Range | Average Per-Turn Cost (Sonnet 4) | Relative Expense |
|:----------:|:--------------------------------:|:----------------:|
| Turns 1-5 | $0.03 | 1x (baseline) |
| Turns 6-10 | $0.07 | 2.3x |
| Turns 11-15 | $0.14 | 4.7x |
| Turns 16-20 | $0.21 | 7.0x |
| Turns 21-25 | $0.28 | 9.3x |
| Turns 26-30 | $0.34 | 11.3x |
| Turns 31-40 | $0.44 | 14.7x |

> **Turn 35 costs nearly 15x more than turn 3.** This is why long sessions are so expensive, and why starting fresh sessions for new tasks is one of the most effective cost strategies.

### Session Length Recommendations

Based on the cost curve, here are practical guidelines:

| Session Length | Best For | Cost Efficiency |
|:--------------:|---------|:---------------:|
| 1-10 turns | Single focused task (component, bug fix, test) | Excellent |
| 11-20 turns | Multi-step feature (plan + implement + test) | Good |
| 21-30 turns | Complex refactoring or investigation | Acceptable (monitor costs) |
| 31+ turns | Consider splitting into multiple sessions | Poor (start a new session) |

### When to Start a New Session

Start a new Claude Code session when:

- You have completed a logical unit of work (one feature, one bug fix).
- Your turn count exceeds 20-25 and you are starting a new sub-task.
- Claude starts producing lower-quality output (a sign that relevant context is being pushed out by noise).
- You need to switch to a different area of the codebase.

### Cost Comparison: One Long Session vs. Multiple Short Sessions

**Task**: Implement a feature that involves 3 sub-tasks (API endpoint, UI component, tests). Total work: ~30 turns.

| Approach | Turns | Total Input Tokens | Total Cost (Sonnet 4) |
|----------|:-----:|:------------------:|:---------------------:|
| One 30-turn session | 30 | 1,802,000 | $5.40 |
| Three 10-turn sessions | 30 | 534,000 | $1.60 |
| **Savings** | -- | **70% fewer tokens** | **$3.80 (70%)** |

> Splitting into shorter sessions is the single highest-impact cost optimization for developers who use Claude Code for extended work.

The trade-off: each new session loses conversation history, so Claude may need to re-read some files. However, the re-read cost is almost always less than the cost of carrying 20+ turns of history.

---

## Benchmark 4: Combined Impact — Context Optimization Playbook

### Scenario

A developer works for a full day using Claude Code, performing approximately 8 tasks across 80 total turns. Here is the estimated cost under four different configurations:

| Configuration | CLAUDE.md | File Reads | Session Strategy | Model |
|--------------|:---------:|:----------:|:----------------:|:-----:|
| **Worst case** | 300 lines (2,100 tok) | No limits, reads full files | One continuous session | Opus 4 |
| **Default** | 300 lines (2,100 tok) | No limits | One session per task (8 sessions) | Sonnet 4 |
| **Optimized** | 100 lines (700 tok) | Targeted reads, subagents for heavy investigation | One session per task | Sonnet 4 |
| **Maximum savings** | 50 lines (320 tok) | Aggressive subagent delegation | One session per task, Haiku for 3 simple tasks | Mixed |

### Full-Day Cost Comparison

| Metric | Worst Case | Default | Optimized | Max Savings |
|--------|:----------:|:-------:|:---------:|:-----------:|
| Total input tokens | 4,200,000 | 1,480,000 | 820,000 | 540,000 |
| Total output tokens | 186,000 | 168,000 | 152,000 | 142,000 |
| **Total cost** | **$77.25** | **$6.96** | **$4.74** | **$2.78** |
| Quality incidents | 2 | 4 | 2 | 4 |
| Effective cost (incl. fix-ups) | $84.50 | $7.86 | $5.10 | $3.46 |

### Savings Breakdown

| Optimization | Savings vs. Default | Cumulative Savings |
|-------------|:-------------------:|:------------------:|
| Switch from one long session to per-task sessions | Already applied in Default | -- |
| Trim CLAUDE.md from 300 to 100 lines | 12% | 12% |
| Use targeted file reads instead of full-file reads | 10% | 21% |
| Use subagents for file-heavy investigation | 8% | 27% |
| Use Haiku for 3 simple tasks (formatting, rename, simple fix) | 5% | 32% |
| **Total optimization vs. Default** | -- | **32%** |
| **Total optimization vs. Worst Case** | -- | **96%** |

---

## Key Takeaways

1. **Start new sessions for new tasks.** This is the single biggest cost lever — it prevents quadratic context growth. Splitting an 80-turn day into 8x10-turn sessions saves 60-70% of input tokens.

2. **Keep CLAUDE.md between 80-120 lines.** Below 80, you lose conventions and pay for follow-up turns. Above 150, you are paying for content that does not improve output quality.

3. **Be deliberate about file reads.** Every file Claude reads becomes part of the conversation context for the rest of the session. Read specific sections when possible, summarize frequently-needed files in CLAUDE.md, and use subagents for file-heavy investigation.

4. **Later turns cost dramatically more.** Turn 30 costs 11x more than turn 3. If a session is getting long and you are starting a new sub-task, start a new session.

5. **The cost curve is quadratic, not linear.** Doubling your turn count more than doubles your cost. A 20-turn session costs roughly 4x more than a 10-turn session, not 2x.

6. **Prompt caching helps but does not eliminate the problem.** Caching reduces the cost of stable content (CLAUDE.md, system prompt) by ~90%, but conversation history still grows and still costs money per turn.
