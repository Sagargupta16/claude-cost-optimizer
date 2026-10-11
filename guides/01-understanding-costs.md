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

Every interaction with Claude Code consumes tokens. Tokens are the fundamental billing unit. On models before Opus 4.7 that is roughly 1 token per 4 characters of English text, or about 0.75 words per token; on the current tokenizer 1M tokens is roughly 2.5M characters or 555K words, about 2.5 characters per token ([Anthropic models overview](https://platform.claude.com/docs/en/about-claude/models/overview)). This repo's estimates assume about 10 tokens per line of code and 10 per line of CLAUDE.md. The CLAUDE.md figure is measured: this repo's 15 CLAUDE.md files (the templates plus the root file) hold 20,161 tokens over 2,048 lines, 9.8 per line counting blank lines (12.3 per non-blank line). That count used tiktoken's cl100k encoding, the same pre-4.7 basis as the repo's other estimates; expect about 30% more on the current tokenizer.

### Current Model Pricing (verified 2026-10-09)

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Cache Hit (per 1M) | 5m Cache Write | 1h Cache Write | Context Window | Max Output |
|-------|:---------------------:|:----------------------:|:---------------------:|:--------------:|:--------------:|:--------------:|:----------:|
| **Fable 5.1** (most capable) | $10.00 | $50.00 | **$0.25** | $12.50 | $20.00 | 1M | 128K |
| **Fable 5** (legacy) | $10.00 | $50.00 | $1.00 | $12.50 | $20.00 | 1M | 128K |
| **Opus 5.5** (recommended default) | $4.00 | $20.00 | **$0.20** | $5.00 | $8.00 | 1M | 128K |
| **Opus 5** (legacy) | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1M | 128K |
| **Opus 4.8** (legacy) | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1M | 128K |
| **Opus 4.7** | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1M | 128K |
| **Opus 4.6** | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1M | 128K |
| **Opus 4.5** | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 200K | 64K |
| Opus 4.1 (retired 2026-08-05, still on Bedrock + Google Cloud) | $15.00 | $75.00 | $1.50 | $18.75 | $30.00 | 200K | 32K |
| **Sonnet 5.5** (latest Sonnet) | $2.00 | $10.00 | **$0.10** | $2.50 | $4.00 | 1M | 128K |
| **Sonnet 5** (legacy) | $2.00 | $10.00 | $0.20 | $2.50 | $4.00 | see note | see note |
| **Sonnet 4.6** | $3.00 | $15.00 | $0.30 | $3.75 | $6.00 | 1M | 64K |
| **Sonnet 4.5** (deprecated; retirement scheduled for 2026-11-30) | $3.00 | $15.00 | $0.30 | $3.75 | $6.00 | 200K | 64K |
| **Haiku 5.5** (latest Haiku), prompt <= 100K tokens | $0.10 | $0.50 | $0.01 | $0.125 | $0.20 | 1M | 128K |
| **Haiku 5.5**, prompt > 100K tokens | $0.50 | $2.50 | $0.05 | $0.625 | $1.00 | 1M | 128K |
| **Haiku 4.5** (legacy) | $1.00 | $5.00 | $0.10 | $1.25 | $2.00 | 200K | 64K |
| **Opus 5.5 (Fast Mode)** | $8.00 (2x) | $40.00 (2x) | N/A | -- | -- | 1M (included) | 128K |
| **Opus 5 / 4.8 (Fast Mode)** | $10.00 (2x) | $50.00 (2x) | N/A | -- | -- | 1M (included) | 128K |

> **Opus 5.5** (released 2026-09-22, `claude-opus-5-5`): **$4/$20, 20% below Opus 5's $5/$25** -- the first Opus price cut since Opus 4.5 lowered $15/$75 to $5/$25 on 2025-11-24 ([Opus 4.5 announcement](https://www.anthropic.com/news/claude-opus-4-5)). Cache hits cost $0.20/1M, **0.05x base input (95% off)**; 5m cache write $5, 1h cache write $8; Batch $2/$10. 1M context (default and max), 128K max output (300K on Batch via the `output-300k-2026-03-24` beta), knowledge cutoff Jun 2026, same tokenizer as Opus 4.7+, minimum cacheable prompt 512 tokens, tool-use system prompt 286 tokens. Bedrock ID `anthropic.claude-opus-5-5`; `claude-opus-5-5` on Google Cloud, Microsoft Foundry and Claude Platform on AWS. Retirement not sooner than 2027-09-22. Anthropic's models overview now says to "start with Claude Opus 5.5 for most workloads"; Fable 5.1 is for demanding reasoning and long-horizon work.
>
> **Cost-relevant breaking changes vs Opus 5**:
> - **Thinking is always on.** `thinking: {type: "disabled"}` and `thinking: {type: "enabled", budget_tokens}` both return 400; effort is the only control. Code that disabled thinking on Opus 5 now pays for thinking tokens (billed as output at $20/1M) it did not pay for before.
> - **Default effort drops to `medium`** (Opus 5 defaulted to `high`), so a request that omits effort now thinks less than it did on Opus 5. All five levels are supported. Re-baseline cost after migrating.
> - Forced `tool_choice` (`any`/`tool`) returns 400 -- use `auto` plus strict tool use or structured outputs. Non-default sampling params (`temperature`/`top_p`/`top_k`) and assistant prefill also return 400.
> - Thinking blocks are tied to the model and conversation, and text between tool calls now comes back in `thinking` blocks (empty at the default display setting). On the Claude API and Google Cloud the `computer_20251124` tool is rejected (use `computer_toolset_20260801`).
> - **No Priority Tier** (Opus 4.8 keeps it). Fast Mode is supported at 2x its own base ($8/$40).
> - Refusals return `stop_reason: "refusal"` with `stop_details`; categories include bio and reasoning_extraction as well as cyber.
>
> **Opus 5** (legacy since the Opus 5.5 launch; GA 2026-07-24, `claude-opus-5`): identical posted price to Opus 4.8 ($5/$25), so the upgrade is free at the posted rate. 1M context at standard rates, 128K max output (300K on Batch via the `output-300k-2026-03-24` beta), knowledge cutoff May 2026, Batch $2.50/$12.50, minimum cacheable prompt 512 tokens. Adaptive thinking with effort levels low/medium/high/xhigh/max, defaulting to `high` on both the Claude API and Claude Code. Bedrock ID `anthropic.claude-opus-5`, Google Cloud `claude-opus-5`; GA on Claude API, Claude Platform on AWS, Bedrock, and Vertex AI. Earliest retirement not sooner than 2027-07-24. Anthropic's models overview now points to Opus 5.5 instead, which costs 20% less; Fable 5.1 is the most capable model.
>
> **Cost-relevant breaking changes vs Opus 4.8**:
> - **Thinking is on by default.** Omit the `thinking` param and you get adaptive thinking. Reasoning tokens bill as **output** at $25/1M. `max_tokens` is a hard cap on thinking **plus** text, so an unchanged small `max_tokens` can be eaten by thinking before the answer is written. Raise it to 64K+ if you run `xhigh` or `max` effort.
> - `thinking: {type: "disabled"}` is allowed only at effort `high` or below. Combining it with `xhigh` or `max` returns a **400 error**.
> - Minimum cacheable prompt drops from 1,024 tokens (Opus 4.8) to **512** (Opus 5), so shorter prefixes now qualify for the cache discount.
> - Ships cybersecurity safety classifiers. Cyber refusals can auto-fall-back to Opus 4.8 via the server-side `fallbacks` param with beta header `server-side-fallback-2026-07-01`.
> - New beta `mid-conversation-tool-changes-2026-07-01` lets tool definitions change between turns **without** invalidating the prompt cache. Previously that was a cache-busting move.
> - Output runs **longer** than Opus 4.8 by default, so re-tune verbosity instructions. Opus 5 also self-verifies, which means carried-over "double-check your work" instructions now pay twice for the same behavior.
>
> **Opus 4.8 is now legacy**: Anthropic's models-overview page moved `claude-opus-4-8` into the Legacy accordion. Retirement date is unchanged at not sooner than 2027-05-28, and it stays the server-side fallback target for Opus 5 cyber refusals. Opus 5.5 costs 20% less ($4/$20), so there is no cost reason to stay on it. The only reasons to pin it are prompts tuned to that snapshot, needing thinking off (Opus 5 rejects it at `xhigh`/`max`, Opus 5.5 always), or Priority Tier, which Opus 5.5 does not offer.
>
> **Fable 5** (legacy, GA 2026-06-09): Anthropic's Mythos-class tier above Opus at **2.5x Opus 5.5's rates** ($10/$50; 2x legacy Opus 5). Always-on adaptive thinking, no Fast Mode, Batch supported ($5/$25), 30-day data retention required. Safety classifiers can refuse a request (`stop_reason: "refusal"`) -- pre-output refusals are not billed. From a cost standpoint, treat Fable 5 as a deliberate splurge for the hardest tasks, not a default.
>
> **Sonnet 5.5** (released 2026-09-28, `claude-sonnet-5-5`): **$2/$10, the same as Sonnet 5**, with the same cache writes and batch rates, but since 2026-10-07 cache hits cost **$0.10/1M, 0.05x base input (95% off)** -- half Sonnet 5's $0.20; 5m cache write $2.50, 1h cache write $4; Batch $1/$5. 1M context at standard rates, 128K max output (300K on Batch via the `output-300k-2026-03-24` beta), knowledge cutoff Jun 2026, same tokenizer as Sonnet 5 (the same text gives the same token count), minimum cacheable prompt **512** tokens (Sonnet 5: 1,024), tool-use system prompt 286 tokens (Sonnet 5: 354). Adaptive thinking is on by default with default effort `high`; no Fast Mode. Bedrock ID `anthropic.claude-sonnet-5-5`; `claude-sonnet-5-5` on Google Cloud, Microsoft Foundry and Claude Platform on AWS. Earliest retirement not sooner than 2027-09-28. It is the current Sonnet flagship; Anthropic's models overview still says to start with Opus 5.5 for most workloads.
>
> **Cost-relevant breaking changes vs Sonnet 5** (each returns a 400 when old code is carried over):
> - `thinking: {type: "disabled"}` and manual `budget_tokens` return 400. The lowest setting is `thinking: {type: "between_tools"}`, which turns off up-front thinking and is accepted only at `low`, `medium` and `high` effort. Reasoning tokens bill as output at $10/1M.
> - **Effort levels are recalibrated**: the same level does not produce the same amount of thinking as on Sonnet 5, so re-run your effort sweep instead of carrying a setting over. Anthropic's starting points: `high` in general, `medium` for well-specified agentic coding and multistep tool use.
> - Forced `tool_choice` (`any`/`tool`) returns 400 -- use `auto` plus strict tool use or structured outputs. Non-default `temperature`/`top_p`/`top_k` also return 400.
> - Thinking blocks are tied to the model and conversation, so keep conversations append-only: replaying a Sonnet 5.5 thinking block after editing earlier history can return 400. On the Claude API and Google Cloud the `computer_20251124` tool is rejected (use `computer_toolset_20260801`). The advisor tool rejects Opus 4.8, Opus 4.7 and Sonnet 5 as advisors for a Sonnet 5.5 executor.
> - Mid-conversation tool changes (beta), mid-conversation system messages and per-message effort (beta) are supported, which Sonnet 5 does not offer, so tools and instructions can change mid-conversation without losing the prompt cache.
>
> **Sonnet 5** (legacy since the Sonnet 5.5 launch, still Active and not deprecated): **$2/$10 permanently** -- the launch intro rate became standard and the increase to $3/$15 was cancelled. Minimum cacheable prompt 1,024 tokens. Retirement not sooner than 2027-06-30. Sonnet 5.5 replaced it as the Sonnet-tier migration target at the same price. Context window and max output are not restated here -- check the [Anthropic models overview](https://docs.claude.com/en/docs/about-claude/models/overview) before you size a request against them.
>
> **Haiku 5.5** (released 2026-10-07, `claude-haiku-5-5`; Bedrock `anthropic.claude-haiku-5-5`): the current Haiku, for "high-volume, latency-sensitive tasks such as classification, extraction, routing" and subagent work. **The first model priced by prompt length**: **$0.10/$0.50** per 1M when the prompt is at most 100,000 tokens (cache hit $0.01, 5m write $0.125, 1h write $0.20, Batch $0.05/$0.25) and **$0.50/$2.50** above it (cache hit $0.05, 5m write $0.625, 1h write $1.00, Batch $0.25/$1.25). Prompt length counts every input token, cache reads and writes included, and each request is priced on its own: a request over the line pays the higher input and output rates even when part of its prompt is a cache hit. Cache hits are 0.1x of the tier's own input price. The cliff: a 100,000-token prompt costs $0.010 of input, a 100,001-token prompt $0.050. Regional endpoints add 10% as on other current models ($0.11/$0.55 at the lower tier on Bedrock regional). 1M context, 128K max output (300K on Batch via `output-300k-2026-03-24`), minimum cacheable prompt **512** (Haiku 4.5: 4,096), tool-use system prompt 286 tokens (`auto`/`none`) / 406 (`any`/`tool`; forced tool use is supported). It uses the newer Claude 4.7+ tokenizer, so the same text is ~30% more tokens than on Haiku 4.5: per task that is roughly 7.7x cheaper than Haiku 4.5 at <= 100K and ~1.5x cheaper above. Adaptive thinking is on by default at effort `medium`; on the API `thinking: {type: "disabled"}` still works at `high` effort or below, but Claude Code cannot turn it off. No Fast Mode. Knowledge cutoff Jun 2026. Earliest retirement not sooner than 2027-10-07. Breaking changes versus Haiku 4.5 are in [Guide 03](03-model-selection.md#migrating-to-haiku-55).
>
> **Haiku 4.5** is now legacy (still Active, not deprecated; earliest retirement 2026-10-15). **Sonnet 4.5** is deprecated: retirement scheduled for 2026-11-30 on the Claude API, with Sonnet 5.5 the recommended replacement.
>
> **1M context at standard rates**: Fable 5.1, Mythos 5.1, Fable 5, Mythos 5, Opus 5.5, Opus 5, Opus 4.8, Opus 4.7, Opus 4.6, Sonnet 5.5, Sonnet 5, and Sonnet 4.6 bill the full 1M window at the standard per-token rate -- no long-context premium. **Sonnet 5.5 at $2/$10 is the cheapest of them** (legacy Sonnet 5 costs the same per token), so reach for it before an Opus tier on long-context work. Haiku 5.5 also has a 1M window and is cheaper still, but it is the one exception to flat pricing: every request over 100K prompt tokens bills at $0.50/$2.50. (The earlier "2x over 200K" pricing applied to Opus 4.1 and older. Note that Opus 4.5, Sonnet 4.5, and Haiku 4.5 are 200K-only.)
>
> **New tokenizer caveat**: Opus 4.7 and later (including Opus 4.8, Opus 5 and Opus 5.5) use the same Opus-4.7-generation tokenizer, which produces **about 30% more tokens** for the same source text ([Anthropic pricing page](https://platform.claude.com/docs/en/about-claude/pricing): "approximately 30% more tokens for the same text"; the exact increase depends on content). Posted pricing stayed at $5/$25 through Opus 5 (Opus 5.5 cut it to $4/$20), but effective per-task cost is about 30% higher than it would have been on Opus 4.6.
>
> **Subscriptions**: Pro **$20/mo** (or **$200/yr ≈ $16.67/mo** with annual billing -- 16.7% off: $200 vs 12 x $20). Max 5x $100/mo. Max 20x $200/mo. **Batch API**: 50% discount on both input and output. **Cache write**: 1.25x base input price (5-min TTL), 2x base input price (1-hour TTL). Since 2026-10-07 Max 5x and Max 20x include $100 and $200 of monthly Claude API credit (Claude Console API only, **not Claude Code**, no rollover). **Cache hit/refresh**: 0.1x base input price on every model except Fable 5.1 / Mythos 5.1 (0.025x) and Opus 5.5 and Sonnet 5.5 (0.05x). **Regional endpoints** (Bedrock / Vertex AI / Claude API `inference_geo: "us"`, scope = Sonnet 4.5+, Haiku 4.5+, Opus 4.5+, and all future models): +10%.

### Off-Peak 2x Usage Events

Anthropic periodically runs promotional events that **double usage limits** during off-peak hours. Past examples include "Spring Break for Claude Code" (March 2026) which offered 2x limits outside the peak window of **8 AM - 2 PM ET** and on all weekends.

These promotions are **not permanent** -- they come and go. Watch the [Anthropic blog](https://www.anthropic.com/news) and [Claude Code support page](https://support.claude.com) for active promotions. When available, shifting heavy work to off-peak hours effectively **halves your cost per unit of work**. Users in Asia, India, and Australia benefit the most since their entire workday falls outside US peak hours.

### What These Numbers Mean in Practice

To build intuition, here is what $1.00 buys you with each model:

| Model | $1 of Input Tokens | $1 of Output Tokens | $1 of Cached Input |
|-------|:-------------------:|:--------------------:|:------------------:|
| **Fable 5** | ~100,000 tokens (~255 pages) | ~20,000 tokens (~51 pages) | ~1,000,000 tokens (~2,550 pages) |
| **Opus 5.5** | ~250,000 tokens (~640 pages) | ~50,000 tokens (~128 pages) | ~5,000,000 tokens (~12,750 pages) |
| **Opus 5 / 4.8 / 4.7 / 4.6** (legacy) | ~200,000 tokens (~510 pages) | ~40,000 tokens (~102 pages) | ~2,000,000 tokens (~5,100 pages) |
| **Sonnet 5.5** | ~500,000 tokens (~1,275 pages) | ~100,000 tokens (~255 pages) | ~10,000,000 tokens (~25,500 pages) |
| **Sonnet 5** (legacy) | ~500,000 tokens (~1,275 pages) | ~100,000 tokens (~255 pages) | ~5,000,000 tokens (~12,750 pages) |
| **Sonnet 4.6** | ~333,300 tokens (~850 pages) | ~66,700 tokens (~170 pages) | ~3,333,300 tokens (~8,500 pages) |
| **Haiku 5.5**, prompts <= 100K | ~10,000,000 tokens (~25,500 pages) | ~2,000,000 tokens (~5,100 pages) | ~100,000,000 tokens (~255,000 pages) |
| **Haiku 5.5**, prompts > 100K | ~2,000,000 tokens (~5,100 pages) | ~400,000 tokens (~1,020 pages) | ~20,000,000 tokens (~51,000 pages) |
| **Haiku 4.5** (legacy) | ~1,000,000 tokens (~2,560 pages) | ~200,000 tokens (~510 pages) | ~10,000,000 tokens (~25,600 pages) |

> Opus 5.5, 5, 4.8 and 4.7's pages per $1 may be about 23% lower than shown due to the new tokenizer (about 30% more tokens for the same text, so 1 - 1/1.3 = 23% fewer pages). Budget with that in mind if you're migrating from 4.6. Haiku 5.5 uses the same newer tokenizer (~30% more tokens than Haiku 4.5 for the same text), so its pages per $1 run about 23% below what its token counts suggest.
>
> On Opus 5.5 (thinking always on) and Opus 5 (thinking on by default), part of that output budget goes to reasoning tokens you never read. They bill at the same output rate as visible text: $20/1M on Opus 5.5, $25/1M on Opus 5.

> **Critical insight**: Output tokens cost **5x more** than input tokens across all models. This is why strategies that reduce Claude's output (Plan Mode, concise instructions) are high-leverage.

### Model Cost Comparisons

Relative to Opus 5.5 (the recommended default Opus; legacy Opus 5 / 4.8 / 4.7 / 4.6 / 4.5 share a $5/$25 base rate). Sonnet 5.5 and legacy Sonnet 5 share $2/$10, so every Sonnet 5.5 ratio below also holds for Sonnet 5. Fable 5.1 sits above the whole ladder at 2.5x Opus 5.5:

| Comparison | Input Savings | Output Savings |
|------------|:------------:|:--------------:|
| Opus 5.5 vs Fable 5.1 | **2.5x cheaper** | **2.5x cheaper** |
| Opus 5.5 vs legacy Opus 5 | **20% cheaper** | **20% cheaper** |
| Sonnet 5.5 vs Opus 5.5 | **2x cheaper** | **2x cheaper** |
| Sonnet 5.5 vs legacy Opus 5 | **2.5x cheaper** | **2.5x cheaper** |
| Haiku 5.5 vs Opus 5.5, prompt <= 100K | **40x cheaper** | **40x cheaper** |
| Haiku 5.5 vs Opus 5.5, prompt > 100K | **8x cheaper** | **8x cheaper** |
| Haiku 5.5 vs Sonnet 5.5, prompt <= 100K | **20x cheaper** | **20x cheaper** |
| Haiku 5.5 vs Sonnet 5.5, prompt > 100K | **4x cheaper** | **4x cheaper** |
| Haiku 5.5 vs Fable 5.1, prompt <= 100K | **100x cheaper** | **100x cheaper** |
| Haiku 5.5 vs legacy Haiku 4.5, prompt <= 100K | **10x cheaper** per token (~7.7x per task) | **10x cheaper** per token (~7.7x per task) |
| Haiku 5.5 vs legacy Haiku 4.5, prompt > 100K | **2x cheaper** per token (~1.5x per task) | **2x cheaper** per token (~1.5x per task) |
| Legacy Haiku 4.5 vs Opus 5.5 | 4x cheaper | 4x cheaper |

Haiku 5.5, Sonnet 5.5 and Opus 5.5 share a tokenizer, so those per-token ratios are also per-task ratios. Against Haiku 4.5 the same text is ~30% more tokens on Haiku 5.5, which is where 7.7x (10 / 1.3) and 1.5x (2 / 1.3) come from.

Switching from Opus 5.5 to Haiku 5.5 for a task that costs $1.00 on Opus 5.5 would cost approximately $0.025 if every request stays at or under 100K prompt tokens ($0.125 if they are all above), and $0.25 on legacy Haiku 4.5. The same task on Sonnet 5.5 would cost about $0.50.

> **Note**: Opus 5.5 is priced at $4/$20 -- 20% below the $5/$25 of Opus 5 / 4.8 / 4.7 / 4.6. The gap between Opus and Sonnet is much smaller than it used to be. At the bottom of the ladder Haiku 5.5 widens it again: 40x below Opus 5.5 per token while a prompt stays at or under 100K tokens (8x above), versus 4x for legacy Haiku 4.5 and the historical 19x. The new tokenizer (Opus 4.7 and later, including Opus 5.5) narrows the "effective" gap slightly further -- budget about 30% higher than the posted rate suggests against pre-4.7 models (Anthropic pricing page). Sonnet 5's $2/$10 is now permanent and Sonnet 5.5 launched at the same rate, so the Sonnet-vs-Opus gap is a durable **2x** against Opus 5.5 (2.5x against legacy Opus 5), not the 1.67x of Sonnet 4.6 vs Opus 5.

### Long Context Pricing (1M)

Fable 5.1, Mythos 5.1, Fable 5, Mythos 5, Opus 5.5, Opus 5, Opus 4.8, Opus 4.7, Opus 4.6, Sonnet 5.5, Sonnet 5, and Sonnet 4.6 support up to 1M tokens of context at **standard rates** across the full window. There is no longer a "2x over 200K" premium -- that pricing applied to Opus 4.1 and older. Sonnet 5.5 and legacy Sonnet 5 ($2/$10) are the cheapest models on that list by a wide margin.

| Model | Input Rate (any context size) | Output Rate (any context size) | Max Context |
|-------|:-----------------------------:|:------------------------------:|:-----------:|
| **Fable 5.1** | $10.00 | $50.00 | 1M |
| **Fable 5** | $10.00 | $50.00 | 1M |
| **Opus 5.5** | $4.00 | $20.00 | 1M |
| **Opus 5** (legacy) | $5.00 | $25.00 | 1M |
| **Opus 4.8** | $5.00 | $25.00 | 1M |
| **Opus 4.7** | $5.00 | $25.00 | 1M |
| **Opus 4.6** | $5.00 | $25.00 | 1M |
| **Sonnet 5.5** | $2.00 | $10.00 | 1M |
| **Sonnet 4.6** | $3.00 | $15.00 | 1M |
| **Haiku 4.5** (legacy) | $1.00 | $5.00 | 200K |

Legacy Sonnet 5 is priced at $2/$10 with no long-context premium either; its exact maximum window is not restated here.

On the models in that table, a 900K-token request is billed at the same per-token rate as a 9K-token request. You still pay for each token, so context growth still costs more in absolute dollars -- but there is no rate cliff at 200K anymore.

**Haiku 5.5 is the exception.** It has a 1M window, but it is the one model from Claude 4.6 on that does not bill the whole window at one rate:

| Haiku 5.5 prompt length | Input | Output | Cache hit | Max Context |
|-------------------------|:-----:|:------:|:---------:|:-----------:|
| <= 100,000 tokens | $0.10 | $0.50 | $0.01 | 1M |
| > 100,000 tokens | $0.50 | $2.50 | $0.05 | 1M |

Prompt length counts all input tokens, including cache reads and writes, and each request is priced on its own: a request over 100K pays the higher input **and** output rates for the whole request, not just the tokens past the line. A 100,000-token prompt costs $0.010 of input; a 100,001-token prompt costs $0.050.

> **Practical implication**: Sending a 300K-token input on Opus 5.5 costs $1.20 at the $4/1M rate ($1.50 on legacy Opus 5 at $5/1M). Under the old pricing, the Opus 5 request would have been $3.00 (entire request at the 2x rate). Long agentic sessions, large-codebase audits, and big-document analysis are now significantly cheaper. On Haiku 5.5 the same 300K input costs $0.15, all of it at the > 100K rate of $0.50/1M.

> **AWS Bedrock / Vertex AI**: Claude models are available on AWS Bedrock and Google Vertex AI at the same pricing for global (cross-region) inference. Regional inference profiles carry a **+10% surcharge** over the standard API rates.

### Fast Mode Pricing

Fast Mode is a beta (research preview) feature available for **Claude Opus 5.5, Opus 5 and Opus 4.8 only** (`claude-opus-5-5`, `claude-opus-5`, `claude-opus-4-8`). Same model weights, same intelligence -- just faster output token generation at premium pricing. All three supported models run at **2x** their own standard rates; the old 6x tier no longer exists. [Join the waitlist](https://claude.com/fast-mode).

| | Input (per 1M) | Output (per 1M) | Multiplier vs Standard |
|---|:---:|:---:|:---:|
| **Standard Opus 5.5** | $4.00 | $20.00 | 1x |
| **Fast Mode Opus 5.5** | $8.00 | $40.00 | **2x** |
| **Standard Opus 5 / 4.8 / 4.7 / 4.6** | $5.00 | $25.00 | 1x |
| **Fast Mode Opus 5** | $10.00 | $50.00 | **2x** |
| **Fast Mode Opus 4.8** | $10.00 | $50.00 | **2x** |
| **Opus 4.7 with `speed: "fast"`** | -- | -- | **error, no fallback** |
| **Opus 4.6 with `speed: "fast"`** | $5.00 | $25.00 | silently 1x (standard speed) |

Key details about Fast Mode:

- **Same model, faster output**: Fast Mode runs the same model with a faster inference configuration. Same weights, same behavior -- only the runtime is different.
- **Up to 2.5x output tokens/second**: The speed gain is on output tokens per second (OTPS), **not** time-to-first-token (TTFT). If you're optimizing for TTFT, Fast Mode does not help.
- **1M context included**: Fast Mode is priced at the 2x multiplier across the full context window, including requests over 200K input tokens. No additional 2x long-context multiplier stacked on top.
- **Cache stacks on top**: Prompt-caching multipliers (1.25x 5m write, 2x 1h write, and the model's hit multiplier: 0.1x on Opus 5 / 4.8, 0.05x on Opus 5.5) apply to Fast Mode rates. So a Fast Mode Opus 5 5m cache write costs $10 × 1.25 = $12.50 / MTok, and a Fast Mode Opus 5 cache hit costs $10 × 0.1 = $1.00 / MTok.
- **Switching invalidates cache**: Fast and Standard speeds do not share cached prefixes. If you toggle speeds mid-conversation, you'll pay a full cache-write cost again.
- **Opus 4.7 now errors**: `speed: "fast"` on Opus 4.7 returns an error, with **no fallback** to standard speed. The request fails outright.
- **Opus 4.6 silently degrades**: `speed: "fast"` on Opus 4.6 runs at standard speed and standard rates. No error is raised; `usage.speed` comes back `"standard"`. You do not overpay, but you also do not get the speedup, so check the field rather than assuming.
- **Fast Mode surface**: Claude API + Managed Agents only. Not available on Bedrock, Vertex AI, Microsoft Foundry, Claude Platform on AWS, the Batch API, or Priority Tier.
- **Not available with Batch API**: 50% batch discount cannot be combined with Fast Mode.
- **Not available with Priority Tier**: Fast Mode and Priority Tier are mutually exclusive.
- **Not available on Claude Platform on AWS**: First-party API only.
- **Activation**: Set `speed: "fast"` in your request and include the `anthropic-beta: fast-mode-2026-02-01` header.
- **Dedicated rate limits**: Fast Mode has its own rate limit pool separate from Standard Opus. Headers like `anthropic-fast-output-tokens-remaining` track it.
- **Use case**: Time-sensitive tasks where latency directly impacts revenue or user experience -- urgent debugging, live demos, real-time agentic loops. Almost never worth it for routine interactive coding.

On Opus 5.5 at 2x its standard rate, the [worked 30-turn session](#worked-example-cost-of-a-30-turn-session) below would go from $1.21 on standard Opus 5.5 to **$2.43** on Fast Mode (legacy Opus 5: $1.89 standard, $3.77 Fast); the cache multipliers apply to the Fast rates, so the whole bill doubles. Use it deliberately and sparingly.

---

## What Counts as Tokens in Claude Code

Every turn in Claude Code involves sending input tokens and receiving output tokens. Understanding exactly what constitutes each is the foundation of cost optimization.

### Input Tokens (You Pay For These Every Turn)

```
Input Token Composition Per Turn
================================

1. System Prompt                          ~3,500 tokens (fixed)
   └── Claude Code's built-in instructions for how to behave,
       use tools, format responses, etc. You cannot change this.
       3,500 is this repo's modelling assumption; the real prompt
       plus tool definitions varies by Claude Code version.

2. CLAUDE.md Contents                     ~10 tokens/line (variable)
   └── Your project's CLAUDE.md file is injected in full on every
       single turn. A 150-line file adds ~1,500 tokens per turn.
       A 500-line file adds ~5,000 tokens per turn.

3. Conversation History                   Grows each turn
   └── Every previous user message and Claude response in the
       current session. This is the #1 driver of cost growth.
       In the worked example below (3,300 tokens added per turn):
       Turn 1: 0 tokens of history
       Turn 10: 29,700 tokens of history (9 x 3,300)
       Turn 30: 95,700 tokens of history (29 x 3,300)

4. Tool Results                           Varies widely
   └── File contents from Read tool:      ~10 tokens/line of code
       Grep/Glob search results:          only the matching lines
       Bash command output:               the whole output, unless a
                                          hook filters it
       Edit tool confirmations:           a short confirmation
       MCP server responses:              Varies
       (The worked example assumes 2,500 tokens of tool results per turn.)

5. User's Current Message                 Usually small
   └── Your prompt for the current turn:  ~100 tokens in the worked example
```

### Output Tokens (You Pay 5x More For These)

```
Output Token Composition Per Turn
=================================

1. Claude's Text Response                 ~400 tokens in the worked example
   └── Explanations, analysis, questions back to you

2. Tool Calls                             ~300 tokens per turn in the worked example
   └── Read, Edit, Bash, Write, Glob, Grep -- each tool call
       includes the tool name and all parameters

3. Code Generation                        ~10 tokens/line
   └── New code written via Edit or Write tools

4. Plan Mode Analysis                     Ordinary output, length set by the task
   └── Structured thinking and planning output

5. Extended Thinking / Reasoning           Varies with effort level
   └── On Opus 5.5 thinking is ALWAYS ON and cannot be
       disabled; effort is the only control. Reasoning tokens
       bill as OUTPUT at $20/1M even though you never read most
       of them. Effort levels are low/medium/high/xhigh/max,
       default `medium`. (Legacy Opus 5: thinking on by default,
       effort default `high`, output $25/1M.)
```

> **Opus 5.5 / Opus 5 `max_tokens` trap**: `max_tokens` is a hard cap on thinking **plus** text. Carry over a small `max_tokens` from an older setup and thinking can consume the whole budget before the answer is written -- you pay for the turn and get no usable output. `max_tokens` is a backstop, not a cost knob: on Anthropic's internal repository-task benchmark a 16,384-token cap ended about a quarter of Opus 5.5's attempts and 43% of Fable 5.1's, and the guidance is 64,000 for agentic work, or 128,000 when a cut-off attempt is costly ([cost-optimization guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence)). "Just turn thinking off" is not available on Opus 5.5 at all (`thinking: {type: "disabled"}` returns 400), and on legacy Opus 5 only at effort `high` or below.

### The Hidden Multiplier: Conversation History

This is the most important concept in Claude Code cost optimization.

**Conversation history is cumulative.** Every message -- yours and Claude's -- becomes part of the input for the next turn. This means:

- **Turn 1**: You send your prompt + system context. Claude responds.
- **Turn 2**: You send your prompt + system context + Turn 1's full exchange. Claude responds.
- **Turn 3**: You send your prompt + system context + Turn 1 + Turn 2. Claude responds.
- **Turn N**: You send your prompt + system context + all previous N-1 turns.

The cost **accelerates** with each turn. A 30-turn session does not cost 30x a single turn -- it costs more because each turn includes all previous turns as input. In the [worked example](#worked-example-cost-of-a-30-turn-session) below, 30 Sonnet 4.6 turns cost 42x the first turn with a warm cache ($1.13 vs $0.027) and 185x with caching off ($5.02). Claude Code bills the re-sent history as a cache read ("re-reads that history at the cached token rate", per its [costs page](https://code.claude.com/docs/en/costs)), which is why the warm-cache multiple is so much smaller.

---

## The Context Window and Its Cost Impact

### How the Context Window Works

Claude's context window (1M tokens for Opus 5.5, Opus 5, Opus 4.8, Opus 4.7, Opus 4.6, Sonnet 5.5, Sonnet 4.6, and Haiku 5.5; 200K for legacy Haiku 4.5) is the maximum amount of text it can process in a single turn. Think of it as Claude's working memory.

```
Context Window (1M tokens for Opus/Sonnet/Haiku 5.5, 200K for Haiku 4.5)
┌─────────────────────────────────────────────────────┐
│ System Prompt          (~3,500 tokens)              │
│ CLAUDE.md              (~1,500 tokens @ 150 lines)  │
│ Conversation History   (grows each turn)            │
│ Current Tool Results   (varies)                     │
│ Your Current Message   (~100 tokens)                │
│                                                     │
│ [Remaining capacity for Claude's response]          │
└─────────────────────────────────────────────────────┘
```

### What Happens When Context Fills Up

As your session progresses, the context window fills with conversation history. When it approaches the limit:

1. **Claude Code auto-compacts**: it summarizes older conversation history when the context nears its limit, at about 967K tokens by default on 1M-window models; `/autocompact` moves that point anywhere from 100K to 1M and saves it per model since v2.1.288 ([model-config page](https://code.claude.com/docs/en/model-config), [changelog](https://code.claude.com/docs/en/changelog)). Details are lost, and the summary request itself costs tokens
2. This can cause Claude to "forget" earlier context and decisions
3. You pay for a very large number of input tokens per turn at this point
4. Quality degrades because Claude loses important context

### Context Window Cost at Capacity

What it costs to fill the context window on a single turn:

| Model | Full 200K Input Cost (per turn) | Full 1M Input Cost (per turn) | Max Output Cost (if maxed) |
|-------|:-------------------------------:|:-----------------------------:|:--------------------------:|
| Opus 5.5 | $0.80 | $4.00 (flat rate, no 200K premium) | $2.56 (128K output) |
| Opus 5 / 4.8 / 4.7 / 4.6 (legacy) | $1.00 | $5.00 (flat rate, no 200K premium) | $3.20 (128K output) |
| Sonnet 5.5 | $0.40 | $2.00 (flat rate, no 200K premium) | $1.28 (128K output) |
| Sonnet 4.6 | $0.60 | $3.00 (flat rate, no 200K premium) | $0.96 (64K output) |
| Haiku 5.5 | $0.10 (> 100K rate) | $0.50 (> 100K rate) | $0.32 (128K output at the > 100K rate) |
| Haiku 4.5 (legacy) | $0.20 | N/A (200K max) | $0.32 (64K output) |

> A 100-turn Opus 5.5 session in the worked example's token mix costs $6.35 with a warm cache all the way (computed with the formula in [Key Formulas](#estimated-session-cost); its last prompt is 331K tokens), and every cache miss at that size re-writes the context for $1.66 (331K x $5/1M). On Opus 5.5 / 5 / 4.8 / 4.7 / 4.6, Sonnet 5.5, Sonnet 5, and Sonnet 4.6 there is no 200K rate cliff -- the full 1M window bills at the standard per-token rate -- but absolute dollars still climb as context grows. Haiku 5.5 has its cliff at 100K instead: a full 200K or 1M prompt bills every input and output token at $0.50/$2.50, 5x its rate below the line.
>
> On Opus 5.5 and Opus 5 the 128K max-output figure covers thinking **plus** visible text, since `max_tokens` caps both together. Reasoning tokens bill as output ($20/1M on Opus 5.5, $25/1M on Opus 5), so a max-output turn can be mostly thinking you never see. (Batch raises the ceiling to 300K via the `output-300k-2026-03-24` beta.)

### Practical Rule of Thumb

| Context size | Cache read per turn (Opus 5.5 / Sonnet 5.5) | Re-write after a cache miss (Opus 5.5) | Action |
|:-:|---|---|---|
| Up to 100K | $0.02 / $0.01 at 100K | $0.50 | Normal; Haiku 5.5 stays in its $0.10 tier |
| 100K-200K | $0.04 / $0.02 at 200K | $1.00 | Haiku 5.5 now bills 5x; `/compact` at the next break |
| 200K-500K | $0.10 / $0.05 at 500K | $2.50 | `/compact` or `/clear` at the next break |
| 500K-967K | $0.19 / $0.10 at 967K | $4.84 | Auto-compact fires at about 967K on 1M-window models |

> Computed from the [Anthropic pricing page](https://platform.claude.com/docs/en/about-claude/pricing): a warm turn reads the context at $0.20/1M (Opus 5.5) or $0.10/1M (Sonnet 5.5); a turn after a pause longer than the cache TTL re-writes it at the 5-minute write rate, $5/1M on Opus 5.5. The 967K auto-compact point is from Claude Code's [model-config page](https://code.claude.com/docs/en/model-config).

---

## Prompt Caching: Your Biggest Automatic Discount

Prompt caching is the single most impactful automatic cost reduction in Claude Code. Understanding it helps you avoid accidentally breaking it.

### How Prompt Caching Works

When you send a request to Claude, the API checks if the beginning of your input matches a recently cached prompt prefix. If it does, those cached tokens are charged at a steep discount. There are three cache-hit multipliers: **0.1x base input (90% off)** on most models, **0.05x (95% off)** on Opus 5.5 and Sonnet 5.5, and **0.025x (97.5% off)** on Fable 5.1 and Mythos 5.1. Haiku 5.5 reads at 0.1x of whichever price tier the request falls in ($0.01 or $0.05).

```
Normal input cost:   $3.00 / 1M tokens (Sonnet 4.6)
Cached input cost:   $0.30 / 1M tokens (Sonnet 4.6) -- 90% cheaper

Normal input cost:   $4.00 / 1M tokens (Opus 5.5)
Cached input cost:   $0.20 / 1M tokens (Opus 5.5)   -- 95% cheaper
```

### What Gets Cached

Claude Code structures each request so that **stable content comes first** in the prompt:

```
Request Structure (simplified)
┌──────────────────────────────────────────┐
│ 1. System Prompt        ← CACHE READ     │  Everything the previous
│ 2. CLAUDE.md            ← CACHE READ     │  request sent is read
│ 3. Earlier History      ← CACHE READ     │  from cache (0.1x input)
│────────────────────────────────────────── │
│ 4. New Exchange         ← CACHE WRITE    │  New since that request:
│ 5. Current Message      ← CACHE WRITE    │  written at 1.25x input
└──────────────────────────────────────────┘
```

On Turn 10 of the [worked example](#worked-example-cost-of-a-30-turn-session) below:
- Tokens 1-30,840 (system + CLAUDE.md + everything turn 9's request sent): **cache read at the model's hit rate (0.1x input on Sonnet 4.6, 0.05x on Opus 5.5 and Sonnet 5.5)**
- Tokens 30,841-34,140 (turn 9's response and tool results, plus the new message): **cache write at 1.25x input** (5-minute TTL), so the next turn reads them

That is how Claude Code bills a session: each request reads the whole previous request from cache and writes only what is new ([prompt-caching page](https://code.claude.com/docs/en/prompt-caching)).

### Minimum Cacheable Prompt Length

A prefix has to clear a per-model token floor before it can be cached at all. A `cache_control` block below the threshold is **silently ignored** -- no error, no discount, and nothing in the response tells you it did not take.

| Model | Minimum cacheable prompt (tokens) |
|-------|:---------------------------------:|
| **Opus 5.5** | 512 |
| **Opus 5** | 512 |
| **Opus 4.8** | 1,024 |
| **Opus 4.7** | 2,048 |
| **Opus 4.6** | 4,096 |
| **Opus 4.5** | 4,096 |
| **Opus 4.1** | 1,024 |
| **Fable 5.1 / Mythos 5.1** | 512 |
| **Fable 5** | 512 |
| **Mythos 5** | 512 |
| **Mythos Preview** (deprecated) | 2,048 |
| **Sonnet 5.5** | 512 |
| **Sonnet 5** | 1,024 |
| **Sonnet 4.6** | 1,024 |
| **Sonnet 4.5** (deprecated) | 1,024 |
| **Haiku 5.5** | 512 |
| **Haiku 4.5** (legacy) | 4,096 |

Opus 5.5 and Opus 5 share the lowest Opus-tier floor at 512 tokens, half of Opus 4.8's 1,024 and a quarter of Opus 4.7's 2,048. Short system prompts and small CLAUDE.md files that were too small to cache on older Opus models now qualify on Opus 5.5 and Opus 5. Sonnet 5.5 halves the Sonnet floor the same way, to 512 from Sonnet 5's 1,024, so short system prompts that never cached on Sonnet 5 now do. Haiku 5.5 cuts the Haiku floor 8x, to 512 from Haiku 4.5's 4,096, so short classification and subagent prompts now cache too.

### Cache Savings in Practice

For the 30-turn Sonnet 4.6 session in the [worked example](#worked-example-cost-of-a-30-turn-session) (84-line CLAUDE.md), input only:

| Component | Tokens over 30 turns | Without Cache | With Cache | Savings |
|-----------|:--------------------:|:-------------:|:----------:|:-------:|
| System prompt (3,500 every turn) | 105,000 | $0.315 | $0.044 | $0.271 |
| CLAUDE.md (840 every turn) | 25,200 | $0.076 | $0.011 | $0.065 |
| Conversation (messages, responses, tool results) | 1,438,500 | $4.316 | $0.762 | $3.554 |
| **Total input** | **1,568,700** | **$4.71** | **$0.82** | **$3.89** |

> Computed: without cache every token bills at $3/1M. With cache each token is written once at $3.75/1M (1.25x) and read at $0.30/1M (0.1x) on every later turn: the system prompt is 3,500 x ($3.75 + 29 x $0.30) / 1M = $0.044. Caching takes 83% off the input bill; output ($0.315) is the same either way.

### What Breaks the Cache

The cache is prefix-based -- it works from the beginning of the prompt forward. If anything changes in the cached prefix, **everything after the change point loses its cache**. Common cache-breakers:

| Action | Cache Impact | Severity |
|--------|-------------|:--------:|
| Editing CLAUDE.md mid-session | Does **not** invalidate the cache. The edit also does not apply until the next `/clear`, `/compact`, or restart, because root and user CLAUDE.md are read once at session start | NONE |
| Normal conversation progression | Only new content is uncached (expected and fine) | LOW |
| Switching models mid-session | Complete cache miss (different model = different cache) | HIGH |
| Changing effort level | Invalidates the cache, except on Opus 5.5 and Fable 5.1 with an API key or subscription, where effort changes keep it | HIGH (NONE on Opus 5.5 / Fable 5.1) |
| Gap between turns longer than the TTL | Cache expires. In Claude Code the main conversation gets a **one-hour** TTL on a Claude subscription within plan usage (subagents, workflows and compaction get five minutes); on an API key, a cloud provider, or usage credits it is **five minutes**. Set it with `promptCacheTtl` or `CLAUDE_CODE_PROMPT_CACHE_TTL` (`5m` or `1h`; subagents via `subagentPromptCacheTtl`), Claude Code v2.1.242+ | MEDIUM |
| Adding/removing MCP servers (or a plugin that provides them) | Invalidates the cache **only when MCP tool search is off**. Tool search is on by default, and then connecting or removing a server keeps the cache | HIGH with tool search off, NONE by default |
| Denying an entire tool | Invalidates the cache only when tool search is off. Scoped rules such as `Read(./dist/**)` never do | HIGH with tool search off, NONE by default |
| Compaction (`/compact`) | Rebuilds the conversation layer, so history is cached again from the summary | MEDIUM |
| Accumulating many images, or upgrading Claude Code | Each invalidates the cache | MEDIUM |
| Changing tool definitions mid-conversation | Historically a full cache bust. On Opus 5, the `mid-conversation-tool-changes-2026-07-01` beta lets tool definitions change between turns **without** invalidating the cache. Sonnet 5.5 supports mid-conversation tool changes (beta) too; Sonnet 5 does not | HIGH without the beta, LOW with it |
| Toggling Fast Mode mid-session | Fast and Standard speeds do not share cached prefixes | HIGH |
| Prefix below the model's minimum cacheable length | Nothing is cached at all, silently (see the table above) | HIGH |

Actions that **keep** the cache in Claude Code: editing repo files, editing CLAUDE.md mid-session, changing permission mode, changing output style, invoking skills or commands, `/recap`, `/rewind`, and spawning a subagent. To see how the cache is doing, `/usage` shows a `Prompt cache (main)` line with hit share, misses, the likely cause, and whether the cache is warm or cold (v2.1.251+).

### Rules for Maximizing Cache Hits

1. **Edit CLAUDE.md whenever you like, but expect a delay.** A mid-session edit keeps the cache, and it also does not take effect until the next `/clear`, `/compact`, or restart.
2. **Keep sessions focused.** Linear conversations cache better than branching ones.
3. **Avoid switching models or effort mid-session** unless the savings from a cheaper setting outweigh the cache loss. Effort changes are free on Opus 5.5 and Fable 5.1 (API key or subscription).
4. **Know your TTL.** A pause longer than the TTL expires the cache: one hour for the main conversation on a subscription within plan usage, five minutes on an API key, a cloud provider, or usage credits. Pick it yourself with `promptCacheTtl` (`5m` or `1h`).
5. **Compact while the cache is warm.** `/compact` sends a summarization request that reads the prefix from cache while warm, so it costs a fraction of the context size; after a break longer than the TTL it reprocesses the full history uncached. `/clear` costs nothing, and `/rewind` returns to an already-cached prefix.
6. **Check your prefix clears the model's floor.** Below the minimum cacheable length there is no discount and no warning. Opus 5.5 and Opus 5 share the most forgiving Opus-tier floor, 512 tokens, and Sonnet 5.5 and Haiku 5.5 match it (1,024 on Sonnet 5, Sonnet 4.6 and Sonnet 4.5; 4,096 on legacy Haiku 4.5).
7. **Leave MCP tool search on.** It is the default, and with it on, connecting or removing an MCP server keeps the cache.

---

## Tracking Your Costs

### The `/usage` Command

Run `/usage` at any point during a Claude Code session to see:

- A Session block with the total cost so far
- A plan usage breakdown, attributed to skills, subagents, plugins, and MCP servers
- A `Prompt cache (main)` line: hit share, misses, likely cause, and warm/cold state (v2.1.251+)

`/insights` complements it with a report on how you work.

```
> /usage

Session Usage:
  Input tokens:  47,832  (~$0.14 at Sonnet pricing)
  Output tokens: 12,451  (~$0.19 at Sonnet pricing)
  Cache hits:    38,200  (saved ~$0.10)
  Total cost:    ~$0.23
  Turns:         15
```

Use `/usage` as a habit check -- run it every 10 turns or so to see if your session is staying within expected bounds.

### What Normal Spend Looks Like

For a baseline, Anthropic's Claude Code costs page puts the enterprise average at about **$13 per developer per active day** and **$150-250 per developer per month**, with 90% of users under $30 per active day. Background token usage is typically under $0.04 per session. If your numbers sit well above that range, start with [Why Sessions Get Expensive](#why-sessions-get-expensive).

Usage can also climb without new prompts from you. Prompt suggestions send a request after each response (mostly cache reads; you can turn them off), and an idle session still spends on scheduled `/loop` tasks, cross-session messages and goal check-ins (at most 3 idle check-ins per goal since v2.1.246; `CLAUDE_CODE_GOAL_CHECKIN_MINUTES=0` turns them off). `/usage` flags any behavior that accounts for 10% or more of your recent usage ([Claude Code costs page](https://code.claude.com/docs/en/costs)).

### The `--max-budget-usd` Flag (Print Mode Only)

`--max-budget-usd` caps what one non-interactive run can spend. It works only with `-p` (print mode); an interactive `claude` session does not enforce it. Spend from subagents counts toward the cap:

```bash
# Cap a scripted run at $5
claude -p --max-budget-usd 5 "fix the failing lint errors"

# Cap a quick task at $1, and its turns too (--max-turns is also print mode only)
claude -p --max-budget-usd 1 --max-turns 10 "summarize the changes on this branch"

# Cap complex feature work at $20
claude -p --max-budget-usd 20 "implement the export endpoint described in docs/export.md"
```

When the cap is reached, the run stops. This prevents runaway runs -- especially important when:

- Running automated workflows (CI, cron, scripts)
- Delegating Claude Code usage to team members through scripts
- Working on tasks that might spiral into unexpected complexity

Interactive sessions have no per-session dollar cap. Watch `/usage`, set a Console workspace spend limit (API key) or a usage-credits spend limit (subscription), or use a PreToolUse budget hook such as [hooks/budget-tracker.sh](../hooks/budget-tracker.sh).

### Recommended Budget Caps by Task Type

The caps below are for `claude -p --max-budget-usd` runs, or as the threshold for a budget hook in interactive work. They are illustrative caps, not measured:

| Task Type | Suggested Cap | Model |
|-----------|:------------:|:-----:|
| Quick bug fix | $2 | Haiku/Sonnet |
| Feature implementation | $7 | Sonnet |
| Complex refactor | $15 | Sonnet/Opus |
| Architecture exploration | $7 | Opus (Plan Mode) |
| Code review | $3 | Sonnet |
| Generating boilerplate | $2 | Haiku |

For scale (computed with the [worked example](#worked-example-cost-of-a-30-turn-session)'s token mix): a 30-turn session is $1.21 on Opus 5.5 and $0.61 on Sonnet 5.5, and a 100-turn Opus 5.5 session is $6.35, so these caps stop runaway runs rather than normal ones.

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

- CLAUDE.md: 84 lines (~840 tokens at 10 tokens per line)
- System prompt: ~3,500 tokens
- Average user message: ~100 tokens
- Average Claude response: ~400 tokens of text + ~300 tokens of tool calls = ~700 output tokens
- Average tool results per turn: ~2,500 tokens (file reads, command outputs)
- So each turn adds **3,300 tokens** to the next request (700 response + 2,500 tool results + 100 next message), and turn N's prompt is 4,440 + (N - 1) x 3,300 tokens
- Prompt caching billed the way Claude Code does it: each request reads the whole previous request from cache (0.1x input on Sonnet 4.6) and writes only what is new (1.25x input, 5-minute TTL), with no pause longer than the TTL. That reads 94% of all input from cache, close to the upper quartile Anthropic measured for coding agent loops (median 88.5%, upper quartile 93.4%, [cost-optimization guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence))

### Turn-by-Turn Cost Calculation

**Turn 1 (no history yet)**

```
Input tokens:
  System prompt:       3,500
  CLAUDE.md:             840
  User message:          100
  ─────────────────────────
  Total input:         4,440 tokens

  Cache read:              0  (first turn, nothing cached yet)
  Cache write:         4,440  (the whole prompt, so turn 2 can read it)

Input cost:  4,440 / 1,000,000 x $3.75  = $0.01665
Output cost: 700 / 1,000,000 x $15.00   = $0.01050
─────────────────────────────────────────────────────
Turn 1 total: $0.027
```

**Turn 5 (some history accumulated)**

```
Input tokens:
  System prompt:       3,500
  CLAUDE.md:             840
  Turns 1-4 history:  13,200  (4 x 3,300)
  User message:          100
  ─────────────────────────
  Total input:        17,640 tokens

  Cache read:         14,340  @ $0.30/1M = $0.00430  (all of turn 4's request)
  Cache write:         3,300  @ $3.75/1M = $0.01238  (turn 4's response and tool results + this message)
  Total input cost:                        $0.01668
  Output cost: 700 / 1,000,000 x $15.00 = $0.01050
  ────────────────────────────────────────────────────
  Turn 5 total: $0.027
```

**Turn 15 (mid-session)**

```
Input tokens:
  System prompt:       3,500
  CLAUDE.md:             840
  Turns 1-14 history: 46,200  (14 x 3,300)
  User message:          100
  ─────────────────────────
  Total input:        50,640 tokens

  Cache read:         47,340  @ $0.30/1M = $0.01420
  Cache write:         3,300  @ $3.75/1M = $0.01238
  Total input cost:                        $0.02658
  Output cost: 700 / 1,000,000 x $15.00 = $0.01050
  ────────────────────────────────────────────────────
  Turn 15 total: $0.037
```

**Turn 30 (end of session)**

```
Input tokens:
  System prompt:       3,500
  CLAUDE.md:             840
  Turns 1-29 history: 95,700  (29 x 3,300)
  User message:          100
  ─────────────────────────
  Total input:       100,140 tokens

  Cache read:         96,840  @ $0.30/1M = $0.02905
  Cache write:         3,300  @ $3.75/1M = $0.01238
  Total input cost:                        $0.04143
  Output cost: 700 / 1,000,000 x $15.00 = $0.01050
  ────────────────────────────────────────────────────
  Turn 30 total: $0.052
```

Turn number t (from turn 2 on) costs $0.024207 + $0.00099 x (t - 2): the cache write ($0.01238) and output ($0.01050) are fixed, and the cache read grows by 3,300 x $0.30/1M = $0.00099 per turn.

### Total Session Cost Summary

| Phase | Turns | Approx Cost | Notes |
|-------|:-----:|:-----------:|-------|
| Planning | 1-3 | $0.08 | Turn 1 writes the whole prompt to cache at 1.25x |
| Implementation | 4-10 | $0.20 | Each turn reads the previous request and writes 3,300 new tokens |
| Writing tests | 11-18 | $0.29 | Cache reads grow with the history |
| Bug fixing | 19-25 | $0.31 | Large context, still read at 0.1x |
| Cleanup | 26-30 | $0.25 | Near-peak context size |
| **Total** | **30** | **~$1.13** | **With prompt caching** |

> Computed with the closed form in [Key Formulas](#estimated-session-cost): 100,140 tokens written x $3.75/1M + 1,468,560 read x $0.30/1M + 21,000 output x $15/1M = $0.376 + $0.441 + $0.315 = $1.13.

### What This Same Session Would Cost Without Caching

Without prompt caching, every input token is charged at full price ($3/1M on all 1,568,700 input tokens):

| Turn Range | With Caching | Without Caching |
|:----------:|:------------:|:---------------:|
| Turns 1-10 | $0.28 | $0.68 |
| Turns 11-20 | $0.38 | $1.67 |
| Turns 21-30 | $0.47 | $2.66 |
| **Total** | **$1.13** | **$5.02** |

> Prompt caching saved **$3.89** on this session -- a **77% reduction** (computed: 1 - $1.13 / $5.02), and 83% of the input cost. Rows are rounded; totals are exact sums. On Anthropic's own benchmarks caching cut agent-loop cost by a factor of 2.7 to 5.3 ([cost-optimization guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence)). This is why preserving the cache is so important.

### What This Session Would Cost on Different Models

| Model | 30-Turn Session Cost | Monthly (5 sessions/day, 22 days) |
|-------|:--------------------:|:---------------------------------:|
| **Opus 5.5** | ~$1.21 | ~$134 |
| **Opus 5 / 4.8 / 4.7 / 4.6** (legacy) | ~$1.89 | ~$207 |
| **Sonnet 5.5** | ~$0.61 | ~$67 |
| **Sonnet 5** (legacy) | ~$0.75 | ~$83 |
| **Sonnet 4.6** | ~$1.13 | ~$124 |
| **Haiku 5.5** | ~$0.045 | ~$5 |
| **Haiku 4.5** (legacy) | ~$0.38 | ~$41 |

> **Note**: Every row re-prices the same token mix as the Sonnet 4.6 walkthrough (100,140 tokens written to cache, 1,468,560 read from it, 21,000 output) at each model's own 5-minute write, cache-hit and output rates: written x write + read x hit + output x output. Opus 5.5 and Sonnet 5.5 land lowest against their input price because their cache reads cost 0.05x instead of 0.1x, which is also why Sonnet 5.5 undercuts legacy Sonnet 5 on this session. With both reading cache at 0.05x, an Opus 5.5 session is exactly 2x a Sonnet 5.5 session here, the same as the per-token gap. The token counts are pre-4.7-tokenizer counts; models on the Claude 4.7+ tokenizer (every row except Sonnet 4.6, Haiku 4.5 and Opus 4.6) see about 30% more tokens for the same text ([Anthropic pricing page](https://platform.claude.com/docs/en/about-claude/pricing)), so their real sessions run about 30% higher.
>
> Haiku 5.5 is priced per request, so the row has to follow the prompt size turn by turn. Turns 1-29 stay at or under 100K prompt tokens and bill at $0.10/$0.50; turn 30's prompt is 100,140 tokens, so that whole request bills at $0.50/$2.50, which adds about $0.007 to the session. That one turn is the gap between ~$0.038 and ~$0.045, and Haiku 5.5 is still ~27x below Opus 5.5 here. On real Haiku 5.5 traffic the same text is ~30% more tokens than these Sonnet 4.6-era counts, so the prompt would cross 100K around turn 23 instead (4,440 + 22 x 3,300 = 77,040 tokens x 1.3 = 100,152) -- run `/compact` before then to stay in the cheap tier. Haiku 5.5 also keeps the thinking blocks from all earlier assistant turns in context, billed as input (Haiku 4.5 kept only the latest turn's), so a real multi-turn session grows faster than this mix ([Haiku 5.5 what's new](https://platform.claude.com/docs/en/models/haiku-5-5/whats-new-haiku-5-5)).
>
> The Opus figures assume the same output volume as the table's Sonnet baseline. In practice Opus 5.5 always thinks (default effort `medium`), and Opus 5 thinks by default and writes longer than Opus 4.8. Reasoning bills as output ($20/1M on Opus 5.5, $25/1M on Opus 5), so a like-for-like session can land above these figures until you tune effort level and verbosity.

---

## Why Sessions Get Expensive

### The Exponential Growth Problem

Session cost does not grow linearly -- it grows quadratically with the number of turns, because each turn includes all previous turns as input. With a warm cache the re-sent part bills at the cache-read rate, so the growth is real but slow; the expensive event is a cache miss.

```
Cost per turn over a session (worked example extended to 50 turns, Sonnet 4.6, warm cache):

Turn  1: $0.027  ▎▎▎
Turn  5: $0.027  ▎▎▎
Turn 10: $0.032  ▎▎▎
Turn 15: $0.037  ▎▎▎▎
Turn 20: $0.042  ▎▎▎▎
Turn 25: $0.047  ▎▎▎▎▎
Turn 30: $0.052  ▎▎▎▎▎
Turn 40: $0.062  ▎▎▎▎▎▎
Turn 50: $0.072  ▎▎▎▎▎▎▎
```

The first 10 turns cost $0.28 in total. The last 10 turns (41-50) cost $0.67 -- **2.4x more** for the same number of turns (computed: $0.024207 + $0.00099 x (t - 2) for turn t). With caching off it would be $0.68 against $4.64, 6.8x. And a cold cache undoes the discount in one turn: turn 50 after a pause longer than the TTL re-writes all 166,140 tokens for $0.63, about 9x the warm-cache turn.

### The Top 5 Cost Drivers

1. **Long sessions without `/compact`** -- The #1 cost driver. In the worked example's token mix, one 50-turn session costs $2.38 with a warm cache, against $1.40 for five 10-turn sessions doing the same work: 41% less, $0.048 vs $0.028 per turn (computed with the formula in [Key Formulas](#estimated-session-cost)).

2. **Large file reads accumulating in history** -- When Claude reads a 1,000-line file (10,000 tokens), that content stays in conversation history for every subsequent turn. Reading 3 large files adds ~30,000 tokens of permanent context.

3. **Bloated CLAUDE.md** -- A 500-line CLAUDE.md adds ~5,000 tokens to every single turn. Over 30 turns, that is 150,000 extra input tokens -- $0.45 on Sonnet 4.6, $0.60 on Opus 5.5 ($0.75 on legacy Opus 5), before caching. With Claude Code's caching it is written once and read on the other 29 turns: $0.062 on Sonnet 4.6, $0.054 on Opus 5.5, $0.104 on legacy Opus 5 per session ([formula](#claudemd-cost-over-a-session)). The larger cost is adherence: Anthropic says longer files "reduce adherence".

4. **Using Opus for routine tasks** -- If 60% of your turns are simple (formatting, small fixes, lookups), using Opus 5.5 for all of them costs 40x more than Haiku 5.5 for those turns while their prompts stay at or under 100K tokens (8x above; 4x against legacy Haiku 4.5). Haiku 5.5 makes this the widest gap in the lineup again, and it adds up across many turns.

5. **Trial-and-error coding instead of planning first** -- Without Plan Mode, Claude might write code, find it does not work, rewrite it, and iterate several times. Each iteration adds both input history and output tokens. No published measurement says how many turns planning saves; Anthropic's [costs page](https://code.claude.com/docs/en/costs) recommends it to prevent "expensive re-work when the initial direction is wrong".

---

## Key Formulas

### Cost Per Turn

```
turn_cost = (cache_read_tokens x cache_read_price)     # everything the previous request sent
          + (cache_write_tokens x cache_write_price)   # what is new since then
          + (output_tokens x output_price)

# A turn after a pause longer than the cache TTL reads nothing:
# its whole prompt is a cache write.
```

### Estimated Session Cost

```
session_cost = sum(turn_cost for each turn)

# Closed form for N turns, one request per turn, warm cache all session:
#   base = system prompt + CLAUDE.md + first message
#   g    = tokens each turn adds to the next request
written_tokens = base + (N - 1) x g                          # every token is written once
read_tokens    = (N - 1) x base + g x (N - 1) x (N - 2) / 2  # each request is read by the next
session_cost   = written_tokens x cache_write_price
               + read_tokens x cache_read_price
               + N x avg_output_tokens x output_price
```

Where:
- `base` = 4,440 and `g` = 3,300 in the [worked example](#worked-example-cost-of-a-30-turn-session) (700 response + 2,500 tool results + 100 next message)
- `cache_write_price` = 1.25x input for the 5-minute TTL (2x for the 1-hour TTL)
- `cache_read_price` = 0.1x input on most models, 0.05x on Opus 5.5 and Sonnet 5.5, 0.025x on Fable 5.1 and Mythos 5.1 ([Anthropic pricing page](https://platform.claude.com/docs/en/about-claude/pricing))
- Check, worked example on Sonnet 4.6: written = 4,440 + 29 x 3,300 = 100,140; read = 29 x 4,440 + 3,300 x 29 x 28 / 2 = 1,468,560; cost = (100,140 x $3.75 + 1,468,560 x $0.30 + 21,000 x $15) / 1M = $1.13

The read term grows with N squared, so session cost is still quadratic in turns, but at the cache-read rate. This is the billing this repo's calculator and tools model ("cache-aware").

### CLAUDE.md Cost Over a Session

```
claude_md_cost = lines x 10 x (cache_write_price + (turns - 1) x cache_read_price)

Example (150 lines, 30 turns, Sonnet 4.6):
= 1,500 x ($3.75 + 29 x $0.30) / 1,000,000
= 1,500 x $12.45 / 1,000,000
= $0.019

Same example on Opus 5.5 (cache hit 0.05x):
= 1,500 x ($5.00 + 29 x $0.20) / 1,000,000
= 1,500 x $10.80 / 1,000,000
= $0.016

Same example on legacy Opus 5 (or Opus 4.8 / 4.7 / 4.6):
= 1,500 x ($6.25 + 29 x $0.50) / 1,000,000
= 1,500 x $20.75 / 1,000,000
= $0.031
```

Each pause longer than the cache TTL adds one more `lines x 10 x cache_write_price`. The 10 tokens per line is this repo's measured figure (9.8 per line across its 15 CLAUDE.md files, pre-4.7 token basis; see [Token Pricing](#token-pricing)).

### Model Switching Break-Even

When does it make sense to break the prompt cache by switching models?

```
# The new model has no cache for this conversation, so it writes the whole context once.
cache_loss    = context_tokens x new_write_price - context_tokens x old_read_price
model_savings = remaining_turns x (old_turn_cost - new_turn_cost)

Switch if: model_savings > cache_loss
```

Computed with the worked example's turn (3,300 new tokens, 700 output) at a 50K-token context:

- **Opus 5.5 to Sonnet 5.5**: the switch writes 50K x $2.50/1M = $0.125 instead of reading it for $0.01, a $0.115 loss; each later turn then costs $0.020 instead of $0.041, so it breaks even after about 6 turns.
- **Opus 5.5 to Haiku 5.5, context under 100K**: the switch writes 50K x $0.125/1M = $0.006, less than the $0.01 cache read Opus 5.5 would bill, so it pays from the first turn.
- **Opus 5.5 to Haiku 5.5, context over 100K**: Haiku 5.5's write rate jumps to $0.625/1M, 3.1x Opus 5.5's $0.20 read. At 150K the switch costs $0.094 against $0.03 to stay, so for a single answer it is cheaper to let Opus 5.5 reply; over two or more turns Haiku still wins. Anthropic's [2026-04-30 post on Claude Code caching](https://claude.com/blog/lessons-from-building-claude-code-prompt-caching-is-everything) makes the same point for switching to Haiku 100K tokens into an Opus conversation.

---

## Key Takeaways

1. **Output tokens cost 5x more than input tokens.** Strategies that reduce Claude's output (Plan Mode, concise prompts, batching) are highest leverage.

2. **Conversation history is the #1 cost driver.** Use `/compact` proactively and start new sessions for new tasks.

3. **Prompt caching cut this guide's 30-turn Sonnet 4.6 session 77% ($1.13 vs $5.02, 83% of the input cost), and 82% at Opus 5.5 or Sonnet 5.5 rates**, where cache reads cost 0.05x (computed: $1.21 vs $6.69 uncached on Opus 5.5). Do not break the cache unnecessarily.

4. **CLAUDE.md loads on every turn.** Anthropic's guidance is to target under 200 lines per file; nothing is truncated past that, it just costs more and is followed less. Every line you cut saves tokens across your entire session.

5. **Model selection matters, and Haiku 5.5 widens the bottom gap again.** Haiku 5.5 at $0.10/$0.50 vs Opus 5.5 at $4/$20 is a 40x difference while the prompt stays at or under 100K tokens (8x above, where Haiku 5.5 bills $0.50/$2.50); legacy Haiku 4.5 at $1/$5 was 4x. Use the cheapest model that gets the job done, and judge it by cost per completed task, not cost per token: a cheaper model that fails still bills. The new tokenizer (Opus 4.7 and later, about 30% more tokens for the same text per Anthropic's pricing page) slightly re-widens the effective gap against pre-4.7 models.

6. **Track your usage.** Run `/usage` regularly. Put `--max-budget-usd` on every scripted `claude -p` run (interactive sessions ignore it). What gets measured gets managed.

7. **The last 10 turns of a long session cost more than the first 10.** In this guide's 50-turn example they cost 2.4x the first 10 with a warm cache ($0.67 vs $0.28) and 6.8x with caching off. Session cost grows quadratically, not linearly, and one cache miss late in a long session costs about 9x a warm turn. Shorter, focused sessions are cheaper than long, wandering ones.

8. **Opus 5.5 is a price cut, but re-baseline after migrating.** $4/$20 is 20% below Opus 5 (now legacy), and cache reads drop to 0.05x. The catch: thinking is always on and cannot be disabled, so code that turned thinking off on Opus 5 now pays for reasoning tokens at $20/1M, while default effort drops to `medium`, so requests that omit effort think less. Set effort deliberately with `/effort`, use a `max_tokens` of 64,000 for agentic work, and audit prompts written for an older model: in Anthropic's published runs, prompts written for Opus 4.8 cost 36% more per ticket on Opus 5 for no accuracy gain, and once audited they were 14% cheaper and more accurate.

---

*Next: [Guide 02 - Context Optimization](02-context-optimization.md) -- practical strategies to reduce input tokens on every turn.*
