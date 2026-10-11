# Guide 08: Prompt Caching

> **Prompt caching is the single largest automatic discount on your Claude Code bill.** It reduces input token costs by 90% on repeated content on most models -- **95% on Opus 5.5 and Sonnet 5.5 (0.05x) and 97.5% on Fable 5.1 and Mythos 5.1 (0.025x)** -- and it happens without any configuration. On Anthropic's benchmarks caching cut agent-loop cost by a factor of 2.7 to 5.3, and 83% on a small triage agent (88% with input trimming); on DeepResearch Bench II it took Fable 5.1 from $37.94 to $7.12 per task ([cost-optimization guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence)). This guide covers how it works, what breaks it, and how to keep the hit rate high.

---

## Table of Contents

- [How Prompt Caching Works](#how-prompt-caching-works)
  - [The Prefix Matching Rule](#the-prefix-matching-rule)
  - [Cache Pricing by Model](#cache-pricing-by-model)
  - [Minimum Cacheable Prompt Length](#minimum-cacheable-prompt-length)
  - [Cache Write vs Cache Hit](#cache-write-vs-cache-hit)
- [What Gets Cached in Claude Code](#what-gets-cached-in-claude-code)
- [What Breaks the Cache](#what-breaks-the-cache)
- [Cache TTL and Economics](#cache-ttl-and-economics)
  - [Standard vs Extended TTL](#standard-vs-extended-ttl)
  - [How Claude Code Picks the Cache TTL](#how-claude-code-picks-the-cache-ttl)
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

In this example, 46,550 tokens (system prompt + CLAUDE.md + tool schemas + conversation history) are cache hits. Only the new user message and tool results (1,600 tokens) are new, and Claude Code writes them to cache at 1.25x the input price so the next turn can read them: "the prefix is the entire previous request and only the latest exchange is new" ([Claude Code prompt caching](https://code.claude.com/docs/en/prompt-caching)).

This is why caching is so powerful in Claude Code specifically. The structure of each turn naturally creates a long, stable prefix: system prompt, then CLAUDE.md, then tool schemas, then the entire conversation history up to this point. Only the newest content at the end is different.

### Cache Pricing by Model

| Model | Standard Input (per 1M) | Cache Hit (per 1M) | Discount | Cache Write (5-min TTL) | Cache Write (1-hour TTL) |
|-------|:-----------------------:|:-------------------:|:--------:|:-----------------------:|:------------------------:|
| **Fable 5.1 / Mythos 5.1** | $10.00 | **$0.25** | **97.5% off** (0.025x) | $12.50 (1.25x) | $20.00 (2x) |
| **Opus 5.5** | $4.00 | **$0.20** | **95% off** (0.05x) | $5.00 (1.25x) | $8.00 (2x) |
| **Sonnet 5.5** | $2.00 | **$0.10** | **95% off** (0.05x) | $2.50 (1.25x) | $4.00 (2x) |
| **Opus 5** (legacy) | $5.00 | $0.50 | **90% off** | $6.25 (1.25x) | $10.00 (2x) |
| **Fable 5 / Mythos 5** (legacy) | $10.00 | $1.00 | **90% off** | $12.50 (1.25x) | $20.00 (2x) |
| **Opus 4.8 (legacy) / 4.7 / 4.6** | $5.00 | $0.50 | **90% off** | $6.25 (1.25x) | $10.00 (2x) |
| **Sonnet 5** (legacy) | $2.00 | $0.20 | **90% off** | $2.50 (1.25x) | $4.00 (2x) |
| **Sonnet 4.6 / 4.5** (4.5 deprecated) | $3.00 | $0.30 | **90% off** | $3.75 (1.25x) | $6.00 (2x) |
| **Haiku 5.5** (prompt <= 100K tokens) | $0.10 | **$0.01** | **90% off** (0.1x) | $0.125 (1.25x) | $0.20 (2x) |
| **Haiku 5.5** (prompt > 100K tokens) | $0.50 | $0.05 | **90% off** (0.1x) | $0.625 (1.25x) | $1.00 (2x) |
| **Haiku 4.5** (legacy) | $1.00 | $0.10 | **90% off** | $1.25 (1.25x) | $2.00 (2x) |

> **There are now three cache-hit multipliers, not one.** Fable 5.1 and Mythos 5.1 read cache at **0.025x base input** ($0.25 per 1M) -- a 97.5% discount. Opus 5.5 and Sonnet 5.5 read at **0.05x** ($0.20 and $0.10 per 1M) -- a 95% discount; Sonnet 5.5 joined this group on 2026-10-07, when its cache read was cut from $0.20 to $0.10. Every other model is still 0.1x (90% off), Haiku 5.5 included, where the 0.1x applies to the request's own tier. If you compute a cache rate anywhere in your own tooling as `input * 0.1`, that formula is now wrong on four models; read the per-model rate instead.
>
> This also flips a planning default. Because a hit costs so little *relative to a miss* on Fable 5.1, losing the cache hurts far more than it does elsewhere, while a read is nearly free. For a 5-to-60-minute gap between turns, re-sending the previous request with `max_tokens: 0` to refresh the 5-minute entry is usually cheaper than paying the 2x write for the 1-hour TTL -- the keep-alive bills only a cheap cache read and no output tokens. (`max_tokens: 0` can't be combined with streaming, structured outputs, or Batches; where the request can't be reshaped, use the 1-hour TTL.)
>
> Absolute savings per 1M cached tokens: **$9.75 on Fable 5.1**, $9.00 on Fable 5, $3.80 on Opus 5.5, $4.50 on legacy Opus 5 / 4.x, **$1.90 on Sonnet 5.5** ($2.00 - $0.10; it was $1.80 before the cut), $1.80 on Sonnet 5, and on Haiku 5.5 $0.09 at <= 100K prompt tokens ($0.10 - $0.01) or $0.45 above ($0.50 - $0.05).

> Sonnet 5 is $2/$10 permanently (the increase to $3/$15 was cancelled), so its cache rates are $0.20 hit, $2.50 5-minute write, $4.00 1-hour write. The multipliers are unchanged -- only the base input price differs. Sonnet 5.5 (`claude-sonnet-5-5`, released 2026-09-28) launched at the same $2/$10 and the same cache rates, with the same tokenizer; on 2026-10-07 Anthropic cut its cache read to **$0.10 (0.05x)**, so it now reads cache at half Sonnet 5's price while the writes stay $2.50 / $4.00.

> **Haiku 5.5 (`claude-haiku-5-5`, released 2026-10-07) caches per prompt-length tier.** It is the first model priced by prompt length: a request whose prompt is <= 100,000 tokens pays $0.10 input, $0.01 cache hit and $0.125 / $0.20 writes; a request over 100,000 tokens pays $0.50, $0.05 and $0.625 / $1.00 on all of it, and its output moves from $0.50 to $2.50. Each cache rate is the usual multiple of its own tier's input (0.1x hit, 1.25x / 2x writes).
>
> **The 100K threshold counts cache reads and cache writes**, so caching a big prefix does not get a request under it. Anthropic prices each request on its own, and a request over the threshold pays the higher prices even when part of its prompt is a cache hit:
>
> ```
> 95,000 cached + 4,000 new = 99,000 prompt tokens  -> <= 100K tier
>   95,000 x $0.01/1M + 4,000 x $0.10/1M = $0.00095 + $0.00040 = $0.00135
>
> 95,000 cached + 6,000 new = 101,000 prompt tokens -> > 100K tier
>   95,000 x $0.05/1M + 6,000 x $0.50/1M = $0.00475 + $0.00300 = $0.00775
> ```
>
> 2% more prompt tokens cost 5.7x more input, and every output token on that request bills at $2.50 instead of $0.50. In a long Claude Code session the cached history grows every turn, so a Haiku 5.5 conversation crosses into the higher tier as soon as the prefix plus the new turn passes 100K. Above the line Haiku 5.5 is still 4x cheaper per token than Sonnet 5.5, but 5x dearer than its own lower tier: `/compact` or start fresh before the prompt reaches 100K, and keep Haiku work to short calls.

> Opus 5.5 (`claude-opus-5-5`, released 2026-09-22) is $4/$20 -- 20% below Opus 5 -- and Anthropic's models overview now says to "start with Claude Opus 5.5 for most workloads". Its cache rates are $0.20 hit, $5.00 5-minute write, $8.00 1-hour write. Opus 5 moved to legacy and keeps its $5/$25 price, the same as Opus 4.8, so the legacy Opus cache numbers in this guide are unchanged.

Cache multipliers stack with other discounts: Batch (50% off) and data residency (+10%) apply on top of the cache-hit and cache-write rates.

### Minimum Cacheable Prompt Length

Caching does not kick in on short prompts. Each model has a minimum cacheable prefix length, and a `cache_control` block below that threshold is **silently ignored** -- no error, no warning, no discount. You pay full input price on that content every single turn and nothing in the response tells you the cache never happened.

| Model | Minimum Cacheable Prompt (tokens) |
|-------|:---------------------------------:|
| **Opus 5.5** | **512** |
| **Opus 5** (legacy) | **512** |
| **Fable 5.1 / Mythos 5.1** | 512 |
| **Fable 5** | 512 |
| **Mythos 5** | 512 |
| **Mythos Preview** (deprecated) | 2,048 |
| **Opus 4.8** (legacy) | 1,024 |
| **Opus 4.7** | 2,048 |
| **Opus 4.6** | 4,096 |
| **Opus 4.5** | 4,096 |
| **Opus 4.1** (retired 2026-08-05) | 1,024 |
| **Sonnet 5.5** | **512** |
| **Sonnet 5** (legacy) | 1,024 |
| **Sonnet 4.6** | 1,024 |
| **Sonnet 4.5** (deprecated) | 1,024 |
| **Haiku 5.5** | **512** |
| **Haiku 4.5** (legacy) | 4,096 |
| **Haiku 3.5** | 2,048 |

**Opus 5 halved the threshold: 512 tokens, down from 1,024 on Opus 4.8, and Opus 5.5 keeps it at 512. Sonnet 5.5 does the same on the Sonnet tier: 512, down from Sonnet 5's 1,024. Haiku 5.5 goes furthest: 512, down from Haiku 4.5's 4,096.** Two consequences:

- **Migrating up is strictly better.** A 700-token system prompt that never cached on Opus 4.8, Sonnet 5 or Haiku 4.5 starts caching on Opus 5.5 (or Opus 5), Sonnet 5.5 or Haiku 5.5 with no code change.
- **Migrating down or sideways is the trap.** A prefix sized for Opus 5.5's 512-token floor silently stops caching on Sonnet 5 (1,024), Opus 4.7 (2,048), or legacy Haiku 4.5 (4,096). The request still succeeds. You just quietly pay 10x on that segment.

**How to check whether you actually got a cache.** Read the `usage` block on the response. If `cache_creation_input_tokens` and `cache_read_input_tokens` are both 0 while your `cache_control` block is set, your prefix was under the threshold and the marker was dropped.

```
Silently uncached (400-token prefix, Haiku 4.5, threshold 4,096):
  usage: { input_tokens: 400, cache_creation_input_tokens: 0, cache_read_input_tokens: 0 }
  50 turns x 400 tokens x $1.00/1M = $0.02   (expected ~$0.002)

Cached (8,000-token prefix, Haiku 4.5):
  usage: { cache_creation_input_tokens: 8000, cache_read_input_tokens: 0 }   turn 1
  usage: { cache_creation_input_tokens: 0, cache_read_input_tokens: 8000 }   turn 2+
```

In Claude Code this rarely bites you: the ~3,500-token system prompt plus tool schemas clears every model's floor from turn 1. It matters when you build custom API tooling with small system prompts, or when you route the same prompt across models with different floors. Size your cacheable prefix against the **highest** floor you route to, not the lowest -- 512 tokens covers the current lineup (Fable 5.1, Opus 5.5, Sonnet 5.5, Haiku 5.5), and 4,096 covers every model on the list, legacy Haiku 4.5 included.

### Cache Write vs Cache Hit

There are three possible states for input tokens:

| State | Cost | When It Happens |
|-------|:----:|-----------------|
| **Cache hit** | 0.1x input price (0.05x on Opus 5.5 and Sonnet 5.5, 0.025x on Fable 5.1 / Mythos 5.1) | Tokens match a cached prefix from a recent request |
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

Both zones are cached, but the dynamic zone's cache is invalidated whenever any of its components change. CLAUDE.md is not one of the things that changes mid-session: Claude Code reads the root and user CLAUDE.md once at session start, so editing the file on disk does not change the prompt and does not invalidate the cache ([Anthropic's prompt-caching docs](https://code.claude.com/docs/en/prompt-caching)). The edit applies after the next `/clear`, `/compact`, or restart.

**Practical implication**: The ~3,500 tokens of static instructions get cached reliably regardless of what you do. Your CLAUDE.md gets cached too, and editing it mid-session is safe for the cache -- just do not expect the new version to apply until you `/clear`, `/compact`, or restart.

### Component Breakdown

| Component | Approx. Tokens | Cache Zone | Cache Behavior |
|-----------|:--------------:|:----------:|----------------|
| **System prompt** | ~3,500 | Static | Cached on every turn after the first. This is Claude Code's built-in instruction set -- it never changes during a session. |
| **Tool schemas (built-in)** | ~1,000-2,000 | Static | Cached if the set of available tools stays constant. Includes Read, Edit, Write, Bash, Grep, Glob, etc. |
| **CLAUDE.md content** | ~7 per line | Dynamic | Read once at session start, so a mid-session edit neither changes the prompt nor breaks the cache (it applies after `/clear`, `/compact`, or restart). A 150-line file adds ~1,050 tokens that stay cached. |
| **Environment context** | ~200-500 | Dynamic | OS, shell, cwd, git status. Changes if you switch directories or git state changes between turns. |
| **MCP tools** | Tool names + server instructions (full schemas only with tool search off) | Dynamic | MCP tool search is on by default: only tool names and server instructions enter context until Claude uses a tool, and connecting or removing a server keeps the cache. With tool search off, full schemas load up front and a server change invalidates the cache. |
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

Because caching relies on exact prefix matching, anything that changes the prefix invalidates the cache from that point forward. A break can cost more than no caching at all: in Anthropic's measured triage run, a cache-busting 25-token status line at the front of the system prompt made the run cost $4.24 instead of $0.59 (7.2x, computed 4.24 / 0.59), more than running with caching off ([cost-optimization guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence)). Here are the specific actions that break it in Claude Code -- and one that famously does not:

### 1. Editing CLAUDE.md Mid-Session (Keeps the Cache)

Editing CLAUDE.md mid-session does **not** invalidate the cache. Claude Code reads the root and user CLAUDE.md once at session start, so changing the file on disk does not change the prompt. The flip side: the edit does not apply until the next `/clear`, `/compact`, or restart. Nested CLAUDE.md files and path-scoped rules load later, when Claude first reads a matching file.

Other actions that keep the cache: editing repo files, changing permission mode, changing output style, invoking skills or commands, `/recap`, `/rewind`, and spawning a subagent.

### 2. Adding or Removing MCP Servers (Only With Tool Search Off)

MCP tool search is on by default: tool definitions are deferred, and only tool names and server instructions enter context until Claude uses a specific tool. With tool search on, connecting or removing a server does **not** invalidate the cache.

The old rule still applies when tool search is off (`ENABLE_TOOL_SEARCH=false`, a custom `ANTHROPIC_BASE_URL`, or models older than the Claude 4.5 generation on Google Cloud). Then full schemas load up front, and connecting or removing a server -- or enabling or disabling a plugin that provides MCP servers, or denying an entire tool -- changes the prefix and breaks the cache on everything that follows.

> **Opus 5 caveat (2026-07-24)**: the new beta `mid-conversation-tool-changes-2026-07-01` lets tool definitions change between turns **without** invalidating the prompt cache. With that beta header set, changing tools mid-conversation is no longer a cache-busting move. Without that header, the old rule stands: changing the tool set reprocesses everything after the schema block at full price. It is a beta opt-in on the API, so assume the old behavior unless you are explicitly sending the header.
>
> **Sonnet 5.5 caveat (2026-09-28)**: mid-conversation tool changes (beta), mid-conversation system messages and per-message effort (beta) are supported on **Sonnet 5.5 and not on Sonnet 5**, so on the Sonnet tier tools and instructions can change mid-conversation without losing the prompt cache only after you move to Sonnet 5.5.

### 3. Cache TTL Expiration

The standard cache has a 5-minute time-to-live. If you wait longer than the TTL between turns, the cache expires and the next turn pays cache write costs on the entire prefix again. In Claude Code the TTL depends on how you pay: a subscription's main conversation gets one hour, everything else gets five minutes (see [How Claude Code Picks the Cache TTL](#how-claude-code-picks-the-cache-ttl)).

This means:
- Rapid consecutive turns (inside the TTL) maximize caching
- Taking a long break mid-session (lunch, meetings) resets the cache
- The content is still in your conversation history -- you just pay full price to reprocess it on the next turn after the gap

### 4. Switching Models Mid-Session

Each model maintains its own cache. Switching from Sonnet to Opus (or vice versa) means the new model has no cached prefix -- everything is processed from scratch.

Switching model also changes the minimum cacheable length. Moving from Opus 5.5, Sonnet 5.5 or Haiku 5.5 (512) to Sonnet 5 (1,024) or legacy Haiku 4.5 (4,096) can turn a previously-cached small prefix into one that never caches at all. See [Minimum Cacheable Prompt Length](#minimum-cacheable-prompt-length).

### 5. Switching Speed Mid-Session (Fast Mode)

Changing `speed` between requests invalidates the prompt cache, the same way switching models does. In Claude Code, turning on fast mode invalidates the cache once per conversation. Fast Mode is supported on **Opus 5.5, Opus 5 and Opus 4.8 only**, each at 2x its own base rate: $8/$40 on Opus 5.5, $10/$50 on Opus 5 and Opus 4.8. Opus 4.7 with `speed: "fast"` returns an error, and Opus 4.6 silently runs at standard speed and standard rates (`usage.speed` comes back `"standard"`). The old 6x tier no longer exists.

Fast Mode is a research preview on the Claude API (plus Managed Agents on Opus 5 and 4.8) -- not on Bedrock, Vertex, Foundry, Claude Platform on AWS, Batch, or Priority Tier.

### 6. Changing Effort Level

Changing the effort level invalidates the cache on most models. The exception is **Opus 5.5 and Fable 5.1 with an API key or a subscription**, where effort changes keep the cache -- so on those two you can drop to `low` for a routine stretch and back up again without paying a rebuild.

A few more actions invalidate the cache in Claude Code: compaction (it rebuilds the conversation layer), accumulating many images, and upgrading Claude Code.

### Summary of Cache-Breaking Actions

| Action | Cache Impact | Cost Penalty |
|--------|-------------|--------------|
| Edit CLAUDE.md mid-session | **None** -- the file is read once at session start | No penalty; the edit applies after `/clear`, `/compact`, or restart |
| Add/remove MCP server, or toggle a plugin that provides MCP servers | None with tool search on (the default); with tool search off, invalidates prefix from schema change onward | With tool search off: all history reprocessed at full input price |
| Deny an entire tool | Same rule: only breaks the cache when tool search is off | With tool search off: all history reprocessed at full input price |
| Change tool definitions mid-conversation (custom API tooling) | Invalidates prefix from schema change onward -- **unless** the `mid-conversation-tool-changes-2026-07-01` beta is enabled, which makes it free (on the Sonnet tier, Sonnet 5.5 only; Sonnet 5 does not support it) | All history reprocessed at full input price (no penalty with the beta) |
| Gap longer than the TTL between turns | Full cache expiration (TTL is 5 minutes, or 1 hour on a subscription's main conversation) | Entire prefix reprocessed (cache write at 1.25x) |
| Switch model mid-session | New model has empty cache, and may have a higher minimum cacheable length | Entire prefix reprocessed (cache write at 1.25x) |
| Change effort level | Invalidates the cache -- **except** on Opus 5.5 and Fable 5.1 with an API key or subscription | Entire prefix reprocessed (none on Opus 5.5 / Fable 5.1) |
| Turn on fast mode | Invalidates the cache once per conversation | Entire prefix reprocessed (cache write at 1.25x, at Fast Mode rates) |
| Accumulate many images, or upgrade Claude Code | Invalidates the cache | Entire prefix reprocessed |
| Prefix under the model's minimum length | `cache_control` silently ignored, no cache ever created | Full input price every turn, with no error to tell you |
| Use `/compact` | Rebuilds the conversation layer with a summary | While warm, the summarization reads the prefix from cache; the new, smaller summary is written to cache |

### /compact vs /clear vs /rewind

These three look similar but cost very different amounts ([Anthropic's prompt-caching docs](https://code.claude.com/docs/en/prompt-caching)):

| Command | What it costs |
|---------|---------------|
| `/compact` | Sends a summarization request that reads the prefix from cache while the cache is warm, so it costs a fraction of the context size. After a break longer than the TTL, it reprocesses the full history uncached. |
| `/clear` | Costs nothing. The next turn starts a fresh, small prefix. |
| `/rewind` | Returns to an already-cached prefix, so it keeps the cache. |

The practical rule: compact while the cache is still warm, not after you come back from a long break. The compressed context becomes a much smaller cacheable prefix going forward, which is usually a net positive for cost -- see [Guide 02](02-context-optimization.md).

---

## Cache TTL and Economics

### Standard vs Extended TTL

| TTL Option | Duration | Write Cost | Availability |
|------------|:--------:|:----------:|--------------|
| **Standard** | 5 minutes | 1.25x input price | API default; Claude Code on an API key, a cloud provider, or usage credits; subagents, workflows and compaction everywhere |
| **Extended** | 1 hour | 2x input price | API parameter; Claude Code main conversation on a subscription; or set `promptCacheTtl` |

### How Claude Code Picks the Cache TTL

Claude Code chooses the TTL for you based on how you pay ([Anthropic's prompt-caching docs](https://code.claude.com/docs/en/prompt-caching)):

| How you use Claude Code | Main conversation | Subagents, workflows, compaction |
|-------------------------|:-----------------:|:--------------------------------:|
| Claude subscription, within plan usage | **1 hour** | 5 minutes |
| API key, cloud provider, or drawing on usage credits | 5 minutes | 5 minutes |

To choose it yourself, set the `promptCacheTtl` setting or the `CLAUDE_CODE_PROMPT_CACHE_TTL` environment variable to `5m` or `1h`. Subagents have their own knob: `subagentPromptCacheTtl` / `CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL`. Both require Claude Code v2.1.242+. On an API key, `1h` raises the write price from 1.25x to 2x input, so run the [extended breakeven math](#extended-ttl-economics) before switching.

**Check your hit rate with `/usage`.** Since v2.1.251, `/usage` shows a `Prompt cache (main)` line with the hit share, misses, the likely cause, and whether the cache is warm or cold. It is the fastest way to confirm a habit is actually breaking the cache before you change it.

### 5-Minute TTL in Practice

This applies wherever Claude Code uses the 5-minute TTL: an API key, a cloud provider, usage credits, and every subagent. A subscription's main conversation gets an hour, so the long-break bullet below only bites there after 60 minutes. The 5-minute window is more generous than it sounds for Claude Code workflows:

- **Active coding sessions**: no published figure gives the typical gap between turns. Every turn sent within 5 minutes of the previous request reads the cache, and `/usage` shows whether yours is warm or cold.
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

On Opus 5.5 and Sonnet 5.5 (hits at 0.05x) and Fable 5.1 / Mythos 5.1 (0.025x) each hit saves more, so the breakeven arrives even sooner.

In other words: if you use the cached content even **once** after writing it, caching has already paid for itself. By the second cache hit, you are saving money. By the 10th hit, the savings are substantial.

**Worked example with 10,000 tokens of stable prefix on Sonnet 4.6:**

| Scenario | Turn 1 Cost | Turn 2 Cost | Turn 3 Cost | Total (3 turns) |
|----------|:-----------:|:-----------:|:-----------:|:---------------:|
| **No caching** | $0.0300 | $0.0300 | $0.0300 | $0.0900 |
| **With caching** | $0.0375 (write) | $0.0030 (hit) | $0.0030 (hit) | $0.0435 |
| **Savings** | -$0.0075 (costs more) | +$0.0270 | +$0.0270 | **+$0.0465 (52% saved)** |

By turn 3, caching has saved 52%. By turn 50, the savings approach 90% on the cached portion.

### Extended TTL Economics

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

In Claude Code this choice is made for you (see [How Claude Code Picks the Cache TTL](#how-claude-code-picks-the-cache-ttl)) unless you set `promptCacheTtl`. It matters most if you are on an API key and considering `1h`, or building custom tooling on the API.

**What Anthropic measured.** With no pauses between turns, the 5-minute default cost 15% less per session than the 1-hour cache on Sonnet 5 and 15% to 18% less on Opus 5.5; the 1-hour cache wins once about 1 turn in 20 follows a 5-to-60-minute pause. On Fable 5.1 a `max_tokens: 0` keep-alive every 4 minutes beat both: $2.29 per session vs $2.42 on the 5-minute cache and $3.09 on the 1-hour cache, with no pauses ([cost-optimization guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence), "Cache duration").

---

## Maximizing Cache Hit Rate

These strategies increase the percentage of input tokens that hit the cache:

### 1. Keep Model and Effort Constant During Sessions

Pick the model (and, on most models, the effort level) before the session starts and keep it. Editing CLAUDE.md is not the problem -- it keeps the cache, though the edit only applies after `/clear`, `/compact`, or restart. Switching models, or changing effort on anything other than Opus 5.5 and Fable 5.1, is what forces a rebuild.

**Cost of one cache break at turn 25 of a 50-turn session (Sonnet 4.6, e.g. an effort change):**

```
Cached history at turn 25:  ~75,000 tokens
Remaining turns:            25
Cache miss cost per turn:   75,000 x ($3.75 write - $0.30 read) / 1,000,000 = $0.2588
Total extra cost:           ~$0.26 (the turn after the break)
                            Claude Code writes the whole prompt back to cache on
                            that turn, so later turns read it again and the
                            penalty is one re-write.
```

The immediate penalty is about $0.26 on Sonnet 4.6, $0.36 on Opus 5.5 (75,000 x ($5.00 - $0.20)), or $0.43 on legacy Opus 5 (75,000 x ($6.25 - $0.50)) for the first turn after the break. Subsequent turns read the rebuilt cache.

### 2. Keep MCP Server Configuration Constant (If Tool Search Is Off)

With MCP tool search on (the default), connecting or removing a server keeps the cache, so this only matters if you run with tool search off. In that case, decide which MCP servers you need before starting a session, and do not connect or disconnect servers mid-session.

If you use different MCP servers for different types of work, use project-scoped MCP configuration (`.mcp.json` at the project root) rather than user-scoped servers in `~/.claude.json`. This way, each project loads only its relevant servers, and you avoid needing to toggle servers during a session.

### 3. Work in Focused Sessions

Many rapid turns on the same topic maximize caching. Across Anthropic's API traffic (14 days ending 2026-08-23, 303,003 organization-days from 106,487 organizations), agent loops read a median 84.2% of their input from cache (upper quartile 91.7%). Coding organizations read a median 88.5% (90.9% once a conversation has 25 or more prior tool calls), with the upper quartile at 93.4% and the top decile at 95.9% or more ([cost-optimization guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence), benchmark reference 17). If `/usage` shows your hit share well below those, something in your prefix is changing.

| Pattern | Cache Efficiency | Why |
|---------|:----------------:|-----|
| Many turns close together | 88.5% median (coding agent loops on Anthropic's API) | Prefix stays warm |
| Turns with long gaps | One full re-write per gap longer than the TTL (5 min on an API key, 1 hour for a subscription's main conversation) | At 100K tokens on Opus 5.5 a re-write costs $0.50 vs $0.02 to read |
| Several short sessions in one directory | Not measured | A new session reads the system prompt from cache only within the TTL and only if its git status snapshot matches |
| Single-turn conversations | Low (Anthropic measured a median 34.6% for API traffic with no tool definitions) | Only the shared system prompt and tools can hit, within the TTL |

### 4. Use /compact Strategically

`/compact` summarizes conversation history into a shorter form, which rebuilds the conversation layer of the cache. But it also dramatically reduces the total token count, making subsequent turns cheaper overall. Run it while the cache is warm: the summarization request then reads the prefix from cache and costs a fraction of the context size, whereas after a break longer than the TTL it reprocesses the full history uncached.

**When /compact helps caching:**
- After a large context has accumulated (50,000+ tokens of history), compact reduces it to ~5,000 tokens. The next turn pays cache write on 5,000 tokens instead of cache hit on 50,000 tokens -- but every turn after that processes far fewer total tokens.

**When /compact hurts caching:**
- If you compact too frequently (every 5-10 turns), you repeatedly pay cache write costs without accumulating enough cached turns to justify it.

**Time unavoidable cache breaks to a compaction boundary.** Compaction rebuilds the conversation layer anyway, so a change that breaks the cache costs least right after it. In Anthropic's measured run (Sonnet 5), changing effort and adding a tool right after the first compaction cost $0.75 per session, against $0.95 for the same change mid-session. Making the change on the compaction request itself cost $0.92, because that summarization pass then cost $0.21 instead of $0.04 ([cost-optimization guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence), "Mid-session changes and compaction").

**Rule of thumb**: Compact when context exceeds 80,000-100,000 tokens, or at natural breakpoints in your work (finishing a feature, switching to a different file).

### 5. Front-Load Stable Content in CLAUDE.md

Claude's prompt is structured so that CLAUDE.md appears near the beginning of the prefix. This means CLAUDE.md content is always in the cached prefix, and because it is read once at session start, mid-session edits do not disturb it. You do not need to reorder content within CLAUDE.md for caching purposes -- the entire file is part of the prefix regardless of internal ordering.

What does matter is size, because the root file loads in full on every session. If you use multiple CLAUDE.md files, remember that subdirectory CLAUDE.md files and path-scoped `.claude/rules/` load on demand, when Claude first reads a matching file -- so moving area-specific content there keeps the always-loaded prefix small.

---

## ROI Calculations

### Scenario 1: 50-Turn Session with Good Caching

**Setup**: Sonnet 4.6, 150-line CLAUDE.md, 3 MCP servers, focused session with turns every 1-2 minutes. No model or effort switches.

**Stable prefix**: System prompt (3,500) + CLAUDE.md (1,050) + Tool schemas (4,000) = 8,550 tokens

```
Turn  1: 8,550 prefix + 100 tokens new input, all written to cache (1.25x)
         Total input cost:  8,650 x $3.75/1M = $0.0324
         Output: 700 tokens x $15.00/1M = $0.0105
         Turn total: $0.043

Turn 10: 8,550 prefix + 27,000 history = 35,550 cached tokens
         + 3,000 new tokens (latest turn exchange + tool results),
           written to cache at 1.25x
         Input cost:  35,550 x $0.30/1M + 3,000 x $3.75/1M
                    = $0.0107 + $0.0113 = $0.0219
         Output: 700 tokens x $15.00/1M = $0.0105
         Turn total: $0.032

Turn 25: 8,550 prefix + 72,000 history = 80,550 cached tokens
         + 3,000 new tokens written at 1.25x
         Input cost:  80,550 x $0.30/1M + 3,000 x $3.75/1M
                    = $0.0242 + $0.0113 = $0.0354
         Output: 700 tokens x $15.00/1M = $0.0105
         Turn total: $0.046

Turn 50: 8,550 prefix + 147,000 history = 155,550 cached tokens
         + 3,000 new tokens written at 1.25x
         Input cost:  155,550 x $0.30/1M + 3,000 x $3.75/1M
                    = $0.0467 + $0.0113 = $0.0579
         Output: 700 tokens x $15.00/1M = $0.0105
         Turn total: $0.068

All 50 turns:  4,093,950 tokens read    x $0.30/1M  = $1.23
               155,650 tokens written   x $3.75/1M  = $0.58
               35,000 output tokens     x $15.00/1M = $0.53
               96.3% of the 4,249,600 input tokens read from cache
```

**Total session cost: $2.34 on Sonnet 4.6** (computed: $1.23 + $0.58 + $0.53)

### Scenario 2: 50-Turn Session with Poor Caching

**Setup**: Same session, but the developer runs with MCP tool search off (`ENABLE_TOOL_SEARCH=false`) and connects or removes an MCP server at turns 10, 20, 30, and 40. Also takes a 20-minute break at turn 15 on an API key (5-minute TTL, so the cache expires). Switches from Sonnet to Opus 5.5 at turn 35.

Each of these events makes Claude Code re-write the whole accumulated prefix to cache at 1.25x instead of reading it. The extra cost is the write minus the read it replaces (prefix sizes from Scenario 1: 8,550 + (turn - 1) x 3,000):

```
Turn 10 (after MCP server change, tool search off):
  Re-write of the 35,550-token prefix
  Extra cost: 35,550 x ($3.75 - $0.30) / 1M = $0.123

Turn 15 (after 20-min break, cache expired):
  Re-write of the 50,550-token prefix
  Extra cost: 50,550 x ($3.75 - $0.30) / 1M = $0.174

Turn 20 (after MCP server change):
  Re-write of the 65,550-token prefix
  Extra cost: 65,550 x ($3.75 - $0.30) / 1M = $0.226

Turn 30 (after MCP server change):
  Re-write of the 95,550-token prefix
  Extra cost: 95,550 x ($3.75 - $0.30) / 1M = $0.330

Turn 35 (model switch to Opus 5.5, new cache):
  Re-write of the 110,550-token prefix on Opus 5.5
  Extra cost: 110,550 x ($5.00 - $0.20) / 1M = $0.531

Turn 40 (after MCP server change, still on Opus 5.5):
  Re-write of the 125,550-token prefix
  Extra cost: 125,550 x ($5.00 - $0.20) / 1M = $0.603
```

**Total with all cache breaks: $4.23** (computed) -- the $2.34 good-caching session from Scenario 1, plus $1.99 of cache-break penalties, minus $0.10 because on warm turns 35-50 Opus 5.5's $0.20 cache hits (Sonnet 4.6: $0.30) save more than its $5.00 writes and $20 output (Sonnet 4.6: $3.75 and $15) add.

That is 1.8x the cost of the same 50-turn session with good caching. Note what is **not** on the list: editing CLAUDE.md mid-session would have cost nothing.

### Comparison Table: Cache Hit Rate Impact

**Scenario 1's 50-turn session on Sonnet 4.6: 4,249,600 input tokens, 3,000 new tokens per turn, 700 output tokens per turn. The hit rate is the share of input tokens read from cache, the figure `/usage` reports.**

| Cache Hit Rate | Input Cost | Output Cost | Total Session Cost | vs No Caching |
|:--------------:|:----------:|:-----------:|:------------------:|:-------------:|
| **96.3%** (warm all session, Scenario 1) | $1.81 | $0.525 | **$2.34** | **82% savings** |
| **90%** | $2.74 | $0.525 | **$3.27** | **75% savings** |
| **75%** | $4.94 | $0.525 | **$5.47** | **59% savings** |
| **50%** | $8.61 | $0.525 | **$9.13** | **31% savings** |
| **25%** | $12.27 | $0.525 | **$12.80** | **4% savings** |
| **0%** (every token written, none read) | $15.94 | $0.525 | **$16.46** | **24% more** |
| **No caching** (1x input) | $12.75 | $0.525 | **$13.27** | baseline |

*Computed: input = 4,249,600 x (hit share x $0.30 + (1 - hit share) x $3.75) / 1M, because Claude Code writes every token it does not read from cache, at 1.25x; with no caching all of them bill at $3.00. Below a 21.7% hit share, caching costs more than none ((3.75 - 3.00) / (3.75 - 0.30)). Anthropic's production medians, 84.2% for agent loops and 88.5% for coding, fall between the 75% and 90% rows ([cost-optimization guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence), benchmark reference 17).*

> Output tokens are never cached -- they are always generated fresh. Caching only affects input tokens. This is why the output cost ($0.525) is constant across all rows.

**Monthly impact (5 sessions/day, 22 working days = 110 sessions):**

| Cache Hit Rate | Monthly Cost (Sonnet 4.6) | Monthly Cost (legacy Opus 5) |
|:--------------:|:---------------------:|:-------------------:|
| **96.3%** (warm) | $257 | $428 |
| **90%** | $359 | $599 |
| **75%** | $601 | $1,002 |
| **50%** | $1,004 | $1,674 |
| **No caching** | $1,460 | $2,434 |

*Computed: 110 x the session cost at that hit share; legacy Opus 5 at $5/$25, $0.50 read, $6.25 write.*

The difference between the warm session and no caching is **$1,203/month on Sonnet 4.6** and **$2,005/month on legacy Opus 5**, and slipping from 96.3% to 90% alone costs $102 and $170 a month. Opus 5.5 lands below the Opus 5 column at every row, because its input ($4 vs $5), output ($20 vs $25) and cache-hit ($0.20 vs $0.50) rates are all lower. Good caching hygiene is one of the most impactful cost optimizations available.

---

## Advanced Patterns

### Structuring CLAUDE.md

CLAUDE.md is part of the cached prefix, but it is read once at session start, so edits never break a running session's cache. What it costs is size: it loads in full on every session. Anthropic's guidance is to "target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence." Apply these principles:

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

Keep it concise, and move workflow-specific instructions (PR reviews, database migrations) into skills or path-scoped `.claude/rules/`, which load on demand instead of on every session.

### Leveraging Custom Commands for Caching

Custom slash commands (defined in `.claude/commands/`) are added to the conversation when invoked, and invoking a skill or command keeps the cache. If you use the same custom commands repeatedly across turns, their content benefits from caching just like the rest of the prompt prefix.

This is another reason to prefer custom commands over repeatedly typing the same complex instructions -- the command text gets cached after the first use.

### Session Planning for Cache Optimization

Structure your work to maximize consecutive turns within the cache TTL:

```
Efficient (cache-friendly):
  Session 1: Implement feature A (30 turns, focused)
  Session 2: Write tests for feature A (20 turns, focused)
  Session 3: Review and refactor (15 turns, focused)

Inefficient (cache-hostile):
  Session 1: Start feature A, get distracted, switch to bug fix,
             come back to feature A, switch models, change effort,
             take a break longer than the TTL, resume (50 scattered turns)
```

The three focused sessions will cost less in total than the single scattered session, even though they process the system prompt and CLAUDE.md from scratch three times. The cache hit rate within each session more than compensates.

### Batch Work Within the TTL Window

If you have multiple related questions or tasks, batch them into consecutive turns rather than spacing them out:

```
Good: Ask question 1, get answer, ask question 2, get answer, ask question 3
      (all within 5 minutes -- cache stays warm)

Bad:  Ask question 1, go do something else for 10 minutes, ask question 2,
      go do something else for 10 minutes, ask question 3
      (on a 5-minute TTL, the cache expires between each question)
```

---

## Common Mistakes

### 1. Changing Effort or Model Every Few Turns

Some developers flip effort up and down (or bounce between models) every few turns, thinking it saves money. On most models each change is a full cache break. (Editing CLAUDE.md, the old suspect, is not: it keeps the cache, and the edit only applies after `/clear`, `/compact`, or restart.)

**The math**: If your session has accumulated 60,000 tokens of cached history on Sonnet 4.6 and you change the effort level, the next turn re-writes all 60,000 tokens to cache at 1.25x instead of reading them: 60,000 x ($3.75 - $0.30) / 1M = an extra $0.21 for that single turn. Do this 4 times in a session and you have wasted $0.83 -- more than a whole 30-turn Opus 5.5 session costs at this repo's calculator defaults ($0.74).

**Better approach**: Pick the model and effort before the session starts. On Opus 5.5 and Fable 5.1 (API key or subscription), effort changes keep the cache, so there you can adjust freely.

### 2. Frequently Switching MCP Servers With Tool Search Off

With MCP tool search on (the default), connecting and disconnecting servers keeps the cache. With tool search off, full schemas sit in the prefix, so every server change breaks it.

**Better approach**: Leave tool search on. If you must run with it off, use project-scoped MCP configs (`.mcp.json` at the project root) to ensure each project has exactly the servers it needs. No toggling required.

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

If you know you will be away for longer than the TTL (5 minutes on an API key, cloud provider or usage credits; an hour on a subscription's main conversation), run `/compact` before stepping away. While the cache is warm, `/compact` reads the history from cache, so it costs a fraction of the context size. When you return, the context will be smaller, and the cache write cost on the first turn back will be lower.

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

1. **Prompt caching bills repeated input at 10% of the input price -- 5% on Opus 5.5 and Sonnet 5.5, 2.5% on Fable 5.1 / Mythos 5.1.** Across Anthropic's API traffic, coding agent loops read a median 88.5% of their input from cache (upper quartile 93.4%). This is the largest automatic cost reduction in Claude Code.

2. **Know the real cache breakers.** Switching models, changing effort (except on Opus 5.5 and Fable 5.1 with an API key or subscription), turning on fast mode (once per conversation), and MCP changes with tool search off all force a rebuild. Editing CLAUDE.md mid-session does not -- but the edit only applies after `/clear`, `/compact`, or restart. `/usage` shows a `Prompt cache (main)` line with your hit share and the likely cause of misses.

3. **Caching pays for itself after just one reuse.** The cache write premium (1.25x) is recovered with a single cache hit (0.1x). Every subsequent hit is pure savings.

4. **Work in focused sessions with turns inside the TTL.** Claude Code gives a subscription's main conversation a 1-hour TTL; an API key, cloud provider, usage credits and every subagent get 5 minutes (override with `promptCacheTtl` and `subagentPromptCacheTtl`). Rapid, focused sessions maintain a warm cache. Scattered work with long gaps between turns wastes money on repeated cache writes.

5. **Run /compact before long breaks.** If you are stepping away for longer than the TTL, compacting first (while the cache is warm) reduces the cache write cost when you return. `/clear` costs nothing; `/rewind` returns to an already-cached prefix.

6. **On this guide's 50-turn Sonnet 4.6 session, caching is the difference between $257 and $1,460 a month** (110 sessions, computed in [the comparison table](#comparison-table-cache-hit-rate-impact)). Slipping from the warm 96.3% hit share to 90% alone costs $102 a month. Good caching hygiene is not optional -- it is one of the highest-ROI optimizations you can make.

7. **Know your model's minimum cacheable prompt length.** Opus 5.5, Opus 5, Sonnet 5.5 and Haiku 5.5 cache from 512 tokens, Opus 4.8 and Sonnet 5 from 1,024, Opus 4.7 from 2,048, legacy Haiku 4.5 from 4,096. Below the floor, `cache_control` is silently ignored -- you pay full price every turn with no error. If you build custom API tooling, check `cache_read_input_tokens` in the `usage` block to confirm the cache is real.

8. **On Haiku 5.5, cached tokens still count toward the 100K tier line.** A request over 100,000 prompt tokens, cache reads and writes included, pays $0.50/$2.50 and a $0.05 cache hit on the whole request instead of $0.10/$0.50 and $0.01. Keep Haiku 5.5 prompts under 100K, cached prefix and all.

---

*Previous: [Guide 07 - MCP Server and Agent Cost Impact](07-mcp-agent-costs.md)*
