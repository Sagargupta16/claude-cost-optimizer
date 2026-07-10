# Guide 11: Speed vs Cost -- Making Claude Faster Without Burning Money

> **Most "make it faster" problems have a free or cheap fix.** Cache warmth, shorter context, model routing, and effort control cover the vast majority of latency complaints at zero or negative cost. Fast Mode is the deliberate splurge -- a 2x-6x token premium that only pays off in one narrow case: when raw output-generation speed directly matters.

---

## Table of Contents

- [The Speed Levers, Ranked by Cost](#the-speed-levers-ranked-by-cost)
- [Fast Mode Economics](#fast-mode-economics)
  - [Pricing by Model](#pricing-by-model)
  - [The OTPS Caveat: What Fast Mode Does Not Speed Up](#the-otps-caveat-what-fast-mode-does-not-speed-up)
  - [Fast Mode and Prompt Caching](#fast-mode-and-prompt-caching)
  - [Compatibility Matrix](#compatibility-matrix)
  - [When the 2x Is Worth It: Deadline Math](#when-the-2x-is-worth-it-deadline-math)
  - [When It Is Not Worth It](#when-it-is-not-worth-it)
- [Latency by Model](#latency-by-model)
- [Thinking and Effort as a Speed Lever](#thinking-and-effort-as-a-speed-lever)
- [Caching as a Latency Tool](#caching-as-a-latency-tool)
- [The Inverse Lever: Batch API When Speed Does Not Matter](#the-inverse-lever-batch-api-when-speed-does-not-matter)
- [Decision Table: "I Need It Faster"](#decision-table-i-need-it-faster)
- [Key Takeaways](#key-takeaways)

---

## The Speed Levers, Ranked by Cost

Every other guide in this series optimizes for cost. This one covers the speed dimension -- and the first thing to understand is that speed and cost are usually **not** in tension. Most speed levers make your sessions cheaper at the same time.

| Rank | Lever | Cost impact | Speed impact | How |
|:----:|-------|-------------|--------------|-----|
| 1 | **Keep the cache warm** | Cheaper (0.1x input on hits) | Up to 85% latency reduction on long prompts | Turns under 5 minutes apart, stable CLAUDE.md, no mid-session config edits ([Guide 08](08-prompt-caching.md)) |
| 2 | **Shorter context** | Cheaper (fewer input tokens per turn) | Faster (less input to process each turn) | `/compact`, fresh sessions per task, small CLAUDE.md, `.claudeignore` ([Guide 02](02-context-optimization.md)) |
| 3 | **Route down to Haiku / Sonnet** | 1.7x (Sonnet) to 5x (Haiku) cheaper than Opus per token | Faster -- smaller models have lower latency | Task routing: Haiku for simple, Sonnet for standard ([Guide 03](03-model-selection.md), [Guide 10](10-task-routing.md)) |
| 4 | **Lower effort / fewer thinking tokens** | Cheaper (thinking tokens are billed output) | Faster (less thinking before the answer) | `effort` parameter on Fable 5 / Opus 4.8 |
| 5 | **Fast Mode** (Opus 4.8 / 4.7 / 4.6 only) | **2x premium** (Opus 4.8) or **6x premium** (4.7/4.6) | Up to 2.5x output tokens per second | `anthropic-beta: fast-mode-2026-02-01`, `speed: "fast"` |

Levers 1-4 are free or negative-cost: they make you faster **and** cheaper. Only lever 5 costs money. Exhaust the first four before reaching for it.

---

## Fast Mode Economics

Fast Mode is a research preview that trades money for output-generation speed: up to 2.5x output tokens per second, at a per-token premium.

### Pricing by Model

| Model | Standard (in/out per 1M) | Fast Mode (in/out per 1M) | Premium | Status |
|-------|:------------------------:|:-------------------------:|:-------:|--------|
| **Opus 4.8** | $5 / $25 | $10 / $50 | **2x** | Supported |
| **Opus 4.7** | $5 / $25 | $30 / $150 | **6x** | Supported, legacy model |
| **Opus 4.6** | $5 / $25 | $30 / $150 | **6x** | **Deprecated** as of the 4.8 launch; removed ~30 days later, then falls back to standard speed |
| Fable 5, Mythos 5, Sonnet (any), Haiku, Opus 4.5 | -- | -- | -- | **No Fast Mode** |

Two immediate conclusions:

1. **If you use Fast Mode at all, use it on Opus 4.8.** The same speed boost costs 2x there versus 6x on 4.7/4.6. A session that costs $2.33 on standard Opus 4.8 costs ~$4.66 on Opus 4.8 Fast Mode -- but ~$14 on Opus 4.7/4.6 Fast Mode. That is 3x the total cost (a 5x larger premium: $11.65 extra vs $2.33 extra) for the same up-to-2.5x speed boost, on an older model.
2. **Fast Mode is not an option on the frontier model.** Fable 5 has no Fast Mode. If your workload runs on Fable 5, your speed levers are caching, context, and effort -- full stop.

### The OTPS Caveat: What Fast Mode Does Not Speed Up

Fast Mode accelerates **output tokens per second (OTPS)** -- the rate at which the response streams out. It does **not** improve **time-to-first-token (TTFT)** -- the wait before the response starts.

This distinction decides whether Fast Mode helps you at all:

| Your bottleneck | Symptom | Does Fast Mode help? |
|-----------------|---------|:--------------------:|
| Long output generation | Response streams slowly for minutes (large code file, long document, big diff) | **Yes** -- up to 2.5x faster streaming |
| Slow start | Long pause before anything appears (huge uncached prompt being processed) | **No** -- fix with caching or shorter context instead |
| Thinking-heavy startup | Long thinking phase before the answer | **Poor value** -- thinking tokens are output tokens, so they may stream faster, but you pay the premium on every one; lowering `effort` removes them instead |
| Many short turns | Each turn is quick but there are dozens of them | **Marginal** -- per-turn output is small, so up to 2.5x OTPS saves seconds while costing 2x on every token |

If your pain is the wait before tokens appear, you are paying a 2x premium for nothing. Diagnose the bottleneck first.

### Fast Mode and Prompt Caching

Cache multipliers stack on the Fast Mode rate, not the standard rate. On Opus 4.7 Fast Mode ($30/1M input):

| Cache state | Multiplier | Opus 4.7 Fast Mode price (per 1M input) |
|-------------|:----------:|:----------------------------------------:|
| 5-min cache write | 1.25x | $30 x 1.25 = **$37.50** |
| 1-hour cache write | 2x | $30 x 2 = **$60.00** |
| Cache hit | 0.1x | $30 x 0.1 = **$3.00** |

Note that a cache hit on Opus 4.7 Fast Mode ($3.00/1M) costs **more than a cache miss on standard Haiku** ($1.00/1M). The premium multiplies through everything.

The bigger trap: **switching between fast and standard speed invalidates the prompt cache.** Fast and standard requests use separate cache pools. If you toggle `speed` mid-session, your next turn pays full cache-write price on the entire accumulated prefix -- at Fast Mode rates if you switched to fast. Pick a speed at the start of a session and keep it.

Fast Mode also draws from a **dedicated rate-limit pool** (surfaced in headers like `anthropic-fast-output-tokens-remaining`), separate from your standard limits.

### Compatibility Matrix

| Surface / feature | Fast Mode works? |
|-------------------|:----------------:|
| Claude API (direct) | Yes (Opus 4.8 / 4.7 / 4.6) |
| Claude Managed Agents | Yes (Opus 4.8) |
| Amazon Bedrock | **No** (stated for Opus 4.8; 4.7/4.6 availability unpublished) |
| Vertex AI | **No** (stated for Opus 4.8; 4.7/4.6 availability unpublished) |
| Microsoft Foundry | **No** (stated for Opus 4.8; 4.7/4.6 availability unpublished) |
| Claude Platform on AWS | **No** |
| Batch API | **No** (they are opposite tradeoffs) |
| Priority Tier | **No** |

Opus 4.8 Fast Mode is Claude API + Managed Agents only. For Opus 4.8, if your traffic runs through Bedrock, Vertex, or Foundry, Fast Mode is not available to you at any price.

### When the 2x Is Worth It: Deadline Math

Fast Mode is an economic decision: token premium versus the value of the time saved. The math is simple enough to run every time.

**Worked example.** An engineer is blocked waiting on a long agentic run that will generate ~100K output tokens on Opus 4.8.

```
Standard Opus 4.8:
  Output cost:  100,000 x $25/1M  = $2.50
  Generation time at ~70 OTPS:    ~24 minutes

Fast Mode Opus 4.8 (2x price, up to 2.5x OTPS):
  Output cost:  100,000 x $50/1M  = $5.00
  Generation time at ~175 OTPS:   ~10 minutes

Premium paid:   $5.00 - $2.50 = $2.50
Time saved:     ~14 minutes of blocked engineer time

At a $60/hour loaded engineer cost:
  14 minutes = $14.00 of engineer time
  $14.00 saved > $2.50 premium  -->  Fast Mode wins by ~5.6x
```

(OTPS figures are illustrative -- the guarantee is "up to 2.5x," not a fixed rate. The premium above counts output only; input tokens are also billed at 2x ($10 vs $5 per 1M), and on context-heavy agentic runs the input premium can dominate. Rerun the math with your observed throughput and full token mix.)

The general rule:

```
Use Fast Mode when:
  (minutes saved / 60) x (hourly cost of whoever is waiting)  >  (output tokens x fast premium)

Fast premium on Opus 4.8 = an extra $25 per 1M output tokens (and $5 per 1M input).
```

For a human actively blocked on the output, this clears easily. For anything else, it usually does not.

### When It Is Not Worth It

| Situation | Why Fast Mode loses | Use instead |
|-----------|--------------------|-------------|
| The task is simple enough for Haiku | Haiku is faster **and** 5x cheaper than standard Opus -- strictly better than paying 2x on Opus | Route to Haiku ([Guide 10](10-task-routing.md)) |
| TTFT is the bottleneck | Fast Mode does not improve time-to-first-token | Warm cache, shorter context, lower effort |
| Nobody is waiting (overnight runs, CI, scheduled jobs) | You are paying 2x to save time nobody experiences | Standard speed, or Batch API for 50% off ([Guide 06](06-access-methods-pricing.md)) |
| You would run it on Opus 4.7/4.6 | 6x premium; a $2.33 session becomes ~$14 | Opus 4.8 (2x) if Fast Mode is truly needed |
| Traffic runs through Bedrock/Vertex/Foundry | Not available | The free levers |
| Session toggles speeds frequently | Every switch invalidates the cache; cache rewrites at fast rates ($37.50/1M for 5-min writes on 4.7) erase the time savings | One speed per session |

---

## Latency by Model

Model choice is itself a speed lever -- generally the strongest one after caching. Smaller models respond faster and cost less.

| Model | Price (in/out per 1M) | Context | Max output | Latency class | Fast Mode | Speed-per-dollar takeaway |
|-------|:---------------------:|:-------:|:----------:|---------------|:---------:|---------------------------|
| **Haiku 4.5** | $1 / $5 | 200K | 64K | Fastest in the lineup | No | Best speed AND best price -- the default for simple tasks |
| **Sonnet 5** | $3 / $15 (intro $2 / $10 through 2026-08-31) | 1M | 128K | Fast | No | Best speed-to-intelligence balance for standard dev work |
| **Opus 4.8** | $5 / $25 | 1M | 128K | Moderate | Yes (2x) | The only sane Fast Mode host; standard speed for most Opus work |
| **Fable 5** | $10 / $50 | 1M | 128K | Slower (always-on adaptive thinking adds a pre-answer phase) | No | Maximum capability; speed levers are effort + caching only |

**The strictly-better rule:** for any task Haiku 4.5 can handle, Haiku beats Opus Fast Mode on **both** axes -- it is faster (lowest latency in the lineup) and 10x cheaper than Opus 4.8 Fast Mode ($1/$5 vs $10/$50). Paying a Fast Mode premium to speed up a task you could have routed down is the most expensive way to solve a routing problem.

Fast Mode only enters the picture when the task genuinely needs Opus-level capability **and** output speed matters. That intersection is narrow.

One tokenizer note: Opus 4.7+, Fable 5, and Sonnet 5 use the new tokenizer, which produces up to ~30-35% more tokens for the same text than pre-4.7 models. More tokens means proportionally more generation time and cost -- factor it into any throughput comparison against older benchmarks.

---

## Thinking and Effort as a Speed Lever

Thinking tokens are billed as output tokens, and they are generated **before** your answer starts. Every thinking token you do not need is latency and money saved simultaneously.

| Model | Thinking behavior | Control |
|-------|-------------------|---------|
| **Fable 5** | Adaptive thinking, **always on** -- `thinking: {type: "disabled"}` is not supported | `effort` parameter controls depth |
| **Opus 4.8** | Adaptive thinking only; `effort` defaults to **high** on all surfaces | Lower `effort` explicitly for routine work |

Practical implications:

- **On Opus 4.8, the default costs you speed.** Effort defaults to high everywhere. For routine tasks (renames, small edits, formatting-adjacent work), lowering effort cuts thinking tokens, which cuts both the pre-answer wait and the output bill.
- **On Fable 5, effort is your only thinking dial.** You cannot turn thinking off. If Fable 5 feels slow, check whether the task justifies high effort before assuming you need a different model.
- **This lever removes tokens instead of streaming them faster.** Thinking happens before your visible answer, so heavy thinking feels like a slow start even though it is output generation under the hood. Fast Mode may stream thinking tokens faster, but you pay the premium on every one of them; lowering effort deletes them entirely -- faster AND cheaper.

Rule of thumb: match effort to task difficulty the same way you match model to task tier ([Guide 10](10-task-routing.md)). High effort on a trivial task wastes seconds and dollars on every single turn.

---

## Caching as a Latency Tool

[Guide 08](08-prompt-caching.md) covers prompt caching as a cost lever (90% off cached input). It is equally a **latency** lever: Anthropic publishes up to **85% latency reduction** for long prompts served from cache, because the cached prefix is not reprocessed at all.

Cache hits primarily improve TTFT -- exactly the bottleneck Fast Mode cannot fix. In a typical Claude Code session, the system prompt, CLAUDE.md, tool schemas, and conversation history form a long stable prefix. When that prefix is a cache hit, the model starts responding almost immediately instead of re-reading tens of thousands of tokens first.

The same hygiene that maximizes cache savings maximizes speed:

- Keep turns under 5 minutes apart (5-minute cache TTL).
- Do not edit CLAUDE.md or settings mid-session -- any prefix change invalidates everything after it.
- Do not toggle Fast Mode mid-session -- separate cache pools, full invalidation.

A warm cache is the single cheapest latency win available: you get up to 85% faster starts **while paying 90% less** for the cached tokens. Nothing else on this page has that sign on both axes.

---

## The Inverse Lever: Batch API When Speed Does Not Matter

Speed optimization has a mirror image: when latency does not matter at all, stop paying for it.

The Batch API is the opposite tradeoff from Fast Mode: **50% off both input and output tokens** in exchange for asynchronous processing with up to a 24-hour turnaround (most batches finish much sooner). Fast Mode and Batch are mutually exclusive by design -- they are the two ends of the same dial.

| Workload | Right end of the dial | Price vs standard |
|----------|----------------------|:-----------------:|
| Engineer actively blocked on long output | Fast Mode (Opus 4.8) | 2x |
| Interactive session, human in the loop | Standard | 1x |
| Overnight doc generation, bulk classification, eval runs, migration sweeps | Batch API | **0.5x** |

If a job runs while nobody watches, putting it on Batch instead of Fast Mode is a 4x price difference on Opus 4.8 (0.5x vs 2x) for zero experienced slowdown. See [Guide 06](06-access-methods-pricing.md) for Batch API mechanics and [Guide 08](08-prompt-caching.md) for how caching interacts with batched workloads.

---

## Decision Table: "I Need It Faster"

Work top to bottom. Stop at the first row that applies -- the levers are ordered so the free fixes come first.

| Symptom | Diagnosis | Lever | Cost impact |
|---------|-----------|-------|:-----------:|
| Nobody is actually waiting on this | You do not have a speed problem | Batch API ([Guide 06](06-access-methods-pricing.md)) | **-50%** |
| Slow start, long pause before first token | Cold cache or oversized context | Warm the cache; turns <5 min apart; stop editing CLAUDE.md mid-session ([Guide 08](08-prompt-caching.md)) | Cheaper (0.1x on hits) |
| Still slow to start, cache is warm | Context bloat | `/compact`, fresh session, trim CLAUDE.md, `.claudeignore` ([Guide 02](02-context-optimization.md)) | Cheaper |
| Slow start on Fable 5 / Opus 4.8, small context | Thinking-heavy startup | Lower `effort` for routine tasks | Cheaper |
| Task is simple (rename, boilerplate, summary, syntax) | Over-modeled | Route to Haiku 4.5 -- faster AND 5x+ cheaper than Opus | **-80% vs Opus** |
| Task is standard dev work on Opus | Over-modeled | Route to Sonnet 5 ($2/$10 intro through 2026-08-31) | -40% to -60% vs Opus |
| Long output streams too slowly, task truly needs Opus, a human is blocked, deadline math clears | The one Fast Mode case | Fast Mode on **Opus 4.8** (never 4.7/4.6 at 6x); one speed for the whole session | **+100%** |
| All of the above and you are on Bedrock/Vertex/Foundry | Fast Mode unavailable | Back to the free levers; consider Claude API direct if the case is chronic | -- |

---

## Key Takeaways

1. **Speed and cost are usually allies, not enemies.** Cache warmth, shorter context, model routing, and effort control all make sessions faster AND cheaper. Fast Mode is the only speed lever that costs extra -- reach for it last.

2. **Diagnose TTFT vs OTPS before spending anything.** Fast Mode only accelerates output streaming (up to 2.5x OTPS). If your pain is the wait before tokens appear, the fix is caching (up to 85% latency reduction), smaller context, or lower effort -- all free or cheaper.

3. **For tasks Haiku can do, Haiku beats Fast Mode on both speed and cost.** It has the lowest latency in the lineup at $1/$5 -- 10x cheaper than Opus 4.8 Fast Mode. Routing down is strictly better than paying up.

4. **If you must use Fast Mode, use Opus 4.8.** The premium is 2x there versus 6x on Opus 4.7/4.6 (and 4.6 Fast Mode is deprecated). A $2.33 session becomes ~$4.66 on 4.8 but ~$14 on 4.7/4.6.

5. **Run the deadline math.** Fast Mode pays off when (engineer time saved) > (token premium). For a blocked human on a 100K-token output, ~$2.50 of premium buys ~14 minutes -- an easy win. For unattended jobs, it buys nothing.

6. **Never toggle speeds mid-session.** Fast and standard use separate cache pools; every switch invalidates your prompt cache and forces full-price rewrites at the new speed's rates ($37.50/1M for a 5-min write on Opus 4.7 Fast Mode).

7. **Effort is the thinking-speed dial.** Fable 5's adaptive thinking is always on and Opus 4.8 defaults to high effort -- lower `effort` on routine tasks cuts thinking tokens, which cuts both latency and output cost.

8. **When nobody is waiting, flip the dial the other way.** Batch API is 50% off for async workloads -- a 4x price difference versus Fast Mode on Opus 4.8 for jobs that run overnight anyway.

---

*Previous: [Guide 10 - Three-Tier Task Routing](10-task-routing.md)*
