# Guide 08: Prompt Caching

> **Prompt caching is the single largest automatic discount on your Claude Code bill.** It reduces input token costs by up to 90% on repeated content -- and it happens without any configuration. Understanding how it works, what breaks it, and how to maximize hit rates can save you hundreds of dollars per month.

---

## Table of Contents

- [How Prompt Caching Works](#how-prompt-caching-works)
  - [The Prefix Matching Rule](#the-prefix-matching-rule)
  - [Cache Pricing by Model](#cache-pricing-by-model)
  - [Cache Write vs Cache Hit](#cache-write-vs-cache-hit)
- [What Gets Cached in Claude Code](#what-gets-cached-in-claude-code)
- [What Breaks the Cache](#what-breaks-the-cache)
- [Cache TTL and Economics](#cache-ttl-and-economics)
  - [Standard vs Extended TTL](#standard-vs-extended-ttl)
  - [Breakeven Math](#breakeven-math)
- [Maximizing Cache Hit Rate](#maximizing-cache-hit-rate)
- [ROI Calculations](#roi-calculations)
  - [Scenario 1: 50-Turn Session with Good Caching](#scenario-1-50-turn-session-with-good-caching)
  - [Scenario 2: 50-Turn Session with Poor Caching](#scenario-2-50-turn-session-with-poor-caching)
  - [Comparison Table: Cache Hit Rate Impact](#comparison-table-cache-hit-rate-impact)
- [Advanced Patterns](#advanced-patterns)
- [Common Mistakes](#common-mistakes)
- [Key Takeaways](#key-takeaways)

---

## How Prompt Caching Works

Claude's API uses prompt caching to avoid reprocessing content it has already seen. The mechanism is straightforward: when the **prefix** of a prompt matches a previous request, the matching portion is served from cache at a steep discount instead of being reprocessed at full price.

This is not a semantic cache. It is an exact prefix match. The cache checks whether the beginning of the current request is byte-for-byte identical to a recent request. If the first 50,000 tokens of your current turn match the first 50,000 tokens of the previous turn, those 50,000 tokens are cache hits. The moment a single token diverges, everything after that point is a cache miss.

### The Prefix Matching Rule

```
Turn N prompt (simplified):
┌─────────────────────────────────────────────────┐
│ System Prompt              (3,500 tokens)        │ ← Cached (identical to Turn N-1)
│ CLAUDE.md                  (1,050 tokens)        │ ← Cached (identical to Turn N-1)
│ Tool Schemas / MCP         (2,000 tokens)        │ ← Cached (identical to Turn N-1)
│ Conversation History       (40,000 tokens)       │ ← Cached (prefix matches Turn N-1)
│ New user message           (100 tokens)          │ ← NOT cached (new content)
│ New tool results           (1,500 tokens)        │ ← NOT cached (new content)
└─────────────────────────────────────────────────┘
```

In this example, 46,550 tokens (system prompt + CLAUDE.md + tool schemas + conversation history) are cache hits. Only the new user message and tool results (1,600 tokens) are charged at full input price.

This is why caching is so powerful in Claude Code specifically. The structure of each turn naturally creates a long, stable prefix: system prompt, then CLAUDE.md, then tool schemas, then the entire conversation history up to this point. Only the newest content at the end is different.

### Cache Pricing by Model

| Model | Standard Input (per 1M) | Cache Hit (per 1M) | Discount | Cache Write (5-min TTL) | Cache Write (1-hour TTL) |
|-------|:-----------------------:|:-------------------:|:--------:|:-----------------------:|:------------------------:|
| **Opus 4.7 / 4.6** | $5.00 | $0.50 | **90% off** | $6.25 (1.25x) | $10.00 (2x) |
| **Sonnet 4.6** | $3.00 | $0.30 | **90% off** | $3.75 (1.25x) | $6.00 (2x) |
| **Haiku 4.5** | $1.00 | $0.10 | **90% off** | $1.25 (1.25x) | $2.00 (2x) |

> All three models offer the same 90% discount on cache hits. The absolute savings are largest on Opus ($4.50 per 1M tokens saved), but the percentage is identical across models.

### Cache Write vs Cache Hit

There are three possible states for input tokens:

| State | Cost | When It Happens |
|-------|:----:|-----------------|
| **Cache hit** | 0.1x input price | Tokens match a cached prefix from a recent request |
| **Cache write** | 1.25x input price (5-min TTL) | Tokens processed for the first time and written to cache |
| **Regular input** | 1x input price | Tokens that are not cached and not written to cache |

The first turn of any session pays the cache write cost. Subsequent turns benefit from cache hits on the stable prefix. This means turn 1 is slightly more expensive than a no-cache world (1.25x), but turns 2-N are dramatically cheaper (0.1x) on the cached portion.

---

## What Gets Cached in Claude Code

In Claude Code, caching happens automatically. You do not need to set any flags or configuration. The following components form the cacheable prefix of each turn:

### The Static/Dynamic Boundary

Based on community research into Claude Code's internals, the system prompt has a **static/dynamic boundary** (internally referred to as the "system prompt dynamic boundary"). This boundary splits the prompt into two zones:

- **Static zone** (before the boundary): Claude Code's built-in instructions, behavioral rules, and tool descriptions. This content is identical across all sessions and never changes during a session. It is highly cacheable -- once written to cache on turn 1, it stays cached for the entire session.
- **Dynamic zone** (after the boundary): Environment context (OS, shell, cwd), git status, CLAUDE.md file contents, runtime configuration, and any session-specific state. This content varies per session and can change between turns.

Both zones are cached, but the dynamic zone's cache is invalidated whenever any of its components change. This is why editing CLAUDE.md mid-session is costly -- it sits in the dynamic zone, and any change invalidates the cache for the entire dynamic section (plus all conversation history that follows it in the prefix).

**Practical implication**: The ~3,500 tokens of static instructions get cached reliably regardless of what you do. Your CLAUDE.md and git status get cached too, but only as long as they remain unchanged between turns. Do not edit CLAUDE.md mid-session -- it will invalidate the dynamic section cache.

### Component Breakdown

| Component | Approx. Tokens | Cache Zone | Cache Behavior |
|-----------|:--------------:|:----------:|----------------|
| **System prompt** | ~3,500 | Static | Cached on every turn after the first. This is Claude Code's built-in instruction set -- it never changes during a session. |
| **Tool schemas (built-in)** | ~1,000-2,000 | Static | Cached if the set of available tools stays constant. Includes Read, Edit, Write, Bash, Grep, Glob, etc. |
| **CLAUDE.md content** | ~7 per line | Dynamic | Cached as long as you do not edit the file mid-session. A 150-line file adds ~1,050 tokens that stay cached. |
| **Environment context** | ~200-500 | Dynamic | OS, shell, cwd, git status. Changes if you switch directories or git state changes between turns. |
| **MCP tool schemas** | ~500-3,000 per server | Dynamic | Cached as long as the MCP server list does not change. Each connected server adds its tool definitions to the prompt. |
| **Conversation history** | Grows each turn | After prefix | The portion of history that is identical to the previous turn (all turns except the newest) is cached. |

### How It Plays Out Over a Session

```
Turn 1:  Cache write on system prompt + CLAUDE.md + tools (6,500 tokens at 1.25x)
Turn 2:  Cache hit on 6,500 tokens + cache write on turn 1 exchange (~3,000 tokens)
Turn 3:  Cache hit on 9,500 tokens + cache write on turn 2 exchange (~3,000 tokens)
...
Turn 50: Cache hit on ~150,000 tokens + cache write on turn 49 exchange (~3,000 tokens)
```

By turn 50, the vast majority of your input tokens are cache hits. Only the newest turn's exchange and your current message are processed at full price.

---

## What Breaks the Cache

Because caching relies on exact prefix matching, anything that changes the prefix invalidates the cache from that point forward. Here are the specific actions that break it:

### 1. Editing CLAUDE.md Mid-Session

CLAUDE.md is part of the prompt prefix, positioned after the system prompt. If you edit it between turns, every token after the edit point becomes a cache miss -- including all conversation history that was previously cached.

```
Before edit:
  System prompt (3,500) + CLAUDE.md v1 (1,050) + Tools (2,000) + History (40,000)
  ──────────────────────────────────────────────────────────────────────────────
  46,550 tokens cached

After editing CLAUDE.md:
  System prompt (3,500) + CLAUDE.md v2 (1,100) + Tools (2,000) + History (40,000)
  ───────────────┐
  3,500 cached   │  43,100 tokens are now cache MISSES
                 └──────────────────────────────────────────────────────────────
```

A single edit to CLAUDE.md at turn 25 of a session can cost you a full-price reprocessing of 40,000+ tokens of conversation history. On Opus, that is ~$0.20 in a single turn that would have cost ~$0.02 as cache hits.

### 2. Adding or Removing MCP Servers

MCP tool schemas are injected into the prompt after CLAUDE.md. Changing the set of connected servers shifts the prefix, breaking the cache on everything that follows.

### 3. Cache TTL Expiration

The standard cache has a 5-minute time-to-live. If you wait more than 5 minutes between turns, the cache expires and the next turn pays cache write costs on the entire prefix again.

This means:
- Rapid consecutive turns (under 5 minutes apart) maximize caching
- Taking a long break mid-session (lunch, meetings) resets the cache
- The content is still in your conversation history -- you just pay full price to reprocess it on the next turn after the gap

### 4. Switching Models Mid-Session

Each model maintains its own cache. Switching from Sonnet to Opus (or vice versa) means the new model has no cached prefix -- everything is processed from scratch.

### Summary of Cache-Breaking Actions

| Action | Cache Impact | Cost Penalty |
|--------|-------------|--------------|
| Edit CLAUDE.md | Invalidates prefix from edit point onward | All history reprocessed at full input price |
| Add/remove MCP server | Invalidates prefix from schema change onward | All history reprocessed at full input price |
| Gap > 5 minutes between turns | Full cache expiration | Entire prefix reprocessed (cache write at 1.25x) |
| Switch model mid-session | New model has empty cache | Entire prefix reprocessed (cache write at 1.25x) |
| Use `/compact` | History replaced with summary | New summary written to cache (smaller prefix) |

> Note: `/compact` is a special case. It intentionally resets context by summarizing conversation history into a shorter form. This breaks the cache on the old history, but the new compressed context becomes a much smaller cacheable prefix going forward. This is usually a net positive for cost -- see [Guide 02](02-context-optimization.md).

---

## Cache TTL and Economics

### Standard vs Extended TTL

| TTL Option | Duration | Write Cost | Availability |
|------------|:--------:|:----------:|--------------|
| **Standard** | 5 minutes | 1.25x input price | Default in Claude Code and API |
| **Extended** | 1 hour | 2x input price | Available via API parameter |

In Claude Code, the standard 5-minute TTL applies. You cannot configure extended TTL through the CLI -- it is an API-level option for custom integrations.

### 5-Minute TTL in Practice

The 5-minute window is more generous than it sounds for Claude Code workflows:

- **Active coding sessions**: Turns typically happen every 30-90 seconds. The cache stays warm throughout.
- **Reviewing output**: Even if you spend 3-4 minutes reading Claude's response before your next message, the cache holds.
- **Short breaks**: A quick coffee break or Slack check (under 5 minutes) does not break the cache.
- **Long breaks**: A 15-minute meeting, lunch, or context switch causes a full cache expiration.

### Breakeven Math

Cache writes cost 1.25x the standard input price, but cache hits save 90%. When does caching pay for itself?

```
Cache write cost:    1.25 x standard_price (per token)
Cache hit savings:   0.90 x standard_price (per token)

Breakeven: 1 write + N hits = cost without caching
  1.25P + N(0.1P) = (1 + N) x P
  1.25 + 0.1N = 1 + N
  0.25 = 0.9N
  N = 0.28

You break even after just 1 cache hit following the initial write.
```

In other words: if you use the cached content even **once** after writing it, caching has already paid for itself. By the second cache hit, you are saving money. By the 10th hit, the savings are substantial.

**Worked example with 10,000 tokens of stable prefix on Sonnet 4.6:**

| Scenario | Turn 1 Cost | Turn 2 Cost | Turn 3 Cost | Total (3 turns) |
|----------|:-----------:|:-----------:|:-----------:|:---------------:|
| **No caching** | $0.0300 | $0.0300 | $0.0300 | $0.0900 |
| **With caching** | $0.0375 (write) | $0.0030 (hit) | $0.0030 (hit) | $0.0435 |
| **Savings** | -$0.0075 (costs more) | +$0.0270 | +$0.0270 | **+$0.0465 (52% saved)** |

By turn 3, caching has saved 52%. By turn 50, the savings approach 90% on the cached portion.

### Extended TTL Economics (API Only)

Extended caching (1-hour TTL) costs 2x on the write instead of 1.25x. This makes sense when:

- Turns are spaced more than 5 minutes apart but less than 1 hour
- The cached prefix is very large (saving more per hit justifies the higher write cost)
- You are building a batch/pipeline system that reuses the same system prompt across many requests

```
Extended cache breakeven:
  2P + N(0.1P) = (1 + N) x P
  2 + 0.1N = 1 + N
  1 = 0.9N
  N = 1.12

You need at least 2 cache hits to break even with extended TTL.
```

For Claude Code users on the standard 5-minute TTL, this is not relevant -- but it matters if you are building custom tooling on the API.

---

## Maximizing Cache Hit Rate

These strategies increase the percentage of input tokens that hit the cache:

### 1. Keep CLAUDE.md Stable During Sessions

Do not edit CLAUDE.md while a session is active. If you need to update it, finish your current session first, then edit, then start a new session. The cost of a mid-session edit compounds over every remaining turn.

**Cost of editing CLAUDE.md at turn 25 of a 50-turn session (Sonnet 4.6):**

```
Cached history at turn 25:  ~75,000 tokens
Remaining turns:            25
Cache miss cost per turn:   75,000 x ($3.00 - $0.30) / 1,000,000 = $0.2025
Total extra cost:           ~$0.2025 (the turn after the edit)
                            Subsequent turns rebuild the cache, so the penalty
                            is primarily one full-price turn.
```

The immediate penalty is roughly $0.20 on Sonnet or $0.34 on Opus for the first turn after the edit. Subsequent turns rebuild the cache quickly.

### 2. Keep MCP Server Configuration Constant

Decide which MCP servers you need before starting a session. Do not connect or disconnect servers mid-session.

If you use different MCP servers for different types of work, use project-level MCP configuration (`.claude/settings.json`) rather than global config. This way, each project loads only its relevant servers, and you avoid needing to toggle servers during a session.

### 3. Work in Focused Sessions

Many rapid turns on the same topic maximize caching:

| Pattern | Cache Efficiency | Why |
|---------|:----------------:|-----|
| 50 turns in 30 minutes | ~90% hit rate | Turns are close together, prefix stays warm |
| 50 turns over 4 hours | ~60% hit rate | Breaks between turns cause TTL expirations |
| 5 separate 10-turn sessions | ~75% hit rate | Each session rebuilds cache from scratch, but sessions are focused |
| 50 single-turn conversations | ~0% hit rate | No caching benefit at all -- every turn is a cold start |

### 4. Use /compact Strategically

`/compact` summarizes conversation history into a shorter form, which resets the cache. But it also dramatically reduces the total token count, making subsequent turns cheaper overall.

**When /compact helps caching:**
- After a large context has accumulated (50,000+ tokens of history), compact reduces it to ~5,000 tokens. The next turn pays cache write on 5,000 tokens instead of cache hit on 50,000 tokens -- but every turn after that processes far fewer total tokens.

**When /compact hurts caching:**
- If you compact too frequently (every 5-10 turns), you repeatedly pay cache write costs without accumulating enough cached turns to justify it.

**Rule of thumb**: Compact when context exceeds 80,000-100,000 tokens, or at natural breakpoints in your work (finishing a feature, switching to a different file).

### 5. Front-Load Stable Content in CLAUDE.md

Claude's prompt is structured so that CLAUDE.md appears near the beginning of the prefix. This means CLAUDE.md content is always in the cached prefix (as long as you do not edit it). You do not need to reorder content within CLAUDE.md for caching purposes -- the entire file is part of the prefix regardless of internal ordering.

However, if you use multiple CLAUDE.md files (project root + subdirectories), keep the root-level file stable and put frequently-changing content in subdirectory files where it has less impact on the prefix.

---

## ROI Calculations

### Scenario 1: 50-Turn Session with Good Caching

**Setup**: Sonnet 4.6, 150-line CLAUDE.md, 3 MCP servers, focused session with turns every 1-2 minutes. No CLAUDE.md edits, no model switches.

**Stable prefix**: System prompt (3,500) + CLAUDE.md (1,050) + Tool schemas (4,000) = 8,550 tokens

```
Turn  1: 8,550 tokens at cache write (1.25x)
         + 100 tokens new input
         Total input cost:  8,550 x $3.75/1M + 100 x $3.00/1M
                          = $0.0321 + $0.0003 = $0.0324
         Output: 700 tokens x $15.00/1M = $0.0105
         Turn total: $0.043

Turn 10: 8,550 prefix + 27,000 history = 35,550 cached tokens
         + 3,000 new tokens (latest turn exchange + tool results)
         Input cost:  35,550 x $0.30/1M + 3,000 x $3.00/1M
                    = $0.0107 + $0.0090 = $0.0197
         Output: 700 tokens x $15.00/1M = $0.0105
         Turn total: $0.030

Turn 25: 8,550 prefix + 72,000 history = 80,550 cached tokens
         + 3,000 new tokens
         Input cost:  80,550 x $0.30/1M + 3,000 x $3.00/1M
                    = $0.0242 + $0.0090 = $0.0332
         Output: 700 tokens x $15.00/1M = $0.0105
         Turn total: $0.044

Turn 50: 8,550 prefix + 147,000 history = 155,550 cached tokens
         + 3,000 new tokens
         Input cost:  155,550 x $0.30/1M + 3,000 x $3.00/1M
                    = $0.0467 + $0.0090 = $0.0557
         Output: 700 tokens x $15.00/1M = $0.0105
         Turn total: $0.066
```

**Total session cost: ~$2.20 on Sonnet 4.6**

### Scenario 2: 50-Turn Session with Poor Caching

**Setup**: Same session, but the developer edits CLAUDE.md at turns 10, 20, 30, and 40. Also takes a 20-minute break at turn 15 (cache expiration). Switches from Sonnet to Opus at turn 35.

Each of these events forces a full-price reprocessing of the entire accumulated context:

```
Turn 10 (after CLAUDE.md edit):
  Full-price reprocessing of ~30,000 tokens
  Extra cost: 30,000 x ($3.00 - $0.30) / 1M = $0.081

Turn 15 (after 20-min break, cache expired):
  Cache write on ~45,000 tokens
  Extra cost: 45,000 x ($3.75 - $0.30) / 1M = $0.155

Turn 20 (after CLAUDE.md edit):
  Full-price reprocessing of ~60,000 tokens
  Extra cost: 60,000 x ($3.00 - $0.30) / 1M = $0.162

Turn 30 (after CLAUDE.md edit):
  Full-price reprocessing of ~90,000 tokens
  Extra cost: 90,000 x ($3.00 - $0.30) / 1M = $0.243

Turn 35 (model switch to Opus, new cache):
  Full-price reprocessing of ~105,000 tokens on Opus
  Extra cost: 105,000 x ($5.00 - $0.50) / 1M = $0.473

Turn 40 (after CLAUDE.md edit, still on Opus):
  Full-price reprocessing of ~120,000 tokens
  Extra cost: 120,000 x ($5.00 - $0.50) / 1M = $0.540
```

**Estimated total with all cache breaks: ~$4.85**

That is more than double the cost of the same 50-turn session with good caching.

### Comparison Table: Cache Hit Rate Impact

**50-turn session on Sonnet 4.6, average 3,000 new tokens per turn, 700 output tokens per turn**

| Cache Hit Rate | Input Cost | Output Cost | Total Session Cost | vs No Caching |
|:--------------:|:----------:|:-----------:|:------------------:|:-------------:|
| **90%** (good) | $1.15 | $0.53 | **$1.68** | **63% savings** |
| **75%** (decent) | $1.78 | $0.53 | **$2.31** | **49% savings** |
| **50%** (poor) | $2.73 | $0.53 | **$3.26** | **28% savings** |
| **25%** (bad) | $3.68 | $0.53 | **$4.21** | **7% savings** |
| **0%** (no caching) | $4.52 | $0.53 | **$5.05** | baseline |

> Output tokens are never cached -- they are always generated fresh. Caching only affects input tokens. This is why the output cost ($0.53) is constant across all rows.

**Monthly impact (5 sessions/day, 22 working days = 110 sessions):**

| Cache Hit Rate | Monthly Cost (Sonnet) | Monthly Cost (Opus) |
|:--------------:|:---------------------:|:-------------------:|
| **90%** | $185 | $308 |
| **75%** | $254 | $423 |
| **50%** | $359 | $598 |
| **0%** | $556 | $926 |

The difference between 90% and 0% cache hit rate is **$371/month on Sonnet** and **$618/month on Opus**. Good caching hygiene is one of the most impactful cost optimizations available.

---

## Advanced Patterns

### Structuring CLAUDE.md for Cache Stability

Since CLAUDE.md is part of the cached prefix, its stability directly impacts your cache hit rate. Apply these principles:

**Put the most stable content first.**

```markdown
# CLAUDE.md

## Tech Stack (rarely changes)
Python 3.12, FastAPI, PostgreSQL, React 19

## Build Commands (rarely changes)
- Test: pytest
- Lint: ruff check .
- Dev: uvicorn main:app --reload

## Project Structure (changes occasionally)
src/ - Application code
tests/ - Test suite
docs/ - Documentation

## Current Sprint Context (changes often)
Working on: auth module refactor
```

Even though CLAUDE.md is loaded as a single block in the prefix, keeping it concise and avoiding unnecessary changes means fewer sessions where you feel the need to edit it.

### Leveraging Custom Commands for Caching

Custom slash commands (defined in `.claude/commands/`) are loaded as part of the system prompt when invoked. If you use the same custom commands repeatedly across turns, their content benefits from caching just like the rest of the prompt prefix.

This is another reason to prefer custom commands over repeatedly typing the same complex instructions -- the command text gets cached after the first use.

### Session Planning for Cache Optimization

Structure your work to maximize consecutive turns within the 5-minute TTL:

```
Efficient (cache-friendly):
  Session 1: Implement feature A (30 turns, focused)
  Session 2: Write tests for feature A (20 turns, focused)
  Session 3: Review and refactor (15 turns, focused)

Inefficient (cache-hostile):
  Session 1: Start feature A, get distracted, switch to bug fix,
             come back to feature A, edit CLAUDE.md, switch models,
             take a 30-minute break, resume (50 scattered turns)
```

The three focused sessions will cost less in total than the single scattered session, even though they process the system prompt and CLAUDE.md from scratch three times. The cache hit rate within each session more than compensates.

### Batch Work Within the TTL Window

If you have multiple related questions or tasks, batch them into consecutive turns rather than spacing them out:

```
Good: Ask question 1, get answer, ask question 2, get answer, ask question 3
      (all within 5 minutes -- cache stays warm)

Bad:  Ask question 1, go do something else for 10 minutes, ask question 2,
      go do something else for 10 minutes, ask question 3
      (cache expires between each question)
```

---

## Common Mistakes

### 1. Editing CLAUDE.md Every Few Turns

Some developers update CLAUDE.md frequently, thinking it helps Claude perform better. It might marginally improve response quality, but the cache penalty is steep.

**The math**: If your session has accumulated 60,000 tokens of cached history and you edit CLAUDE.md, the next turn reprocesses all 60,000 tokens at full price. On Sonnet, that is an extra $0.16 for that single turn. Do this 4 times in a session and you have wasted $0.64 -- more than many entire sessions cost.

**Better approach**: Set up your CLAUDE.md once before the session starts. If you realize you need to add something, make a mental note and update it after the session ends.

### 2. Frequently Switching MCP Servers

Connecting and disconnecting MCP servers mid-session breaks the cache for the same reason as editing CLAUDE.md -- it changes the prompt prefix.

**Better approach**: Use project-level MCP configs (`.claude/settings.json`) to ensure each project has exactly the servers it needs. No toggling required.

### 3. Very Short Sessions (1-2 Turns)

Caching is a multi-turn investment. The first turn pays the cache write cost (1.25x). If you only use 1-2 turns and then start a new session, you pay the write premium without enough hits to recoup it.

**The math for a single-turn session on Sonnet 4.6:**

| | With Cache Write | Without Caching | Difference |
|---|:---:|:---:|:---:|
| 8,550 prefix tokens | $0.0321 (at 1.25x) | $0.0257 (at 1x) | +$0.0064 more |

You pay an extra $0.006 per single-turn session due to cache writes that never get reused. Across 100 single-turn sessions, that is $0.64 wasted.

**Better approach**: If you regularly do single-turn tasks, the cache write overhead is negligible in absolute terms. But if you can batch related questions into multi-turn sessions, you will save significantly.

### 4. Not Understanding That Cache Writes Cost More Than Regular Input

A common misconception is that caching is always free or always cheaper. The first turn of a session is slightly more expensive (1.25x on the prefix) than it would be without caching. The savings come from subsequent turns. If you only ever do 1-turn sessions, caching has a small net cost.

In practice, this almost never matters -- the overhead is tiny and most sessions are multi-turn. But it is worth understanding the mechanics.

### 5. Taking Long Breaks Without Compacting First

If you know you will be away for more than 5 minutes (meeting, lunch, context switch), run `/compact` before stepping away. When you return, the context will be smaller, and the cache write cost on the first turn back will be lower.

```
Without compacting before break:
  Return to session with 80,000 tokens of expired cache
  Cache write: 80,000 x $3.75/1M = $0.30 (Sonnet)

With compacting before break:
  /compact reduces history to ~8,000 tokens
  Return to session with 8,000 tokens of expired cache
  Cache write: 8,000 x $3.75/1M = $0.03 (Sonnet)

  Savings: $0.27 on the first turn back
```

---

## Key Takeaways

1. **Prompt caching gives you a 90% discount on repeated input tokens.** In a typical multi-turn session, 80-90% of input tokens are cache hits. This is the largest automatic cost reduction in Claude Code.

2. **Do not edit CLAUDE.md during an active session.** A mid-session edit forces full-price reprocessing of all accumulated conversation history. Set up CLAUDE.md before starting and leave it alone.

3. **Caching pays for itself after just one reuse.** The cache write premium (1.25x) is recovered with a single cache hit (0.1x). Every subsequent hit is pure savings.

4. **Work in focused sessions with turns under 5 minutes apart.** The cache TTL is 5 minutes. Rapid, focused sessions maintain a warm cache. Scattered work with long gaps between turns wastes money on repeated cache writes.

5. **Run /compact before long breaks.** If you are stepping away for more than 5 minutes, compacting first reduces the cache write cost when you return.

6. **The difference between good and poor caching is $370+/month.** On Sonnet with 110 sessions/month, the gap between 90% and 0% cache hit rate is $371. Good caching hygiene is not optional -- it is one of the highest-ROI optimizations you can make.

---

*Previous: [Guide 07 - MCP Server and Agent Cost Impact](07-mcp-agent-costs.md)*
