# Guide 01: Understanding Claude Code Costs

> Before you can optimize costs, you need to understand exactly how billing works, where your tokens go, and why some sessions cost 10x more than others.

---

## Table of Contents

- [Token Pricing](#token-pricing)
  - [Long Context Pricing (1M)](#long-context-pricing-1m)
  - [Fast Mode Pricing](#fast-mode-pricing)
- [What Counts as Tokens in Claude Code](#what-counts-as-tokens-in-claude-code)
- [The Context Window and Its Cost Impact](#the-context-window-and-its-cost-impact)
- [Prompt Caching: Your Biggest Automatic Discount](#prompt-caching-your-biggest-automatic-discount)
  - [Minimum Cacheable Prompt Length](#minimum-cacheable-prompt-length)
- [Tracking Your Costs](#tracking-your-costs)
- [Worked Example: Cost of a 30-Turn Session](#worked-example-cost-of-a-30-turn-session)
- [Why Sessions Get Expensive](#why-sessions-get-expensive)
- [Key Takeaways](#key-takeaways)

---

## Token Pricing

Every interaction with Claude Code consumes tokens. Tokens are the fundamental billing unit — roughly 1 token per 4 characters of English text, or about 0.75 words per token. Code tends to be slightly less dense: a typical line of code is around 8-12 tokens.

### Current Model Pricing (verified 2026-07-25)

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Cache Hit (per 1M) | 5m Cache Write | 1h Cache Write | Context Window | Max Output |
|-------|:---------------------:|:----------------------:|:---------------------:|:--------------:|:--------------:|:--------------:|:----------:|
| **Fable 5** (most capable) | $10.00 | $50.00 | $1.00 | $12.50 | $20.00 | 1M | 128K |
| **Opus 5** (Opus flagship) | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1M | 128K |
| **Opus 4.8** (legacy) | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1M | 128K |
| **Opus 4.7** | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1M | 128K |
| **Opus 4.6** | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1M | 128K |
| **Opus 4.5** | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 200K | 64K |
| **Opus 4.1** (deprecated, retires 2026-08-05) | $15.00 | $75.00 | $1.50 | $18.75 | $30.00 | 200K | 32K |
| **Sonnet 5** | $3.00 ($2.00 intro) | $15.00 ($10.00 intro) | $0.30 | $3.75 | $6.00 | see note | see note |
| **Sonnet 4.6** | $3.00 | $15.00 | $0.30 | $3.75 | $6.00 | 1M | 64K |
| **Sonnet 4.5** | $3.00 | $15.00 | $0.30 | $3.75 | $6.00 | 200K | 64K |
| **Haiku 4.5** | $1.00 | $5.00 | $0.10 | $1.25 | $2.00 | 200K | 64K |
| **Opus 5 / 4.8 (Fast Mode)** | $10.00 (2x) | $50.00 (2x) | N/A | -- | -- | 1M (included) | 128K |

> **Opus 5** (GA 2026-07-24, `claude-opus-5`): identical posted price to Opus 4.8 ($5/$25), so the upgrade is free at the posted rate. 1M context at standard rates, 128K max output (300K on Batch via the `output-300k-2026-03-24` beta), knowledge cutoff May 2026, Batch $2.50/$12.50, minimum cacheable prompt 512 tokens. Adaptive thinking with effort levels low/medium/high/xhigh/max, defaulting to `high` on both the Claude API and Claude Code. Bedrock ID `anthropic.claude-opus-5`, Google Cloud `claude-opus-5`; GA on Claude API, Claude Platform on AWS, Bedrock, and Vertex AI. Earliest retirement not sooner than 2027-07-24. Anthropic's models-overview page now says to start with Opus 5 for complex agentic coding and enterprise work; Fable 5 remains the highest-capability model overall.
>
> **Cost-relevant breaking changes vs Opus 4.8**:
> - **Thinking is on by default.** Omit the `thinking` param and you get adaptive thinking. Reasoning tokens bill as **output** at $25/1M. `max_tokens` is a hard cap on thinking **plus** text, so an unchanged small `max_tokens` can be eaten by thinking before the answer is written. Raise it to 64K+ if you run `xhigh` or `max` effort.
> - `thinking: {type: "disabled"}` is allowed only at effort `high` or below. Combining it with `xhigh` or `max` returns a **400 error**.
> - Minimum cacheable prompt drops from 1,024 tokens (Opus 4.8) to **512** (Opus 5), so shorter prefixes now qualify for the cache discount.
> - Ships cybersecurity safety classifiers. Cyber refusals can auto-fall-back to Opus 4.8 via the server-side `fallbacks` param with beta header `server-side-fallback-2026-07-01`.
> - New beta `mid-conversation-tool-changes-2026-07-01` lets tool definitions change between turns **without** invalidating the prompt cache. Previously that was a cache-busting move.
> - Output runs **longer** than Opus 4.8 by default, so re-tune verbosity instructions. Opus 5 also self-verifies, which means carried-over "double-check your work" instructions now pay twice for the same behavior.
>
> **Opus 4.8 is now legacy**: Anthropic's models-overview page moved `claude-opus-4-8` into the Legacy accordion. Retirement date is unchanged at not sooner than 2027-05-28, and it stays the server-side fallback target for Opus 5 cyber refusals. Same $5/$25 price means there is no cost reason to stay on it. The only reasons to pin it are prompts tuned to that snapshot, or needing thinking off at `xhigh`/`max` effort (which Opus 5 rejects).
>
> **Fable 5** (GA 2026-06-09): Anthropic's Mythos-class tier above Opus at **2x Opus 5's rates** ($10/$50). Always-on adaptive thinking, no Fast Mode, Batch supported ($5/$25), 30-day data retention required. Safety classifiers can refuse a request (`stop_reason: "refusal"`) -- pre-output refusals are not billed. From a cost standpoint, treat Fable 5 as a deliberate splurge for the hardest tasks, not a default.
>
> **Sonnet 5**: $3/$15 standard, with **intro pricing of $2/$10 through 2026-08-31**. Minimum cacheable prompt 1,024 tokens. Retirement not sooner than 2027-06-30. It is the current Sonnet-tier migration target, replacing Sonnet 4.6. Context window and max output are not restated here -- check the [Anthropic models overview](https://docs.claude.com/en/docs/about-claude/models/overview) before you size a request against them.
>
> **1M context at standard rates**: Fable 5, Opus 5, Opus 4.8, Opus 4.7, Opus 4.6, and Sonnet 4.6 bill the full 1M window at the standard per-token rate -- no long-context premium. (The earlier "2x over 200K" pricing applied to Opus 4.1 and older. Note that Opus 4.5 and Sonnet 4.5 are 200K-only.)
>
> **New tokenizer caveat**: Opus 4.7 and later (including Opus 4.8 and Opus 5) use the same Opus-4.7-generation tokenizer, which may use up to **35% more tokens** for the same source text. Posted pricing is unchanged ($5/$25), but effective per-task cost is 20-35% higher than it would have been on Opus 4.6.
>
> **Subscriptions**: Pro **$20/mo** (or **$200/yr ≈ $16.67/mo** with annual billing — ~17% off). Max 5x $100/mo. Max 20x $200/mo. **Batch API**: 50% discount on both input and output. **Cache write**: 1.25x base input price (5-min TTL), 2x base input price (1-hour TTL). **Cache hit/refresh**: 0.1x base input price. **Regional endpoints** (Bedrock / Vertex AI / Claude API `inference_geo: "us"`, scope = Sonnet 4.5+, Haiku 4.5+, Opus 4.5+, and all future models): +10%.

### Off-Peak 2x Usage Events

Anthropic periodically runs promotional events that **double usage limits** during off-peak hours. Past examples include "Spring Break for Claude Code" (March 2026) which offered 2x limits outside the peak window of **8 AM - 2 PM ET** and on all weekends.

These promotions are **not permanent** -- they come and go. Watch the [Anthropic blog](https://www.anthropic.com/news) and [Claude Code support page](https://support.claude.com) for active promotions. When available, shifting heavy work to off-peak hours effectively **halves your cost per unit of work**. Users in Asia, India, and Australia benefit the most since their entire workday falls outside US peak hours.

### What These Numbers Mean in Practice

To build intuition, here is what $1.00 buys you with each model:

| Model | $1 of Input Tokens | $1 of Output Tokens | $1 of Cached Input |
|-------|:-------------------:|:--------------------:|:------------------:|
| **Fable 5** | ~100,000 tokens (~255 pages) | ~20,000 tokens (~51 pages) | ~1,000,000 tokens (~2,550 pages) |
| **Opus 5 / 4.8 / 4.7 / 4.6** | ~200,000 tokens (~510 pages) | ~40,000 tokens (~102 pages) | ~2,000,000 tokens (~5,100 pages) |
| **Sonnet 5 / 4.6** | ~333,300 tokens (~850 pages) | ~66,700 tokens (~170 pages) | ~3,333,300 tokens (~8,500 pages) |
| **Haiku 4.5** | ~1,000,000 tokens (~2,560 pages) | ~200,000 tokens (~510 pages) | ~10,000,000 tokens (~25,600 pages) |

> Opus 5, 4.8 and 4.7's token counts may be ~20-35% lower than shown (fewer pages per $1) due to the new tokenizer. Budget with that in mind if you're migrating from 4.6.
>
> On Opus 5, default-on thinking means part of that output budget goes to reasoning tokens you never read. They bill at the same $25/1M as visible text.

> **Critical insight**: Output tokens cost **5x more** than input tokens across all models. This is why strategies that reduce Claude's output (Plan Mode, concise instructions) are high-leverage.

### Model Cost Comparisons

Relative to Opus 5 (the Opus-tier flagship; Opus 4.8 / 4.7 / 4.6 / 4.5 share the same base rate). Fable 5 sits above the whole ladder at 2x Opus:

| Comparison | Input Savings | Output Savings |
|------------|:------------:|:--------------:|
| Opus 5 vs Fable 5 | **2x cheaper** | **2x cheaper** |
| Sonnet 5 vs Opus 5 | **1.67x cheaper** | **1.67x cheaper** |
| Haiku 4.5 vs Opus 5 | **5x cheaper** | **5x cheaper** |
| Haiku 4.5 vs Fable 5 | **10x cheaper** | **10x cheaper** |
| Haiku 4.5 vs Sonnet 5 | **3x cheaper** | **3x cheaper** |

Switching from Opus to Haiku for a task that costs $1.00 on Opus would cost approximately $0.20 on Haiku. The same task on Sonnet would cost about $0.60.

> **Note**: Opus 5 is priced at $5/$25 -- the same as Opus 4.8 / 4.7 / 4.6 and the same level Sonnet used to be at. The gap between models is much smaller than it used to be. Model selection still saves money, but the ratios are more modest (5x Haiku-to-Opus vs the historical 19x). The new tokenizer (Opus 4.7 and later) narrows the "effective" gap slightly further -- budget ~20-35% higher for Opus 5 than the posted rate suggests. Sonnet 5's $2/$10 intro rate through 2026-08-31 makes the Sonnet-vs-Opus gap temporarily 2.5x instead of 1.67x.

### Long Context Pricing (1M)

Fable 5, Opus 5, Opus 4.8, Opus 4.7, Opus 4.6, and Sonnet 4.6 support up to 1M tokens of context at **standard rates** across the full window. There is no longer a "2x over 200K" premium -- that pricing applied to Opus 4.1 and older.

| Model | Input Rate (any context size) | Output Rate (any context size) | Max Context |
|-------|:-----------------------------:|:------------------------------:|:-----------:|
| **Fable 5** | $10.00 | $50.00 | 1M |
| **Opus 5** | $5.00 | $25.00 | 1M |
| **Opus 4.8** | $5.00 | $25.00 | 1M |
| **Opus 4.7** | $5.00 | $25.00 | 1M |
| **Opus 4.6** | $5.00 | $25.00 | 1M |
| **Sonnet 4.6** | $3.00 | $15.00 | 1M |
| **Haiku 4.5** | $1.00 | $5.00 | 200K |

Sonnet 5 is priced at $3/$15 ($2/$10 intro through 2026-08-31) with no long-context premium either; its exact maximum window is not restated here.

A 900K-token request is billed at the same per-token rate as a 9K-token request. You still pay for each token, so context growth still costs more in absolute dollars -- but there is no rate cliff at 200K anymore.

> **Practical implication**: Sending a 300K-token input on Opus 5 costs $1.50 at the $5/1M rate. Under the old pricing, it would have been $3.00 (entire request at the 2x rate). Long agentic sessions, large-codebase audits, and big-document analysis are now significantly cheaper.

> **AWS Bedrock / Vertex AI**: Claude models are available on AWS Bedrock and Google Vertex AI at the same pricing for global (cross-region) inference. Regional inference profiles carry a **+10% surcharge** over the standard API rates.

### Fast Mode Pricing

Fast Mode is a beta (research preview) feature available for **Claude Opus 5 and Opus 4.8 only** (`claude-opus-5`, `claude-opus-4-8`). Same model weights, same intelligence -- just faster output token generation at premium pricing. Both supported models run at **2x** standard rates; the old 6x tier no longer exists. [Join the waitlist](https://claude.com/fast-mode).

| | Input (per 1M) | Output (per 1M) | Multiplier vs Standard |
|---|:---:|:---:|:---:|
| **Standard Opus 5 / 4.8 / 4.7 / 4.6** | $5.00 | $25.00 | 1x |
| **Fast Mode Opus 5** | $10.00 | $50.00 | **2x** |
| **Fast Mode Opus 4.8** | $10.00 | $50.00 | **2x** |
| **Opus 4.7 with `speed: "fast"`** | -- | -- | **error, no fallback** |
| **Opus 4.6 with `speed: "fast"`** | $5.00 | $25.00 | silently 1x (standard speed) |

Key details about Fast Mode:

- **Same model, faster output**: Fast Mode runs the same model with a faster inference configuration. Same weights, same behavior — only the runtime is different.
- **Up to 2.5x output tokens/second**: The speed gain is on output tokens per second (OTPS), **not** time-to-first-token (TTFT). If you're optimizing for TTFT, Fast Mode does not help.
- **1M context included**: Fast Mode is priced at the 2x multiplier across the full context window, including requests over 200K input tokens. No additional 2x long-context multiplier stacked on top.
- **Cache stacks on top**: Prompt-caching multipliers (1.25x 5m write, 2x 1h write, 0.1x hit) apply to Fast Mode rates. So a Fast Mode Opus 5 5m cache write costs $10 × 1.25 = $12.50 / MTok, and a Fast Mode Opus 5 cache hit costs $10 × 0.1 = $1.00 / MTok.
- **Switching invalidates cache**: Fast and Standard speeds do not share cached prefixes. If you toggle speeds mid-conversation, you'll pay a full cache-write cost again.
- **Opus 4.7 now errors**: `speed: "fast"` on Opus 4.7 returns an error, with **no fallback** to standard speed. The request fails outright.
- **Opus 4.6 silently degrades**: `speed: "fast"` on Opus 4.6 runs at standard speed and standard rates. No error is raised; `usage.speed` comes back `"standard"`. You do not overpay, but you also do not get the speedup, so check the field rather than assuming.
- **Fast Mode surface**: Claude API + Managed Agents only. Not available on Bedrock, Vertex AI, Microsoft Foundry, Claude Platform on AWS, the Batch API, or Priority Tier.
- **Not available with Batch API**: 50% batch discount cannot be combined with Fast Mode.
- **Not available with Priority Tier**: Fast Mode and Priority Tier are mutually exclusive.
- **Not available on Claude Platform on AWS**: First-party API only.
- **Activation**: Set `speed: "fast"` in your request and include the `anthropic-beta: fast-mode-2026-02-01` header.
- **Dedicated rate limits**: Fast Mode has its own rate limit pool separate from Standard Opus. Headers like `anthropic-fast-output-tokens-remaining` track it.
- **Use case**: Time-sensitive tasks where latency directly impacts revenue or user experience — urgent debugging, live demos, real-time agentic loops. Almost never worth it for routine interactive coding.

On Opus 5 at 2x the standard rate, a session that would cost $2.33 on standard Opus would cost roughly **$4.66** on Fast Mode. Use it deliberately and sparingly.

---

## What Counts as Tokens in Claude Code

Every turn in Claude Code involves sending input tokens and receiving output tokens. Understanding exactly what constitutes each is the foundation of cost optimization.

### Input Tokens (You Pay For These Every Turn)

```
Input Token Composition Per Turn
================================

1. System Prompt                          ~3,000-4,000 tokens (fixed)
   └── Claude Code's built-in instructions for how to behave,
       use tools, format responses, etc. You cannot change this.

2. CLAUDE.md Contents                     ~7 tokens/line (variable)
   └── Your project's CLAUDE.md file is injected in full on every
       single turn. A 150-line file adds ~1,050 tokens per turn.
       A 500-line file adds ~3,500 tokens per turn.

3. Conversation History                   Grows each turn
   └── Every previous user message and Claude response in the
       current session. This is the #1 driver of cost growth.
       Turn 1: ~0 tokens of history
       Turn 10: ~5,000-20,000 tokens of history
       Turn 30: ~30,000-100,000+ tokens of history

4. Tool Results                           Varies widely
   └── File contents from Read tool:      ~10 tokens/line of code
       Grep/Glob search results:          ~50-500 tokens per search
       Bash command output:               ~10-5,000 tokens
       Edit tool confirmations:           ~50-200 tokens
       MCP server responses:              Varies

5. User's Current Message                 Usually small
   └── Your prompt for the current turn:  ~20-200 tokens typically
```

### Output Tokens (You Pay 5x More For These)

```
Output Token Composition Per Turn
=================================

1. Claude's Text Response                 ~50-500 tokens
   └── Explanations, analysis, questions back to you

2. Tool Calls                             ~50-200 tokens each
   └── Read, Edit, Bash, Write, Glob, Grep — each tool call
       includes the tool name and all parameters

3. Code Generation                        ~10 tokens/line
   └── New code written via Edit or Write tools

4. Plan Mode Analysis                     ~200-1,000 tokens
   └── Structured thinking and planning output

5. Extended Thinking / Reasoning           Varies with effort level
   └── On Opus 5 thinking is ON by default when you omit the
       `thinking` param. Reasoning tokens bill as OUTPUT at
       $25/1M even though you never read most of them. Effort
       levels are low/medium/high/xhigh/max, default `high` on
       both the Claude API and Claude Code.
```

> **Opus 5 `max_tokens` trap**: `max_tokens` is a hard cap on thinking **plus** text. Carry over a small `max_tokens` from an Opus 4.8 setup and thinking can consume the whole budget before the answer is written -- you pay for the turn and get no usable output. Raise it to 64K+ when running `xhigh` or `max` effort. Note also that `thinking: {type: "disabled"}` is only legal at effort `high` or below; pairing it with `xhigh` or `max` returns a 400 error, so "just turn thinking off" is not available at the top two effort levels.

### The Hidden Multiplier: Conversation History

This is the most important concept in Claude Code cost optimization.

**Conversation history is cumulative.** Every message — yours and Claude's — becomes part of the input for the next turn. This means:

- **Turn 1**: You send your prompt + system context. Claude responds.
- **Turn 2**: You send your prompt + system context + Turn 1's full exchange. Claude responds.
- **Turn 3**: You send your prompt + system context + Turn 1 + Turn 2. Claude responds.
- **Turn N**: You send your prompt + system context + all previous N-1 turns.

The cost **accelerates** with each turn. A 30-turn session does not cost 30x a single turn — it costs far more because each turn includes all previous turns as input.

---

## The Context Window and Its Cost Impact

### How the Context Window Works

Claude's context window (1M tokens for Opus 5, Opus 4.8, Opus 4.7, Opus 4.6, and Sonnet 4.6; 200K for Haiku 4.5) is the maximum amount of text it can process in a single turn. Think of it as Claude's working memory.

```
Context Window (1M tokens for Opus/Sonnet, 200K for Haiku)
┌─────────────────────────────────────────────────────┐
│ System Prompt          (~3,500 tokens)              │
│ CLAUDE.md              (~1,050 tokens @ 150 lines)  │
│ Conversation History   (grows each turn)            │
│ Current Tool Results   (varies)                     │
│ Your Current Message   (~100 tokens)                │
│                                                     │
│ [Remaining capacity for Claude's response]          │
└─────────────────────────────────────────────────────┘
```

### What Happens When Context Fills Up

As your session progresses, the context window fills with conversation history. When it approaches the limit:

1. **Claude Code automatically truncates** older messages from the conversation history
2. This can cause Claude to "forget" earlier context and decisions
3. You pay for a very large number of input tokens per turn at this point
4. Quality degrades because Claude loses important context

### Context Window Cost at Capacity

What it costs to fill the context window on a single turn:

| Model | Full 200K Input Cost (per turn) | Full 1M Input Cost (per turn) | Max Output Cost (if maxed) |
|-------|:-------------------------------:|:-----------------------------:|:--------------------------:|
| Opus 5 / 4.8 / 4.7 / 4.6 | $1.00 | $5.00 (flat rate, no 200K premium) | $3.20 (128K output) |
| Sonnet 4.6 | $0.60 | $3.00 (flat rate, no 200K premium) | $0.96 (64K output) |
| Haiku 4.5 | $0.20 | N/A (200K max) | $0.32 (64K output) |

> Long sessions on Opus can cost $5-20+. On Opus 5 / 4.8 / 4.7 / 4.6, Sonnet 5, and Sonnet 4.6 there is no 200K rate cliff -- the full 1M window bills at the standard per-token rate -- but absolute dollars still climb as context grows.
>
> On Opus 5 the 128K max-output figure covers thinking **plus** visible text, since `max_tokens` caps both together. Reasoning tokens bill as output at $25/1M, so a max-output turn can be mostly thinking you never see. (Batch raises the ceiling to 300K via the `output-300k-2026-03-24` beta.)

### Practical Rule of Thumb

| Context Usage | Status | Action |
|:-------------:|--------|--------|
| 0-25% (~0-50K) | Healthy | Normal operation |
| 25-50% (~50-100K) | Monitor | Consider `/compact` if conversation is growing |
| 50-75% (~100-150K) | Warning | Run `/compact` or start a new session |
| 75-100% (~150-200K) | Critical | Start a new session — cost per turn is very high |

---

## Prompt Caching: Your Biggest Automatic Discount

Prompt caching is the single most impactful automatic cost reduction in Claude Code. Understanding it helps you avoid accidentally breaking it.

### How Prompt Caching Works

When you send a request to Claude, the API checks if the beginning of your input matches a recently cached prompt prefix. If it does, those cached tokens are charged at a **90% discount**.

```
Normal input cost:   $3.00 / 1M tokens (Sonnet 4.6)
Cached input cost:   $0.30 / 1M tokens (Sonnet 4.6) — 90% cheaper
```

### What Gets Cached

Claude Code structures each request so that **stable content comes first** in the prompt:

```
Request Structure (simplified)
┌──────────────────────────────────────────┐
│ 1. System Prompt        ← CACHED         │  These stay the same
│ 2. CLAUDE.md            ← CACHED         │  between turns, so they
│ 3. Earlier History      ← CACHED         │  get cached automatically
│────────────────────────────────────────── │
│ 4. Recent History       ← NOT cached     │  New content from
│ 5. Current Message      ← NOT cached     │  recent turns
└──────────────────────────────────────────┘
```

On a typical Turn 10:
- Tokens 1-50,000 (system + CLAUDE.md + turns 1-8): **Cached at 90% discount**
- Tokens 50,001-55,000 (turn 9 + current message): **Full price**

### Minimum Cacheable Prompt Length

A prefix has to clear a per-model token floor before it can be cached at all. A `cache_control` block below the threshold is **silently ignored** -- no error, no discount, and nothing in the response tells you it did not take.

| Model | Minimum cacheable prompt (tokens) |
|-------|:---------------------------------:|
| **Opus 5** | 512 |
| **Opus 4.8** | 1,024 |
| **Opus 4.7** | 2,048 |
| **Opus 4.6** | 4,096 |
| **Opus 4.5** | 4,096 |
| **Opus 4.1** | 1,024 |
| **Fable 5** | 512 |
| **Mythos 5** | 512 |
| **Mythos Preview** (retired 2026-06-30) | 2,048 |
| **Sonnet 5** | 1,024 |
| **Sonnet 4.6** | 1,024 |
| **Sonnet 4.5** | 1,024 |
| **Haiku 4.5** | 4,096 |

Opus 5 has the lowest Opus-tier floor at 512 tokens, half of Opus 4.8's 1,024 and a quarter of Opus 4.7's 2,048. Short system prompts and small CLAUDE.md files that were too small to cache on older Opus models now qualify on Opus 5.

### Cache Savings in Practice

For a 30-turn session on Sonnet 4.6 with a 150-line CLAUDE.md:

| Component | Tokens (approx) | Without Cache | With Cache | Savings |
|-----------|:---------------:|:-------------:|:----------:|:-------:|
| System prompt (per turn) | 3,500 | $0.0105 | $0.00105 | $0.00945 |
| CLAUDE.md (per turn) | 1,050 | $0.00315 | $0.000315 | $0.002835 |
| Cached history (avg per turn) | 25,000 | $0.075 | $0.0075 | $0.0675 |
| **Total cache savings over 30 turns** | | | | **~$2.39** |

### What Breaks the Cache

The cache is prefix-based — it works from the beginning of the prompt forward. If anything changes in the cached prefix, **everything after the change point loses its cache**. Common cache-breakers:

| Action | Cache Impact | Severity |
|--------|-------------|:--------:|
| Editing CLAUDE.md mid-session | Invalidates everything after CLAUDE.md in the prefix | HIGH |
| Normal conversation progression | Only new content is uncached (expected and fine) | LOW |
| Switching models mid-session | Complete cache miss (different model = different cache) | HIGH |
| Very long gap between turns | Cache may expire (TTL is ~5 minutes) | MEDIUM |
| Adding/removing MCP servers | Changes system prompt structure | HIGH |
| Changing tool definitions mid-conversation | Historically a full cache bust. On Opus 5, the `mid-conversation-tool-changes-2026-07-01` beta lets tool definitions change between turns **without** invalidating the cache | HIGH without the beta, LOW with it |
| Toggling Fast Mode mid-session | Fast and Standard speeds do not share cached prefixes | HIGH |
| Prefix below the model's minimum cacheable length | Nothing is cached at all, silently (see the table above) | HIGH |

### Rules for Maximizing Cache Hits

1. **Do not edit CLAUDE.md during a session.** Make changes before you start or after you finish.
2. **Keep sessions focused.** Linear conversations cache better than branching ones.
3. **Avoid switching models mid-session** unless the savings from a cheaper model outweigh the cache loss.
4. **Maintain a steady pace.** Very long pauses (5+ minutes) between turns can cause cache expiration.
5. **Use `/compact` strategically.** It resets conversation history, which means the cache restarts — but the reduced context often makes this worthwhile for very long sessions.
6. **Check your prefix clears the model's floor.** Below the minimum cacheable length there is no discount and no warning. Opus 5's 512-token floor is the most forgiving in the Opus tier.

---

## Tracking Your Costs

### The `/usage` Command

Run `/usage` at any point during a Claude Code session to see:

- Total input tokens consumed in the session
- Total output tokens consumed
- Estimated cost so far
- Breakdown by category (if available)

```
> /usage

Session Usage:
  Input tokens:  47,832  (~$0.14 at Sonnet pricing)
  Output tokens: 12,451  (~$0.19 at Sonnet pricing)
  Cache hits:    38,200  (saved ~$0.10)
  Total cost:    ~$0.23
  Turns:         15
```

Use `/usage` as a habit check — run it every 10-15 turns to see if your session is staying within expected bounds.

### The `--max-budget-usd` Flag

Set a hard spending cap when starting a session:

```bash
# Cap session at $5
claude --max-budget-usd 5

# Cap session at $1 for quick tasks
claude --max-budget-usd 1

# Cap session at $20 for complex feature work
claude --max-budget-usd 20
```

When the budget limit is reached, Claude Code will stop processing and notify you. This prevents runaway sessions — especially important when:

- Learning or experimenting
- Running automated workflows
- Delegating Claude Code usage to team members
- Working on tasks that might spiral into unexpected complexity

### Recommended Budget Caps by Task Type

| Task Type | Suggested Cap | Model |
|-----------|:------------:|:-----:|
| Quick bug fix | $1-2 | Haiku/Sonnet |
| Feature implementation | $3-7 | Sonnet |
| Complex refactor | $5-15 | Sonnet/Opus |
| Architecture exploration | $3-7 | Opus (Plan Mode) |
| Code review | $1-3 | Sonnet |
| Generating boilerplate | $0.50-2 | Haiku |

---

## Worked Example: Cost of a 30-Turn Session

Let us walk through a realistic coding session step by step and calculate the actual cost. This example uses **Sonnet 4.6** ($3/$15 per 1M tokens, $0.30 cached input per 1M).

### Scenario

You are building a new API endpoint for a Node.js/Express application. The session involves:
- Planning the approach (turns 1-3)
- Implementing the route handler (turns 4-10)
- Writing tests (turns 11-18)
- Fixing bugs found in tests (turns 19-25)
- Final cleanup (turns 26-30)

### Assumptions

- CLAUDE.md: 120 lines (~840 tokens)
- System prompt: ~3,500 tokens
- Average user message: ~100 tokens
- Average Claude response: ~400 tokens of text + ~300 tokens of tool calls = ~700 output tokens
- Average tool results per turn: ~1,500 tokens (file reads, command outputs)
- Prompt cache hit rate: ~80% of eligible content

### Turn-by-Turn Cost Calculation

**Turn 1 (no history yet)**

```
Input tokens:
  System prompt:       3,500
  CLAUDE.md:             840
  User message:          100
  ─────────────────────────
  Total input:         4,440 tokens

  Cached:                  0  (first turn, nothing cached yet)
  Uncached:            4,440

Input cost:  4,440 / 1,000,000 x $3.00  = $0.01332
Output cost: 700 / 1,000,000 x $15.00   = $0.01050
─────────────────────────────────────────────────────
Turn 1 total: $0.024
```

**Turn 5 (some history accumulated)**

```
Input tokens:
  System prompt:       3,500  (cached)
  CLAUDE.md:             840  (cached)
  Turns 1-4 history:  12,000  (mostly cached)
  Tool results:        1,500  (not cached)
  User message:          100  (not cached)
  ─────────────────────────
  Total input:        17,940 tokens

  Cached:             14,340  @ $0.30/1M = $0.00430
  Uncached:            3,600  @ $3.00/1M = $0.01080
  Total input cost:                        $0.01510
  Output cost: 700 / 1,000,000 x $15.00 = $0.01050
  ────────────────────────────────────────────────────
  Turn 5 total: $0.026
```

**Turn 15 (mid-session)**

```
Input tokens:
  System prompt:       3,500  (cached)
  CLAUDE.md:             840  (cached)
  Turns 1-14 history: 45,000  (mostly cached)
  Tool results:        2,000  (not cached)
  User message:          100  (not cached)
  ─────────────────────────
  Total input:        51,440 tokens

  Cached:             42,840  @ $0.30/1M = $0.01285
  Uncached:            8,600  @ $3.00/1M = $0.02580
  Total input cost:                        $0.03865
  Output cost: 800 / 1,000,000 x $15.00 = $0.01200
  ────────────────────────────────────────────────────
  Turn 15 total: $0.051
```

**Turn 30 (end of session)**

```
Input tokens:
  System prompt:       3,500  (cached)
  CLAUDE.md:             840  (cached)
  Turns 1-29 history: 95,000  (mostly cached)
  Tool results:        3,000  (not cached)
  User message:          100  (not cached)
  ─────────────────────────
  Total input:       102,440 tokens

  Cached:             86,340  @ $0.30/1M = $0.02590
  Uncached:           16,100  @ $3.00/1M = $0.04830
  Total input cost:                        $0.07420
  Output cost: 700 / 1,000,000 x $15.00 = $0.01050
  ────────────────────────────────────────────────────
  Turn 30 total: $0.085
```

### Total Session Cost Summary

| Phase | Turns | Approx Cost | Notes |
|-------|:-----:|:-----------:|-------|
| Planning | 1-3 | $0.07 | Small context, mostly uncached first turn |
| Implementation | 4-10 | $0.20 | File reads add tokens, cache building up |
| Writing tests | 11-18 | $0.38 | Context growing, more tool usage |
| Bug fixing | 19-25 | $0.40 | Large context, lots of back-and-forth |
| Cleanup | 26-30 | $0.35 | Near-peak context size |
| **Total** | **30** | **~$1.40** | **With prompt caching** |

### What This Same Session Would Cost Without Caching

Without prompt caching, every input token is charged at full price:

| Turn Range | With Caching | Without Caching |
|:----------:|:------------:|:---------------:|
| Turns 1-10 | $0.27 | $0.56 |
| Turns 11-20 | $0.53 | $1.45 |
| Turns 21-30 | $0.60 | $2.15 |
| **Total** | **$1.40** | **$4.16** |

> Prompt caching saved **~$2.76** on this session — a **66% reduction**. This is why preserving the cache is so important.

### What This Session Would Cost on Different Models

| Model | 30-Turn Session Cost | Monthly (5 sessions/day, 22 days) |
|-------|:--------------------:|:---------------------------------:|
| **Opus 5 / 4.8 / 4.7 / 4.6** | ~$2.33 | ~$256 |
| **Sonnet 5 / 4.6** | ~$1.40 | ~$154 |
| **Haiku 4.5** | ~$0.47 | ~$52 |

> **Note**: With Opus 5 (and Opus 4.8 / 4.7 / 4.6) at $5/$25, the cost gap between models is much narrower than it used to be. Opus sessions are only ~1.7x more expensive than Sonnet, making it practical to use Opus more often. Haiku at $1/$5 is still the clear budget choice at 5x cheaper than Opus.
>
> The Opus 5 figure assumes the same output volume as the table's Sonnet baseline. In practice Opus 5 thinks by default and writes longer than Opus 4.8, and both bill as output at $25/1M, so a like-for-like session can land above ~$2.33 until you tune effort level and verbosity.

---

## Why Sessions Get Expensive

### The Exponential Growth Problem

Session cost does not grow linearly — it grows quadratically with the number of turns, because each turn includes all previous turns as input.

```
Cost per turn over a session (illustrative, Sonnet 4.6):

Turn  1: $0.02  ▎
Turn  5: $0.03  ▎▎
Turn 10: $0.04  ▎▎▎
Turn 15: $0.05  ▎▎▎▎
Turn 20: $0.06  ▎▎▎▎▎
Turn 25: $0.07  ▎▎▎▎▎▎
Turn 30: $0.09  ▎▎▎▎▎▎▎
Turn 40: $0.12  ▎▎▎▎▎▎▎▎▎
Turn 50: $0.16  ▎▎▎▎▎▎▎▎▎▎▎▎
```

The first 10 turns might cost $0.27 total. The last 10 turns (41-50) might cost $1.40 total — **5x more** for the same number of turns.

### The Top 5 Cost Drivers

1. **Long sessions without `/compact`** — The #1 cost driver. A 50-turn session costs dramatically more per-turn than five 10-turn sessions doing the same work.

2. **Large file reads accumulating in history** — When Claude reads a 1,000-line file (10,000 tokens), that content stays in conversation history for every subsequent turn. Reading 3 large files adds ~30,000 tokens of permanent context.

3. **Bloated CLAUDE.md** — A 500-line CLAUDE.md adds ~3,500 tokens to every single turn. Over 30 turns, that is 105,000 extra input tokens — $0.32 on Sonnet, $0.53 on Opus.

4. **Using Opus for routine tasks** — If 60% of your turns are simple (formatting, small fixes, lookups), using Opus for all of them costs 5x more than Haiku for those turns. The gap is narrower than it used to be, but still adds up across many turns.

5. **Trial-and-error coding instead of planning first** — Without Plan Mode, Claude might write code, find it does not work, rewrite it, and iterate 4-5 times. Each iteration adds both input history and output tokens. Planning first typically reduces total turns by 30-50%.

---

## Key Formulas

### Cost Per Turn

```
turn_cost = (uncached_input_tokens x input_price_per_token)
          + (cached_input_tokens x cached_price_per_token)
          + (output_tokens x output_price_per_token)
```

### Estimated Session Cost

```
session_cost = sum(turn_cost for each turn)

# Rough approximation for N turns:
session_cost ≈ N x avg_output_tokens x output_price
             + (base_input x N x (1 - cache_rate) x input_price)
             + (base_input x N x cache_rate x cached_price)
             + (N x (N-1) / 2 x avg_turn_size x blended_input_price)
```

Where:
- `base_input` = system prompt + CLAUDE.md (~4,500 tokens)
- `avg_turn_size` = average tokens added per turn (~3,000-4,000)
- `cache_rate` = ~0.80 for typical sessions
- `blended_input_price` = `(cache_rate x cached_price) + ((1 - cache_rate) x input_price)`

### CLAUDE.md Cost Over a Session

```
claude_md_cost = lines x 7 x turns x blended_input_price

Example (150 lines, 30 turns, Sonnet 4.6, 80% cache rate):
= 150 x 7 x 30 x ((0.80 x $0.0000003) + (0.20 x $0.000003))
= 31,500 x $0.00000084
= $0.026

Same example on Opus 5 (or Opus 4.8 / 4.7 / 4.6):
= 31,500 x ((0.80 x $0.0000005) + (0.20 x $0.000005))
= 31,500 x $0.0000014
= $0.044
```

### Model Switching Break-Even

When does it make sense to break the prompt cache by switching models?

```
cache_loss = cached_tokens x (full_input_price - cached_input_price) for remaining turns
model_savings = remaining_turns x avg_turn_cost x (1 - cheaper_model_ratio)

Switch if: model_savings > cache_loss
```

For a rough rule of thumb: if you have more than 3-4 turns left in a session, switching to a model that is 3x+ cheaper is almost always worth the cache break. With the narrower price gaps between current models, the break-even point may be higher when switching between Opus and Sonnet (only 1.67x difference).

---

## Key Takeaways

1. **Output tokens cost 5x more than input tokens.** Strategies that reduce Claude's output (Plan Mode, concise prompts, batching) are highest leverage.

2. **Conversation history is the #1 cost driver.** Use `/compact` proactively and start new sessions for new tasks.

3. **Prompt caching automatically saves ~60-70%** on input costs for multi-turn sessions. Do not break the cache unnecessarily.

4. **CLAUDE.md loads on every turn.** Keep it under 150 lines. Every line you cut saves tokens across your entire session.

5. **Model selection still matters, but the gaps are smaller.** Haiku 4.5 at $1/$5 vs Opus 5/4.8/4.7/4.6 at $5/$25 is a 5x difference. Use the cheapest model that gets the job done -- but Opus is now much more accessible at the same price Sonnet used to be. The new tokenizer (Opus 4.7 and later, +~35% tokens for the same text) slightly re-widens the effective gap.

6. **Track your usage.** Run `/usage` regularly. Set `--max-budget-usd` on every session. What gets measured gets managed.

7. **The last 10 turns of a long session cost more than the first 10.** Session cost grows quadratically, not linearly. Shorter, focused sessions are cheaper than long, wandering ones.

8. **Opus 5 is a free upgrade at the posted rate, but not at the effective rate.** Same $5/$25 as Opus 4.8, which is now legacy. The catch is default-on thinking plus longer output, both billed at $25/1M. Set the effort level deliberately, raise `max_tokens` to 64K+ if you run `xhigh`/`max`, and drop any inherited "double-check your work" instruction since Opus 5 self-verifies.

---

*Next: [Guide 02 - Context Optimization](02-context-optimization.md) — practical strategies to reduce input tokens on every turn.*
