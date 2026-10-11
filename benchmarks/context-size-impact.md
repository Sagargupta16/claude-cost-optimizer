# Context Size Impact Benchmarks

> How CLAUDE.md size, file reads, and context window fill percentage affect costs over real sessions.

## Why Context Size Matters

Every turn in Claude Code re-sends the entire conversation context to the model. This includes:

1. **System prompt** -- Claude Code's built-in instructions (~2,000 tokens, constant)
2. **CLAUDE.md** -- your project configuration file (variable, loaded every turn)
3. **Conversation history** -- all previous messages and tool results (grows each turn)
4. **Current turn content** -- the new user message, file reads, tool results

The first two items are **fixed overhead per turn**. The third **grows linearly** with each turn. This means:

- A 50-line CLAUDE.md in a 30-turn session is loaded 30 times.
- A 300-line CLAUDE.md in the same session is loaded 30 times.
- The difference compounds with every turn.

> **Note on prompt caching**: Claude Code caches the whole unchanged prefix (system prompt, CLAUDE.md, earlier conversation turns) between turns. Cached tokens cost 90% less (95% on Opus 5.5 and Sonnet 5.5, 97.5% on Fable 5.1) ([prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)). The token counts below are pre-cache (raw) values; after turn 1 every unchanged token, CLAUDE.md and history alike, bills at the cache-read rate ([Claude Code prompt caching](https://code.claude.com/docs/en/prompt-caching)), so the relative differences between sizes hold at that lower rate.

---

## Benchmark 1: CLAUDE.md Size Over a 30-Turn Session

### Setup

Three CLAUDE.md files of different sizes, all providing project configuration for the same React + TypeScript codebase:

| Version | Lines | Tokens | What's Included |
|---------|:-----:|:------:|-----------------|
| **Minimal** | 42 | 420 | Build/test commands, file structure, 3 key conventions |
| **Standard** | 98 | 980 | Above + code style rules, testing patterns, common pitfalls |
| **Bloated** | 310 | 3,100 | Above + full API docs, copy-pasted style guide, redundant examples, historical notes |

Token counts are lines x 10, the repo's per-line figure, measured on this repo's 15 CLAUDE.md files (`templates/CLAUDE.md/**` plus the root `CLAUDE.md`): 20,161 cl100k tokens over 2,048 lines, 9.8 per line counting blank lines (12.3 per non-blank line). The Opus 4.7+ tokenizer produces about 30% more tokens for the same text ([pricing page](https://platform.claude.com/docs/en/about-claude/pricing)); Sonnet 4.6, used here, does not use it.

Each CLAUDE.md version was used across a simulated 30-turn session performing a mix of tasks (component creation, bug fix, test writing, refactoring). The model is Sonnet 4.6 for all runs.

### CLAUDE.md Token Overhead Per Turn

The CLAUDE.md is loaded as input on every turn. Here is the raw (pre-cache) overhead:

| Turn | Minimal (420 tok) | Standard (980 tok) | Bloated (3,100 tok) |
|:----:|:------------------:|:-------------------:|:-------------------:|
| 1 | 420 | 980 | 3,100 |
| 5 | 420 | 980 | 3,100 |
| 10 | 420 | 980 | 3,100 |
| 15 | 420 | 980 | 3,100 |
| 20 | 420 | 980 | 3,100 |
| 25 | 420 | 980 | 3,100 |
| 30 | 420 | 980 | 3,100 |
| **Total (30 turns)** | **12,600** | **29,400** | **93,000** |

### Cumulative CLAUDE.md Cost Over 30 Turns (Sonnet 4.6)

Using Sonnet 4.6 input pricing ($3.00 / 1M tokens):

| CLAUDE.md Size | Total Tokens (30 turns) | Raw Cost | With 90% Caching* | Effective Cost |
|----------------|:-----------------------:|:--------:|:-------------------:|:--------------:|
| Minimal (420) | 12,600 | $0.038 | $0.005 | **$0.005** |
| Standard (980) | 29,400 | $0.088 | $0.012 | **$0.012** |
| Bloated (3,100) | 93,000 | $0.279 | $0.039 | **$0.039** |

*Caching applies to turns 2-30 at a 90% discount (Sonnet 4.6 reads at 0.1x). Turn 1 writes the cache at 1.25x the input price ([prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)). Computed: CLAUDE.md tokens x $3.75/1M on turn 1 + 29 x CLAUDE.md tokens x $0.30/1M (Standard: $0.0037 + $0.0085 = $0.012).*

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

*These session totals and follow-up counts are simulated figures from an earlier, pre-cache version of this benchmark. They were not re-derived with the Benchmark 3 formula, and the follow-up counts are not measured.*

### Analysis

| | Minimal | Standard | Bloated |
|------|:-------:|:--------:|:-------:|
| Raw CLAUDE.md overhead | Lowest | Moderate | Highest |
| Task quality | Lower (missing conventions leads to follow-ups) | Good balance | Marginally better quality, but diminishing returns |
| Effective cost (quality-adjusted) | $3.14 | **$2.82** | $3.06 |

**Key finding**: The Standard CLAUDE.md (~100 lines, ~980 tokens) hits the sweet spot. The Minimal version saves on per-turn overhead but causes 8 follow-up turns due to missing convention information -- those extra turns cost more than the tokens saved. The Bloated version provides marginally better first-pass quality but wastes tokens on content Claude rarely needs (historical notes, redundant examples).

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

### Single File Read -- Cost Propagation

When Claude reads a file on turn 3 of a 10-turn session, that file's content stays in the conversation history for turns 3-10 (8 turns). Here is the input token overhead from that single file read:

| File Size | Tokens per Turn | Turns in Context | Total Added Tokens | Added Cost (Sonnet 5.5) |
|:---------:|:---------------:|:----------------:|:------------------:|:---------------------:|
| 1 KB | 250 | 8 | 2,000 | $0.004 |
| 10 KB | 2,500 | 8 | 20,000 | $0.040 |
| 100 KB | 25,000 | 8 | 200,000 | $0.400 |

> A single 100 KB file read adds $0.40 to a Sonnet 5.5 session ($2/1M input, the same on legacy Sonnet 5; $0.60 on Sonnet 4.6 at $3/1M). With Opus 5.5 ($4/1M), that same read adds **$0.80** in propagated input costs ($1.00 on legacy Opus 5).

### Multiple File Reads -- Compounding Effect

Many tasks require Claude to read several files. Here is the total overhead when multiple files are read on turn 2 of a 10-turn session (9 turns of propagation):

| Files Read | Total Tokens Added to Context | Propagated Over 9 Turns | Added Cost (Sonnet 5.5) | Added Cost (Opus 5.5) |
|:----------:|:-----------------------------:|:-----------------------:|:---------------------:|:-------------------:|
| 3 x 1 KB | 750 | 6,750 | $0.01 | $0.03 |
| 3 x 10 KB | 7,500 | 67,500 | $0.14 | $0.27 |
| 1 x 10 KB + 1 x 100 KB | 27,500 | 247,500 | $0.50 | $0.99 |
| 3 x 100 KB | 75,000 | 675,000 | $1.35 | $2.70 |

Pre-cache input cost at $2/1M (Sonnet 5.5, and legacy Sonnet 5) and $4/1M (Opus 5.5). On legacy Opus 5 ($5/1M) each Opus figure is 25% higher.

### File Read Optimization Strategies

| Strategy | When to Use | Token Savings |
|----------|-------------|:-------------:|
| Add `Read(...)` deny rules to `permissions.deny` for large generated/vendor files (`.claudeignore` is not a Claude Code feature) | Always | Keeps Claude's file tools out of `node_modules`, `dist`, lock files; no published savings figure |
| Ask Claude to read specific sections ("lines 50-120") | When you know where the relevant code is | 1 - lines read / file length for that read (lines 50-120 of a 2,000-line file: 96% fewer tokens) |
| Summarize large files in CLAUDE.md instead of reading them | For files Claude reads repeatedly (config, types) | No published figure; a summary in CLAUDE.md loads every session, so it pays off only for files Claude would otherwise read in most sessions |
| Use subagents for file-heavy investigation | When the task requires reading many files | Keeps main context clean |
| Read files early in the session | When you know you will need them | Maximizes cache benefit for subsequent turns |

### Recommended Maximum File Reads Per Session

Based on cost-efficiency data, here are guidelines for how many file reads to budget per session:

| Model | Small Files (1 KB) | Medium Files (10 KB) | Large Files (100 KB) |
|-------|:------------------:|:-------------------:|:-------------------:|
| Haiku 5.5 | 20+ (negligible cost) | 10-15 | 1-2 (delegate to subagent), and keep the prompt under 100K tokens or every token in the request pays 5x |
| Haiku 4.5 (legacy) | 20+ (negligible cost) | 10-15 | 1-2 (delegate to subagent) |
| Sonnet 5.5 | 15-20 | 5-10 | 1 (delegate to subagent) |
| Opus 5.5 | 10-15 | 5-8 | 1-2 (delegate to subagent) |

---

## Benchmark 3: Context Window Fill Percentage and Cost Curve

### How Context Grows

Claude Code uses the model's full context window: **1M tokens on Opus 5.5 and Opus 5 (at standard rates, no long-context premium), Opus 4.8, Opus 4.7, Opus 4.6, Sonnet 5.5, Sonnet 5, and Sonnet 4.6**, **1M on Haiku 5.5, which is not at one rate -- a request whose prompt is over 100K tokens pays $0.50/$2.50 instead of $0.10/$0.50**, and **200K on Haiku 4.5 (legacy)**. As a session progresses, the context fills with conversation history. The figures below are **computed, not measured**: this repo's calculator defaults (3,500-token system prompt, 100-line CLAUDE.md at the measured 10 tokens per line (1,000 tokens, see Benchmark 1), 3,000 tokens of MCP tool definitions, one 2,000-token file read in context, 1,500 tokens of history added per turn, 500 output tokens per turn) on Sonnet 4.6, billed the way Claude Code caches a conversation: "the prefix is the entire previous request and only the latest exchange is new" ([Claude Code prompt caching](https://code.claude.com/docs/en/prompt-caching)). The fill column is a share of a 200K window, since most sessions stay well under the 1M cap.

*Computed: prompt at turn n = 9,500 + (n - 1) x 1,500 tokens. Turn 1 writes the whole prompt to cache at $3.75/1M (1.25x). Every later turn reads the previous prompt at $0.30/1M (0.1x) and writes the 1,500 new tokens at $3.75/1M; output is 500 x $15/1M = $0.0075 per turn. Rates from [docs/pricing-data.md](../docs/pricing-data.md).*

| Turn | Context at That Turn | Cumulative Input Tokens Sent | Per-Turn Input Cost (Sonnet 4.6) |
|:----:|:--------------------:|:------------------------------:|:------------------------------:|
| 1 | 5% (9,500 tok) | 9,500 | $0.0356 |
| 5 | 8% (15,500 tok) | 62,500 | $0.0098 |
| 10 | 12% (23,000 tok) | 162,500 | $0.0121 |
| 15 | 15% (30,500 tok) | 300,000 | $0.0143 |
| 20 | 19% (38,000 tok) | 475,000 | $0.0166 |
| 25 | 23% (45,500 tok) | 687,500 | $0.0188 |
| 30 | 27% (53,000 tok) | 937,500 | $0.0211 |
| 40 | 34% (68,000 tok) | 1,550,000 | $0.0256 |

> **Context grows linearly and the tokens sent grow quadratically**, because each turn re-sends all previous history. The bill grows far more slowly: after turn 1, everything already sent is a cache read at 0.1x input on Sonnet 4.6, and only the 1,500 new tokens are written at 1.25x. Turn 1 pays the most input of any turn in the table, because it writes the whole 9,500-token prompt to cache.

### The Cost Curve (Chart as Table)

Cumulative session cost by turn count (Sonnet 4.6, 100-line CLAUDE.md, one 2,000-token file read in context; computed with the formula above, input plus output):

```
Turn  | Cost   | Visual (each block = $0.02)
------+--------+-------------------------------------------
  1   | $0.04  | ##
  5   | $0.11  | #####
 10   | $0.20  | ##########
 15   | $0.31  | ###############
 20   | $0.42  | #####################
 25   | $0.55  | ############################
 30   | $0.69  | ##################################
 35   | $0.84  | ##########################################
 40   | $1.00  | ##################################################
```

### Cost Per Turn Increases Over Time

Later turns cost more than early ones because they carry all prior context, but with a warm cache the growth is a cache read at 0.1x input, so it is gradual (computed, input plus output, same formula):

| Turn Range | Average Per-Turn Cost (Sonnet 4.6) | Relative Expense |
|:----------:|:--------------------------------:|:----------------:|
| Turns 1-5 | $0.0219 | 1x (baseline) |
| Turns 6-10 | $0.0187 | 0.85x |
| Turns 11-15 | $0.0209 | 0.95x |
| Turns 16-20 | $0.0232 | 1.06x |
| Turns 21-25 | $0.0254 | 1.16x |
| Turns 26-30 | $0.0277 | 1.26x |
| Turns 31-40 | $0.0311 | 1.41x |

*Turns 1-5 average high because turn 1 writes the whole prompt to cache ($0.0431, against $0.0160 for turn 2).*

> **Turn 35 costs 1.9x turn 3 ($0.0308 vs $0.0164).** What makes a long session expensive is a cache miss: after a break longer than the cache lifetime, turn 35 re-writes its 59,000-token prefix for $0.22 on Sonnet 4.6, against $0.018 to read it (59,000 x $3.75/1M vs x $0.30/1M).

### Session Length Recommendations

Based on the cost curve, here are practical guidelines. The cost column is the computed average per turn for a session of that length (Sonnet 4.6, warm cache, same formula):

| Session Length | Best For | Cost per Turn (warm cache) |
|:--------------:|---------|:---------------:|
| 1-10 turns | Single focused task (component, bug fix, test) | $0.020 (10-turn session, $0.20) |
| 11-20 turns | Multi-step feature (plan + implement + test) | $0.021 (20-turn session, $0.42) |
| 21-30 turns | Complex refactoring or investigation | $0.023 (30-turn session, $0.69) |
| 31+ turns | Consider splitting into multiple sessions | $0.025 (40-turn session, $1.00); one cache miss re-writes 60K+ tokens |

### When to Start a New Session

Start a new Claude Code session when:

- You have completed a logical unit of work (one feature, one bug fix).
- Your turn count exceeds 20-25 and you are starting a new sub-task.
- Claude starts producing lower-quality output (a sign that relevant context is being pushed out by noise).
- You need to switch to a different area of the codebase.

### Cost Comparison: One Long Session vs. Multiple Short Sessions

**Task**: Implement a feature that involves 3 sub-tasks (API endpoint, UI component, tests). Total work: ~30 turns.

| Approach | Turns | Total Input Tokens | Total Cost (Sonnet 4.6) |
|----------|:-----:|:------------------:|:---------------------:|
| One 30-turn session | 30 | 937,500 | $0.689 |
| Three 10-turn sessions | 30 | 487,500 | $0.609 |
| **Savings** | -- | **48% fewer tokens** | **$0.080 (12%)** |

*Computed with the Benchmark 3 formula: one 30-turn session vs three 10-turn sessions at the same defaults, 500 output tokens per turn in both.*

> With prompt caching, splitting sessions sends far fewer tokens but saves less money, because the history it drops was billing at the cache-read rate. The same split saves 12% here, and 1.8% on Opus 5.5 or Sonnet 5.5, which read cache at 0.05x. An 80-turn day split into eight 10-turn sessions saves 40% on Sonnet 4.6 and 23% on Opus 5.5 or Sonnet 5.5 (computed, same defaults). For comparison, moving a task from Opus 5.5 to Haiku 5.5 cuts its per-token price 97.5% on prompts up to 100K tokens ([pricing page](https://platform.claude.com/docs/en/about-claude/pricing): $0.10 vs $4 input).

The trade-off: each new session loses conversation history, so Claude may need to re-read some files. Re-reading a 2,000-token file in a new session costs $0.0075 on Sonnet 4.6 (written to cache at $3.75/1M); carrying 20 turns of history (30,000 tokens) costs $0.009 in cache reads on every later turn (30,000 x $0.30/1M).

---

## Benchmark 4: Combined Impact -- Context Optimization Playbook

### Scenario

A developer works for a full day using Claude Code, performing 8 tasks across 80 total turns. The cost of each configuration below is **computed, not measured**, with the Benchmark 3 formula: the same 3,500-token system prompt, 3,000 tokens of MCP tool definitions, 1,500 tokens of history per turn and 500 output tokens per turn, each turn reading the previous request from cache and writing the new exchange at 1.25x. Only the parameters in the table change.

| Configuration | CLAUDE.md | File Reads | Session Strategy | Model |
|--------------|:---------:|:----------:|:----------------:|:-----:|
| **Worst case** | 300 lines (3,000 tok) | Full files: 2,000 tokens in context per turn | One continuous 80-turn session | Opus 4.8 |
| **Default** | 300 lines (3,000 tok) | Full files: 2,000 tokens per turn | One session per task (8 x 10 turns) | Sonnet 4.6 |
| **Optimized** | 100 lines (1,000 tok) | Targeted reads, assumed to halve file tokens: 1,000 per turn (subagents not modeled) | One session per task | Sonnet 4.6 |
| **Maximum savings** | 50 lines (500 tok) | Targeted reads, 1,000 per turn (subagents not modeled) | One session per task, Haiku 4.5 for 3 simple tasks | Sonnet 4.6 + Haiku 4.5 |

### Full-Day Cost Comparison

| Metric | Worst Case | Default | Optimized | Max Savings |
|--------|:----------:|:-------:|:---------:|:-----------:|
| Total input tokens | 5,660,000 | 1,460,000 | 1,220,000 | 1,180,000 |
| Total output tokens | 40,000 | 40,000 | 40,000 | 40,000 |
| **Total cost** | **$4.58** | **$1.73** | **$1.57** | **$1.16** |
| Quality incidents | Not measured | Not measured | Not measured | Not measured |
| Effective cost (incl. fix-ups) | Not measured | Not measured | Not measured | Not measured |

*Computed: rates from [docs/pricing-data.md](../docs/pricing-data.md) (Opus 4.8 $5/$25, cache read $0.50, 5-minute write $6.25; Sonnet 4.6 $3/$15, $0.30, $3.75; Haiku 4.5 $1/$5, $0.10, $1.25). Output is fixed at 500 tokens per turn, so the output row is the same in every column. Most of the worst case's gap is the model and the single session: the same 80-turn session on Sonnet 4.6 costs $2.75, and splitting it into 8 sessions takes it to the Default's $1.73 (37% less). CLAUDE.md token counts are lines x 10, the per-line figure measured in Benchmark 1.*

### Savings Breakdown

| Optimization | Savings vs. Default | Cumulative Savings |
|-------------|:-------------------:|:------------------:|
| Switch from one long session to per-task sessions | Already applied in Default (37% below the same day run as one Sonnet 4.6 session) | -- |
| Trim CLAUDE.md from 300 to 100 lines | 6.0% | 6.0% |
| Use targeted file reads instead of full-file reads (2,000 to 1,000 tokens per turn, assumed) | 3.0% | 9.0% |
| Use subagents for file-heavy investigation | Not modeled; no Claude Code measurement (Anthropic's [cookbook](https://platform.claude.com/cookbook/cost-optimization-cost-optimization) cut one agent loop 78% with a subagent) | -- |
| Trim CLAUDE.md further, from 100 to 50 lines | 1.5% | 10.5% |
| Use Haiku 4.5 for 3 simple tasks (formatting, rename, simple fix) | 22.4% | 32.8% |
| **Total optimization vs. Default** | -- | **32.8%** |
| **Total optimization vs. Worst Case** | -- | **74.6%** |

With Haiku 5.5 instead of Haiku 4.5 for those 3 tasks, the Max Savings day costs $0.99: 42.9% below Default and 78.4% below the worst case (computed, same formula; Haiku 5.5 at $0.10/$0.50, every prompt here under its 100K tier line).

---

## Key Takeaways

1. **Start new sessions for new tasks.** Splitting an 80-turn day into eight 10-turn sessions sends 76% fewer input tokens at this repo's calculator defaults (5.50M vs 1.30M). Claude Code bills unchanged history at the cache-read rate ([costs page](https://code.claude.com/docs/en/costs)), so the dollar saving is smaller: about 23% on Opus 5.5 or Sonnet 5.5 (40% on Sonnet 4.6, which reads cache at 0.1x) with a warm cache and 500 output tokens per turn (computed: calculator defaults, each turn reading the previous request from cache and writing only the new exchange at 1.25x).

2. **Keep CLAUDE.md between 80-120 lines.** Below 80, you lose conventions and pay for follow-up turns. Above 150, you are paying for content that does not improve output quality.

3. **Be deliberate about file reads.** Every file Claude reads becomes part of the conversation context for the rest of the session. Read specific sections when possible, summarize frequently-needed files in CLAUDE.md, and use subagents for file-heavy investigation.

4. **Later turns cost more, gradually, while the cache stays warm.** Turn 30 costs 1.7x turn 3 on Sonnet 4.6 ($0.0286 vs $0.0164, computed). A late turn gets expensive when the cache misses, because the whole history is re-written at 1.25x. If a session is getting long and you are starting a new sub-task, start a new session.

5. **Tokens grow quadratically; with caching, cost grows close to linearly.** A 20-turn session sends 2.9x the tokens of a 10-turn session (475,000 vs 162,500) but costs 2.1x as much on Sonnet 4.6 ($0.42 vs $0.20, computed), because the re-sent history bills at the cache-read rate.

6. **Prompt caching helps but does not eliminate the problem.** Caching bills the whole unchanged prefix (system prompt, CLAUDE.md and the conversation so far) at 0.1x input (0.05x on Opus 5.5 and Sonnet 5.5, 0.025x on Fable 5.1). What still grows is the size of that prefix, so a long session pays a cache read of the full history on every turn ([costs page](https://code.claude.com/docs/en/costs): "a one-line question in a session that has been open all day still draws usage for the whole conversation").
