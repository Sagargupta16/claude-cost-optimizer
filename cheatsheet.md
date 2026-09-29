# Claude Code Cost Optimization Cheatsheet

> One-page quick reference. Print it, bookmark it, pin it. Every strategy links to a detailed guide.
>
> **Pricing verified: 2026-09-29.** Sources: [platform pricing](https://platform.claude.com/docs/en/about-claude/pricing), [models overview](https://platform.claude.com/docs/en/about-claude/models/overview), [model deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations), [Opus 5.5 overview](https://platform.claude.com/docs/en/models/opus-5-5/overview), [Sonnet 5.5 overview](https://platform.claude.com/docs/en/models/sonnet-5-5/overview), [what's new in Sonnet 5.5](https://platform.claude.com/docs/en/models/sonnet-5-5/whats-new-sonnet-5-5), [Claude Code model config](https://code.claude.com/docs/en/model-config), [migrating to Opus 5.5](https://platform.claude.com/docs/en/models/opus-5-5/migration-guide), [migrating to Opus 5](https://platform.claude.com/docs/en/models/opus-5/migration-guide), [fast mode](https://platform.claude.com/docs/en/build-with-claude/fast-mode), [prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching), [introducing Fable 5 / Mythos 5](https://platform.claude.com/docs/en/about-claude/models/introducing-claude-fable-5-and-claude-mythos-5).

---

## Token Pricing At a Glance

| Model | Input / 1M tokens | Output / 1M tokens | Cache Hit / 1M | 5m Cache Write | 1h Cache Write | Context | Max Output | Min cache | Relative Cost |
|-------|:-----------------:|:-------------------:|:--------------:|:--------------:|:--------------:|:-------:|:----------:|:---------:|:-------------:|
| **Fable 5.1** (highest capability) | $10.00 | $50.00 | **$0.25** | $12.50 | $20.00 | 1M | 128K | 512 | 2.5x baseline |
| **Fable 5** (legacy) | $10.00 | $50.00 | $1.00 | $12.50 | $20.00 | 1M | 128K | 512 | 2.5x baseline |
| **Mythos 5** (limited, Glasswing) | $10.00 | $50.00 | $1.00 | $12.50 | $20.00 | 1M | 128K | 512 | 2.5x baseline |
| **Opus 5.5** (Opus flagship, recommended default) | $4.00 | $20.00 | **$0.20** | $5.00 | $8.00 | 1M | 128K | **512** | 1x (baseline) |
| **Opus 5** (legacy) | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1M | 128K | 512 | 1.25x baseline |
| **Opus 4.8** (legacy) | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1M | 128K | 1,024 | 1.25x baseline |
| **Opus 4.7** | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1M | 128K | 2,048 | 1.25x baseline |
| **Opus 4.6** | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1M | 128K | 4,096 | 1.25x baseline |
| **Opus 4.5** | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 200K | 64K | 4,096 | 1.25x baseline |
| Opus 4.1 (retired 2026-08-05, still on Bedrock + Google Cloud) | $15.00 | $75.00 | $1.50 | $18.75 | $30.00 | 200K | 32K | 1,024 | 3.75x baseline |
| **Sonnet 5.5** (Sonnet flagship) | $2.00 | $10.00 | $0.20 | $2.50 | $4.00 | 1M | 128K | **512** | **2x cheaper** |
| **Sonnet 5** (legacy) | $2.00 | $10.00 | $0.20 | $2.50 | $4.00 | 1M | 128K | 1,024 | **2x cheaper** |
| **Sonnet 4.6** | $3.00 | $15.00 | $0.30 | $3.75 | $6.00 | 1M | 64K | 1,024 | **~1.3x cheaper** |
| **Sonnet 4.5** | $3.00 | $15.00 | $0.30 | $3.75 | $6.00 | 200K | 64K | 1,024 | **~1.3x cheaper** |
| **Haiku 4.5** | $1.00 | $5.00 | $0.10 | $1.25 | $2.00 | 200K | 64K | 4,096 | **4x cheaper** |
| **Opus 5.5 (Fast Mode)** | $8.00 (2x) | $40.00 (2x) | N/A | -- | -- | 1M | 128K | -- | 2x baseline |
| **Opus 5 / 4.8 (Fast Mode)** | $10.00 (2x) | $50.00 (2x) | N/A | -- | -- | 1M | 128K | -- | 2.5x baseline |
| **Mythos Preview** (deprecated, no retirement date) | $25.00 | $125.00 | $2.50 | $31.25 | $50.00 | 1M | -- | 2,048 | 6.25x baseline |

> **Relative Cost baseline is Opus 5.5** ($4/$20), the current Opus flagship. Output tokens cost **5x more** than input tokens across all current models. Reducing Claude's verbosity is high-leverage.
>
> **1M context on Opus 5.5 / 5 / 4.8 / 4.7 / 4.6 / Sonnet 5.5 / Sonnet 5 / Sonnet 4.6 is at standard rates** -- no long-context premium. (Earlier "2x over 200K" pricing is obsolete.) **Haiku 4.5, Sonnet 4.5, Opus 4.5, and Opus 4.1 are 200K-context only.** **Sonnet 5** (`claude-sonnet-5`) is **$2/$10 permanently** -- the launch intro rate became the standard price and the rise to $3/$15 was cancelled.
>
> **Cache pricing math**: 5m write = 1.25x base input; 1h write = 2x base input; cache hit/refresh = 0.1x base input, except **0.05x on Opus 5.5** and **0.025x on Fable 5.1 / Mythos 5.1** (three multipliers, so read the per-model rate). So a 5m cache pays off after 1 reuse, a 1h cache after 2 reuses. Multipliers stack with Batch (50% off) and data residency (+10%).
>
> **Min cache column = minimum cacheable prompt length.** Below it, a `cache_control` block does nothing -- no error, no discount, full input price every turn. Opus 5.5, Opus 5 and Sonnet 5.5 halve the threshold of Opus 4.8 and Sonnet 5 (1,024 -> **512**), so prompts that never cached on those start caching for free. Haiku 4.5 / Opus 4.6 / Opus 4.5 need 4,096 tokens before caching does anything at all.
>
> **Opus 5.5 / 5 / 4.8 / 4.7 tokenizer**: The tokenizer introduced with Opus 4.7 uses **up to 35% more tokens** for the same text. Effective per-task cost is higher than posted pricing implies. Budget accordingly when comparing 5.5 / 5 / 4.8 / 4.7 to 4.6 / Sonnet 4.6.
>
> **Opus 5.5** (released 2026-09-22): the current Opus-tier flagship -- Anthropic's models overview now says to "start with Claude Opus 5.5 for most workloads". **$4/$20, 20% below Opus 5**, the first Opus release to lower the rate. Cache hit **$0.20 (0.05x base input, 95% off)**, 5m write $5, 1h write $8, Batch $2/$10, Fast Mode $8/$40, min cacheable prompt 512. What changes your bill: (1) **adaptive thinking is always on** -- `thinking: {type:"disabled"}` and `budget_tokens` both return a **400**, so code that disabled thinking on Opus 5 now pays for thinking tokens (billed as output); (2) **default effort drops to `medium`** (Opus 5 defaulted to `high`), so a request that omits effort thinks less than it did -- effort is the only control; (3) forced `tool_choice` (`any`/`tool`), non-default sampling params, and assistant prefill all return a **400**; (4) **no Priority Tier** (Opus 4.8 keeps it). Re-baseline cost after migrating. Knowledge cutoff Jun 2026. Earliest retirement: not sooner than 2027-09-22.
>
> **Sonnet 5.5** (released 2026-09-28): the current Sonnet flagship; Sonnet 5 is now legacy. **$2/$10 -- identical to Sonnet 5**, including caching (hit $0.20, 0.1x base input; 5m write $2.50, 1h write $4) and Batch ($1/$5), with the same tokenizer, so migrating is free at the posted rate. Min cacheable prompt **512** (Sonnet 5: 1,024), tool-use system prompt 286 tokens (Sonnet 5: 354), no Fast Mode. Adaptive thinking is on by default at effort `high`, reasoning bills as output at $10/1M, and effort levels are recalibrated -- re-run your effort sweep rather than carrying a Sonnet 5 setting over. What returns a **400** when Sonnet 5 code is carried over: (1) `thinking: {type:"disabled"}` and manual `budget_tokens` -- the lowest setting is `thinking: {type:"between_tools"}`, accepted only at `low`/`medium`/`high` effort; (2) forced `tool_choice` (`any`/`tool`) and non-default sampling params; (3) replaying a Sonnet 5.5 thinking block after editing earlier history -- keep conversations append-only; (4) `computer_20251124` on the Claude API and Google Cloud (use `computer_toolset_20260801`); (5) Opus 4.8, Opus 4.7 or Sonnet 5 as the advisor for a Sonnet 5.5 executor. Mid-conversation tool changes (beta), system messages and per-message effort (beta) work on Sonnet 5.5, not Sonnet 5, without losing the prompt cache. Knowledge cutoff Jun 2026. Earliest retirement: not sooner than 2027-09-28.
>
> **Opus 5** (GA 2026-07-24, **legacy since the Opus 5.5 launch**): the previous Opus-tier flagship. **$5/$25 -- identical to Opus 4.8**, so moving to it from 4.8 was free at the posted rate, but three behaviors change your bill: (1) **adaptive thinking is ON by default** when you omit the `thinking` param, and reasoning tokens bill as output at $25/1M with `max_tokens` capping thinking **plus** text (raise it to 64K+ at `xhigh`/`max`); (2) `thinking: {type:"disabled"}` is legal only at effort `high` or below -- combining it with `xhigh`/`max` returns a **400**; (3) min cacheable prompt is 512 tokens. Output also runs longer than 4.8 by default, so re-tune verbosity instructions, and drop any "verify your work" instruction you carried over (it self-verifies). Ships cybersecurity classifiers -- pair with the server-side `fallbacks` param (beta `server-side-fallback-2026-07-01`) to auto-retry cyber refusals on Opus 4.8. Batch $2.50/$12.50. Knowledge cutoff May 2026. New beta `mid-conversation-tool-changes-2026-07-01` lets tools change between turns without busting the cache.
>
> **Fable 5** (GA 2026-06-09, now legacy behind Fable 5.1 at the same price): a Mythos-class tier above Opus at **$10/$50 (2x legacy Opus 5, 2.5x Opus 5.5)**. Always-on adaptive thinking (no `disabled`; control depth with `effort`, `low` through `xhigh`/`max`). Safety classifiers may decline requests: HTTP 200 + `stop_reason: "refusal"`; **pre-output refusals cost $0**; the beta `fallbacks` param retries on another model server-side, and fallback credit refunds the cache-switch cost. No Fast Mode; Batch supported ($5/$25). Requires 30-day data retention. **Cost note**: for cost-sensitive work, Opus 5.5 at 2.5x less is the sweet spot -- reach for Fable 5 when the task genuinely needs the extra capability (hardest reasoning, longest agentic runs).
>
> **Mythos 5**: same model, specs, and price as Fable 5 but **without safety classifiers**. Limited availability via [Project Glasswing](https://anthropic.com/glasswing) only. Successor to Mythos Preview, which is **deprecated** with no published retirement date.
>
> **Opus 4.8 status**: moved to **legacy** by the Opus 5 launch, and Opus 5.5 now costs 20% less ($4/$20), so there is no cost reason to stay -- migrate unless your prompts are tuned to this snapshot, you need thinking off (Opus 5.5 never allows it; Opus 5 rejects it at `xhigh`/`max`), or you need Priority Tier (Opus 5.5 has none). Still the server-side fallback target for Opus 5 cyber refusals. Earliest retirement 2027-05-28.
>
> **Fast Mode (research preview)**: **Opus 5.5, Opus 5 and Opus 4.8 only**, via the `fast-mode-2026-02-01` beta header (`speed: "fast"`). All at **2x their own base rate: $8 / $40 per MTok on Opus 5.5, $10 / $50 on Opus 5 and 4.8**. Up to **2.5x output tokens/second** -- the gain is on OTPS, not time-to-first-token. **Opus 4.7 now errors** on `speed: "fast"` with no fallback; **Opus 4.6 silently runs standard speed at standard rates** (`usage.speed` returns `"standard"`). The old 6x Opus 4.7 / 4.6 Fast Mode tier no longer exists. Claude API + Managed Agents only: NOT on Claude Platform on AWS, Bedrock, Vertex AI, Microsoft Foundry, Batch API, or Priority Tier. Switching speeds invalidates prompt cache. Dedicated rate limits via `anthropic-fast-*` response headers. [Join the waitlist](https://claude.com/fast-mode).
>
> **Subscriptions**: Pro **$20/mo** (or **$200/yr ≈ $16.67/mo**, ~17% off). Max 5x $100/mo. Max 20x $200/mo. **Batch API**: 50% off both input and output. **Regional endpoints** (Bedrock / Vertex AI / Claude API `inference_geo: "us"`, scope = Sonnet 4.5+, Haiku 4.5+, Opus 4.5+, and all future models): +10% premium.

### Thinking Modes by Model

| Model | Extended thinking | Adaptive thinking | Default state |
|-------|:-----------------:|:-----------------:|:-------------:|
| Fable 5.1 | No | Yes (always on) | On, cannot disable |
| Fable 5 | No | Yes (always on) | On, cannot disable |
| Mythos 5 | No | Yes (always on) | On, cannot disable |
| **Opus 5.5** | No | Yes (always on) | **On, cannot disable** (effort defaults to `medium`) |
| Opus 5 | No | Yes | **On by default** |
| Opus 4.8 | No | Yes | Off unless requested |
| Opus 4.7 | No | Yes | Off unless requested |
| Opus 4.6 | Yes | Yes | Off unless requested |
| Opus 4.5 | Yes | -- | Off unless requested |
| **Sonnet 5.5** | No | Yes | **On by default**, `disabled` returns 400 (effort defaults to `high`) |
| Sonnet 5 | No | Yes | Off unless requested |
| Sonnet 4.6 | Yes | Yes | Off unless requested |
| Sonnet 4.5 | Yes | -- | Off unless requested |
| Haiku 4.5 | Yes | No | Off unless requested |

> **Extended thinking** adds explicit reasoning tokens you pay for as output. **Adaptive thinking** lets the model decide when and how much to think based on task difficulty -- no separate billing flag. Opus 4.7 replaced extended thinking with adaptive thinking + the `xhigh` effort level; Opus 4.8 keeps the same surface and defaults `effort` to `high`.
>
> **Opus 5 flips the default**: omit the `thinking` param and it thinks adaptively, billing those tokens as output at $25/1M. `max_tokens` caps thinking **plus** text, so a value carried over from 4.8 can be consumed by thinking before the answer starts -- budget 64K+ if you run `xhigh`/`max`. To turn it off, send `thinking: {type: "disabled"}`, but only at effort `high` or below: pairing `disabled` with `xhigh` or `max` returns a **400**.
>
> **Opus 5.5 removes the off switch**: thinking is always on, and both `thinking: {type: "disabled"}` and `budget_tokens` return a **400**. Effort is the only control and it defaults to `medium` (Opus 5: `high`), so set it explicitly when you migrate and re-baseline cost.
>
> **Sonnet 5.5 has no off switch either**: `thinking: {type: "disabled"}` and manual `budget_tokens` return a **400**. To stop up-front thinking on routine turns, send `thinking: {type: "between_tools"}` at effort `high` or below (`xhigh`/`max` + `between_tools` returns a 400).
>
> On **Fable 5 / Mythos 5** thinking is always on -- omit the `thinking` param (an explicit `disabled` returns a 400) and control depth purely with `effort`.

### Model Lifecycle

Verified 2026-09-29 against the [model deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations) page.

**Recently retired** (requests will fail):

| Model | Retired on | Migrate to |
|-------|:---------:|-----------|
| Opus 3 (`claude-3-opus-20240229`) | 2026-01-05 | Opus 5.5 |
| Sonnet 3.7 (`claude-3-7-sonnet-20250219`) | 2026-02-19 | Sonnet 5.5 |
| Haiku 3.5 (`claude-3-5-haiku-20241022`) | 2026-02-19 (still on Bedrock + Vertex AI) | Haiku 4.5 |
| Haiku 3 (`claude-3-haiku-20240307`) | 2026-04-20 | Haiku 4.5 |
| Sonnet 4 (`claude-sonnet-4-20250514`) | 2026-06-15 | Sonnet 5.5 |
| Opus 4 (`claude-opus-4-20250514`) | 2026-06-15 | Opus 5.5 |
| Opus 4.1 (`claude-opus-4-1-20250805`) | 2026-08-05 (still on Bedrock + Google Cloud) | Opus 5.5 |

**Deprecated** (still working, no retirement date published):

| Model | State | Migrate to |
|-------|:-----:|-----------|
| Mythos Preview (`claude-mythos-preview`) | Deprecated, no published retirement date | Mythos 5 (Glasswing) |

**Tentative retirement dates** (every model below is still **Active** -- these are dates to plan around, not deprecations):

| Model | Retirement date | Migration target |
|-------|:--------------:|-----------------|
| Sonnet 4.5 (`claude-sonnet-4-5-20250929`) | Not before 2026-09-29 | Sonnet 5.5 |
| Haiku 4.5 (`claude-haiku-4-5-20251001`) | Not before 2026-10-15 | (current) |
| Opus 4.5 (`claude-opus-4-5-20251101`) | Not before 2026-11-24 | Opus 5.5 |
| Opus 4.6 (`claude-opus-4-6`) | Not before 2027-02-05 | Opus 5.5 |
| Sonnet 4.6 (`claude-sonnet-4-6`) | Not before 2027-02-17 | Sonnet 5.5 |
| Opus 4.7 (`claude-opus-4-7`) | Not before 2027-04-16 | Opus 5.5 |
| Opus 4.8 (`claude-opus-4-8`) | Not before 2027-05-28 | Opus 5.5 |
| Fable 5.1 (`claude-fable-5-1`) | Not before 2027-09-01 | (current) |
| Fable 5 (`claude-fable-5`) | Not before 2027-06-09 | Fable 5.1 |
| **Sonnet 5.5** (`claude-sonnet-5-5`) | Not before **2027-09-28** | (current) |
| Sonnet 5 (`claude-sonnet-5`) | Not before 2027-06-30 | Sonnet 5.5 |
| Opus 5 (`claude-opus-5`) | Not before 2027-07-24 | Opus 5.5 |
| **Opus 5.5** (`claude-opus-5-5`) | Not before **2027-09-22** | (current) |

> **One model is deprecated: Mythos Preview.** It is still functional and Anthropic publishes no retirement date for it; migrate to Mythos 5. Opus 4.1, the last dated forced migration, retired on 2026-08-05. Every other model reads **Active** on the deprecations page, so no request is on a countdown. Sonnet 4.5, Haiku 4.5 and Opus 4.5 are Active and not deprecated; the nearest dates are Sonnet 4.5 (not sooner than 2026-09-29) and Haiku 4.5 (not sooner than 2026-10-15) -- earliest possible dates to plan around, not deadlines Anthropic has committed to.
>
> **Off-Peak 2x Usage**: Anthropic periodically runs promotional events that double usage limits outside peak hours (typically 8 AM - 2 PM ET) and on all weekends. If you're outside the US, your entire workday likely falls in the 2x window. Watch the [Anthropic blog](https://www.anthropic.com/news) for announcements.
>
> **CLI Cost Controls**: `--max-budget-usd <amount>` caps spending per `claude -p` run (print mode only; interactive sessions ignore it). `--fallback-model <model>` switches to the model(s) you name when the primary is overloaded or unavailable; `fallbackModel` in settings persists the chain.

---

## Legacy & Retired Models (reference only)

> Migration context for code still pinned to older model IDs. **Do not use these for new work** -- prices, IDs, and capabilities are kept here for archive value only.

### Recently retired (requests now fail)

| Model | Retired on | Last priced at (input / output per 1M) | Migrate to |
|-------|:---------:|:--------------------------------------:|-----------|
| Claude Opus 3 (`claude-3-opus-20240229`) | 2026-01-05 | $15 / $75 | Opus 5.5 |
| Claude Sonnet 3.7 (`claude-3-7-sonnet-20250219`) | 2026-02-19 | $3 / $15 | Sonnet 5.5 |
| Claude Haiku 3.5 (`claude-3-5-haiku-20241022`) | 2026-02-19 (still on Bedrock + Vertex AI) | $0.80 / $4 | Haiku 4.5 |
| Claude Haiku 3 (`claude-3-haiku-20240307`) | 2026-04-20 | $0.25 / $1.25 | Haiku 4.5 |
| Claude Sonnet 4 (`claude-sonnet-4-20250514`) | 2026-06-15 | $3 / $15 | Sonnet 5.5 |
| Claude Opus 4 (`claude-opus-4-20250514`) | 2026-06-15 | $15 / $75 | Opus 5.5 |
| Claude Opus 4.1 (`claude-opus-4-1-20250805`) | 2026-08-05 (still on Bedrock + Google Cloud) | $15 / $75 | Opus 5.5 |
| Claude Sonnet 3.5 v1 (`claude-3-5-sonnet-20240620`) | 2025-10-28 | $3 / $15 | Sonnet 5.5 |
| Claude Sonnet 3.5 v2 (`claude-3-5-sonnet-20241022`) | 2025-10-28 | $3 / $15 | Sonnet 5.5 |
| Claude Sonnet 3 (`claude-3-sonnet-20240229`) | 2025-07-21 | $3 / $15 | Sonnet 5.5 |
| Claude 2 / 2.1 (`claude-2.0`, `claude-2.1`) | 2025-07-21 | $8 / $24 | Opus 5.5 |
| Claude Instant 1.x | 2024-11-06 | $0.80 / $2.40 | Haiku 4.5 |
| Claude 1.x | 2024-11-06 | $8 / $24 | Haiku 4.5 |

### Deprecated (still working)

| Model | State | Priced at (input / output per 1M) | Migrate to |
|-------|:-----:|:--------------------------------:|-----------|
| Claude Mythos Preview (`claude-mythos-preview`) | Deprecated, no published retirement date | $25 / $125 | Mythos 5 (Glasswing) |

Opus 4.1, deprecated 2026-06-05, retired on 2026-08-05 and is listed under "Recently retired" above. Every other model Anthropic still serves reads **Active**.

### Historical pricing patterns (no longer in effect)

The following pricing constructs were real but have since been retired or restructured. Listed here for migration context if you're reading older guides:

- **"2x input, 1.5x output above 200K"** long-context premium -- applied to Opus 4.1 and older. Obsolete on Opus 5.5 / 5 / 4.8 / 4.7 / 4.6, Sonnet 5.5, Sonnet 5, and Sonnet 4.6, which bill 1M context at standard rates.
- **Opus 4.1 ($15/$75)** -- original "Opus 4.x" pricing, 3x the $5/$25 Opus rates and 3.75x Opus 5.5. **Retired 2026-08-05** on the Claude API (still served on Bedrock and Google Cloud). Migrate to Opus 5.5.
- **6x Fast Mode on Opus 4.7 / 4.6 ($30/$150)** -- removed at the Opus 5 launch. Opus 4.7 now errors on `speed: "fast"`; Opus 4.6 silently serves standard speed at standard rates. Fast Mode is Opus 5.5 / 5 / 4.8 only, all at 2x their own base rate.
- **Bedrock-only ARN-versioned IDs** like `anthropic.claude-opus-4-20250514-v1:0` -- still resolve via the legacy InvokeModel/Converse path, but the new Mantle endpoint uses cleaner provider-prefixed IDs (`anthropic.claude-opus-5`).
- **Single endpoint type on Bedrock** -- pre-Sonnet-4.5, all Bedrock traffic was effectively "global". The +10% regional premium is a 4.5+ generation construct.

### Snapshots that are still active (not retired, but not the headline tier)

These models are GA and priced but generally not the recommended target for new work -- listed under "Legacy" because they're previous-generation snapshots:

| Snapshot | Pricing (input / output per 1M) | Context | Earliest retirement | Why use |
|----------|:-------------------------------:|:-------:|:-------------------:|---------|
| Opus 5 | $5 / $25 | 1M | 2027-07-24 | Previous flagship -- Opus 5.5 is 20% cheaper per token. Pin only if you need thinking disabled or forced `tool_choice`, both of which Opus 5.5 rejects |
| Opus 4.8 | $5 / $25 | 1M | 2027-05-28 | Older flagship -- same price as Opus 5. Pin only if prompts are tuned to it, you need thinking off at `xhigh`/`max`, or you need Priority Tier (Opus 5.5 has none). Fallback target for Opus 5 cyber refusals |
| Opus 4.7 | $5 / $25 | 1M | 2027-04-16 | Pinned workloads. Fast Mode removed (errors) |
| Opus 4.6 | $5 / $25 | 1M | 2027-02-05 | Stable snapshot of the previous-tokenizer Opus. Fast Mode silently downgrades |
| Opus 4.5 | $5 / $25 | 200K | 2026-11-24 | Pinned workloads only |
| Sonnet 5 | $2 / $10 | 1M | 2027-06-30 | Previous Sonnet flagship -- same price as Sonnet 5.5. Pin only if you need thinking disabled or forced `tool_choice`, both of which Sonnet 5.5 rejects |
| Sonnet 4.6 | $3 / $15 | 1M | 2027-02-17 | Pinned workloads -- migrate to Sonnet 5.5 |
| Sonnet 4.5 | $3 / $15 | 200K | 2026-09-29 | Pinned workloads only |

> Authoritative source for all dates: [Anthropic model deprecations page](https://platform.claude.com/docs/en/about-claude/model-deprecations).

---

## All Strategies - Ranked by Impact

### Tier 1: High Impact (Do These First)

| # | Strategy | Savings | Effort | Explanation | Guide |
|---|----------|:-------:|:------:|-------------|-------|
| 1 | **Use cheaper models for simple tasks** | 20-40% | 1 min | Run `claude --model haiku` for formatting, simple fixes, file lookups, and boilerplate - Haiku costs 1/4 of Opus 5.5 per token (1/5th of legacy Opus 5); judge by cost per completed task, since a cheap attempt that fails still bills | [Model Selection](guides/03-model-selection.md) |
| 2 | **Delegate work to subagents** | 20-40% | 5 min | Subagent tool calls get their own isolated context; large file searches and multi-file reads happen outside your main conversation, keeping your primary context small | [Workflow Patterns](guides/04-workflow-patterns.md) |
| 3 | **Use Plan Mode before coding** | 15-25% | 0 min | Press `Shift+Tab` to toggle Plan Mode - Claude thinks through the approach before writing code, preventing expensive trial-and-error cycles that waste output tokens | [Workflow Patterns](guides/04-workflow-patterns.md) |
| 4 | **Trim CLAUDE.md to under 200 lines** | No published figure | 15 min | CLAUDE.md loads in full at session start and rides along as input on *every turn*. Anthropic's guidance: "target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence." Move workflow-specific instructions into skills or path-scoped `.claude/rules/` so they load on demand | [Context Optimization](guides/02-context-optimization.md) |
| 5 | **Preserve prompt cache** | 10-25% | 5 min | Cached input tokens cost 90% less (95% on Opus 5.5, 97.5% on Fable 5.1). What breaks the cache: switching models, changing effort (except on Opus 5.5 and Fable 5.1), turning on fast mode, compaction. Editing CLAUDE.md mid-session does *not* break it (the edit applies after `/clear`, `/compact` or a restart). Keep conversation flow linear | [Understanding Costs](guides/01-understanding-costs.md) |

### Tier 2: Medium Impact (Set Up Once)

| # | Strategy | Savings | Effort | Explanation | Guide |
|---|----------|:-------:|:------:|-------------|-------|
| 6 | **Add `Read(...)` deny rules** | No published figure | 2 min | Add `permissions.deny` rules such as `Read(./node_modules/**)` and `Read(./dist/**)` to `.claude/settings.json` to keep Claude's file tools (and `cat`/`head`/`tail` in Bash) out of dependencies, build output, lock files, and `.env`. Scoped Read rules do not invalidate the prompt cache. `.claudeignore` is not a Claude Code feature -- move any patterns you have into deny rules | [Context Optimization](guides/02-context-optimization.md) |
| 7 | **Use `/compact` regularly** | 10-20% | 0 min | Run `/compact` when conversation gets long (20+ turns) to summarize history and reset context window - prevents the exponential cost growth of long sessions | [Context Optimization](guides/02-context-optimization.md) |
| 8 | **Set budget caps** | 0%* | 1 min | Use `claude -p --max-budget-usd 5` for scripted runs (print mode only), a Console workspace spend limit, or a PreToolUse budget hook ([hooks/budget-tracker.sh](hooks/budget-tracker.sh)) to prevent runaway sessions. Claude Code has no spend-cap setting in settings.json. Does not save tokens directly but prevents surprise bills | [Understanding Costs](guides/01-understanding-costs.md) |
| 9 | **Create custom slash commands** | 10-15% | 10 min | Define reusable commands in `.claude/commands/` for repeated workflows - avoids re-explaining the same instructions across sessions, saving input tokens each time | [Workflow Patterns](guides/04-workflow-patterns.md) |
| 10 | **Use batch operations** | 15-30% | 5 min | Group related changes into single prompts instead of one-at-a-time requests - "rename X in all 12 files" beats 12 individual "rename X in this file" turns | [Workflow Patterns](guides/04-workflow-patterns.md) |

### Tier 3: Ongoing Habits (Compound Over Time)

| # | Strategy | Savings | Effort | Explanation | Guide |
|---|----------|:-------:|:------:|-------------|-------|
| 11 | **Write concise prompts** | 5-10% | Ongoing | Be specific and direct - "Add null check to `processOrder` in `src/orders.ts` line 47" beats "Can you look at the orders file and maybe add some error handling?" | [Context Optimization](guides/02-context-optimization.md) |
| 12 | **Avoid reading entire large files** | 5-15% | Ongoing | Point Claude to specific line ranges or functions instead of letting it `Read` a 2000-line file - use "read lines 100-150 of X" or reference functions by name | [Context Optimization](guides/02-context-optimization.md) |
| 13 | **Start new sessions for new tasks** | 10-20% | Ongoing | Fresh sessions have minimal context; a 50-turn session carries all prior history as input - start clean when switching tasks to avoid paying for irrelevant context | [Understanding Costs](guides/01-understanding-costs.md) |
| 14 | **Use memory files over inline repeats** | 5-10% | 5 min | Put project conventions in CLAUDE.md once rather than repeating "use single quotes" or "always add tests" in every prompt - say it once, reference forever | [Context Optimization](guides/02-context-optimization.md) |
| 15 | **Monitor with `/usage`** | Awareness | 0 min | Run `/usage` periodically to see token consumption in your current session - knowing where tokens go is the first step to reducing them | [Understanding Costs](guides/01-understanding-costs.md) |

---

## Model Selection Quick Decision

```
Is the task...
├── Hardest reasoning, longest agentic runs, budget allows 2.5x?        → Fable 5.1
├── Complex architecture, long agentic run, or hardest coding?         → Opus 5.5
├── Standard feature work, code review, writing tests?                 → Sonnet 5.5
├── Simple fix, formatting, boilerplate, file lookup?                  → Haiku 4.5
└── Not sure?                                                          → Start with Sonnet 5.5
```

**Switch models mid-session**: Type `/model` and select, or start with `claude --model sonnet`. The `sonnet` alias means Sonnet 5.5 only on the Anthropic API: on Bedrock, Google Cloud and Microsoft Foundry it is Sonnet 4.5 ($3/$15, 200K -- 1.5x the price for a smaller window) and on Claude Platform on AWS it is Sonnet 4.6 ($3/$15, 1M), so pin `--model claude-sonnet-5-5` (Bedrock: `anthropic.claude-sonnet-5-5`) or set `ANTHROPIC_DEFAULT_SONNET_MODEL` (Claude Code v2.1.284+).

> **Note**: Opus 5.5 is priced at $4/$20 - 20% below Opus 5 / 4.8 / 4.7 / 4.6 ($5/$25). The gap between models is smaller, so switching down to Haiku ($1/$5) provides a 4x savings from Opus 5.5 (5x from the $5/$25 Opus models), not 19x as it was historically. The Opus 4.7+ tokenizer (shared by Opus 5.5) can bump effective cost up to 35%. Anthropic's own models overview says to "start with Claude Opus 5.5 for most workloads"; the tree above starts with Sonnet 5.5 because it is half the per-token price.
>
> **Watch thinking on Opus 5.5 and Opus 5**: both think by default, and reasoning tokens bill as output ($20/1M on Opus 5.5, $25/1M on Opus 5). Opus 5.5 cannot turn thinking off -- lower `effort` instead (it defaults to `medium`). On Opus 5 you can send `thinking: {type: "disabled"}` (effort `high` or below). For mechanical work, dropping to Sonnet 5.5 is half the per-token price of Opus 5.5.

---

## Platform Comparison

| Feature | Anthropic API | Claude Platform on AWS | AWS Bedrock | Google Vertex AI | Claude Code |
|---------|:---:|:---:|:---:|:---:|:---:|
| Standard pricing | Base rates | Same (CCU billing) | Same (global) / +10% (regional) | Same (global) / +10% (regional) | Included in plan |
| Opus 5.5 availability | **Yes** | **Yes** | **Yes** (`anthropic.claude-opus-5-5`) | **Yes** | Via `/model` |
| Opus 5 availability | **GA** | **GA** | **GA** (`anthropic.claude-opus-5`) | **GA** | Via `/model` |
| Sonnet 5.5 availability | **Yes** | **Yes** | **Yes** (`anthropic.claude-sonnet-5-5`) | **Yes** | Via `/model` (v2.1.284+) |
| Sonnet 5 availability | GA | GA | GA | GA | Via `/model` |
| Haiku 4.5 availability | GA | GA | GA | GA | Via `/model` |
| 1M context | Yes (Opus 5.5/5/4.8/4.7/4.6, Sonnet 5.5/5/4.6) | Yes | Yes | Yes | Yes |
| Fast Mode (research preview) | **Yes (Opus 5.5 + 5 + 4.8, 2x)** | No | No | No | (depends on plan) |
| Batch API (50% off) | Yes | No | Yes | Yes | N/A |
| Prompt caching | Yes | Yes | Yes | Yes | Automatic |
| Data-residency premium | +10% (`inference_geo: "us"`, 4.6+ models) | +10% (`inference_geo: "us"`) | Bedrock regional pricing | Vertex regional pricing | -- |
| Fable 5.1 availability | **GA** | **GA** | **GA** | **GA** | Via `/model` (plan/API-key dependent) |
| Mythos 5 | Glasswing only | Glasswing only | Glasswing only | Glasswing only | -- |

> **Bedrock / Vertex**: Same models, same capabilities. Global (cross-region) inference matches API pricing. Regional inference profiles add ~10%. The +10% premium scope is **Sonnet 4.5+, Haiku 4.5+, Opus 4.5+, and all future models**; older models retain their existing pricing.
>
> **Opus 5.5 model IDs**: `anthropic.claude-opus-5-5` on Bedrock; `claude-opus-5-5` on the Claude API, Google Cloud, Microsoft Foundry, and Claude Platform on AWS.
>
> **Opus 5 on Bedrock**: **Generally available** via Claude in Amazon Bedrock (the Messages-API endpoint) with model ID `anthropic.claude-opus-5`. The legacy InvokeModel/Converse path with the `us.anthropic.claude-opus-5` cross-region inference profile works for backward compatibility. Google Cloud uses `claude-opus-5`. (Fast Mode is Claude API + Managed Agents only -- not on Bedrock or Vertex.)
>
> **Claude Platform on AWS**: Anthropic-operated alternative on AWS Marketplace, billed in **Claude Consumption Units (CCU)** at $0.01 per CCU. Token usage is rated in USD at standard per-model rates, then converted to CCUs. Typically gets same-day feature parity with the Anthropic API. Fast Mode and Batch API are NOT available on this platform.

---

## Cost Formula

```
Turn Cost = (Input Tokens x Input Price) + (Output Tokens x Output Price)

Where Input Tokens =
    System Prompt (~3,500 tokens, fixed)
  + CLAUDE.md (~7 tokens/line x number of lines)
  + Conversation History (grows each turn)
  + Tool Results (file contents, search results, command output)
  + MCP Responses (if using MCP servers)

Session Cost = Sum of all turns
             - Prompt Cache Savings (up to 90% on repeated input;
                                     95% on Opus 5.5, 97.5% on Fable 5.1)
```

---

## Quick Copy-Paste Configs

### Minimal Read deny rules (`.claude/settings.json`)

`.claudeignore` is not a Claude Code feature -- Claude Code never reads it. The documented way to keep Claude's file tools out of a path is `permissions.deny` with `Read(...)` rules:

```json
{
  "permissions": {
    "deny": [
      "Read(./node_modules/**)",
      "Read(./dist/**)",
      "Read(./build/**)",
      "Read(./coverage/**)",
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(*.min.js)",
      "Read(./package-lock.json)"
    ]
  }
}
```

Patterns use gitignore syntax: `./path` is relative to the project, `**` crosses directories, and a bare name such as `Read(.env)` matches at any depth. The rules also cover `cat`/`head`/`tail`/`sed` in Bash. No published measurement exists for what they save -- it depends on how often Claude would otherwise open those files. Migrating a `.claudeignore`: `dir/` becomes `Read(./dir/**)`, any other line containing `/` becomes `Read(./line)` (strip a leading `/`), and a bare name or glob becomes `Read(line)`. Skip blank lines, `#` comments and `!` negations.

### Budget-Conscious Launch Command

```bash
# Daily development on the cheaper model
claude --model sonnet

# Quick fixes with cheapest model
claude --model haiku

# Scripted or CI runs: hard dollar cap (--max-budget-usd works in print mode only)
claude -p --model sonnet --max-budget-usd 5 "fix the failing lint errors"
```

Interactive sessions have no dollar-cap flag: watch `/usage`, or use a PreToolUse budget hook ([hooks/budget-tracker.sh](hooks/budget-tracker.sh)).

### Cost-Saving CLAUDE.md Header

```markdown
# Project: MyApp

Tech: TypeScript, React 19, Node 22, PostgreSQL
Style: ESLint + Prettier (run `npm run lint` before committing)
Tests: Vitest - run `npm test` for unit, `npm run e2e` for Playwright
Build: `npm run build` - must pass before PR

## Key Rules
- Prefer editing existing files over creating new ones
- Always add tests for new functions
- Use existing patterns from nearby files as reference
```

> That is 10 lines. It gives Claude everything it needs. Every extra line costs you tokens on every turn.

---

## Session Workflow for Minimum Cost

```
1. Start session       → claude --model sonnet
2. Complex problem?    → /model opus (switch up temporarily)
3. Plan first          → Shift+Tab to toggle Plan Mode
4. Be specific         → Reference exact files, line numbers, function names
5. Batch changes       → Group related edits into one prompt
6. Monitor             → /usage (check token consumption)
7. Getting long?       → /compact (summarize and reset context)
8. Simple task?        → /model haiku (switch down temporarily)
9. New topic?          → Start a fresh session
10. Done               → Check /usage - learn your patterns
```

---

## Numbers Worth Memorizing

| Fact | Number |
|------|--------|
| Fable 5.1 output is ___ per 1M tokens | **$50** (2.5x Opus 5.5) |
| Fable 5.1 cache read is ___ per 1M tokens | **$0.25** (0.025x -- the deepest discount; Opus 5.5 reads at 0.05x) |
| Opus 5.5 output is ___ per 1M tokens | **$20** (Opus 5 / 4.8: $25) |
| Opus 5.5 cache read is ___ per 1M tokens | **$0.20** (0.05x, 95% off) |
| Haiku 4.5 is ___ cheaper than Opus 5.5 on input | **4x** (5x vs legacy Opus 5, 10x vs Fable 5.1) |
| Opus 5.5 / Opus 5 / Sonnet 5.5 minimum cacheable prompt | **512 tokens** (half the 1,024 of Opus 4.8 and Sonnet 5) |
| Output tokens cost ___ more than input | **5x** |
| Prompt cache discount | **90%** (95% on Opus 5.5, 97.5% on Fable 5.1 / Mythos 5.1) |
| CLAUDE.md loads on every ___ | **turn** |
| CLAUDE.md size guidance per file | **under 200 lines** (Anthropic's guidance; CLAUDE.md is never truncated -- the only size cap is that Claude Code skips a file over 4 MiB) |
| Auto memory (`MEMORY.md`) loaded at session start | **first 200 lines or 25KB**, whichever comes first -- the only truncation |
| 1 line of code is roughly ___ tokens | **~10** |
| Token estimation rule of thumb | **~1 token per 4 bytes** of text |
| Opus 4.7+ tokenizer overhead vs older models | **up to +35%** |
| 150-line CLAUDE.md per turn is roughly | **~1,050 tokens** |
| 50-turn session CLAUDE.md cost (Sonnet 4.6) | **~$0.16** |
| 50-turn session CLAUDE.md cost (Opus 5.5, pre-cache) | **~$0.21** (~$0.26 on Opus 5; factor +35% for new tokenizer) |
| Average tool result size | **500-5,000 tokens** |
| Compaction trigger threshold | **~10,000 tokens** of compactable content |
| Messages preserved after /compact | **4 most recent** |
| Fable 5.1 / Fable 5 / Opus 5.5 / 5 / 4.8 / 4.7 / 4.6 / Sonnet 5.5 / Sonnet 5 max output per turn | **128K tokens** |
| Sonnet 4.6 / 4.5 / Haiku 4.5 max output per turn | **64K tokens** |

---

## Output Token Optimization

Output tokens cost 5x more than input across all models. Most strategies above target input -- these target the expensive side.

| Strategy | Savings (output) | How |
|----------|:----------------:|-----|
| **Use a brevity skill (e.g. caveman)** | 65% (caveman's own claim, not measured here) | System prompt that strips filler, pleasantries, and hedging from responses. Technical accuracy unchanged. See [caveman](https://github.com/JuliusBrussee/caveman) |
| **"Be concise" in CLAUDE.md** | 20-40% | Add "Be concise. Skip explanations unless asked." to your CLAUDE.md. Simple but effective |
| **Batch outputs** | 10-20% | "Rename X in all files" (one response) vs 12 individual rename requests (12 responses) |
| **Suppress explanations** | 15-30% | "Just show the code, no explanation" or "diff only" for mechanical tasks |
| **Use Plan Mode wisely** | 10-20% | Plan Mode output is cheaper than failed code generation + correction cycles |

> **Research backing**: A March 2026 study ([arXiv:2604.00025](https://arxiv.org/abs/2604.00025)) found that brevity constraints actually *improved* model accuracy by 26 percentage points on certain benchmarks. Less verbose does not mean less correct.

### CLAUDE.md Compression

Your CLAUDE.md loads on every turn as input tokens. Applying brevity rules to it compounds savings:

```
BEFORE (68 chars):
"This project uses React with TypeScript. Always use functional components."

AFTER (42 chars, same info):
"React + TypeScript. Functional components only."
```

Every character saved in CLAUDE.md saves tokens on every turn of every session. At 30 turns/session and 3 sessions/day, a 1,000-character reduction saves ~165,000 input tokens/month.

---

## Emergency Cost Reduction

Already spending too much? Do these right now:

1. **Switch to Haiku** for the rest of the session: `/model haiku`
2. **Run `/compact`** to shrink conversation history
3. **Start a new session** if context is bloated beyond recovery
4. **Set a hard cap**: `claude -p --max-budget-usd 2 "..."` for scripted runs, or a budget hook ([hooks/budget-tracker.sh](hooks/budget-tracker.sh)) for interactive sessions
5. **Audit your CLAUDE.md** - delete anything Claude does not need on every turn

---

## Links

| Resource | Link |
|----------|------|
| Getting Started (5 min) | [guides/00-getting-started.md](guides/00-getting-started.md) |
| Understanding Costs (deep dive) | [guides/01-understanding-costs.md](guides/01-understanding-costs.md) |
| Context Optimization | [guides/02-context-optimization.md](guides/02-context-optimization.md) |
| Model Selection Guide | [guides/03-model-selection.md](guides/03-model-selection.md) |
| Workflow Patterns | [guides/04-workflow-patterns.md](guides/04-workflow-patterns.md) |
| Team Budgeting | [guides/05-team-budgeting.md](guides/05-team-budgeting.md) |
| Three-Tier Task Routing | [guides/10-task-routing.md](guides/10-task-routing.md) |
| Speed vs Cost | [guides/11-speed-vs-cost.md](guides/11-speed-vs-cost.md) |
| CLAUDE.md Templates | [templates/CLAUDE.md/](templates/CLAUDE.md/) |
| Token Estimator Tool | [tools/token-estimator/](tools/token-estimator/) |
| Usage Analyzer Tool | [tools/usage-analyzer/](tools/usage-analyzer/) |
| claude-rate (local setup rater) | [tools/claude-rate/](tools/claude-rate/) |
| Caveman skill (output tokens) | [github.com/JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) |

---

*This cheatsheet covers the strategies. For the reasoning and benchmarks behind each one, read the full guides.*
