# Guide 08: Prompt Caching

> **Prompt caching is the single largest automatic discount on your Claude Code bill.** It reduces input token costs by 90% on repeated content on most models -- **95% on Opus 5.5 and Sonnet 5.5 (0.05x) and 97.5% on Fable 5.1 and Mythos 5.1 (0.025x)** -- and it happens without any configuration. On Anthropic's benchmarks caching cut cost by a factor of 4.8 to 7.2 on a research agent and by 83% to 86% on a small triage agent (88% with input trimming); on DeepResearch Bench II it took Fable 5.1 from $40.58 to $5.64 a task and Sonnet 5.5 from $5.13 to $1.05. Without caching, a run costs 3.3x as much on Opus 5.5 and 3.1x on Sonnet 5.5 (SWE-bench Pro), 1.7x on Haiku 5.5 (Managed Agents tasks) and 7.3x on Sonnet 5.5 for the triage agent ([cost-optimization guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence), "Why caching comes first" and the lever table, read 2026-11-01). This guide covers how it works, what breaks it, and how to keep the hit rate high.

---

## Table of Contents

- [How Prompt Caching Works](#how-prompt-caching-works)
  - [The Prefix Matching Rule](#the-prefix-matching-rule)
  - [Cache Pricing by Model](#cache-pricing-by-model)
  - [Minimum Cacheable Prompt Length](#minimum-cacheable-prompt-length)
  - [Cache Write vs Cache Hit](#cache-write-vs-cache-hit)
- [What Gets Cached in Claude Code](#what-gets-cached-in-claude-code)
- [What Breaks the Cache](#what-breaks-the-cache)
  - [Diagnose a Miss](#diagnose-a-miss)
- [Cache TTL and Economics](#cache-ttl-and-economics)
  - [Standard vs Extended TTL](#standard-vs-extended-ttl)
  - [How Claude Code Picks the Cache TTL](#how-claude-code-picks-the-cache-ttl)
  - [Idle Compaction](#idle-compaction)
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
│ CLAUDE.md                  (1,500 tokens)        │ ← Cached (identical to Turn N-1)
│ Tool Schemas / MCP         (2,000 tokens)        │ ← Cached (identical to Turn N-1)
│ Conversation History       (40,000 tokens)       │ ← Cached (prefix matches Turn N-1)
│ New user message           (100 tokens)          │ ← NOT cached (new content)
│ New tool results           (1,500 tokens)        │ ← NOT cached (new content)
└─────────────────────────────────────────────────┘
```

In this example, 47,000 tokens (system prompt + CLAUDE.md + tool schemas + conversation history) are cache hits. Only the new user message and tool results (1,600 tokens) are new, and Claude Code writes them to cache at 1.25x the input price so the next turn can read them: "the prefix is the entire previous request and only the latest exchange is new" ([Claude Code prompt caching](https://code.claude.com/docs/en/prompt-caching)).

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
> This also flips a planning default. Because a hit costs so little *relative to a miss* on Fable 5.1, losing the cache hurts far more than it does elsewhere, while a read is nearly free. When pauses run for minutes, re-sending the previous request with `max_tokens: 0` every 4 minutes to refresh the 5-minute entry cost 13% to 20% less than paying the 2x write for the 1-hour TTL on Fable 5.1 -- the keep-alive bills only a cheap cache read and no output tokens. On Opus 5.5 and Sonnet 5.5 it wins only when few turns pause (only 1 or 2 gaps in 20 between 5 minutes and an hour: 8% to 13% less on Opus 5.5, 8% to 16% less on Sonnet 5.5), and the 1-hour TTL wins when a pause comes before every turn; on Haiku 5.5, whose cache reads are 0.1x, Anthropic says to use the "Any model" rows of its table (5-minute default when turns arrive seconds apart or gaps over an hour are common, 1-hour TTL once about 1 turn in 20 follows a pause of 5 minutes to an hour) ([cost-optimization guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence), "Pick the cache duration", read 2026-11-01). (`max_tokens: 0` can't be combined with streaming, structured outputs, or Batches; where the request can't be reshaped, use the 1-hour TTL.)
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

Both zones are cached, but the dynamic zone's cache is invalidated whenever any of its components change. CLAUDE.md is not one of the things that changes mid-session: Claude Code reads the root and user CLAUDE.md once at session start, so editing the file on disk does not change the prompt and does not invalidate the cache ([Anthropic's prompt-caching docs](https://code.claude.com/docs/en/prompt-caching)). The edit applies after the next `/clear`, `/compact`, or restart. Anthropic's own docs describe three layers instead of two zones: the system prompt (core instructions and tool definitions), project context (CLAUDE.md, auto memory and unscoped rules, which change when a session starts or after `/clear` or `/compact`) and the conversation. The conversation opens with an announcement of the working directory, platform, shell and OS version, and carries the git status snapshot taken at startup ([prompt caching docs](https://code.claude.com/docs/en/prompt-caching), read 2026-11-01).

**Practical implication**: The ~3,500 tokens of static instructions get cached reliably regardless of what you do. Your CLAUDE.md gets cached too, and editing it mid-session is safe for the cache -- just do not expect the new version to apply until you `/clear`, `/compact`, or restart.

### Component Breakdown

| Component | Approx. Tokens | Cache Zone | Cache Behavior |
|-----------|:--------------:|:----------:|----------------|
| **System prompt** | ~3,500 | Static | Cached on every turn after the first. This is Claude Code's built-in instruction set -- it never changes during a session. |
| **Tool schemas (built-in)** | ~1,000-2,000 | Static | Cached if the set of available tools stays constant. Includes Read, Edit, Write, Bash and, on Windows, Grep and Glob (on macOS, Linux and WSL Claude Code leaves them out of the default tools and searches through Bash; [tools reference](https://code.claude.com/docs/en/tools-reference), read 2026-11-01), etc. |
| **CLAUDE.md content** | ~10 per line | Dynamic | Read once at session start, so a mid-session edit neither changes the prompt nor breaks the cache (it applies after `/clear`, `/compact`, or restart). A 150-line file adds ~1,500 tokens that stay cached. The per-line figure is measured on this repo's 15 CLAUDE.md files: 20,161 cl100k tokens over 2,048 lines, 9.8 per line counting blank lines; the Opus 4.7+ tokenizer adds about 30% ([pricing page](https://platform.claude.com/docs/en/about-claude/pricing)). |
| **Environment context** | ~200-500 | Dynamic | OS, shell, cwd, git status. Anthropic's docs put the working-directory and OS announcement and the git status snapshot at the start of the conversation, and the snapshot is taken at startup, so sequential sessions share a prefix only when it matches. |
| **MCP tools** | Tool names + server instructions (full schemas only with tool search off) | Dynamic | MCP tool search is on by default: only tool names and server instructions enter context until Claude uses a tool, and connecting or removing a server keeps the cache. With tool search off, full schemas load up front and a server change invalidates the cache. |
| **Conversation history** | Grows each turn | After prefix | The portion of history that is identical to the previous turn (all turns except the newest) is cached. |

### How It Plays Out Over a Session

```
Turn 1:  Cache write on system prompt + CLAUDE.md + tools (7,000 tokens at 1.25x)
Turn 2:  Cache hit on 7,000 tokens + cache write on turn 1 exchange (~3,000 tokens)
Turn 3:  Cache hit on 10,000 tokens + cache write on turn 2 exchange (~3,000 tokens)
...
Turn 50: Cache hit on ~154,000 tokens + cache write on turn 49 exchange (~3,000 tokens)
```

By turn 50, the vast majority of your input tokens are cache hits. Only the newest turn's exchange and your current message are processed at full price.

---

## What Breaks the Cache

Because caching relies on exact prefix matching, anything that changes the prefix invalidates the cache from that point forward. A break can cost more than no caching at all: in Anthropic's measured triage run, a cache-busting 25-token status line at the front of the system prompt made the run cost $4.24 instead of $0.59 (7.2x, computed 4.24 / 0.59), more than running with caching off ([cost-optimization guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence), "What breaks the cache", read 2026-11-01). Here are the specific actions that break it in Claude Code -- and one that famously does not:

### 1. Editing CLAUDE.md Mid-Session (Keeps the Cache)

Editing CLAUDE.md mid-session does **not** invalidate the cache. Claude Code reads the root and user CLAUDE.md once at session start, so changing the file on disk does not change the prompt. The flip side: the edit does not apply until the next `/clear`, `/compact`, or restart. Nested CLAUDE.md files and path-scoped rules load later, when Claude first reads a matching file.

Other actions that keep the cache: editing repo files, changing permission mode, changing output style, invoking skills or commands, `/recap`, `/rewind`, and spawning a subagent. An ordinary subagent starts a cache of its own on a 5-minute TTL; a fork (on by default in `claude -p`, the SDK, desktop and VS Code since v2.1.302) inherits the parent's system prompt, tools and history, so its first request reads the parent's cache ([prompt caching docs](https://code.claude.com/docs/en/prompt-caching), "Subagents and the cache", read 2026-11-01).

### 2. Adding or Removing MCP Servers (Only With Tool Search Off)

MCP tool search is on by default: tool definitions are deferred, and only tool names and server instructions enter context until Claude uses a specific tool. With tool search on, connecting or removing a server does **not** invalidate the cache.

The old rule still applies when tool search is off or unavailable (`ENABLE_TOOL_SEARCH=false`, `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS`, a gateway that rejects it, models older than the Claude 4.5 generation on Google Cloud's Agent Platform (Google managed, formerly Vertex AI), or a Microsoft Foundry deployment hosted on Azure). Then full schemas load up front, and connecting or removing a server -- or enabling or disabling a plugin that provides MCP servers, or denying an entire tool -- changes the prefix and breaks the cache on everything that follows. A custom `ANTHROPIC_BASE_URL` no longer turns tool search off by itself: it is on behind a custom base URL by default since v2.1.304 ([MCP docs](https://code.claude.com/docs/en/mcp), read 2026-11-01).

> **Mid-conversation tool changes caveat (updated 2026-11-01)**: the beta `inline-tools-2026-09-15` lets tools change between turns **without** invalidating the prompt cache (add or remove a tool by reference, or define a tool inside a `tool_addition` block in a mid-conversation system message). The older `mid-conversation-tool-changes-2026-07-01` header (first announced 2026-07-24 for Opus 5) still works for changes that name a tool by reference. With a header set, changing tools mid-conversation is no longer a cache-busting move. Without one, the old rule stands: changing the tool set reprocesses everything after the schema block at full price. It is a beta opt-in on the API, so assume the old behavior unless you are explicitly sending the header ([mid-conversation system messages and tool changes](https://platform.claude.com/docs/en/build-with-claude/mid-conversation-system-messages), [Opus 5.5 migration guide](https://platform.claude.com/docs/en/models/opus-5-5/migration-guide), read 2026-11-01).
>
> **Sonnet 5.5 caveat (2026-09-28)**: mid-conversation tool changes (beta), mid-conversation system messages and per-message effort (beta) are supported on **Sonnet 5.5 and not on Sonnet 5**, so on the Sonnet tier tools and instructions can change mid-conversation without losing the prompt cache only after you move to Sonnet 5.5. Mid-conversation system messages and tool changes are also available on Fable 5.1, Mythos 5.1, Fable 5, Mythos 5, Opus 5.5, Opus 5, Opus 4.8 and Haiku 5.5; per-message effort (beta, `mid-conversation-output-config-2026-07-01`) on Fable 5.1, Mythos 5.1, Opus 5.5, Opus 5 and Haiku 5.5 on the Claude API and Google Cloud (Google managed).

### 3. Cache TTL Expiration

The standard cache has a 5-minute time-to-live. If you wait longer than the TTL between turns, the cache expires and the next turn pays cache write costs on the entire prefix again. In Claude Code the TTL depends on how you pay: a subscription's main conversation gets one hour, everything else gets five minutes (see [How Claude Code Picks the Cache TTL](#how-claude-code-picks-the-cache-ttl)).

This means:
- Rapid consecutive turns (inside the TTL) maximize caching
- Taking a long break mid-session (lunch, meetings) resets the cache
- The content is still in your conversation history -- you just pay full price to reprocess it on the next turn after the gap

### 4. Switching Models Mid-Session

Each model maintains its own cache. Switching from Sonnet to Opus (or vice versa) means the new model has no cached prefix -- everything is processed from scratch. Some switches are easy to miss: each plan-mode toggle under the `opusplan` setting, an automatic fallback model after a safety-classifier flag, and a skill or command whose frontmatter names a different `model` all count as model switches ([prompt caching docs](https://code.claude.com/docs/en/prompt-caching), "Switching models", read 2026-11-01).

Switching model also changes the minimum cacheable length. Moving from Opus 5.5, Sonnet 5.5 or Haiku 5.5 (512) to Sonnet 5 (1,024) or legacy Haiku 4.5 (4,096) can turn a previously-cached small prefix into one that never caches at all. See [Minimum Cacheable Prompt Length](#minimum-cacheable-prompt-length).

### 5. Switching Speed Mid-Session (Fast Mode)

Changing `speed` between requests invalidates the prompt cache, the same way switching models does: fast and standard speed keep separate caches. In Claude Code, the first time you turn fast mode on in a conversation the next request reads the whole conversation so far uncached at fast mode rates, and each later toggle (including the automatic fallback to standard speed after a rate limit and the return to fast mode) can read it uncached again, so turn it on at the start of a session ([Claude Code prompt caching](https://code.claude.com/docs/en/prompt-caching), "Turning on fast mode", read 2026-11-01). Fast Mode is supported on **Opus 5.5, Opus 5 and Opus 4.8 only**, each at 2x its own base rate: $8/$40 on Opus 5.5, $10/$50 on Opus 5 and Opus 4.8. Opus 4.7 with `speed: "fast"` returns an error, and Opus 4.6 silently runs at standard speed and standard rates (`usage.speed` comes back `"standard"`). The old 6x tier no longer exists.

Fast Mode is generally available on Opus 5.5 (no beta header) and a research preview on Opus 5 and Opus 4.8, which need the `fast-mode-2026-02-01` header; Opus 4.8 Fast Mode is deprecated (2026-10-30) and will be removed on 2026-11-30. Opus 5.5 runs it on the Claude API, Google Cloud (Anthropic managed) and Microsoft Foundry deployments hosted on Azure; Opus 5 and Opus 4.8 on the Claude API only (plus Managed Agents). It is not on Bedrock, Google Cloud (Google managed, formerly Vertex AI), Claude Platform on AWS, Batch, or Priority Tier, and Claude Code offers it only on the Anthropic API or a subscription with usage credits turned on ([fast mode docs](https://platform.claude.com/docs/en/build-with-claude/fast-mode), [Claude Code fast mode](https://code.claude.com/docs/en/fast-mode), read 2026-11-01).

### 6. Changing Effort Level

Changing the effort level invalidates the cache on most models. The exception is **Opus 5.5, Sonnet 5.5, Haiku 5.5 and Fable 5.1 with an API key or a Claude subscription**, where effort changes keep the cache -- so on those four you can drop to `low` for a routine stretch and back up again without paying a rebuild. The exemption does not apply on Amazon Bedrock, Google Cloud's Agent Platform or a Claude apps gateway, with `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS`, or under a HIPAA configuration; there an effort change rebuilds the cache as on other models ([Claude Code prompt caching](https://code.claude.com/docs/en/prompt-caching), "Changing effort level", read 2026-11-01). On your own API calls the same change at the top level invalidates the cache: on a cached conversation of about 100,000 tokens Anthropic measured it at 20 to 40 times the cost of changing effort per message ([cost-optimization guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence), "What breaks the cache", read 2026-11-01).

A few more actions invalidate the cache in Claude Code: compaction (it rebuilds the conversation layer), accumulating many images, and upgrading Claude Code.

### Summary of Cache-Breaking Actions

| Action | Cache Impact | Cost Penalty |
|--------|-------------|--------------|
| Edit CLAUDE.md mid-session | **None** -- the file is read once at session start | No penalty; the edit applies after `/clear`, `/compact`, or restart |
| Add/remove MCP server, or toggle a plugin that provides MCP servers | None with tool search on (the default); with tool search off, invalidates prefix from schema change onward | With tool search off: all history reprocessed at full input price |
| Deny an entire tool | Same rule: only breaks the cache when tool search is off | With tool search off: all history reprocessed at full input price |
| Change tool definitions mid-conversation (custom API tooling) | Invalidates prefix from schema change onward -- **unless** the `inline-tools-2026-09-15` beta (or the older `mid-conversation-tool-changes-2026-07-01` for changes by reference) is enabled, which makes it free (on the Sonnet tier, Sonnet 5.5 only; Sonnet 5 does not support it) | All history reprocessed at full input price (no penalty with the beta) |
| Gap longer than the TTL between turns | Full cache expiration (TTL is 5 minutes, or 1 hour on a subscription's main conversation) | Entire prefix reprocessed (cache write at 1.25x) |
| Switch model mid-session | New model has empty cache, and may have a higher minimum cacheable length | Entire prefix reprocessed (cache write at 1.25x) |
| Change effort level | Invalidates the cache -- **except** in Claude Code on Opus 5.5, Sonnet 5.5, Haiku 5.5 and Fable 5.1 with an API key or subscription (not on Bedrock, Google Cloud's Agent Platform, a Claude apps gateway or a HIPAA configuration) | Entire prefix reprocessed (none on those four models) |
| Turn fast mode on or off | Fast and standard speed keep separate caches, so each toggle (and the automatic fallback to standard speed after a rate limit) can read the conversation uncached again | Entire prefix reprocessed (cache write at 1.25x, at Fast Mode rates when going to fast) |
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

The practical rule: compact while the cache is still warm, not after you come back from a long break. The compressed context becomes a much smaller cacheable prefix going forward, which is usually a net positive for cost -- see [Guide 02](02-context-optimization.md). The turn after a compaction is not just the summary: Claude Code re-reads up to five recently read or edited files (a file over 5,000 tokens comes back as a path only), re-injects invoked skill bodies at up to 5,000 tokens each and 25,000 in total, and rebuilds the skill list (v2.1.304+) ([context window docs](https://code.claude.com/docs/en/context-window), read 2026-11-01).

### Diagnose a Miss

Since v2.1.260 Claude Code names the likely cause of the last cache miss in two places: the `Prompt cache (main)` line of `/usage` (for example `likely cause: tool definitions changed`), and `prompt_cache.last_miss_cause.causes` in the status line's input, an array of one or more cause names. Both summarize the main conversation of the current session; subagent requests are not counted. A request counts as a miss when it re-processed more than 5% and at least 2,000 tokens of what it could have read from cache, with no compaction or tool-result clearing to explain it; those count as expected rebuilds instead ([prompt caching docs](https://code.claude.com/docs/en/prompt-caching), [status line docs](https://code.claude.com/docs/en/statusline), read 2026-11-03).

| Cause name | What changed | What to do |
|------------|--------------|------------|
| `tools_changed` | The set of tool definitions in the request (the status line also gives `tools_added` and `tools_removed`) | With tool search off, or under an `ENABLE_TOOL_SEARCH=auto` threshold, a server connecting, a server or plugin you disable, or a tool you deny outright changes the set. Settle servers and deny rules before the session, and leave tool search on ([Adding or Removing MCP Servers](#2-adding-or-removing-mcp-servers-only-with-tool-search-off)) |
| `system_prompt_changed` | The system prompt layer, core instructions and tool definitions (the status line gives `system_char_delta`, the change in characters) | Keep `--system-prompt` and `--append-system-prompt` text the same for the life of a conversation; by default a resumed conversation keeps the system prompt it started with until it is compacted |
| `ttl_expired_5m` | The gap since the last request outlasted the 5-minute TTL | Batch related turns inside the TTL, `/compact` before a long break ([Taking Long Breaks](#5-taking-long-breaks-without-compacting-first)), and on an API key run the [extended breakeven](#extended-ttl-economics) before setting `promptCacheTtl` to `1h` |
| `likely_server_side` | Claude Code found no change on your side | Nothing in your setup to change |

The cause names are examples the docs list, not a closed set. To watch them live, `claude-rate --statusline` (claude-rate 0.4.0 or later) reads the same status line input and prints the cache state with the last miss cause; [templates/settings/statusline.json](../templates/settings/statusline.json) has the settings snippet.

`/usage` and the status line see one session. For a longer look back, `claude-rate --usage` (claude-rate 0.4.0 or later) walks the last 30 days of your local transcripts, main conversation and subagents alike, and lists cache breaks by likely cause with the extra list-price dollars each cost over a warm read, plus a 1-hour TTL what-if for the main conversation and for subagents separately. The what-if compares the share of 5-minute writes that were rebuilds after a 5-to-60-minute gap with the break-even share (1h write - 5m write) / (1h write - cache read): 38.5% on Opus 5.5, computed as ($8.00 - $5.00) / ($8.00 - $0.20). Its causes come from what transcripts record (a miss reason Claude Code wrote, if any, then compaction markers, model, speed, the gap between timestamps, effort and Claude Code version; anything else is "unknown"), so they are heuristics, and the gaps it measures include the time Claude spent generating a response. The dollars are list price; on a subscription they show where the allowance went, not a bill.

---

## Cache TTL and Economics

### Standard vs Extended TTL

| TTL Option | Duration | Write Cost | Availability |
|------------|:--------:|:----------:|--------------|
| **Standard** | 5 minutes | 1.25x input price | API default; Claude Code on an API key, a cloud provider, or usage credits; subagents, workflows and compaction everywhere |
| **Extended** | 1 hour | 2x input price | API parameter; Claude Code main conversation on a subscription; or set `promptCacheTtl` |

### How Claude Code Picks the Cache TTL

Claude Code chooses the TTL for you based on how you pay ([Anthropic's prompt-caching docs](https://code.claude.com/docs/en/prompt-caching)):

| How you use Claude Code | Main conversation | Subagents, forks, workflows, compaction |
|-------------------------|:-----------------:|:--------------------------------:|
| Claude subscription, within plan usage | **1 hour** | 5 minutes |
| API key, cloud provider, or drawing on usage credits | 5 minutes | 5 minutes |

To choose it yourself, set the `promptCacheTtl` setting or the `CLAUDE_CODE_PROMPT_CACHE_TTL` environment variable to `5m` or `1h`. Subagents have their own knob: `subagentPromptCacheTtl` / `CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL`. Both require Claude Code v2.1.242+. On an API key, `1h` raises the write price from 1.25x to 2x input, so run the [extended breakeven math](#extended-ttl-economics) before switching. To confirm which TTL your main conversation's writes used, run `claude -p "hello" --output-format json` and read `usage.cache_creation` (`ephemeral_5m_input_tokens` vs `ephemeral_1h_input_tokens`); the OpenTelemetry `api_request` event splits cache writes the same way with `cache_creation_5m_tokens` and `cache_creation_1h_tokens` (v2.1.300) ([prompt caching docs](https://code.claude.com/docs/en/prompt-caching), [changelog](https://code.claude.com/docs/en/changelog), read 2026-11-01).

**Check your hit rate with `/usage`.** Since v2.1.251, `/usage` shows a `Prompt cache (main)` line with the hit share, misses, the likely cause, and whether the cache is warm or cold. It is the fastest way to confirm a habit is actually breaking the cache before you change it. Large cache misses also show in `/usage` under "What's contributing to your limits usage?" since v2.1.311 ([changelog](https://code.claude.com/docs/en/changelog), read 2026-11-01). To act on a miss, see [Diagnose a Miss](#diagnose-a-miss).

**Across a team**, Claude Code's own OpenTelemetry export (client-side, set in managed settings; starting point in [templates/settings/telemetry-team.json](../templates/settings/telemetry-team.json), budgeting in [Guide 05](05-team-budgeting.md)) reports `claude_code.token.usage` by type. The fleet's hit share is `cacheRead / (input + cacheRead + cacheCreation)`, the same ratio `/usage`, the status line's `hit_ratio` and claude-rate report, because the metric's `input` type leaves out cache reads and writes ([monitoring docs](https://code.claude.com/docs/en/monitoring-usage), read 2026-11-03).

### 5-Minute TTL in Practice

This applies wherever Claude Code uses the 5-minute TTL: an API key, a cloud provider, usage credits, and every subagent. A subscription's main conversation gets an hour, so the long-break bullet below only bites there after 60 minutes. The 5-minute window is more generous than it sounds for Claude Code workflows:

- **Active coding sessions**: no published figure gives the typical gap between turns. Every turn sent within 5 minutes of the previous request reads the cache, and `/usage` shows whether yours is warm or cold.
- **Reviewing output**: Even if you spend 3-4 minutes reading Claude's response before your next message, the cache holds.
- **Short breaks**: A quick coffee break or Slack check (under 5 minutes) does not break the cache.
- **Long breaks**: A 15-minute meeting, lunch, or context switch causes a full cache expiration.

### Idle Compaction

Claude Code can compact a long conversation you leave idle while it is on the one-hour TTL. In the terminal, a conversation of 200K or more tokens left idle for about 54 minutes is compacted before its one-hour cache expires, so your next message does not reprocess it all (v2.1.299). In VS Code and the Claude Desktop Code tab a 200K+ token conversation left idle is summarized, and the summary is used on your next message if the cache has expired (v2.1.314). Since v2.1.314 it also runs for subscribers with telemetry turned off, and on Bedrock, Google Cloud, Foundry and LLM gateways once the one-hour cache is on. Because it runs before the cache expires, the summarization request should read the prefix from the warm cache, as `/compact` does (see [/compact vs /clear vs /rewind](#compact-vs-clear-vs-rewind)); the costs page lists idle compaction among the things that can use tokens while you are idle.

Controls: `CLAUDE_CODE_IDLE_COMPACT_MIN_TOKENS` changes the 200,000-token minimum, and `"idleCompaction": false` in settings.json (or the `Idle compaction` row in `/config`, v2.1.302) turns it off ([prompt caching docs](https://code.claude.com/docs/en/prompt-caching), [costs page](https://code.claude.com/docs/en/costs), [changelog](https://code.claude.com/docs/en/changelog), read 2026-11-01).

How it changes the "compact before a break" advice below: it needs the one-hour TTL, so it applies to a subscription's main conversation by default and not to an API key, usage credits or a cloud provider on the five-minute default. On a subscription, a conversation under 200K tokens is not idle-compacted, so a manual `/compact` before a break longer than an hour still applies; above 200K tokens, idle compaction does it for you after about 54 minutes. A break shorter than the TTL needs neither, because the cache is still warm.

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

**What Anthropic measured.** With no pauses between turns, the 5-minute default cost about 19% less per session than the 1-hour cache on Sonnet 5.5 (it was 15% on Sonnet 5) and about 15% to 18% less on Opus 5.5; the 1-hour cache wins once about 1 turn in 20 follows a 5-to-60-minute pause. On Fable 5.1 a `max_tokens: 0` keep-alive every 4 minutes beat both: $2.29 per session vs $2.42 on the 5-minute cache and $3.09 on the 1-hour cache, with no pauses ([cost-optimization guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence), "Pick the cache duration", read 2026-11-01).

---

## Maximizing Cache Hit Rate

These strategies increase the percentage of input tokens that hit the cache:

### 1. Keep Model and Effort Constant During Sessions

Pick the model (and, on most models, the effort level) before the session starts and keep it. Editing CLAUDE.md is not the problem -- it keeps the cache, though the edit only applies after `/clear`, `/compact`, or restart. Switching models, or changing effort on anything other than Opus 5.5, Sonnet 5.5, Haiku 5.5 and Fable 5.1 (and on those four, anywhere the exemption does not apply: Bedrock, Google Cloud's Agent Platform, a Claude apps gateway, a HIPAA configuration), is what forces a rebuild.

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

Many rapid turns on the same topic maximize caching. Across Anthropic's API traffic (14 days ending 2026-08-23, 303,003 organization-days from 106,487 organizations), agent loops read a median 84.2% of their input from cache (upper quartile 91.7%). About 72% of coding organization-days read 80% or more, and the top decile reads 95.9% or more for coding; in a six-hour sample of coding requests with 25 or more prior tool calls, 92% of input was read from cache, 7% written and under 1% uncached ([cost-optimization guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence), benchmark reference 17, read 2026-11-01). If `/usage` shows your hit share well below those, something in your prefix is changing.

| Pattern | Cache Efficiency | Why |
|---------|:----------------:|-----|
| Many turns close together | 84.2% median across agent loops on Anthropic's API; 92% of input read from cache for coding requests with 25+ prior tool calls (six-hour sample) | Prefix stays warm |
| Turns with long gaps | One full re-write per gap longer than the TTL (5 min on an API key, 1 hour for a subscription's main conversation) | At 100K tokens on Opus 5.5 a re-write costs $0.50 vs $0.02 to read |
| Several short sessions in one directory | Not measured | A new session reads the system prompt from cache only within the TTL and only if its git status snapshot matches |
| Single-turn conversations | Not measured (Anthropic no longer publishes a figure for API traffic without tool definitions) | Only the shared system prompt and tools can hit, within the TTL |

### 4. Use /compact Strategically

`/compact` summarizes conversation history into a shorter form, which rebuilds the conversation layer of the cache. But it also dramatically reduces the total token count, making subsequent turns cheaper overall. Run it while the cache is warm: the summarization request then reads the prefix from cache and costs a fraction of the context size, whereas after a break longer than the TTL it reprocesses the full history uncached.

**When /compact helps caching:**
- After a large context has accumulated (50,000+ tokens of history), compact reduces it to ~5,000 tokens. The next turn pays cache write on 5,000 tokens instead of cache hit on 50,000 tokens -- but every turn after that processes far fewer total tokens.

**When /compact hurts caching:**
- If you compact too frequently (every 5-10 turns), you repeatedly pay cache write costs without accumulating enough cached turns to justify it.

**Time unavoidable cache breaks to a compaction boundary.** Compaction rebuilds the conversation layer anyway, so a change that breaks the cache costs least right after it. In Anthropic's measured run (Sonnet 5), changing effort and adding a tool right after the first compaction cost $0.75 per session, against $0.95 for the same change mid-session. Making the change on the compaction request itself cost $0.92, because that summarization pass then cost $0.21 instead of $0.04 ([cost-optimization guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence), end of "What breaks the cache", read 2026-11-01).

**Rule of thumb**: Compact when context exceeds 80,000-100,000 tokens, or at natural breakpoints in your work (finishing a feature, switching to a different file).

### 5. Front-Load Stable Content in CLAUDE.md

Claude's prompt is structured so that CLAUDE.md appears near the beginning of the prefix. This means CLAUDE.md content is always in the cached prefix, and because it is read once at session start, mid-session edits do not disturb it. You do not need to reorder content within CLAUDE.md for caching purposes -- the entire file is part of the prefix regardless of internal ordering.

What does matter is size, because the root file loads in full on every session (a file over 4 MiB is skipped; `MEMORY.md` loads its first 200 lines or 25KB). If you use multiple CLAUDE.md files, remember that subdirectory CLAUDE.md files and path-scoped `.claude/rules/` load on demand, when Claude first reads a matching file -- so moving area-specific content there keeps the always-loaded prefix small. Since v2.1.309 each on-demand file is capped: 40,000 characters at a 200K window and 150,000 at 1M (200,000 on Opus 4.6 and Sonnet 4.6), and Claude receives only the start of a larger one ([memory docs](https://code.claude.com/docs/en/memory), read 2026-11-01).

---

## ROI Calculations

### Scenario 1: 50-Turn Session with Good Caching

**Setup**: Sonnet 4.6, 150-line CLAUDE.md, 3 MCP servers, focused session with turns every 1-2 minutes. No model or effort switches.

**Stable prefix**: System prompt (3,500) + CLAUDE.md (1,500: 150 lines at 10 tokens per line) + Tool schemas (4,000) = 9,000 tokens

```
Turn  1: 9,000 prefix + 100 tokens new input, all written to cache (1.25x)
         Total input cost:  9,100 x $3.75/1M = $0.0341
         Output: 700 tokens x $15.00/1M = $0.0105
         Turn total: $0.045

Turn 10: 9,000 prefix + 27,000 history = 36,000 cached tokens
         + 3,000 new tokens (latest turn exchange + tool results),
           written to cache at 1.25x
         Input cost:  36,000 x $0.30/1M + 3,000 x $3.75/1M
                    = $0.0108 + $0.0113 = $0.0221
         Output: 700 tokens x $15.00/1M = $0.0105
         Turn total: $0.033

Turn 25: 9,000 prefix + 72,000 history = 81,000 cached tokens
         + 3,000 new tokens written at 1.25x
         Input cost:  81,000 x $0.30/1M + 3,000 x $3.75/1M
                    = $0.0243 + $0.0113 = $0.0356
         Output: 700 tokens x $15.00/1M = $0.0105
         Turn total: $0.046

Turn 50: 9,000 prefix + 147,000 history = 156,000 cached tokens
         + 3,000 new tokens written at 1.25x
         Input cost:  156,000 x $0.30/1M + 3,000 x $3.75/1M
                    = $0.0468 + $0.0113 = $0.0581
         Output: 700 tokens x $15.00/1M = $0.0105
         Turn total: $0.069

All 50 turns:  4,116,000 tokens read    x $0.30/1M  = $1.23
               156,100 tokens written   x $3.75/1M  = $0.59
               35,000 output tokens     x $15.00/1M = $0.53
               96.3% of the 4,272,100 input tokens read from cache
```

**Total session cost: $2.35 on Sonnet 4.6** (computed: $1.23 + $0.59 + $0.53)

### Scenario 2: 50-Turn Session with Poor Caching

**Setup**: Same session, but the developer runs with MCP tool search off (`ENABLE_TOOL_SEARCH=false`) and connects or removes an MCP server at turns 10, 20, 30, and 40. Also takes a 20-minute break at turn 15 on an API key (5-minute TTL, so the cache expires). Switches from Sonnet to Opus 5.5 at turn 35.

Each of these events makes Claude Code re-write the whole accumulated prefix to cache at 1.25x instead of reading it. The extra cost is the write minus the read it replaces (prefix sizes from Scenario 1: 9,000 + (turn - 1) x 3,000):

```
Turn 10 (after MCP server change, tool search off):
  Re-write of the 36,000-token prefix
  Extra cost: 36,000 x ($3.75 - $0.30) / 1M = $0.124

Turn 15 (after 20-min break, cache expired):
  Re-write of the 51,000-token prefix
  Extra cost: 51,000 x ($3.75 - $0.30) / 1M = $0.176

Turn 20 (after MCP server change):
  Re-write of the 66,000-token prefix
  Extra cost: 66,000 x ($3.75 - $0.30) / 1M = $0.228

Turn 30 (after MCP server change):
  Re-write of the 96,000-token prefix
  Extra cost: 96,000 x ($3.75 - $0.30) / 1M = $0.331

Turn 35 (model switch to Opus 5.5, new cache):
  Re-write of the 111,000-token prefix on Opus 5.5
  Extra cost: 111,000 x ($5.00 - $0.20) / 1M = $0.533

Turn 40 (after MCP server change, still on Opus 5.5):
  Re-write of the 126,000-token prefix
  Extra cost: 126,000 x ($5.00 - $0.20) / 1M = $0.605
```

**Total with all cache breaks: $4.24** (computed: $2.345 + $1.997 - $0.098) -- the $2.35 good-caching session from Scenario 1, plus $2.00 of cache-break penalties, minus $0.10 because on warm turns 35-50 Opus 5.5's $0.20 cache hits (Sonnet 4.6: $0.30) save more than its $5.00 writes and $20 output (Sonnet 4.6: $3.75 and $15) add.

That is 1.8x the cost of the same 50-turn session with good caching. Note what is **not** on the list: editing CLAUDE.md mid-session would have cost nothing.

### Comparison Table: Cache Hit Rate Impact

**Scenario 1's 50-turn session on Sonnet 4.6: 4,272,100 input tokens, 3,000 new tokens per turn, 700 output tokens per turn. The hit rate is the share of input tokens read from cache, the figure `/usage` reports.**

| Cache Hit Rate | Input Cost | Output Cost | Total Session Cost | vs No Caching |
|:--------------:|:----------:|:-----------:|:------------------:|:-------------:|
| **96.3%** (warm all session, Scenario 1) | $1.82 | $0.525 | **$2.35** | **82% savings** |
| **90%** | $2.76 | $0.525 | **$3.28** | **75% savings** |
| **75%** | $4.97 | $0.525 | **$5.49** | **59% savings** |
| **50%** | $8.65 | $0.525 | **$9.18** | **31% savings** |
| **25%** | $12.34 | $0.525 | **$12.86** | **4% savings** |
| **0%** (every token written, none read) | $16.02 | $0.525 | **$16.55** | **24% more** |
| **No caching** (1x input) | $12.82 | $0.525 | **$13.34** | baseline |

*Computed: input = 4,272,100 x (hit share x $0.30 + (1 - hit share) x $3.75) / 1M, because Claude Code writes every token it does not read from cache, at 1.25x; with no caching all of them bill at $3.00. Below a 21.7% hit share, caching costs more than none ((3.75 - 3.00) / (3.75 - 0.30)). Anthropic's production median for agent loops, 84.2% (upper quartile 91.7%), falls between the 75% and 90% rows, and its 92% read share for coding requests with 25 or more prior tool calls sits just above the 90% row ([cost-optimization guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence), benchmark reference 17, read 2026-11-01).*

> Output tokens are never cached -- they are always generated fresh. Caching only affects input tokens. This is why the output cost ($0.525) is constant across all rows.

**Monthly impact (5 sessions/day, 22 working days = 110 sessions):**

| Cache Hit Rate | Monthly Cost (Sonnet 4.6) | Monthly Cost (legacy Opus 5) |
|:--------------:|:---------------------:|:-------------------:|
| **96.3%** (warm) | $258 | $430 |
| **90%** | $361 | $601 |
| **75%** | $604 | $1,007 |
| **50%** | $1,009 | $1,682 |
| **No caching** | $1,468 | $2,446 |

*Computed: 110 x the session cost at that hit share; legacy Opus 5 at $5/$25, $0.50 read, $6.25 write.*

The difference between the warm session and no caching is **$1,210/month on Sonnet 4.6** and **$2,016/month on legacy Opus 5**, and slipping from 96.3% to 90% alone costs $103 and $171 a month. Opus 5.5 lands below the Opus 5 column at every row, because its input ($4 vs $5), output ($20 vs $25) and cache-hit ($0.20 vs $0.50) rates are all lower. Good caching hygiene is one of the most impactful cost optimizations available.

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

**Better approach**: Pick the model and effort before the session starts. On Opus 5.5, Sonnet 5.5, Haiku 5.5 and Fable 5.1 (API key or subscription, not on Bedrock, Google Cloud's Agent Platform, a Claude apps gateway or under a HIPAA configuration), effort changes keep the cache in Claude Code, so there you can adjust freely.

### 2. Frequently Switching MCP Servers With Tool Search Off

With MCP tool search on (the default), connecting and disconnecting servers keeps the cache. With tool search off, full schemas sit in the prefix, so every server change breaks it.

**Better approach**: Leave tool search on. If you must run with it off, use project-scoped MCP configs (`.mcp.json` at the project root) to ensure each project has exactly the servers it needs. No toggling required.

### 3. Very Short Sessions (1-2 Turns)

Caching is a multi-turn investment. The first turn pays the cache write cost (1.25x). If you only use 1-2 turns and then start a new session, you pay the write premium without enough hits to recoup it.

**The math for a single-turn session on Sonnet 4.6:**

| | With Cache Write | Without Caching | Difference |
|---|:---:|:---:|:---:|
| 9,000 prefix tokens | $0.0338 (at 1.25x) | $0.0270 (at 1x) | +$0.0068 more |

You pay an extra $0.007 per single-turn session due to cache writes that never get reused (9,000 x $0.75/1M). Across 100 single-turn sessions, that is $0.68 wasted.

**Better approach**: If you regularly do single-turn tasks, the cache write overhead is negligible in absolute terms. But if you can batch related questions into multi-turn sessions, you will save significantly.

### 4. Not Understanding That Cache Writes Cost More Than Regular Input

A common misconception is that caching is always free or always cheaper. The first turn of a session is slightly more expensive (1.25x on the prefix) than it would be without caching. The savings come from subsequent turns. If you only ever do 1-turn sessions, caching has a small net cost.

In practice, this almost never matters -- the overhead is tiny and most sessions are multi-turn. But it is worth understanding the mechanics.

### 5. Taking Long Breaks Without Compacting First

If you know you will be away for longer than the TTL (5 minutes on an API key, cloud provider or usage credits; an hour on a subscription's main conversation), run `/compact` before stepping away. While the cache is warm, `/compact` reads the history from cache, so it costs a fraction of the context size. When you return, the context will be smaller, and the cache write cost on the first turn back will be lower.

On a subscription's one-hour TTL, idle compaction (see [Idle Compaction](#idle-compaction)) handles a break of about 54 minutes or more for a conversation of 200K+ tokens, so the manual `/compact` matters most for a smaller conversation, or on the five-minute TTL. If you resume an old conversation anyway, Pro and Max users get a warning (v2.1.304) when resuming would use a noticeable share of the 5-hour limit, and can start a new conversation instead ([changelog](https://code.claude.com/docs/en/changelog), read 2026-11-01).

```
Without compacting before break:
  Return to session with 80,000 tokens of expired cache
  Cache write: 80,000 x $3.75/1M = $0.30 (Sonnet 4.6)

With compacting before break:
  /compact reduces history to ~8,000 tokens
  Return to session with 8,000 tokens of expired cache
  Cache write: 8,000 x $3.75/1M = $0.03 (Sonnet 4.6)

  Savings: $0.27 on the first turn back
  On Sonnet 5.5 ($2.50/1M 5-minute write): $0.20 vs $0.02, saving $0.18
```

To price your own breaks, set Breaks per session, Break length and Cache TTL under Session events in the [calculator](https://sagargupta.online/claude-cost-optimizer/calculator/).

---

## Key Takeaways

1. **Prompt caching bills repeated input at 10% of the input price -- 5% on Opus 5.5 and Sonnet 5.5, 2.5% on Fable 5.1 / Mythos 5.1.** Across Anthropic's API traffic, agent loops read a median 84.2% of their input from cache (upper quartile 91.7%). This is the largest automatic cost reduction in Claude Code.

2. **Know the real cache breakers.** Switching models, changing effort (except in Claude Code on Opus 5.5, Sonnet 5.5, Haiku 5.5 and Fable 5.1 with an API key or subscription), toggling fast mode (separate caches per speed), and MCP changes with tool search off all force a rebuild. Editing CLAUDE.md mid-session does not -- but the edit only applies after `/clear`, `/compact`, or restart. `/usage` shows a `Prompt cache (main)` line with your hit share and the likely cause of misses.

3. **Caching pays for itself after just one reuse.** The cache write premium (1.25x) is recovered with a single cache hit (0.1x). Every subsequent hit is pure savings.

4. **Work in focused sessions with turns inside the TTL.** Claude Code gives a subscription's main conversation a 1-hour TTL; an API key, cloud provider, usage credits and every subagent get 5 minutes (override with `promptCacheTtl` and `subagentPromptCacheTtl`). Rapid, focused sessions maintain a warm cache. Scattered work with long gaps between turns wastes money on repeated cache writes.

5. **Run /compact before long breaks.** If you are stepping away for longer than the TTL, compacting first (while the cache is warm) reduces the cache write cost when you return. On a subscription's one-hour TTL, Claude Code does this for you after about 54 minutes idle once a conversation is 200K+ tokens (idle compaction, v2.1.299; turn it off with `"idleCompaction": false`); under 200K tokens, or on a five-minute TTL, the manual `/compact` still applies. `/clear` costs nothing; `/rewind` returns to an already-cached prefix.

6. **On this guide's 50-turn Sonnet 4.6 session, caching is the difference between $258 and $1,468 a month** (110 sessions, computed in [the comparison table](#comparison-table-cache-hit-rate-impact)). Slipping from the warm 96.3% hit share to 90% alone costs $103 a month. Good caching hygiene is not optional -- it is one of the highest-ROI optimizations you can make.

7. **Know your model's minimum cacheable prompt length.** Opus 5.5, Opus 5, Sonnet 5.5 and Haiku 5.5 cache from 512 tokens, Opus 4.8 and Sonnet 5 from 1,024, Opus 4.7 from 2,048, legacy Haiku 4.5 from 4,096. Below the floor, `cache_control` is silently ignored -- you pay full price every turn with no error. If you build custom API tooling, check `cache_read_input_tokens` in the `usage` block to confirm the cache is real.

8. **On Haiku 5.5, cached tokens still count toward the 100K tier line.** A request over 100,000 prompt tokens, cache reads and writes included, pays $0.50/$2.50 and a $0.05 cache hit on the whole request instead of $0.10/$0.50 and $0.01. Keep Haiku 5.5 prompts under 100K, cached prefix and all.

---

*Previous: [Guide 07 - MCP Server and Agent Cost Impact](07-mcp-agent-costs.md)*
