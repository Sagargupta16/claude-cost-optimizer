# Guide 03: Model Selection

> **The single highest-impact optimization.** Choosing the right model per task can reduce your Claude Code bill by 30-60% with zero loss in output quality.

Most developers default to the most capable model for everything. This is like hiring a senior architect to change a lightbulb. Claude Fable 5.1 is extraordinary, but for renaming a variable it is a $50/M-output-token lightbulb-changer (and Opus 5.5 a $20 one). With the 4.7-generation tokenizer using up to 35% more tokens for the same text, the effective cost penalty for over-using top-tier models is even higher than posted pricing suggests.

> **Opus 5.5** (`claude-opus-5-5`, released 2026-09-22) is the recommended default Opus: Anthropic's models overview now says to "start with Claude Opus 5.5 for most workloads". It costs **$4/$20**, 20% below Opus 5's $5/$25 -- the first Opus release to lower the rate -- and cache hits read at **0.05x** base input ($0.20). Opus 5 is now legacy. Two behavior changes matter for cost: adaptive thinking is **always on** (it cannot be disabled; reasoning tokens bill as output at $20/1M), and default effort drops to **medium**. See [Migrating to Opus 5.5](#migrating-to-opus-55) below and [Guide 08](08-prompt-caching.md) for the caching side.

> **Sonnet 5.5** (`claude-sonnet-5-5`, released 2026-09-28) is the current Sonnet flagship at **$2/$10, the same rate as Sonnet 5**, with the same tokenizer, a cache floor halved to 512 tokens, and since 2026-10-07 cache hits at **$0.10 (0.05x)**, half Sonnet 5's $0.20. Sonnet 5 is now legacy. It rejects some Sonnet 5 request shapes, and in Claude Code the `sonnet` alias only means Sonnet 5.5 on the Anthropic API. See [Migrating to Sonnet 5.5](#migrating-to-sonnet-55) and [the `sonnet` alias table](#the-sonnet-alias-depends-on-your-provider).

> **Haiku 5.5** (`claude-haiku-5-5`, released 2026-10-07) is the current Haiku and the first model priced by prompt length: **$0.10/$0.50 up to 100K prompt tokens, $0.50/$2.50 above**. Below the line it is 40x cheaper per token than Opus 5.5 and 20x cheaper than Sonnet 5.5. Haiku 4.5 is now legacy. In Claude Code the `haiku` alias means Haiku 5.5 only on the Anthropic API. See [Migrating to Haiku 5.5](#migrating-to-haiku-55) and [the alias table](#the-sonnet-alias-depends-on-your-provider).

---

## Table of Contents

- [Model Lineup and Pricing](#model-lineup-and-pricing)
- [The 80/20 Rule of Model Selection](#the-8020-rule-of-model-selection)
- [Task Complexity Decision Tree](#task-complexity-decision-tree)
- [Task Categories with Recommended Models](#task-categories-with-recommended-models)
- [How to Set the Model](#how-to-set-the-model)
- [Cost-Per-Task Examples](#cost-per-task-examples)
- [The Common Mistake: Opus for Everything](#the-common-mistake-opus-for-everything)
- [Advanced: Dynamic Model Routing](#advanced-dynamic-model-routing)
- [Quick Reference Card](#quick-reference-card)

---

## Model Lineup and Pricing

### Current Pricing (verified 2026-10-09, per 1M tokens)

| Model | Input Cost | Output Cost | Cache Hit | 5m Cache Write | 1h Cache Write | Min cacheable prompt | Relative Cost | Context Window | Max Output |
|-------|:----------:|:-----------:|:---------:|:--------------:|:--------------:|:--------------------:|:-------------:|:--------------:|:----------:|
| **Fable 5.1** (most capable) | $10.00 | $50.00 | **$0.25** | $12.50 | $20.00 | 512 | 2.5x baseline | 1M | 128K |
| **Opus 5.5** (recommended default Opus) | $4.00 | $20.00 | **$0.20** | $5.00 | $8.00 | 512 | 1x (baseline) | 1M | 128K |
| **Opus 5** (legacy) | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 512 | 1.25x baseline | 1M | 128K |
| **Opus 4.8** (legacy) | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1,024 | 1.25x baseline | 1M | 128K |
| **Opus 4.7** | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 2,048 | 1.25x baseline | 1M | 128K |
| **Opus 4.6** | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 4,096 | 1.25x baseline | 1M | 128K |
| **Opus 4.5** | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 4,096 | 1.25x baseline | 200K | 64K |
| Opus 4.1 (retired 2026-08-05, still on Bedrock + Google Cloud) | $15.00 | $75.00 | $1.50 | $18.75 | $30.00 | 1,024 | 3.75x baseline | 200K | 32K |
| **Sonnet 5.5** (Sonnet flagship) | $2.00 | $10.00 | **$0.10** | $2.50 | $4.00 | 512 | 2x cheaper | 1M | 128K |
| **Sonnet 5** (legacy) | $2.00 | $10.00 | $0.20 | $2.50 | $4.00 | 1,024 | 2x cheaper | 1M | 128K |
| **Sonnet 4.6** | $3.00 | $15.00 | $0.30 | $3.75 | $6.00 | 1,024 | ~1.33x cheaper | 1M | 64K |
| **Sonnet 4.5** (deprecated) | $3.00 | $15.00 | $0.30 | $3.75 | $6.00 | 1,024 | ~1.33x cheaper | 200K | 64K |
| **Haiku 5.5** (latest Haiku), prompt <= 100K tokens | $0.10 | $0.50 | $0.01 | $0.125 | $0.20 | 512 | 40x cheaper | 1M | 128K |
| **Haiku 5.5**, prompt > 100K tokens | $0.50 | $2.50 | $0.05 | $0.625 | $1.00 | 512 | 8x cheaper | 1M | 128K |
| **Haiku 4.5** (legacy) | $1.00 | $5.00 | $0.10 | $1.25 | $2.00 | 4,096 | 4x cheaper | 200K | 64K |

> **Cache Hit** is 0.1x base input on most models, including both Haiku 5.5 tiers. The exceptions: **Opus 5.5 and Sonnet 5.5 read at 0.05x** ($0.20 and $0.10, 95% off) and **Fable 5.1 / Mythos 5.1 read at 0.025x** ($0.25, 97.5% off). Read the per-model rate rather than multiplying input by 0.1.

> **Min cacheable prompt** is the number of tokens a prefix must reach before `cache_control` does anything. Below the threshold the block is **silently ignored**: no error, no discount, full input price every turn. Opus 5 and Opus 5.5 halving it to 512 means short system prompts that never cached on Opus 4.8 now do, and Sonnet 5.5 does the same for Sonnet (512 versus Sonnet 5's 1,024). Haiku 5.5 brings Haiku down to 512 too, from Haiku 4.5's 4,096.

> **Opus 5** (GA 2026-07-24, legacy since the Opus 5.5 launch on 2026-09-22): the previous Opus-tier flagship. **Same $5/$25 as Opus 4.8**, so that upgrade was free at the posted rate; Opus 5.5 is now 20% cheaper per token. 1M context at standard rates, 128K max output (300K on Batch via the `output-300k-2026-03-24` beta), Batch $2.50/$12.50, Fast Mode supported at 2x ($10/$50), knowledge cutoff May 2026, earliest retirement 2027-07-24. Four cost-relevant changes versus Opus 4.8:
> 1. **Adaptive thinking is ON by default** when you omit the `thinking` param. Reasoning tokens bill as output at $25/1M, and `max_tokens` caps thinking **plus** text -- carry over a small `max_tokens` and thinking can eat the budget before the answer is written. Raise it to 64K+ at `xhigh`/`max` effort.
> 2. **`thinking: {type: "disabled"}` is only legal at effort `high` or below.** Pairing it with `xhigh` or `max` returns a 400. On Opus 4.8 that combination was allowed.
> 3. **Minimum cacheable prompt drops to 512 tokens** (from 1,024).
> 4. **Cybersecurity safety classifiers** ship with it. A cyber refusal can auto-fall-back to Opus 4.8 via the server-side `fallbacks` param (beta `server-side-fallback-2026-07-01`).
>
> Opus 5 also writes **longer output than Opus 4.8 by default** and self-verifies its own work. Re-tune verbosity instructions after migrating, and delete carried-over "double-check your work" prompts -- you are now paying twice for behavior the model already performs.
>
> **Fable 5** (GA 2026-06-09, legacy): the Mythos-class tier **above** Opus at **$10/$50, 2x Opus 5**, superseded by Fable 5.1 at the same posted rate. 1M context at standard rates, 128K max output, always-on adaptive thinking (control depth with `effort`), Batch supported ($5/$25), no Fast Mode, 30-day data retention required, min cacheable prompt 512. Safety classifiers can decline a request (HTTP 200 + `stop_reason: "refusal"`; pre-output refusals are free; beta `fallbacks` retries another model server-side). **Cost guidance**: reach for Fable 5 only when the task genuinely needs frontier-plus capability -- the hardest reasoning, the longest autonomous runs. For everything else Opus 5.5, 2.5x cheaper, is the efficient frontier. **Mythos 5** is the same model minus the classifiers, limited to approved [Project Glasswing](https://anthropic.com/glasswing) customers.
>
> **Opus 4.8 status**: Legacy as of the Opus 5 launch. Earliest retirement 2027-05-28. **Same $5/$25 as Opus 5, and Opus 5.5 is 20% cheaper, so there is no cost argument for staying.** Fast Mode supported at 2x. Min cacheable prompt 1,024. Reasons to pin it: prompts tuned to this snapshot, a workload that needs thinking off (Opus 5.5 rejects that outright; Opus 5 rejects it at `xhigh`/`max`), or Priority Tier, which Opus 4.8 keeps and Opus 5.5 does not offer. It also remains the server-side fallback target for Opus 5 cyber refusals.
>
> **Opus 4.7 status**: Legacy. Earliest retirement 2027-04-16. Same price. **Fast Mode was removed here** -- `speed: "fast"` now returns an error with no fallback to standard. Min cacheable prompt 2,048. Pick 4.7 only if you have prompts pinned to that snapshot.
>
> **Opus 4.6 status**: Legacy. Earliest retirement 2027-02-05. Same price. **Fast Mode was removed here too, but silently** -- `speed: "fast"` is accepted and runs at standard speed and standard rates (`usage.speed` comes back `"standard"`). Min cacheable prompt 4,096, the highest of any Opus. Pick 4.6 only if you want a stable snapshot or your prompts already perform well on it.
>
> **Opus 4.5 (200K-only)**: Legacy; not deprecated, earliest retirement 2026-11-24. Same price as the rest of the legacy Opus tier but smaller context window, no Fast Mode, and a 4,096-token cache floor. Generally migrate to Opus 5.5 unless your code is pinned to this snapshot.
>
> **Sonnet 5.5** (`claude-sonnet-5-5`, released 2026-09-28): the current Sonnet flagship, which Anthropic describes as "the best combination of speed and intelligence". **$2/$10, the same rate as Sonnet 5**, with the same cache writes, Batch ($1/$5) and tokenizer, so the same text gives the same token count and migration is free at the posted rate; since 2026-10-07 cache hits cost **$0.10 (0.05x)**, half Sonnet 5's $0.20, so cached work is cheaper than on Sonnet 5. 1M context at standard rates, 128K max output (300K on Batch via the `output-300k-2026-03-24` beta), knowledge cutoff Jun 2026, no Fast Mode, min cacheable prompt **512** (half Sonnet 5's 1,024), tool-use system prompt 286 tokens (Sonnet 5: 354). Adaptive thinking is on by default, effort defaults to `high`. Earliest retirement 2027-09-28. The cost-efficient default for most production work; check the five breaking changes in [Migrating to Sonnet 5.5](#migrating-to-sonnet-55) before switching.
>
> **Sonnet 5** (`claude-sonnet-5`, GA 2026-06-30, legacy since the Sonnet 5.5 launch; still Active, not deprecated, earliest retirement 2027-06-30): the previous Sonnet flagship -- adaptive thinking (`effort` defaults to high on the Claude API and Claude Code), 1M context at standard rates, 128K max output, no Fast Mode, min cacheable prompt 1,024. Uses the newer tokenizer (~30% more tokens for the same text). **$2/$10 per MTok, and that is now the permanent standard price** -- the launch rate was labelled introductory through 2026-08-31, but Anthropic made it standard and cancelled the increase to $3/$15. That puts Sonnet 5 at **half the price of Opus 5.5** (60% below legacy Opus 5) and a third below legacy Sonnet 4.6. Sonnet 5.5 costs the same per token and half as much per cache hit ($0.10 versus $0.20), so the reason to stay is a harness that depends on something Sonnet 5.5 rejects; Sonnet 4.6 is legacy and strictly more expensive than either.
>
> **Sonnet 4.5 (200K-only)**: **Deprecated** (announced 2026-09-30); retirement scheduled for 2026-11-30 on the Claude API. Same price as Sonnet 4.6 but smaller context window. Migrate to Sonnet 5.5, the recommended replacement. On Bedrock, Google Cloud and Microsoft Foundry the `sonnet` alias still resolves to Sonnet 4.5 -- see [the alias table](#the-sonnet-alias-depends-on-your-provider).
>
> **Haiku 5.5** (`claude-haiku-5-5`, released 2026-10-07): the current Haiku, for "high-volume, latency-sensitive tasks such as classification, extraction, routing" and subagent work. **$0.10/$0.50 up to 100K prompt tokens, $0.50/$2.50 above** -- the first tiered model. 1M context, 128K max output, min cacheable prompt **512**, adaptive thinking on by default at effort `medium`, no Fast Mode. Earliest retirement not sooner than 2027-10-07. Check the five breaking changes in [Migrating to Haiku 5.5](#migrating-to-haiku-55) before switching.
>
> **Haiku 4.5 (200K-only)**: Legacy; not deprecated, earliest retirement 2026-10-15. $1/$5, 64K max output, a 4,096-token cache floor. 10x Haiku 5.5's per-token rate below 100K prompt tokens, so migrate unless your code depends on something Haiku 5.5 rejects.
>
> **Opus 4.1**: **Retired 2026-08-05** on the Claude API -- requests now fail. It is still served on Bedrock and Google Cloud, which set their own schedules, at the old $15/$75 (3.75x Opus 5.5 rates). Migrate to Opus 5.5.

> **Claude Mythos Preview** ([Project Glasswing](https://anthropic.com/glasswing)): superseded by Mythos 5 and **deprecated** -- still functional, no longer recommended, and Anthropic publishes no retirement date for it. It is the invitation-only research preview ($25/$125) for defensive cybersecurity through Glasswing partners. Its successor Mythos 5 drops to $10/$50 (same as Fable 5) and remains Glasswing-only; the prediction that Mythos-class capabilities would reach a widely released model came true as **Fable 5**, which is GA for everyone. **Mythos 5.1** (`claude-mythos-5-1`, same specs and pricing as Fable 5.1) is now "Verification required" rather than Glasswing-only: organizations verified through Anthropic's verification programs, such as the Cyber Verification Program, can use it on the Claude API, Bedrock (`anthropic.claude-mythos-5-1`), Google Cloud and Microsoft Foundry, but not on Claude Platform on AWS.

### Migrating to Opus 5.5

Source: Anthropic's Opus 5.5 overview and migration guide (platform.claude.com/docs/en/models/opus-5-5), read 2026-09-28.

**The price cut.** $4/$20 per 1M versus $5/$25 on Opus 5 and Opus 4.8: 20% off every token. Cache hits drop to $0.20 (0.05x base input, versus 0.1x on Opus 5), 5m / 1h cache writes are $5 / $8, Batch is $2/$10, and Fast Mode (research preview, Claude API only) is $8/$40, 2x its own base. Same 1M context, 128K max output (300K on Batch via `output-300k-2026-03-24`), 512-token cache floor, and the same tokenizer as Opus 4.7+. Earliest retirement 2027-09-22. IDs: `claude-opus-5-5` (Claude API, Google Cloud, Microsoft Foundry, Claude Platform on AWS), `anthropic.claude-opus-5-5` (Bedrock).

**Four breaking changes versus Opus 5** (each returns a 400 if you carry old code over):

1. **Thinking cannot be disabled.** Adaptive thinking is always on; `thinking: {type: "disabled"}` and `thinking: {type: "enabled", budget_tokens}` both return 400. Effort is the only control.
2. **Forced `tool_choice` (`any` / `tool`) is rejected.** Use `auto` plus strict tool use or structured outputs.
3. **Thinking blocks are tied to the model and conversation** that produced them.
4. **`computer_20251124` is rejected on the Claude API and Google Cloud.** Use `computer_toolset_20260801`.

Also rejected: non-default `temperature` / `top_p` / `top_k`, and assistant prefill. Text between tool calls now comes back in `thinking` blocks, empty at the default display setting.

**Default effort is `medium`** (Opus 5 defaulted to `high`). The cost consequence cuts both ways: a request that omits effort now thinks less than it did on Opus 5, but code that disabled thinking on Opus 5 now pays for thinking tokens (billed as output at $20/1M) it did not pay for before. Re-baseline cost per task after migrating rather than assuming the 20% rate cut is your saving.

**No Priority Tier.** Opus 4.8 keeps it; if you depend on Priority Tier capacity, Opus 5.5 is not a drop-in replacement yet.

**Refusals** come back as `stop_reason: "refusal"` with `stop_details`; the categories include bio and reasoning_extraction as well as cyber.

### Migrating to Sonnet 5.5

Source: Anthropic's Sonnet 5.5 overview and what's-new page (platform.claude.com/docs/en/models/sonnet-5-5), read 2026-09-29.

**Same rate, same tokenizer, cheaper cache hits.** $2/$10 per 1M, the same as Sonnet 5, with the same cache writes (5m / 1h $2.50 / $4) and Batch ($1/$5). Cache hits were cut on 2026-10-07 to **$0.10 (0.05x base input, 95% off)**, half Sonnet 5's $0.20, so each 1M cached tokens saves $1.90 against a miss instead of $1.80. The same text gives the same token count, so migration is free at the posted rate and cheaper on cached work. Two small input-side savings come with it: the minimum cacheable prompt halves to **512 tokens** (Sonnet 5: 1,024), so short system prompts that never cached on Sonnet 5 now do, and the tool-use system prompt is **286 tokens** (Sonnet 5: 354). Same 1M context, 128K max output (300K on Batch via `output-300k-2026-03-24`). Earliest retirement 2027-09-28. IDs: `claude-sonnet-5-5` (Claude API, Google Cloud, Microsoft Foundry, Claude Platform on AWS), `anthropic.claude-sonnet-5-5` (Bedrock).

**Five breaking changes versus Sonnet 5** (each returns a 400 if you carry old code over):

1. **Thinking cannot be disabled.** `thinking: {type: "disabled"}` and manual `budget_tokens` return 400. The lowest setting is `thinking: {type: "between_tools"}`, which turns off up-front thinking; it is accepted only at `low`, `medium` and `high` effort (`xhigh` or `max` plus `between_tools` is a 400).
2. **Forced `tool_choice` (`any` / `tool`) is rejected.** Use `auto` plus strict tool use or structured outputs.
3. **Thinking blocks are tied to the model and conversation.** Keep conversations append-only: replaying a Sonnet 5.5 thinking block after editing earlier history can return 400.
4. **`computer_20251124` is rejected on the Claude API and Google Cloud** (Bedrock still accepts it). Use `computer_toolset_20260801`.
5. **The advisor tool rejects Opus 4.8, Opus 4.7 and Sonnet 5** as advisors for a Sonnet 5.5 executor.

Also rejected: non-default `temperature` / `top_p` / `top_k`. Text between tool calls comes back in `thinking` blocks, empty at the default display setting.

**Effort is recalibrated.** The default is `high`, but the same level does not produce the same amount of thinking as on Sonnet 5, so re-run your effort sweep instead of carrying a setting over. Anthropic's starting points: `high` in general, `medium` for well-specified agentic coding and multistep tool use. Reasoning tokens bill as output at $10/1M; to stop up-front thinking on routine turns, send `between_tools` at `high` effort or below.

**Mid-conversation changes keep the cache.** Mid-conversation tool changes (beta), mid-conversation system messages and per-message effort (beta) are supported on Sonnet 5.5 and not on Sonnet 5, so tools and instructions can change mid-conversation without losing the prompt cache.

**In Claude Code**, Sonnet 5.5 needs v2.1.284 or later, and the `sonnet` alias resolves to it only on the Anthropic API -- see [the `sonnet` alias table](#the-sonnet-alias-depends-on-your-provider).

### Migrating to Haiku 5.5

Source: Anthropic's Haiku 5.5 overview and what's-new page (platform.claude.com/docs/en/models/haiku-5-5) and the pricing page, read 2026-10-09.

**Two price tiers, and a cliff at 100K.** Haiku 5.5 is the first Claude model priced by prompt length. Up to 100,000 prompt tokens: $0.10/$0.50 per 1M (cache hits $0.01; 5m / 1h cache writes $0.125 / $0.20; Batch $0.05/$0.25). Above 100,000: $0.50/$2.50 (cache hits $0.05; writes $0.625 / $1.00; Batch $0.25/$1.25). Prompt length counts every input token, cache reads and writes included, and each request is priced on its own: a request over the line pays the higher input and output rates even when part of its prompt is a cache hit. A 100,000-token prompt costs $0.010 of input; a 100,001-token prompt costs $0.050, 5x more. Keep Haiku prompts under 100K -- short subagent, classification and routing calls are where it wins.

**1M context, 128K output, newer tokenizer.** The window grows to 1M (Haiku 4.5: 200K) and max output to 128K (Haiku 4.5: 64K; 300K on Batch via `output-300k-2026-03-24`). Haiku 5.5 uses the Claude 4.7+ tokenizer, so the same text is **~30% more tokens** than on Haiku 4.5. Per token it is 10x cheaper than Haiku 4.5's $1/$5 at <= 100K and 2x above; per task that is roughly **7.7x** (10 / 1.3) and **~1.5x** (2 / 1.3). Against Sonnet 5.5 (same tokenizer) it is 20x cheaper at <= 100K and 4x above; against Opus 5.5, 40x and 8x.

**512-token cache floor** (Haiku 4.5: 4,096), so short system prompts that never cached on Haiku 4.5 now do. Tool-use system prompt 286 tokens (`auto`/`none`) / 406 (`any`/`tool`): unlike Opus 5.5 and Sonnet 5.5, forced tool use is supported. No Fast Mode.

**Five breaking changes versus Haiku 4.5** (each returns a 400 if you carry old code over):

1. **Manual extended thinking is rejected.** `budget_tokens` returns 400; use adaptive thinking.
2. **Non-default `temperature` / `top_p` / `top_k` are rejected.**
3. **Assistant prefill is rejected.** End `messages` with a user turn.
4. **`computer_20250124` is rejected on the Claude API and Google Cloud.** Use `computer_toolset_20260801`.
5. **Changing earlier turns invalidates thinking blocks.** Keep conversations append-only.

Also changed: responses can begin with `thinking` blocks (select content blocks by `type`, not position), thinking text is omitted by default, and safety classifiers can decline a request (`stop_reason: "refusal"`, with no server-side fallback).

**Adaptive thinking is on by default, effort `medium`.** On the API, `thinking: {type: "disabled"}` still works at `high` effort or below. In Claude Code you cannot turn thinking off on Haiku 5.5, so lower `effort` instead.

**IDs**: `claude-haiku-5-5` (Claude API, Google Cloud, Microsoft Foundry, Claude Platform on AWS), `anthropic.claude-haiku-5-5` (Bedrock). Knowledge cutoff Jun 2026. Earliest retirement not sooner than 2027-10-07.

**In Claude Code**, the `haiku` alias resolves to Haiku 5.5 only on the Anthropic API (v2.1.293 or later); on Claude Platform on AWS, Bedrock, Google Cloud and Microsoft Foundry it still means Haiku 4.5 -- see [the alias table](#the-sonnet-alias-depends-on-your-provider).

### What These Numbers Mean in Practice

A typical Claude Code turn involves roughly **2,000-5,000 input tokens** and **500-3,000 output tokens**. Here is what a single turn costs across models:

| Scenario | Input Tokens | Output Tokens | Opus 5.5* | Sonnet 5.5 | Haiku 5.5 (<= 100K) |
|----------|:------------:|:-------------:|:---------:|:--------:|:---------:|
| Quick fix (small) | 2,000 | 500 | $0.018 | $0.009 | $0.00045 |
| Component creation (medium) | 5,000 | 2,000 | $0.060 | $0.030 | $0.0015 |
| Architecture analysis (large) | 10,000 | 5,000 | $0.140 | $0.070 | $0.0035 |
| Multi-file refactor (XL) | 20,000 | 10,000 | $0.280 | $0.140 | $0.007 |

> *Opus 5.5 costs shown at its posted rate ($4/$20). Legacy Opus 5 and Opus 4.8 ($5/$25) cost 1.25x these figures. Multiply by ~1.2-1.35 to account for the 4.7-generation tokenizer's higher token counts on the same text (Opus 5.5 uses the same tokenizer). Add thinking tokens too: on Opus 5.5 adaptive thinking is always on and bills as output, so a turn can bill well above its visible output, more so above the default `medium` effort. Lower `effort` for routine turns; thinking cannot be switched off on Opus 5.5. Every prompt here is under 100K tokens, so Haiku 5.5 is priced at its lower tier ($0.10/$0.50); it also thinks by default (effort `medium`). Legacy Haiku 4.5 ($1/$5) costs 10x the Haiku 5.5 column for the same token counts.

> **Key insight**: Output tokens cost 5x more than input tokens across all models. Tasks that generate a lot of code (scaffolding, boilerplate, test suites) are where model selection has the most impact.

### Prompt Caching and Real-World Costs

Claude Code uses prompt caching, which reduces the cost of repeated input tokens by 90% on most models (95% on Opus 5.5 and Sonnet 5.5, 97.5% on Fable 5.1 and Mythos 5.1). After the first turn of a session, cached content (system prompt, CLAUDE.md, stable conversation history) costs far less. This means:

- **First turn** of a session is the most expensive
- **Subsequent turns** benefit heavily from caching
- **Model selection still matters** because output tokens are never cached, and output is where most cost accumulates in code-generation tasks
- **Model selection also sets the cache floor.** Your prefix has to clear the model's minimum cacheable length before any of this applies -- 512 tokens on Opus 5.5, Opus 5, Sonnet 5.5, Haiku 5.5 and the Fable models, 1,024 on Opus 4.8, Sonnet 5, Sonnet 4.6 and Sonnet 4.5, 4,096 on legacy Haiku 4.5 and Opus 4.6/4.5. Routing a short-prompt task down to Haiku 5.5 saves 40x on the token rate versus Opus 5.5 while the prompt stays at or under 100K tokens, and any prefix of 512 tokens or more still caches; on legacy Haiku 4.5 the same move saved 4x and lost the discount entirely below 4,096.

---

## The 80/20 Rule of Model Selection

> **80% of your Claude Code tasks can be handled by a cheaper model.** The remaining 20% genuinely benefit from Opus.

Here is a breakdown of a typical developer's daily Claude Code usage:

```
Typical daily task distribution:
├── 40%  Simple tasks (formatting, renames, lookups, simple edits)     → Haiku 5.5
├── 40%  Medium tasks (components, bug fixes, tests, docs)             → Sonnet
└── 20%  Complex tasks (architecture, multi-file refactors, debugging) → Opus
```

### Cost Impact of the 80/20 Rule

Assume 50 tasks per day with an average cost of $0.10/task on Opus 5:

| Strategy | Daily Cost | Monthly Cost (22 days) | Savings |
|----------|:----------:|:----------------------:|:-------:|
| **All Opus 5** (legacy) | $5.00 | $110.00 | -- |
| **All Opus 5.5** (same work, $4/$20) | $4.00 | $88.00 | **20%** |
| **80/20 split** (Sonnet 5.5 for the 80%) | $2.60 | $57.20 | **48%** |
| **Optimized split** (40/40/20: Haiku 5.5 / Sonnet 5.5 / Opus) | $1.84 | $40.48 | **63%** |

Savings are measured against all-Opus 5; the split rows still price their Opus 20% at Opus 5's $0.10/task, Sonnet 5.5 at $0.04 (two-fifths of Opus 5 per token) and Haiku 5.5 at $0.002 (one-fiftieth, with every simple-task prompt under 100K tokens). The 20 Haiku 5.5 tasks cost $0.04 a day in total, so nearly all of the optimized split's spend is Sonnet and Opus. Moving to Opus 5.5 alone is a 20% cut per token, but routing is still worth three times that. Opus 5 posted the same $5/$25 as Opus 4.8 and 4.7/4.6, so the absolute dollar savings are smaller than they were against Opus 4.1 ($15/$75) -- but a 48-63% reduction still adds up fast across a team. Model selection remains the single biggest lever you have, and two things make skipping Opus more valuable than the table suggests: the tokenizer overhead, and thinking (default-on on Opus 5, always on on Opus 5.5), which inflates the output side of every turn you route there unnecessarily.

### Price the Completed Task, Not the Token

Anthropic's cost-optimization guide (platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence) makes the point this whole guide rests on: optimize **cost per completed task**, not cost per token. A cheaper model that fails still bills, and so does the retry. Its published runs (directional, not guarantees):

- **Effort before model.** On research work (Fable 5), `medium` matched the default's accuracy at 70-85% of its cost; `low` gave up 1-3 points for a third to a half off. On long-horizon coding, Opus 5 gave up about 2 points at `medium` for half the cost.
- **Run at `low`, retry only the failures.** Running everything at `low` and re-running only failures at the default reached ~93% pass for ~$0.70/task, versus 91.7% for $1.39 running everything at the default: same pass rate, half the cost.
- **Price the tail, not the median.** On one 20-problem run, two problems carried 43% of spend. Budget from your worst tasks, not the typical one.
- **`max_tokens` is a backstop, not a knob.** A 16,384 cap ended 15% of Opus 5's coding attempts unsolved; use 64,000 for agentic work.
- **Old prompts over-work new models.** Prompts written for Opus 4.8 cost 36% more per ticket on Opus 5 for no accuracy gain; audited, they were 14% cheaper and more accurate. Re-audit prompts when you move to Opus 5.5.

---

## Task Complexity Decision Tree

Use this decision tree to quickly decide which model to use:

```
START: What is the task?
│
├── Does it require understanding complex architecture or
│   reasoning about multi-file interactions?
│   ├── YES → Is it a planning/analysis task (no code output)?
│   │         ├── YES → Opus 5.5 (plan mode)
│   │         └── NO  → Opus 5.5 (Fable 5.1 only if Opus 5.5 fails)
│   └── NO ↓
│
├── Does it require generating new code with non-trivial logic?
│   ├── YES → Is the logic self-contained in 1-2 files?
│   │         ├── YES → Sonnet
│   │         └── NO  → Sonnet (consider Opus if > 5 files)
│   └── NO ↓
│
├── Is it a mechanical/repetitive change?
│   (formatting, renaming, simple find-replace, adding imports)
│   ├── YES → Haiku 5.5 (keep the prompt under 100K tokens)
│   └── NO ↓
│
├── Is it a lookup or question about the codebase?
│   ├── YES → Haiku 5.5 (for simple questions) / Sonnet (for analysis)
│   └── NO ↓
│
└── Default → Sonnet (the safest general-purpose choice)
```

### The "Two Question" Shortcut

If the decision tree feels heavy, just ask two questions:

1. **Does this task require reasoning about how multiple components interact?** If yes: Opus (Opus 5.5 by default). If no: continue.
2. **Does this task require generating non-trivial new logic?** If yes: Sonnet. If no: Haiku 5.5.

---

## Task Categories with Recommended Models

### Simple Tasks: Use Haiku 5.5

**Cost per task: $0.0004-$0.003** at Haiku 5.5's <= 100K-prompt rate ($0.10/$0.50; legacy Haiku 4.5 at $1/$5 was $0.003-$0.02)

Haiku handles these tasks with the same quality as more expensive models. There is no benefit to using Sonnet or Opus here.

| Task | Example | Why Haiku Works |
|------|---------|-----------------|
| **Code formatting** | "Fix the indentation in `utils.py`" | Mechanical transformation, no reasoning needed |
| **Variable/function renaming** | "Rename `getData` to `fetchUserProfile`" | Simple find-and-replace with scope awareness |
| **Import management** | "Add missing imports to this file" | Pattern matching against existing code |
| **Simple type annotations** | "Add TypeScript types to these function params" | Inferring types from usage patterns |
| **Comment updates** | "Update the JSDoc for this function" | Reading function signature, writing description |
| **Config file changes** | "Add `cors: true` to the server config" | Small edits to structured files |
| **Git operations** | "Create a commit message for these changes" | Summarizing diffs |
| **File lookups** | "What files import from `utils/auth`?" | Grep-based search, no deep reasoning |
| **Simple error fixes** | "Fix this missing semicolon / closing bracket" | Syntax-level corrections |
| **Moving/copying files** | "Move `Header.tsx` to `components/layout/`" | File system operations with import updates |

**How to invoke**:
```bash
claude --model haiku "rename getUserData to fetchUserProfile in src/api/"
```

### Medium Tasks: Use Sonnet 5.5

**Cost per task: $0.02-$0.15**

Sonnet is the sweet spot for most development work. It handles logic, generates quality code, and understands context well.

| Task | Example | Why Sonnet Works |
|------|---------|------------------|
| **Component creation** | "Create a pagination component with prev/next" | Generates well-structured code with standard patterns |
| **Bug fixes** | "Fix the race condition in the auth flow" | Understands cause-and-effect in code, traces logic |
| **Test writing** | "Write unit tests for the CartService class" | Follows testing patterns, covers edge cases |
| **API endpoint creation** | "Add a PUT endpoint for updating user profiles" | Follows existing patterns in the codebase |
| **Database queries** | "Write a query to get users with expired subs" | Understands schema relationships |
| **Documentation** | "Write API docs for the payment module" | Reads code, generates structured documentation |
| **Code review** | "Review this PR diff for issues" | Identifies common anti-patterns and bugs |
| **Refactoring (single file)** | "Extract the validation logic into its own function" | Restructures code while preserving behavior |
| **Error handling** | "Add proper error handling to the API layer" | Understands failure modes, generates try/catch patterns |
| **State management** | "Add Redux slice for the notification feature" | Follows established state patterns in the project |

**How to invoke**:
```bash
claude --model sonnet "write unit tests for src/services/CartService.ts"
```

### Complex Tasks: Use Opus 5.5

**Cost per task: $0.04-$0.40+** (higher in practice due to the tokenizer and always-on thinking)

Reserve Opus for tasks where deep reasoning, multi-file coordination, or architectural understanding provides genuine value. At $4/$20 (20% below Opus 5 and 4.8/4.7/4.6 at $5/$25, and well down from 4.1's $15/$75) the cost penalty for using it is smaller than it used to be, but it is still 2x more than Sonnet 5.5 and 40x more than Haiku 5.5 at posted rates (8x once a Haiku prompt passes 100K tokens), the tokenizer adds another 20-35% of effective cost, and always-on thinking adds billable output on top of that. Defaulting to Opus for every task remains wasteful.

**Why Opus 5.5 over Opus 5**: 20% cheaper per token, cache hits at half Opus 5's rate ($0.20 versus $0.50), and Anthropic's recommended starting model. The catch is the four breaking changes in [Migrating to Opus 5.5](#migrating-to-opus-55): if your harness disables thinking or forces `tool_choice`, fix that before switching.

**Why Opus 5 over Opus 4.8** (the previous step): same posted price, better agentic coding, and a cache floor half as high (512 versus 1,024 tokens), so more of your system prompt actually caches. Opus 5 also self-verifies its work before reporting and takes instructions literally, which on long autonomous runs (audit, multi-file refactor, migration) often pays for itself by avoiding retry loops. The flip side is verbosity: Opus 5 writes longer than 4.8 by default, so trim your verbosity instructions rather than assuming an old prompt is still cost-optimal.

**Thinking modes differ, and this is the migration trap**:
- **Opus 5.5** uses **adaptive thinking, ALWAYS ON**. `thinking: {type: "disabled"}` and `budget_tokens` both return 400; effort (default `medium`, all five levels) is the only control.
- **Opus 5** uses **adaptive thinking, ON by default** when the `thinking` param is omitted. Effort defaults to `high`. `thinking: {type: "disabled"}` works only at effort `high` or below -- pairing it with `xhigh` or `max` is a 400.
- **Opus 4.8** uses **adaptive thinking, off unless requested**. Effort defaults to `high` on all surfaces (the Claude Code default was `xhigh` on 4.7).
- **Opus 4.7** uses **adaptive thinking** plus an `xhigh` effort level.
- **Opus 4.6** uses **extended thinking** -- you can configure a reasoning token budget.
- If you have prompts or harnesses tuned against extended thinking's explicit budget knobs, they will not carry over to 4.8 or 5. And if you are moving from 4.8 to 5, the same request now costs more unless you explicitly manage thinking: budget the difference before rolling out, and raise `max_tokens` to 64K+ if you run `xhigh` or `max`. Moving from 5 to 5.5, code that disabled thinking now pays for it, while code that omitted effort now runs at `medium` instead of `high`: re-baseline either way.

**Benchmarks published by Anthropic for Opus 4.6** (the numbers were even higher for Mythos Preview, the tier that Fable 5 / Mythos 5 now succeed -- included below for reference):

| Benchmark | Opus 4.6 | Mythos Preview (deprecated tier) |
|-----------|:--------:|:----------------------------:|
| SWE-bench Verified | 80.8% | 93.9% |
| SWE-bench Pro | 53.4% | 77.8% |
| Terminal-Bench 2.0 | 65.4% | 82.0% |
| CyberGym (vuln reproduction) | 66.6% | 83.1% |

> Mythos-class capability is now generally available as **Fable 5** ($10/$50). Anthropic has not published a per-benchmark scorecard for Fable 5 or Opus 5 on these exact suites -- when official numbers land, this table should be extended.

| Task | Example | Why Opus Is Worth It |
|------|---------|----------------------|
| **Architecture design** | "Design the module structure for a plugin system" | Requires reasoning about abstractions, trade-offs, extensibility |
| **Multi-file refactoring** | "Migrate from REST to GraphQL across 15 files" | Needs to hold the full picture, coordinate changes, avoid breakage |
| **Complex debugging** | "Find why checkout fails intermittently under load" | Requires reasoning across multiple systems, race conditions, state |
| **Performance optimization** | "Identify and fix the N+1 queries in the API" | Needs to trace data flow through multiple layers |
| **Security auditing** | "Review the auth system for vulnerabilities" | Requires deep understanding of attack vectors, subtle bugs |
| **Migration planning** | "Plan the migration from Webpack to Vite" | Needs to understand build system internals, dependency implications |
| **Design pattern implementation** | "Implement CQRS for the order processing system" | Complex pattern with many interacting components |
| **System integration** | "Integrate Stripe webhooks with our event system" | Multiple systems, error handling, idempotency concerns |
| **Algorithm development** | "Implement a rate limiter with sliding window" | Algorithmic reasoning, edge cases, correctness proofs |
| **Legacy code understanding** | "Explain how the billing engine works end-to-end" | Reading and synthesizing across a large, undocumented codebase |

**How to invoke**:
```bash
claude --model opus "design a plugin architecture for our CLI tool"
```

**Want a specific Opus snapshot explicitly?** Use the dated/aliased ID:
- Opus 5.5: `--model claude-opus-5-5` (Claude API, Google Cloud, Microsoft Foundry, Claude Platform on AWS), `anthropic.claude-opus-5-5` (Bedrock)
- Opus 5 (legacy): `--model claude-opus-5` (Claude API), `anthropic.claude-opus-5` (Bedrock Messages API), `us.anthropic.claude-opus-5` (Bedrock legacy InvokeModel/Converse), `claude-opus-5` (Vertex AI)
- Opus 4.8: `--model claude-opus-4-8` (Claude API), `anthropic.claude-opus-4-8` (Bedrock Messages API), `us.anthropic.claude-opus-4-8` (Bedrock legacy InvokeModel/Converse)
- Opus 4.7: `--model claude-opus-4-7` (Claude API), `anthropic.claude-opus-4-7` (Bedrock)
- Opus 4.6: `--model claude-opus-4-6` (Claude API), `anthropic.claude-opus-4-6-v1` (Bedrock legacy InvokeModel/Converse)
- Opus 4.5: `--model claude-opus-4-5-20251101`
- Opus 4.1: `--model claude-opus-4-1-20250805` -- **retired 2026-08-05 on the Claude API; this ID now fails there.** Still resolvable on Bedrock and Google Cloud

The `opus` alias maps to Opus 5.5 on current Claude Code releases (on Microsoft Foundry it still means Opus 4.6). If you need a pinned snapshot, name it explicitly rather than relying on the alias -- the alias moves with each Opus launch.

#### The `sonnet` alias depends on your provider

Per Claude Code's model-config page (code.claude.com/docs/en/model-config, read 2026-09-29; `haiku` column read 2026-10-09), the aliases resolve by provider:

| Provider | `opus` | `sonnet` | `haiku` |
|----------|--------|----------|---------|
| Anthropic API | Opus 5.5 | **Sonnet 5.5** | **Haiku 5.5** |
| Claude Platform on AWS | Opus 5.5 | Sonnet 4.6 | Haiku 4.5 |
| Amazon Bedrock, Google Cloud | Opus 5.5 | **Sonnet 4.5** | Haiku 4.5 |
| Microsoft Foundry | Opus 4.6 | Sonnet 4.5 | Haiku 4.5 |

**Cost gotcha**: on Bedrock, Google Cloud and Foundry, `--model sonnet` means Sonnet 4.5 at $3/$15 with a 200K context -- 1.5x the price of Sonnet 5.5 for a smaller window, and Sonnet 4.5 is now deprecated (retirement scheduled for 2026-11-30). On Claude Platform on AWS it means Sonnet 4.6 ($3/$15, 1M). Pin it with `--model claude-sonnet-5-5` (Bedrock: `anthropic.claude-sonnet-5-5`) or set `ANTHROPIC_DEFAULT_SONNET_MODEL`. Sonnet 5.5 requires Claude Code v2.1.284 or later.

**Same gotcha for `haiku`**: it means Haiku 5.5 only on the Anthropic API (Claude Code v2.1.293 or later). Everywhere else it is legacy Haiku 4.5 at $1/$5 -- 10x Haiku 5.5's per-token rate below 100K prompt tokens, with a 200K window and a 4,096-token cache floor. Pin it with `ANTHROPIC_DEFAULT_HAIKU_MODEL` (`claude-haiku-5-5`, Bedrock `anthropic.claude-haiku-5-5`), which also sets the model Claude Code uses for background functionality.

---

## How to Set the Model

### Method 1: The `--model` Flag (Per-Task)

The most direct approach. Override the model for a single invocation:

```bash
# Use Haiku for a quick rename
claude --model haiku "rename processData to transformPayload in src/"

# Use Sonnet for a component
claude --model sonnet "create a modal dialog component"

# Use Opus for architecture work
claude --model opus "design the caching layer for our API"
```

**Best for**: Ad-hoc tasks where you know the complexity upfront.

### Method 2: Default Model in Settings (Session Default)

Set a default model in your Claude Code settings (`~/.claude/settings.json` or project-level `.claude/settings.json`):

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "model": "sonnet"
}
```

Then override with `--model` only when needed. This way, your baseline cost is Sonnet-level, and you opt into Opus explicitly. Outside the Anthropic API, `"sonnet"` does not resolve to Sonnet 5.5 (see [the `sonnet` alias table](#the-sonnet-alias-depends-on-your-provider)), so pin `claude-sonnet-5-5` (Bedrock: `anthropic.claude-sonnet-5-5`) there.

**Best for**: Establishing a cost-efficient baseline across all sessions.

### Method 3: Command Frontmatter (Per-Command)

Define the model inside a Claude Code custom command (`.claude/commands/*.md`):

```markdown
---
model: haiku
---

Fix formatting issues in the files I specify. Do not change logic or behavior.
Only fix indentation, trailing whitespace, and missing newlines.
```

This ensures the command always uses the specified model regardless of your session default.

**Best for**: Repetitive tasks that should always use a specific model.

### Method 4: Subagent Model Configuration

When using the Task tool to delegate work to a subagent, the subagent uses its own model configuration. You can instruct the main agent to delegate specific tasks to cheaper subagents:

```
Use a subagent to find all files that import from 'utils/deprecated'.
The subagent should use Haiku since this is a simple search task.
```

Anthropic's costs page (code.claude.com/docs/en/costs) recommends setting `model: haiku` in the subagent definition for simple subagent tasks, so the choice does not depend on the main agent remembering it.

You can also configure subagent model preferences in your CLAUDE.md:

```markdown
# Subagent Guidelines
- Use Haiku for: file searches, simple edits, formatting
- Use Sonnet for: code generation, test writing, bug fixes
- Use Opus only for: architecture decisions, complex multi-file work
```

**Best for**: Automated delegation where different subtasks have different complexity levels.

---

## Cost-Per-Task Examples

These are real-world estimates based on typical token usage patterns. All costs assume prompt caching is active (not the first turn of a session).

> The Opus column is priced at Opus 5.5 ($4/$20); legacy Opus 5 and Opus 4.8 ($5/$25) cost 1.25x those figures. The Sonnet 5.5 column is priced at $2/$10 (legacy Sonnet 5 costs the same) -- it undercuts Sonnet 4.6's $3/$15, so any Sonnet figure inherited from the 4.6 era overstates the cost by a third. The Haiku column is priced at Haiku 5.5's lower tier ($0.10/$0.50), because every request in these examples stays under 100K prompt tokens; legacy Haiku 4.5 ($1/$5) costs 10x those figures for the same token counts. The Haiku quality rows are carried over from Haiku 4.5, not re-measured on Haiku 5.5. What the tables do **not** include is thinking: on Opus 5.5 it is always on and reasoning tokens bill as output at $20/1M, so a turn can bill noticeably more than the output column shows, especially above the default `medium` effort. Treat the Opus numbers as a floor.

### Example 1: Rename a Function

**Task**: Rename `getUserData` to `fetchUserProfile` across 8 files.

| | Haiku 5.5 | Sonnet 5.5 | Opus 5.5 |
|-|:---------:|:----------:|:--------:|
| Input tokens | ~3,000 | ~3,000 | ~3,000 |
| Output tokens | ~1,200 | ~1,200 | ~1,200 |
| **Cost** | **$0.0009** | **$0.018** | **$0.036** |
| Quality | Identical | Identical | Identical |

**Verdict**: Haiku 5.5. Saves $0.035 per rename vs Opus 5.5. Over 10 renames/day, that is $0.35/day saved. Haiku 5.5 is 40x cheaper per token than Opus 5.5 at this prompt size, for tasks where quality is identical.

### Example 2: Write Unit Tests for a Service

**Task**: Write comprehensive unit tests for `PaymentService` (5 methods, ~200 lines).

| | Haiku 5.5 | Sonnet 5.5 | Opus 5.5 |
|-|:---------:|:----------:|:--------:|
| Input tokens | ~8,000 | ~8,000 | ~8,000 |
| Output tokens | ~4,000 | ~4,000 | ~4,000 |
| **Cost** | **$0.0028** | **$0.056** | **$0.112** |
| Quality | Good (may miss edge cases) | Very good | Excellent (not worth 2x more) |

**Verdict**: Sonnet. Saves $0.056 vs Opus 5.5 with negligible quality difference for standard test writing.

### Example 3: Debug a Race Condition

**Task**: Investigate and fix intermittent auth failures in a distributed system spanning 12 files.

| | Haiku 5.5 | Sonnet 5.5 | Opus 5.5 |
|-|:---------:|:----------:|:--------:|
| Turns needed | ~15 (struggles) | ~8 | ~4 |
| Total input tokens | ~120,000 | ~80,000 | ~60,000 |
| Total output tokens | ~30,000 | ~25,000 | ~20,000 |
| **Total cost** | **$0.027** | **$0.410** | **$0.640** |
| Quality | Poor (likely fails) | Decent | High (finds root cause) |
| Time | 25 min | 15 min | 8 min |

**Verdict**: Opus. Opus 5.5 costs more than Sonnet here ($0.64 vs $0.41), but it solves the task in fewer turns, and a Haiku or Sonnet attempt that fails still bills -- cost per *completed* task is what counts. Haiku 5.5's 15 turns average ~8,000 input tokens each (120,000 / 15), far under its 100K line, so its $0.027 is all at the lower tier; it is cheap, but a cheap failure is still a failure. This is also the task type where Opus 5.5's always-on thinking earns its keep: race-condition debugging is exactly the reasoning-heavy work those tokens buy.

### Example 4: Create a CRUD API Endpoint

**Task**: Add a new `/api/projects` endpoint with GET, POST, PUT, DELETE.

| | Haiku 5.5 | Sonnet 5.5 | Opus 5.5 |
|-|:---------:|:----------:|:--------:|
| Input tokens | ~6,000 | ~6,000 | ~6,000 |
| Output tokens | ~3,500 | ~3,500 | ~3,500 |
| **Cost** | **$0.0024** | **$0.047** | **$0.094** |
| Quality | Adequate (follows patterns) | Good | Excellent (overkill) |

**Verdict**: Sonnet. Standard CRUD follows patterns that Sonnet handles well.

### Example 5: Plan a Database Migration

**Task**: Design the migration strategy from MongoDB to PostgreSQL for a 20-collection database with complex relationships.

| | Haiku 5.5 | Sonnet 5.5 | Opus 5.5 |
|-|:---------:|:----------:|:--------:|
| Input tokens | ~15,000 | ~15,000 | ~15,000 |
| Output tokens | ~8,000 | ~8,000 | ~8,000 |
| **Cost** | **$0.0055** | **$0.110** | **$0.220** |
| Quality | Superficial plan | Good plan | Thorough, catches edge cases |

**Verdict**: Opus. Migration planning is high-stakes. A missed edge case can cost days of developer time. The extra $0.11 vs Sonnet is negligible compared to the cost of a botched migration.

---

## The Common Mistake: Opus for Everything

### The "Premium Default" Anti-Pattern

Many developers set Opus as their default model and never change it. Their reasoning: "I want the best output, and the cost is acceptable."

With Opus 5.5's pricing ($4/$20, 20% below the $5/$25 of Opus 5 and 4.8/4.7/4.6, far below 4.1's $15/$75), this anti-pattern is less financially devastating than it used to be, but it is still wasteful, and two things quietly widen the gap back out: the 4.7-generation tokenizer (up to 35% more tokens per turn) and Opus 5.5's always-on thinking (extra billed output on every turn, including the trivial ones).

**1. Quality is often identical across models for simple tasks.**

For formatting, renaming, import management, config changes, and other mechanical tasks, Haiku produces output that is indistinguishable from Opus. On Opus 5.5 you are paying 40x more per token than on Haiku 5.5 while the prompt stays at or under 100K tokens (8x above; 4x against legacy Haiku 4.5) for the same result.

**2. The cost still compounds.**

```
Scenario: 50 tasks/day, 22 working days/month

All Opus 5.5: 50 tasks x $0.08 avg x 22 days = $88/month (+35% tokenizer = ~$119,
              more once always-on thinking is counted)
Smart split:  ((20 x $0.002) + (20 x $0.04) + (10 x $0.08)) x 22 = $36/month

Annual difference: $623
Team of 5 annual difference: $3,115
```

($0.08 is the Opus 5 era's $0.10 average at Opus 5.5's 20% lower rate. The Haiku 5.5 and Sonnet 5.5 averages are 1/40 and 1/2 of it, their per-token ratios to Opus 5.5, with every simple-task prompt under 100K tokens.) While the savings are more modest than they were at old Opus pricing, $3,115/year for a 5-person team is still worth capturing -- especially since it requires no loss in output quality.

**3. More expensive does not mean faster for simple tasks.**

Opus does not rename a variable faster than Haiku. The latency is often higher because Opus generates more thorough (but unnecessary) reasoning for simple tasks -- and on Opus 5.5 that reasoning always happens (thinking cannot be disabled), so the only way to shrink the penalty is a lower `effort`.

### How to Break the Habit

1. **Set Sonnet as your default model.** This is the best general-purpose starting point.
2. **Create Haiku commands** for your most frequent simple tasks (formatting, renaming, lookups).
3. **Explicitly opt into Opus** with `--model opus` only when you are doing architecture, complex debugging, or multi-file planning.
4. **Review your usage weekly.** Look at which tasks used Opus and ask: "Did that task genuinely need Opus?"

---

## Advanced: Dynamic Model Routing

### CLAUDE.md-Based Routing Guidelines

Add model routing guidance to your CLAUDE.md so Claude Code itself helps you pick the right model when delegating to subagents:

```markdown
# Model Routing
When delegating subtasks:
- Haiku: file searches, grep operations, simple edits, formatting, git operations
- Sonnet: code generation, test writing, bug fixes, documentation, single-file refactors
- Opus: architecture decisions, multi-file refactors, complex debugging, security reviews
```

### Cost-Aware Command Library

Build a library of commands with pre-assigned models:

```
.claude/commands/
├── format.md          (model: haiku)
├── rename.md          (model: haiku)
├── find-usages.md     (model: haiku)
├── write-test.md      (model: sonnet)
├── fix-bug.md         (model: sonnet)
├── create-component.md (model: sonnet)
├── review-arch.md     (model: opus)
├── plan-refactor.md   (model: opus)
└── security-audit.md  (model: opus)
```

This way, model selection is built into your workflow. You do not have to think about it each time.

### The Escalation Pattern

Start with the cheapest model and escalate only if needed:

1. **Try Haiku first.** If the output is good, you are done.
2. **If Haiku struggles**, retry with Sonnet.
3. **If Sonnet struggles**, retry with Opus.

This sounds like it wastes tokens on failed attempts, but in practice, most tasks succeed on the first try with the cheaper model, and the few that need escalation still cost less overall than defaulting to Opus. The same logic works on the effort axis: Anthropic's published run at `low` effort, re-running only failures at the default, matched the all-default pass rate for half the cost (see [Price the Completed Task, Not the Token](#price-the-completed-task-not-the-token)).

---

## Quick Reference Card

```
HAIKU 5.5 ($0.10/$0.50 per 1M up to 100K prompt tokens, $0.50/$2.50 above;
512-token cache floor, 1M context, default effort medium) -- the default Haiku
├── Formatting and linting fixes
├── Variable and function renaming
├── Import management
├── Config file edits
├── File searches and lookups
├── Git commit messages
├── Simple type annotations
├── Mechanical find-and-replace
└── Cost control: keep each prompt under 100K tokens (the whole request
    bills at the higher tier once it crosses)

SONNET 5.5 ($2/$10 per 1M tokens, same rate as legacy Sonnet 5; cache hit
$0.10, 512-token cache floor, default effort high) -- the default Sonnet
├── Component and module creation
├── Bug fixes (single file or simple multi-file)
├── Unit and integration test writing
├── API endpoint creation
├── Documentation generation
├── Code review
├── Single-file refactoring
└── Error handling implementation

OPUS 5.5 ($4/$20 per 1M tokens, cache hit $0.20, +~35% tokenizer overhead,
thinking ALWAYS ON, default effort medium) -- the default Opus
├── Architecture design and planning
├── Multi-file refactoring (5+ files)
├── Complex debugging (race conditions, memory leaks)
├── Long autonomous agentic runs
├── Performance optimization (N+1 queries, bottlenecks)
├── Security auditing
├── Migration planning
├── System integration design
├── Legacy code comprehension
└── Cost control: lower `effort` (thinking cannot be disabled; forced
    tool_choice, prefill and non-default sampling params all return 400)

OPUS 5 ($5/$25 per 1M tokens -- legacy, 1.25x Opus 5.5)
└── Only if you need thinking disabled or forced tool_choice (Opus 5.5 rejects both)

SONNET 5 ($2/$10 per 1M tokens -- legacy, same rate as Sonnet 5.5 but cache hit $0.20)
└── Only if you need thinking disabled or forced tool_choice (Sonnet 5.5 rejects both)

HAIKU 4.5 ($1/$5 per 1M tokens -- legacy, 10x Haiku 5.5's lower-tier rate)
└── Only if your code still needs budget_tokens, non-default sampling params or
    prefill (Haiku 5.5 rejects all three); `haiku` still means it off the Anthropic API

FABLE 5 ($10/$50 per 1M tokens -- 2.5x Opus 5.5, legacy; superseded by Fable 5.1)
├── The absolute hardest reasoning problems Opus 5.5 can't crack
├── The longest autonomous agentic runs (single turns can run many minutes)
├── Mythos-class capability without a Glasswing invitation
└── Note: always-on thinking, no Fast Mode, safety classifiers may refuse
    (pre-output refusals are free; use the beta fallbacks param to retry)

OPUS 4.8 ($5/$25 per 1M tokens -- legacy, same price as Opus 5, Fast Mode 2x)
└── Only if your prompts are tuned to this snapshot, you need thinking off,
    or you need Priority Tier (Opus 5.5 has none)

OPUS 4.7 ($5/$25 per 1M tokens -- legacy, Fast Mode REMOVED: speed "fast" errors)
└── Only if you have prompts pinned to that snapshot

OPUS 4.6 ($5/$25 per 1M tokens -- legacy, Fast Mode REMOVED: silently runs standard)
└── Only if you have prompts tuned to the older tokenizer or want a stable snapshot

FAST MODE -- OPUS 5.5, OPUS 5 or OPUS 4.8 only (2x each model's own base:
$8/$40 on Opus 5.5, $10/$50 on Opus 5 and 4.8; Claude API + Managed Agents only,
Opus 5.5 Fast Mode is a research preview on the Claude API; the old 6x tier no longer exists)
└── Only when output latency directly impacts revenue / UX
    (live demos, real-time agentic loops, urgent debugging)
    NOT for routine interactive coding
```

---

## Next Steps

- Set Sonnet as your default model today
- Create 2-3 Haiku commands for your most common simple tasks
- Read [Guide 04: Workflow Patterns](04-workflow-patterns.md) for additional cost-saving strategies
- Use the [Token Estimator](../tools/token-estimator/README.md) to measure costs before and after switching models

---

*[Back to README](../README.md) | [Previous: Context Optimization](02-context-optimization.md) | [Next: Workflow Patterns](04-workflow-patterns.md)*
