# Guide 11: Speed vs Cost -- Making Claude Faster Without Burning Money

> **Most "make it faster" problems have a free or cheap fix.** Cache warmth, shorter context, model routing, and effort control cover the vast majority of latency complaints at zero or negative cost. Fast Mode is the deliberate splurge -- a flat 2x token premium that only pays off in one narrow case: when raw output-generation speed directly matters.

> **Updated 2026-07-25 for the Opus 5 launch.** Fast Mode narrowed to Opus 5 and Opus 4.8 only, both at 2x. The old 6x tier on Opus 4.7 / 4.6 is gone: `speed: "fast"` now errors on Opus 4.7, and Opus 4.6 accepts it but silently runs at standard speed and standard rates. If you were budgeting for a 6x premium, that line item no longer exists.

---

## Table of Contents

- [The Speed Levers, Ranked by Cost](#the-speed-levers-ranked-by-cost)
- [Fast Mode Economics](#fast-mode-economics)
  - [Pricing by Model](#pricing-by-model)
  - [The OTPS Caveat: What Fast Mode Does Not Speed Up](#the-otps-caveat-what-fast-mode-does-not-speed-up)
  - [Fast Mode and Prompt Caching](#fast-mode-and-prompt-caching)
  - [Compatibility Matrix](#compatibility-matrix)
  - [When the 2x Is Worth It: Deadline Math](#when-the-2x-is-worth-it-deadline-math)
  - [Opus 5 and the Default-On Thinking Tax](#opus-5-and-the-default-on-thinking-tax)
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
| 4 | **Lower effort / fewer thinking tokens** | Cheaper (thinking tokens are billed output) | Faster (less thinking before the answer) | `effort` parameter on Fable 5 / Opus 5 / Opus 4.8 |
| 5 | **Fast Mode** (Opus 5 / Opus 4.8 only) | **2x premium** on both | Up to 2.5x output tokens per second | `anthropic-beta: fast-mode-2026-02-01`, `speed: "fast"` |

Levers 1-4 are free or negative-cost: they make you faster **and** cheaper. Only lever 5 costs money. Exhaust the first four before reaching for it.

---

## Fast Mode Economics

Fast Mode is a research preview that trades money for output-generation speed: up to 2.5x output tokens per second, at a per-token premium.

### Pricing by Model

| Model | Standard (in/out per 1M) | Fast Mode (in/out per 1M) | Premium | Status |
|-------|:------------------------:|:-------------------------:|:-------:|--------|
| **Opus 5** | $5 / $25 | $10 / $50 | **2x** | Supported -- the current default host |
| **Opus 4.8** | $5 / $25 | $10 / $50 | **2x** | Supported, legacy model |
| **Opus 4.7** | $5 / $25 | -- | -- | **Removed** -- `speed: "fast"` returns an error, with no fallback to standard |
| **Opus 4.6** | $5 / $25 | -- | -- | **Removed** -- `speed: "fast"` is accepted but silently runs standard speed at standard rates (`usage.speed` comes back `"standard"`) |
| Fable 5, Mythos 5, Sonnet (any), Haiku, Opus 4.5 | -- | -- | -- | **No Fast Mode** |

Three immediate conclusions:

1. **Fast Mode is now a flat 2x on both supported models.** Opus 5 and Opus 4.8 charge the same $10/$50 for it. The old 6x tier ($30/$150 on Opus 4.7 / 4.6) no longer exists, so the "pick the cheap Fast Mode host" decision is gone -- pick Opus 5 because it is the current model, not because the premium differs. A session that costs $2.33 on standard Opus 5 costs about $4.66 on Opus 5 Fast Mode.
2. **The two removals fail differently, and one fails silently.** Opus 4.7 errors, so you find out immediately. Opus 4.6 accepts the request and quietly serves standard speed at standard rates -- no error, no premium, no speedup. If a pipeline still sends `speed: "fast"` to Opus 4.6 and someone reports "Fast Mode stopped helping," check `usage.speed` in the response before debugging anything else.
3. **Fast Mode is not an option on the frontier model.** Fable 5 has no Fast Mode. If your workload runs on Fable 5, your speed levers are caching, context, and effort -- full stop.

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

Cache multipliers stack on the Fast Mode rate, not the standard rate. On Opus 5 Fast Mode ($10/1M input):

| Cache state | Multiplier | Opus 5 Fast Mode price (per 1M input) |
|-------------|:----------:|:--------------------------------------:|
| 5-min cache write | 1.25x | $10 x 1.25 = **$12.50** |
| 1-hour cache write | 2x | $10 x 2 = **$20.00** |
| Cache hit | 0.1x | $10 x 0.1 = **$1.00** |

Note that a cache hit on Opus 5 Fast Mode ($1.00/1M) costs the same as a cache **miss** on standard Haiku 4.5 ($1.00/1M). The premium multiplies through everything, cache discounts included. Opus 4.8 Fast Mode has identical numbers.

The bigger trap: **switching between fast and standard speed invalidates the prompt cache.** Fast and standard requests use separate cache pools. If you toggle `speed` mid-session, your next turn pays full cache-write price on the entire accumulated prefix -- at Fast Mode rates if you switched to fast. Pick a speed at the start of a session and keep it.

Fast Mode also draws from a **dedicated rate-limit pool** (surfaced in headers like `anthropic-fast-output-tokens-remaining`), separate from your standard limits.

### Compatibility Matrix

| Surface / feature | Fast Mode works? |
|-------------------|:----------------:|
| Claude API (direct) | Yes (Opus 5 / Opus 4.8) |
| Claude Managed Agents | Yes (Opus 5 / Opus 4.8) |
| Amazon Bedrock | **No** |
| Vertex AI | **No** |
| Microsoft Foundry | **No** |
| Claude Platform on AWS | **No** |
| Batch API | **No** (they are opposite tradeoffs) |
| Priority Tier | **No** |

Fast Mode is Claude API + Managed Agents only. If your traffic runs through Bedrock, Vertex, Foundry, or Claude Platform on AWS, Fast Mode is not available to you at any price on any model.

### When the 2x Is Worth It: Deadline Math

Fast Mode is an economic decision: token premium versus the value of the time saved. The math is simple enough to run every time.

**Worked example.** An engineer is blocked waiting on a long agentic run that will generate ~100K output tokens on Opus 5. (Opus 4.8 produces identical numbers -- same standard rate, same 2x premium.)

```
Standard Opus 5:
  Output cost:  100,000 x $25/1M  = $2.50
  Generation time at ~70 OTPS:    ~24 minutes

Fast Mode Opus 5 (2x price, up to 2.5x OTPS):
  Output cost:  100,000 x $50/1M  = $5.00
  Generation time at ~175 OTPS:   ~10 minutes

Premium paid:   $5.00 - $2.50 = $2.50
Time saved:     ~14 minutes of blocked engineer time

At a $60/hour loaded engineer cost:
  14 minutes = $14.00 of engineer time
  $14.00 saved > $2.50 premium  -->  Fast Mode wins by ~5.6x
```

(OTPS figures are illustrative -- the guarantee is "up to 2.5x," not a fixed rate. The premium above counts output only; input tokens are also billed at 2x ($10 vs $5 per 1M), and on context-heavy agentic runs the input premium can dominate. On Opus 5 there is a second complication: thinking is on by default and thinking tokens are output tokens, so the same task produces more billable output than an Opus 4.8 baseline did. Rerun the math with your observed throughput and full token mix.)

The general rule:

```
Use Fast Mode when:
  (minutes saved / 60) x (hourly cost of whoever is waiting)  >  (output tokens x fast premium)

Fast premium on Opus 5 and Opus 4.8 = an extra $25 per 1M output tokens (and $5 per 1M input).
```

For a human actively blocked on the output, this clears easily. For anything else, it usually does not.

### When It Is Not Worth It

| Situation | Why Fast Mode loses | Use instead |
|-----------|--------------------|-------------|
| The task is simple enough for Haiku | Haiku is faster **and** 5x cheaper than standard Opus -- strictly better than paying 2x on Opus | Route to Haiku ([Guide 10](10-task-routing.md)) |
| TTFT is the bottleneck | Fast Mode does not improve time-to-first-token | Warm cache, shorter context, lower effort |
| Nobody is waiting (overnight runs, CI, scheduled jobs) | You are paying 2x to save time nobody experiences | Standard speed, or Batch API for 50% off ([Guide 06](06-access-methods-pricing.md)) |
| You would run it on Opus 4.7 or 4.6 | Fast Mode was removed there: 4.7 errors outright, 4.6 silently serves standard speed | Opus 5 if Fast Mode is truly needed |
| The wait is mostly thinking on Opus 5 | Fast Mode streams thinking tokens faster but bills the 2x premium on all of them | Lower `effort`, or disable thinking at effort high or below |
| Traffic runs through Bedrock/Vertex/Foundry | Not available | The free levers |
| Session toggles speeds frequently | Every switch invalidates the cache; cache rewrites at fast rates ($12.50/1M for a 5-min write on Opus 5) erase the time savings | One speed per session |

---

### Opus 5 and the Default-On Thinking Tax

Opus 5 changed the shape of the latency problem more than the price of it. The posted rate is unchanged at $5/$25, but two behavior changes move where your seconds and dollars go:

**Thinking is ON by default.** Omit the `thinking` parameter on Opus 5 and you get adaptive thinking; on Opus 4.8 the same request got none. Thinking tokens are billed as output at $25/1M and they are generated **before** your answer starts, so the identical prompt that felt fast on Opus 4.8 can feel slower on Opus 5 while costing more -- with no config change on your side. That is the single most common "why did my latency regress after upgrading" cause right now.

**`max_tokens` is a hard cap on thinking plus text.** If you carried over a small `max_tokens` from an Opus 4.8 integration, thinking can consume the budget before the visible answer is written. Raise it to 64K or more if you run `xhigh` or `max` effort.

Your two dials, in order of preference:

| Want | Do | Cost effect |
|------|----|-------------|
| Less thinking, keep it available | Lower `output_config.effort` (defaults to `high`) | Fewer output tokens, faster start |
| No thinking at all | `thinking: {type: "disabled"}` -- **only legal at effort `high` or below** | Removes the thinking bill entirely |

Pairing `thinking: {type: "disabled"}` with `xhigh` or `max` effort returns a **400 error**, so there is no way to buy maximum effort and skip thinking. That combination was your escape hatch on Opus 4.8; on Opus 5 it is a validation failure.

One more thing worth auditing after an upgrade: Opus 5 produces **longer output than Opus 4.8 by default** and self-verifies its own work. Carried-over prompt instructions like "double-check your answer" or "explain your reasoning step by step" now pay twice for behavior the model already performs, and verbose-by-default output is billed output. Re-tune verbosity instructions rather than assuming the old prompt is still cost-optimal.

---

## Latency by Model

Model choice is itself a speed lever -- generally the strongest one after caching. Smaller models respond faster and cost less.

| Model | Price (in/out per 1M) | Context | Max output | Latency class | Fast Mode | Speed-per-dollar takeaway |
|-------|:---------------------:|:-------:|:----------:|---------------|:---------:|---------------------------|
| **Haiku 4.5** | $1 / $5 | 200K | 64K | Fastest in the lineup | No | Best speed AND best price -- the default for simple tasks |
| **Sonnet 5** | $3 / $15 (intro $2 / $10 through 2026-08-31) | 1M | 128K | Fast | No | Best speed-to-intelligence balance for standard dev work |
| **Opus 5** | $5 / $25 | 1M | 128K | Moderate, and slower out of the box than 4.8 was (thinking is on by default) | Yes (2x) | The current Fast Mode host; standard speed for most Opus work |
| **Opus 4.8** | $5 / $25 | 1M | 128K | Moderate | Yes (2x) | Legacy. Same price and same 2x Fast Mode as Opus 5 -- no speed or cost reason to stay |
| **Fable 5** | $10 / $50 | 1M | 128K | Slower (always-on adaptive thinking adds a pre-answer phase) | No | Maximum capability; speed levers are effort + caching only |

**The strictly-better rule:** for any task Haiku 4.5 can handle, Haiku beats Opus Fast Mode on **both** axes -- it is faster (lowest latency in the lineup) and 10x cheaper than Opus 5 Fast Mode ($1/$5 vs $10/$50). Paying a Fast Mode premium to speed up a task you could have routed down is the most expensive way to solve a routing problem.

Fast Mode only enters the picture when the task genuinely needs Opus-level capability **and** output speed matters. That intersection is narrow.

One tokenizer note: Opus 5, Opus 4.8, Opus 4.7, Fable 5, and Sonnet 5 all use the newer tokenizer, which produces up to ~30-35% more tokens for the same text than pre-4.7 models. More tokens means proportionally more generation time and cost -- factor it into any throughput comparison against older benchmarks. Opus 5 shares the Opus 4.7-generation tokenizer exactly, so migrating from 4.7 or 4.8 needs no token re-baselining.

---

## Thinking and Effort as a Speed Lever

Thinking tokens are billed as output tokens, and they are generated **before** your answer starts. Every thinking token you do not need is latency and money saved simultaneously.

| Model | Thinking behavior | Control |
|-------|-------------------|---------|
| **Fable 5** | Adaptive thinking, **always on** -- `thinking: {type: "disabled"}` is not supported | `effort` parameter controls depth |
| **Opus 5** | Adaptive thinking, **on by default** when you omit the `thinking` param; `effort` defaults to **high** | Lower `effort`, or `thinking: {type: "disabled"}` at effort high or below (400 at xhigh/max) |
| **Opus 4.8** | Adaptive thinking, **off** unless you ask for it; `effort` defaults to **high** on all surfaces | Lower `effort` explicitly for routine work |
| **Sonnet 5** | Adaptive thinking; `effort` defaults to **high** on the Claude API and Claude Code | Lower `effort` for routine work |

Practical implications:

- **On Opus 5, the default costs you both speed and money.** Thinking is on unless you disable it, and effort starts at high. The same request that returned straight text on Opus 4.8 now generates a thinking phase first, billed as output at $25/1M. For routine tasks, lower effort or disable thinking outright.
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
| Engineer actively blocked on long output | Fast Mode (Opus 5) | 2x |
| Interactive session, human in the loop | Standard | 1x |
| Overnight doc generation, bulk classification, eval runs, migration sweeps | Batch API | **0.5x** |

If a job runs while nobody watches, putting it on Batch instead of Fast Mode is a 4x price difference on Opus 5 (0.5x vs 2x) for zero experienced slowdown -- $2.50/$12.50 per 1M on Batch versus $10/$50 on Fast Mode. Batch also unlocks 300K max output on Opus 5 via the `output-300k-2026-03-24` beta, which Fast Mode cannot do at any price. See [Guide 06](06-access-methods-pricing.md) for Batch API mechanics and [Guide 08](08-prompt-caching.md) for how caching interacts with batched workloads.

---

## Decision Table: "I Need It Faster"

Work top to bottom. Stop at the first row that applies -- the levers are ordered so the free fixes come first.

| Symptom | Diagnosis | Lever | Cost impact |
|---------|-----------|-------|:-----------:|
| Nobody is actually waiting on this | You do not have a speed problem | Batch API ([Guide 06](06-access-methods-pricing.md)) | **-50%** |
| Slow start, long pause before first token | Cold cache or oversized context | Warm the cache; turns <5 min apart; stop editing CLAUDE.md mid-session ([Guide 08](08-prompt-caching.md)) | Cheaper (0.1x on hits) |
| Still slow to start, cache is warm | Context bloat | `/compact`, fresh session, trim CLAUDE.md, `.claudeignore` ([Guide 02](02-context-optimization.md)) | Cheaper |
| Latency regressed right after moving to Opus 5 | Thinking is on by default now | Lower `effort`, or `thinking: {type: "disabled"}` at effort high or below | Cheaper (removes billed thinking output) |
| Slow start on Fable 5 / Opus 5 / Opus 4.8, small context | Thinking-heavy startup | Lower `effort` for routine tasks | Cheaper |
| Task is simple (rename, boilerplate, summary, syntax) | Over-modeled | Route to Haiku 4.5 -- faster AND 5x+ cheaper than Opus | **-80% vs Opus** |
| Task is standard dev work on Opus | Over-modeled | Route to Sonnet 5 ($2/$10 intro through 2026-08-31) | -40% to -60% vs Opus |
| Long output streams too slowly, task truly needs Opus, a human is blocked, deadline math clears | The one Fast Mode case | Fast Mode on **Opus 5** (4.7 errors, 4.6 silently ignores it); one speed for the whole session | **+100%** |
| All of the above and you are on Bedrock/Vertex/Foundry | Fast Mode unavailable | Back to the free levers; consider Claude API direct if the case is chronic | -- |

---

## Key Takeaways

1. **Speed and cost are usually allies, not enemies.** Cache warmth, shorter context, model routing, and effort control all make sessions faster AND cheaper. Fast Mode is the only speed lever that costs extra -- reach for it last.

2. **Diagnose TTFT vs OTPS before spending anything.** Fast Mode only accelerates output streaming (up to 2.5x OTPS). If your pain is the wait before tokens appear, the fix is caching (up to 85% latency reduction), smaller context, or lower effort -- all free or cheaper.

3. **For tasks Haiku can do, Haiku beats Fast Mode on both speed and cost.** It has the lowest latency in the lineup at $1/$5 -- 10x cheaper than Opus 5 Fast Mode. Routing down is strictly better than paying up.

4. **Fast Mode is a flat 2x on Opus 5 and Opus 4.8, and unavailable everywhere else.** The 6x tier is gone: Opus 4.7 errors on `speed: "fast"`, and Opus 4.6 accepts it but silently serves standard speed at standard rates. Check `usage.speed` in the response if you suspect a pipeline is still asking for Fast Mode on a model that no longer honors it.

5. **Run the deadline math.** Fast Mode pays off when (engineer time saved) > (token premium). For a blocked human on a 100K-token output, ~$2.50 of premium buys ~14 minutes -- an easy win. For unattended jobs, it buys nothing.

6. **Never toggle speeds mid-session.** Fast and standard use separate cache pools; every switch invalidates your prompt cache and forces full-price rewrites at the new speed's rates ($12.50/1M for a 5-min write on Opus 5 Fast Mode).

7. **Effort is the thinking-speed dial, and Opus 5 changed its default.** Thinking is on by default on Opus 5 (it was off on Opus 4.8), Fable 5's is always on, and effort starts at high on all three. Lowering `effort` cuts thinking tokens, which cuts both latency and output cost. `thinking: {type: "disabled"}` removes them entirely but is only legal at effort high or below -- pairing it with xhigh or max returns a 400.

8. **When nobody is waiting, flip the dial the other way.** Batch API is 50% off for async workloads -- a 4x price difference versus Fast Mode on Opus 5 ($2.50/$12.50 versus $10/$50) for jobs that run overnight anyway.

---

*Previous: [Guide 10 - Three-Tier Task Routing](10-task-routing.md)*
