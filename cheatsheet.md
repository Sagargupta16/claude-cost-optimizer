# Claude Code Cost Optimization Cheatsheet

> One-page quick reference. Print it, bookmark it, pin it. Every strategy links to a detailed guide.
>
> **Pricing verified: 2026-11-10.** Sources: [platform pricing](https://platform.claude.com/docs/en/about-claude/pricing), [models overview](https://platform.claude.com/docs/en/about-claude/models/overview), [what's new in Fable 5.2](https://platform.claude.com/docs/en/models/fable-5-2/whats-new-fable-5-2), [release notes](https://platform.claude.com/docs/en/release-notes/overview), [model deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations), [Opus 5.5 overview](https://platform.claude.com/docs/en/models/opus-5-5/overview), [Sonnet 5.5 overview](https://platform.claude.com/docs/en/models/sonnet-5-5/overview), [what's new in Sonnet 5.5](https://platform.claude.com/docs/en/models/sonnet-5-5/whats-new-sonnet-5-5), [Haiku 5.5 overview](https://platform.claude.com/docs/en/models/haiku-5-5/overview), [what's new in Haiku 5.5](https://platform.claude.com/docs/en/models/haiku-5-5/whats-new-haiku-5-5), [API credits for subscribers](https://platform.claude.com/docs/en/about-claude/api-credits-for-subscribers), [Claude Code model config](https://code.claude.com/docs/en/model-config), [migrating to Opus 5.5](https://platform.claude.com/docs/en/models/opus-5-5/migration-guide) (with its "from Opus 5" and "from Opus 4.8" sections), [fast mode](https://platform.claude.com/docs/en/build-with-claude/fast-mode), [prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching), [Fable 5.1 overview](https://platform.claude.com/docs/en/models/fable-5-1/overview), [Fable 5 overview](https://platform.claude.com/docs/en/models/fable-5/overview). Plans re-read 2026-11-01: [Claude pricing](https://claude.com/pricing), [Ultra plan](https://support.claude.com/en/articles/17728952-what-is-the-ultra-plan), [usage bundles](https://support.claude.com/en/articles/14246112-buy-usage-bundles), [monthly API credits](https://support.claude.com/en/articles/17154008-monthly-api-credits-for-max-ultra-and-team-plans). Fast mode, lifecycle and Claude Code notes re-read 2026-11-10: [Claude Code fast mode](https://code.claude.com/docs/en/fast-mode), [Claude Code prompt caching](https://code.claude.com/docs/en/prompt-caching), [Claude Code changelog](https://code.claude.com/docs/en/changelog).

---

## Token Pricing At a Glance

| Model | Input / 1M tokens | Output / 1M tokens | Cache Hit / 1M | 5m Cache Write | 1h Cache Write | Context | Max Output | Min cache | Relative Cost |
|-------|:-----------------:|:-------------------:|:--------------:|:--------------:|:--------------:|:-------:|:----------:|:---------:|:-------------:|
| **Fable 5.2** (highest capability) | $8.00 | $40.00 | **$0.20** | $10.00 | $16.00 | 1M | 128K | 512 | 2x baseline |
| **Fable 5.1** (legacy) | $10.00 | $50.00 | **$0.25** | $12.50 | $20.00 | 1M | 128K | 512 | 2.5x baseline |
| **Fable 5** (legacy) | $10.00 | $50.00 | $1.00 | $12.50 | $20.00 | 1M | 128K | 512 | 2.5x baseline |
| **Mythos 5** (limited, verification required) | $10.00 | $50.00 | $1.00 | $12.50 | $20.00 | 1M | 128K | 512 | 2.5x baseline |
| **Opus 5.5** (Opus flagship, recommended default) | $4.00 | $20.00 | **$0.20** | $5.00 | $8.00 | 1M | 128K | **512** | 1x (baseline) |
| **Opus 5** (legacy) | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1M | 128K | 512 | 1.25x baseline |
| **Opus 4.8** (legacy) | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1M | 128K | 1,024 | 1.25x baseline |
| **Opus 4.7** | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1M | 128K | 2,048 | 1.25x baseline |
| **Opus 4.6** | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1M | 128K | 4,096 | 1.25x baseline |
| **Opus 4.5** | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 200K | 64K | 4,096 | 1.25x baseline |
| Opus 4.1 (retired 2026-08-05, still on Bedrock + Google Cloud) | $15.00 | $75.00 | $1.50 | $18.75 | $30.00 | 200K | 32K | 1,024 | 3.75x baseline |
| **Sonnet 5.5** (Sonnet flagship) | $2.00 | $10.00 | **$0.10** | $2.50 | $4.00 | 1M | 128K | **512** | **2x cheaper** |
| **Sonnet 5** (legacy) | $2.00 | $10.00 | $0.20 | $2.50 | $4.00 | 1M | 128K | 1,024 | **2x cheaper** |
| **Sonnet 4.6** | $3.00 | $15.00 | $0.30 | $3.75 | $6.00 | 1M | 64K | 1,024 | **~1.3x cheaper** |
| **Sonnet 4.5** (deprecated) | $3.00 | $15.00 | $0.30 | $3.75 | $6.00 | 200K | 64K | 1,024 | **~1.3x cheaper** |
| **Haiku 5.5** (prompt <= 100K tokens) | $0.10 | $0.50 | $0.01 | $0.125 | $0.20 | 1M | 128K | **512** | **40x cheaper** |
| **Haiku 5.5** (prompt > 100K tokens) | $0.50 | $2.50 | $0.05 | $0.625 | $1.00 | 1M | 128K | 512 | **8x cheaper** |
| **Haiku 4.5** (legacy) | $1.00 | $5.00 | $0.10 | $1.25 | $2.00 | 200K | 64K | 4,096 | **4x cheaper** |
| **Fable 5.2 (Fast Mode)** | $16.00 (2x) | $80.00 (2x) | $0.40 | $20.00 | $32.00 | 1M | 128K | 512 | 4x baseline |
| **Opus 5.5 (Fast Mode)** | $8.00 (2x) | $40.00 (2x) | $0.40 | $10.00 | $16.00 | 1M | 128K | 512 | 2x baseline |
| **Opus 5 / 4.8 (Fast Mode; 4.8's removed 2026-11-30)** | $10.00 (2x) | $50.00 (2x) | $1.00 | $12.50 | $20.00 | 1M | 128K | 512 / 1,024 | 2.5x baseline |
| **Mythos Preview** (deprecated, no retirement date) | $25.00 | $125.00 | $2.50 | $31.25 | $50.00 | 1M | -- | 2,048 | 6.25x baseline |

> **Relative Cost baseline is Opus 5.5** ($4/$20), the current Opus flagship. Output tokens cost **5x more** than input tokens across all current models. Reducing Claude's verbosity is high-leverage. The Fast Mode cache columns are computed, because the [pricing page](https://platform.claude.com/docs/en/about-claude/pricing) says prompt caching multipliers apply on top of fast mode pricing (read 2026-11-10): Fable 5.2 $16 x 0.025 = $0.40 hit, $16 x 1.25 = $20 5m write, $16 x 2 = $32 1h write; Opus 5.5 $8 x 0.05 = $0.40 hit, $8 x 1.25 = $10 5m write, $8 x 2 = $16 1h write; Opus 5 / 4.8 $10 x 0.1, x 1.25 and x 2.
>
> **1M context on Opus 5.5 / 5 / 4.8 / 4.7 / 4.6 / Sonnet 5.5 / Sonnet 5 / Sonnet 4.6 is at standard rates** -- no long-context premium. (Earlier "2x over 200K" pricing is obsolete.) **Haiku 5.5 has 1M context but is the exception**: a prompt over 100K tokens bills at $0.50/$2.50 instead of $0.10/$0.50. **Haiku 4.5, Sonnet 4.5, Opus 4.5, and Opus 4.1 are 200K-context only.** **Sonnet 5** (`claude-sonnet-5`) is **$2/$10 permanently** -- the launch intro rate became the standard price and the rise to $3/$15 was cancelled.
>
> **Cache pricing math**: 5m write = 1.25x base input; 1h write = 2x base input; cache hit/refresh = 0.1x base input, except **0.05x on Opus 5.5 and Sonnet 5.5** and **0.025x on Fable 5.2 / Mythos 5.2 / Fable 5.1 / Mythos 5.1** (three multipliers, so read the per-model rate; on Haiku 5.5 it is 0.1x of whichever tier the request falls in). So a 5m cache pays off after 1 reuse, a 1h cache after 2 reuses. Multipliers stack with Batch (50% off) and data residency (+10%).
>
> **Min cache column = minimum cacheable prompt length.** Below it, a `cache_control` block does nothing -- no error, no discount, full input price every turn. Opus 5.5, Opus 5 and Sonnet 5.5 halve the threshold of Opus 4.8 and Sonnet 5 (1,024 -> **512**), so prompts that never cached on those start caching for free. Haiku 5.5 sits at 512 too, an 8x drop from Haiku 4.5's 4,096. Legacy Haiku 4.5 / Opus 4.6 / Opus 4.5 need 4,096 tokens before caching does anything at all.
>
> **Opus 5.5 / 5 / 4.8 / 4.7 tokenizer**: The tokenizer introduced with Opus 4.7 produces **about 30% more tokens** for the same text ([Anthropic's pricing page](https://platform.claude.com/docs/en/about-claude/pricing); the [Opus 4.7 launch post](https://www.anthropic.com/news/claude-opus-4-7) put it at roughly 1.0-1.35x by content type). Effective per-task cost is higher than posted pricing implies. Budget accordingly when comparing 5.5 / 5 / 4.8 / 4.7 to 4.6 / Sonnet 4.6. Haiku 5.5 uses the same newer tokenizer: about **30% more tokens than Haiku 4.5** for the same text.
>
> **Fable 5.2** (released 2026-11-09, `claude-fable-5-2`): the most capable widely released model; Fable 5.1 is now legacy (Active, not deprecated, still $10/$50). **$8/$40, 20% below Fable 5.1 on every rate and exactly 2x Opus 5.5** (Fable 5.1 was 2.5x). Cache hit **$0.20 (0.025x base input)**, the same dollar rate as Opus 5.5's; 5m write $10, 1h write $16, Batch $4/$20, Fast Mode $16/$80, min cacheable prompt 512. Anthropic still says to start with Opus 5.5 and move to Fable 5.2 when evals on Opus at higher effort fall short. What changes your bill: (1) adaptive thinking is always on, and at `high` effort or above it thinks before almost every reply, so lower effort for easy turns (API default `high`, Claude Code default `medium`); (2) it delegates readily to subagents when a prompt invites it, and Anthropic warns that "subagents can account for a large part of what a session costs"; (3) editing earlier turns invalidates its thinking blocks on every account, and only Fable 5.2 and Mythos 5.2 read them, so moving the conversation to any other model drops them (unbilled) -- keep history append-only. Forced `tool_choice` returns a **400**, and so does `computer_20251124` everywhere except Bedrock. Requires 30-day data retention. In Claude Code the `fable` alias is Fable 5.2 from v2.1.321. Earliest retirement: not sooner than 2027-11-09 ([what's new in Fable 5.2](https://platform.claude.com/docs/en/models/fable-5-2/whats-new-fable-5-2), read 2026-11-10).
>
> **Opus 5.5** (released 2026-09-22): the current Opus-tier flagship -- Anthropic's models overview now says to "start with Claude Opus 5.5 for most workloads". **$4/$20, 20% below Opus 5's $5/$25** (the first Opus price cut since [Opus 4.5](https://www.anthropic.com/news/claude-opus-4-5) lowered $15/$75 to $5/$25 on 2025-11-24). Cache hit **$0.20 (0.05x base input, 95% off)**, 5m write $5, 1h write $8, Batch $2/$10, Fast Mode $8/$40 (generally available since 2026-10-15, no beta header), min cacheable prompt 512. What changes your bill: (1) **adaptive thinking is always on** -- `thinking: {type:"disabled"}` and `budget_tokens` both return a **400**, so code that disabled thinking on Opus 5 now pays for thinking tokens (billed as output); (2) **default effort drops to `medium`** (Opus 5 defaulted to `high`), so a request that omits effort thinks less than it did -- effort is the only control; (3) forced `tool_choice` (`any`/`tool`), non-default sampling params, and assistant prefill all return a **400**; (4) **no Priority Tier** (Opus 4.8 keeps it). Re-baseline cost after migrating. Knowledge cutoff Jun 2026. Earliest retirement: not sooner than 2027-09-22.
>
> **Sonnet 5.5** (released 2026-09-28): the current Sonnet flagship; Sonnet 5 is now legacy. **$2/$10, the same as Sonnet 5**, with the same cache writes (5m $2.50, 1h $4), Batch ($1/$5) and tokenizer -- but since 2026-10-07 cache hits read at **$0.10 (0.05x base input, 95% off)**, half Sonnet 5's $0.20, so migrating never costs more at the posted rate and cached input gets cheaper. Min cacheable prompt **512** (Sonnet 5: 1,024), tool-use system prompt 286 tokens (Sonnet 5: 354), no Fast Mode. Adaptive thinking is on by default at effort `high` on the Claude API (Claude Code's own default for Sonnet 5.5 is `medium`, [model config](https://code.claude.com/docs/en/model-config), read 2026-11-01), reasoning bills as output at $10/1M, and effort levels are recalibrated -- re-run your effort sweep rather than carrying a Sonnet 5 setting over. What returns a **400** when Sonnet 5 code is carried over: (1) `thinking: {type:"disabled"}` and manual `budget_tokens` -- the lowest setting is `thinking: {type:"between_tools"}`, accepted only at `low`/`medium`/`high` effort; (2) forced `tool_choice` (`any`/`tool`) and non-default sampling params; (3) replaying a Sonnet 5.5 thinking block after editing earlier history -- keep conversations append-only; (4) `computer_20251124` on the Claude API and Google Cloud (use `computer_toolset_20260801`); (5) Opus 4.8, Opus 4.7, Sonnet 5 or Haiku 5.5 as the advisor for a Sonnet 5.5 executor (read 2026-11-01). Mid-conversation tool changes (beta, header `inline-tools-2026-09-15`), system messages and per-message effort (beta) work on Sonnet 5.5, not Sonnet 5, without losing the prompt cache. Knowledge cutoff Jun 2026. Earliest retirement: not sooner than 2027-09-28.
>
> **Haiku 5.5** (released 2026-10-07): the current Haiku; Haiku 4.5 is now legacy. **The first model priced by prompt length: $0.10/$0.50 up to 100K prompt tokens, $0.50/$2.50 above.** Prompt length counts every input token, cache reads and writes included, and each request is priced on its own, so a 100,001-token prompt pays 5x the input rate of a 100,000-token one ($0.050 vs $0.010 of input) and 5x the output rate, even when most of it is a cache hit. Up to 100K: cache hit $0.01, 5m write $0.125, 1h write $0.20, Batch $0.05/$0.25; above: $0.05, $0.625, $1.00, $0.25/$1.25. Per token that is 10x cheaper than Haiku 4.5 below 100K and 2x above, but the newer tokenizer makes the same text about 30% more tokens, so roughly 7.7x and 1.5x per task (computed: 10 / 1.3 and 2 / 1.3); against Sonnet 5.5 it is 20x / 4x, against Opus 5.5 40x / 8x. 1M context, 128K max output (300K on Batch with `output-300k-2026-03-24`), min cacheable prompt **512** (Haiku 4.5: 4,096), no Fast Mode. Adaptive thinking is on by default at effort `medium`; `thinking: {type:"disabled"}` still works on the API at `high` or below, but Claude Code cannot turn it off. What returns a **400** when Haiku 4.5 code is carried over: (1) manual `budget_tokens`; (2) non-default sampling params; (3) assistant prefill; (4) `computer_20250124` on the Claude API, Google Cloud and Amazon Bedrock (use `computer_toolset_20260801`, or `computer_20251124` on Bedrock; read 2026-11-01); (5) replaying thinking blocks after editing earlier turns -- keep conversations append-only. Forced tool use still works. Keep Haiku prompts under 100K: short subagent and classification calls are where it wins. Knowledge cutoff Jun 2026. Earliest retirement: not sooner than 2027-10-07.
>
> **Opus 5** (GA 2026-07-24, **legacy since the Opus 5.5 launch**): the previous Opus-tier flagship. **$5/$25 -- identical to Opus 4.8**, so moving to it from 4.8 was free at the posted rate, but three behaviors change your bill: (1) **adaptive thinking is ON by default** when you omit the `thinking` param, and reasoning tokens bill as output at $25/1M with `max_tokens` capping thinking **plus** text (raise it to 64K+ at `xhigh`/`max`); (2) `thinking: {type:"disabled"}` is legal only at effort `high` or below -- combining it with `xhigh`/`max` returns a **400**; (3) min cacheable prompt is 512 tokens. Output also runs longer than 4.8 by default, so re-tune verbosity instructions, and drop any "verify your work" instruction you carried over (it self-verifies). Ships cybersecurity classifiers -- pair with the server-side `fallbacks` param (beta `server-side-fallback-2026-07-01`) to auto-retry cyber refusals on Opus 4.8. Batch $2.50/$12.50. Knowledge cutoff May 2026. The beta `mid-conversation-tool-changes-2026-07-01` lets tools change between turns without busting the cache; the current header is `inline-tools-2026-09-15`, and the older one still works for changes that name a tool by reference ([Opus 5.5 migration guide](https://platform.claude.com/docs/en/models/opus-5-5/migration-guide), read 2026-11-01).
>
> **Fable 5** (GA 2026-06-09, now legacy behind Fable 5.1, at the same price, and Fable 5.2): a Mythos-class tier above Opus at **$10/$50 (2x legacy Opus 5, 2.5x Opus 5.5)**. Always-on adaptive thinking (no `disabled`; control depth with `effort`, `low` through `xhigh`/`max`). Safety classifiers may decline requests: HTTP 200 + `stop_reason: "refusal"`; **pre-output refusals cost $0**; the beta `fallbacks` param retries on another model server-side, and fallback credit refunds the cache-switch cost. No Fast Mode; Batch supported ($5/$25). Requires 30-day data retention. **Cost note**: for cost-sensitive work, Opus 5.5 at 2.5x less is the sweet spot -- reach for Fable 5.2 ($8/$40, 20% below Fable 5, and a fifth of its $1 cache-read rate at $0.20) when the task genuinely needs the extra capability (hardest reasoning, longest agentic runs).
>
> **Mythos 5**: same model, specs, and price as Fable 5 but **without safety classifiers**. Mythos 5.2 has the same capabilities and prices as Fable 5.2, Fast Mode included. Mythos 5, 5.1 and 5.2 require verification through Anthropic's verification programs, such as the [Cyber Verification Program](https://www.anthropic.com/news/cyber-verification-program), which on 2026-10-06 grew into Defense, Red Team and Specialized Access tiers; [Project Glasswing](https://www.anthropic.com/glasswing) members move to Specialized Access (read 2026-11-01). Successor to Mythos Preview, which is **deprecated** with no published retirement date.
>
> **Opus 4.8 status**: moved to **legacy** by the Opus 5 launch, and Opus 5.5 now costs 20% less ($4/$20), so there is no cost reason to stay -- migrate unless your prompts are tuned to this snapshot, you need thinking off (Opus 5.5 never allows it; Opus 5 rejects it at `xhigh`/`max`), or you need Priority Tier (Opus 5.5 has none). Still the server-side fallback target for Opus 5 cyber refusals. Its Fast Mode was deprecated on 2026-10-30 and is removed on 2026-11-30, after which `speed: "fast"` on `claude-opus-4-8` errors with no fallback ([fast mode](https://platform.claude.com/docs/en/build-with-claude/fast-mode), read 2026-11-01). Earliest retirement 2027-05-28.
>
> **Fast Mode** (`speed: "fast"`): **Fable 5.2, Mythos 5.2, Opus 5.5, Opus 5 and Opus 4.8 only**. **Fable 5.2** has it with no beta header on the Claude API, both Claude Models on Google Cloud offerings (Google sets the price on the Google-managed one) and Microsoft Foundry hosted on Anthropic, where it is a separate model, `claude-fable-5-2-fast`. **Opus 5.5 is generally available** (out of research preview since 2026-10-15, no beta header) on the Claude API (Messages and Managed Agents), Claude Models on Google Cloud (Anthropic managed) and Microsoft Foundry (hosted on Azure). **Opus 5 and Opus 4.8 are a research preview** on the Claude API only, behind the `fast-mode-2026-02-01` beta header; **Opus 4.8's fast mode was deprecated on 2026-10-30 and is removed on 2026-11-30**, after which `speed: "fast"` on `claude-opus-4-8` errors with no fallback. All at **2x their own base rate: $16 / $80 per MTok on Fable 5.2 and Mythos 5.2, $8 / $40 on Opus 5.5, $10 / $50 on Opus 5 and 4.8**, with caching and data-residency multipliers on top. Up to **2.5x output tokens/second** -- the gain is on OTPS, not time-to-first-token. **Opus 4.7 errors** on `speed: "fast"`; **Opus 4.6 silently runs standard speed at standard rates** (`usage.speed` returns `"standard"`). The old 6x Opus 4.7 / 4.6 Fast Mode tier no longer exists. NOT on Claude Platform on AWS, Bedrock, the Batch API or Priority Tier, and on Google Cloud (Google managed, formerly Vertex AI) only for Fable 5.2. Fast and standard speed keep separate caches, so each switch, including an automatic fallback to standard after a rate limit, can read the conversation uncached again. Dedicated rate limits via `anthropic-fast-*` response headers. Opus 5 access goes through your account manager or the [waitlist](https://claude.com/fast-mode); Opus 5.5 needs no request. In Claude Code, fast mode runs on Opus 5.5 / 5 / 4.8, not on Bedrock, Google Cloud, Foundry or Claude Platform on AWS, and on Fable 5.2 from v2.1.321 (`/fast` while on it); subscribers pay for it with usage credits only ([fast mode](https://platform.claude.com/docs/en/build-with-claude/fast-mode), [Claude Code fast mode](https://code.claude.com/docs/en/fast-mode), read 2026-11-10).
>
> **Subscriptions** (Free, Pro, Max, Ultra, Team, Enterprise; read 2026-11-01): Pro **$20/mo** (or **$200/yr**, $16.67/mo, 17% off; computed: 200 / 12 and 1 - 200 / 240). **Max $100/mo** (formerly Max 5x; 5x Pro usage every 5 hours and every week). **Ultra $200/mo** (formerly Max 20x, same price; 10x Pro usage every week, with no 5-hour limit for verified accounts). Max and Ultra bill monthly only. Claude Code is included on every paid plan, not on Free. On Max, Ultra and Team Premium, Fable 5.2, 5.1 and 5 use is included for at most half of the weekly limit; Pro and Team Standard pay for Fable with usage credits ([Fable on your plan](https://support.claude.com/en/articles/15424964-claude-fable-models-on-your-plan), read 2026-11-10). Fable 5.2 launch offers: Pro and Team Standard get Fable included through 2026-11-16 11:59 pm PT; Max, Ultra and Team Premium get one to three Fable limit resets by subscription length, expiring 2027-03-08 ([launch offers](https://support.claude.com/en/articles/17506494-claude-fable-5-2-launch-offers)). **Usage credits** (formerly extra usage) bill past the limits at API rates, with a monthly spend limit; **usage bundles** prepay them at a discount: $45 for $50 of usage, $200 for $250, $700 for $1,000. **Monthly API credits** (since 2026-10-07): Max $100, Ultra $200, Team $20 per Standard seat and $100 per Premium seat (pooled, capped at $500/month). They cover the Claude API in the linked Console org, including `claude -p` and the Agent SDK run with that org's API key, but **not interactive Claude Code** (terminal, IDE, desktop, web), usage credits, or Bedrock / Google Cloud / Foundry; they need 7 days on the plan and expire each month with no rollover; Free, Pro and Enterprise are not eligible. **Batch API**: 50% off both input and output. **Regional endpoints** (Bedrock / Google Cloud / Claude API `inference_geo: "us"`, scope = Sonnet 4.5+, Haiku 4.5+, Opus 4.5+, and all future models): +10% premium.

### Thinking Modes by Model

| Model | Extended thinking | Adaptive thinking | Default state |
|-------|:-----------------:|:-----------------:|:-------------:|
| **Fable 5.2** | No | Yes (always on) | **On, cannot disable** (effort defaults to `high` on the API, `medium` in Claude Code) |
| Fable 5.1 | No | Yes (always on) | On, cannot disable |
| Fable 5 | No | Yes (always on) | On, cannot disable |
| Mythos 5 | No | Yes (always on) | On, cannot disable |
| **Opus 5.5** | No | Yes (always on) | **On, cannot disable** (effort defaults to `medium`) |
| Opus 5 | No | Yes | **On by default** |
| Opus 4.8 | No | Yes | Off unless requested |
| Opus 4.7 | No | Yes | Off unless requested |
| Opus 4.6 | Yes | Yes | Off unless requested |
| Opus 4.5 | Yes | -- | Off unless requested |
| **Sonnet 5.5** | No | Yes | **On by default**, `disabled` returns 400 (effort defaults to `high` on the API, `medium` in Claude Code) |
| Sonnet 5 | No | Yes | Off unless requested |
| Sonnet 4.6 | Yes | Yes | Off unless requested |
| Sonnet 4.5 | Yes | -- | Off unless requested |
| **Haiku 5.5** | No | Yes | **On by default** (effort defaults to `medium`; `disabled` works at `high` or below, not in Claude Code) |
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

Verified 2026-11-10 against the [model deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations) page.

**Recently retired** (requests will fail):

| Model | Retired on | Migrate to |
|-------|:---------:|-----------|
| Opus 3 (`claude-3-opus-20240229`) | 2026-01-05 | Opus 5.5 |
| Sonnet 3.7 (`claude-3-7-sonnet-20250219`) | 2026-02-19 | Sonnet 5.5 |
| Haiku 3.5 (`claude-3-5-haiku-20241022`) | 2026-02-19 | Haiku 5.5 |
| Haiku 3 (`claude-3-haiku-20240307`) | 2026-04-20 | Haiku 5.5 |
| Sonnet 4 (`claude-sonnet-4-20250514`) | 2026-06-15 (still on Bedrock + Google Cloud) | Sonnet 5.5 |
| Opus 4 (`claude-opus-4-20250514`) | 2026-06-15 (still on Google Cloud) | Opus 5.5 |
| Opus 4.1 (`claude-opus-4-1-20250805`) | 2026-08-05 (still on Bedrock + Google Cloud) | Opus 5.5 |

**Deprecated** (still working, no longer recommended):

| Model | State | Migrate to |
|-------|:-----:|-----------|
| Sonnet 4.5 (`claude-sonnet-4-5-20250929`) | Deprecated; retirement scheduled for 2026-11-30 | Sonnet 5.5 |
| Mythos Preview (`claude-mythos-preview`) | Deprecated, no published retirement date | Mythos 5.2 or 5.1 (verification required) |

**Tentative retirement dates** (every model below is still **Active** -- these are dates to plan around, not deprecations):

| Model | Retirement date | Migration target |
|-------|:--------------:|-----------------|
| Haiku 4.5 (`claude-haiku-4-5-20251001`, legacy) | Active; no retirement announced (its earliest date, 2026-10-15, has passed) | Haiku 5.5 |
| **Haiku 5.5** (`claude-haiku-5-5`) | Not before **2027-10-07** | (current) |
| Opus 4.5 (`claude-opus-4-5-20251101`) | Not before 2026-11-24 | Opus 5.5 |
| Opus 4.6 (`claude-opus-4-6`) | Not before 2027-02-05 | Opus 5.5 |
| Sonnet 4.6 (`claude-sonnet-4-6`) | Not before 2027-02-17 | Sonnet 5.5 |
| Opus 4.7 (`claude-opus-4-7`) | Not before 2027-04-16 | Opus 5.5 |
| Opus 4.8 (`claude-opus-4-8`) | Not before 2027-05-28 | Opus 5.5 |
| **Fable 5.2** (`claude-fable-5-2`) | Not before **2027-11-09** | (current) |
| Fable 5.1 (`claude-fable-5-1`, legacy) | Not before 2027-09-01 | Fable 5.2 |
| Fable 5 (`claude-fable-5`) | Not before 2027-06-09 | Fable 5.2 |
| **Sonnet 5.5** (`claude-sonnet-5-5`) | Not before **2027-09-28** | (current) |
| Sonnet 5 (`claude-sonnet-5`) | Not before 2027-06-30 | Sonnet 5.5 |
| Opus 5 (`claude-opus-5`) | Not before 2027-07-24 | Opus 5.5 |
| **Opus 5.5** (`claude-opus-5-5`) | Not before **2027-09-22** | (current) |

> **Two models are deprecated.** Sonnet 4.5 was deprecated (announced 2026-09-30), with retirement scheduled for **2026-11-30** on the Claude API -- migrate to Sonnet 5.5, and note that Claude Code's `sonnet` alias still resolves to it on Bedrock, Google Cloud and Foundry. Mythos Preview is still functional and Anthropic publishes no retirement date for it; migrate to Mythos 5.2 or 5.1 (both need verification). Opus 4.1 retired on 2026-08-05. Every other model reads **Active** on the deprecations page. Haiku 4.5 is legacy but still Active: its earliest date, 2026-10-15, has passed with no retirement announced. The nearest date ahead is Opus 4.5 (not sooner than 2026-11-24) -- an earliest possible date to plan around, not a deadline Anthropic has committed to. These dates apply to Anthropic-operated platforms; Bedrock and Google Cloud (Google managed) set their own schedules. In both lifecycle tables in this file, "Migrate to" is this repo's pick (the current model of the same tier); the deprecations page's recommended replacement is Opus 4.8 for Opus 3, Opus 4 and Opus 4.1, and Haiku 4.5 for Haiku 3 and Haiku 3.5 (read 2026-11-01).
>
> **Off-Peak 2x Usage**: no promotion is running (none on the [pricing page](https://claude.com/pricing) or the Help Center usage articles, read 2026-11-01). The one documented event ran 2026-03-13 to 2026-03-28 and doubled 5-hour usage outside the weekday 8 AM - 2 PM ET peak (Help Center article 14063676, now offline). Watch the [Anthropic news page](https://www.anthropic.com/news) for any new one.
>
> **CLI Cost Controls**: `--max-budget-usd <amount>` caps spending per `claude -p` run (print mode only; interactive sessions ignore it). `--fallback-model <model>` switches to the model(s) you name when the primary is overloaded or unavailable; `fallbackModel` in settings persists the chain. `maxEffortLevel` in any settings file caps effort for every model or per model, on any plan and provider, and Enterprise admins can set per-role effort caps ([model config](https://code.claude.com/docs/en/model-config), read 2026-11-01).

---

## Legacy & Retired Models (reference only)

> Migration context for code still pinned to older model IDs. **Do not use these for new work** -- prices, IDs, and capabilities are kept here for archive value only.

### Recently retired (requests now fail)

| Model | Retired on | Last priced at (input / output per 1M) | Migrate to |
|-------|:---------:|:--------------------------------------:|-----------|
| Claude Opus 3 (`claude-3-opus-20240229`) | 2026-01-05 | $15 / $75 | Opus 5.5 |
| Claude Sonnet 3.7 (`claude-3-7-sonnet-20250219`) | 2026-02-19 | $3 / $15 | Sonnet 5.5 |
| Claude Haiku 3.5 (`claude-3-5-haiku-20241022`) | 2026-02-19 | $0.80 / $4 | Haiku 5.5 |
| Claude Haiku 3 (`claude-3-haiku-20240307`) | 2026-04-20 | $0.25 / $1.25 | Haiku 5.5 |
| Claude Sonnet 4 (`claude-sonnet-4-20250514`) | 2026-06-15 (still on Bedrock + Google Cloud) | $3 / $15 | Sonnet 5.5 |
| Claude Opus 4 (`claude-opus-4-20250514`) | 2026-06-15 (still on Google Cloud) | $15 / $75 | Opus 5.5 |
| Claude Opus 4.1 (`claude-opus-4-1-20250805`) | 2026-08-05 (still on Bedrock + Google Cloud) | $15 / $75 | Opus 5.5 |
| Claude Sonnet 3.5 v1 (`claude-3-5-sonnet-20240620`) | 2025-10-28 | $3 / $15 | Sonnet 5.5 |
| Claude Sonnet 3.5 v2 (`claude-3-5-sonnet-20241022`) | 2025-10-28 | $3 / $15 | Sonnet 5.5 |
| Claude Sonnet 3 (`claude-3-sonnet-20240229`) | 2025-07-21 | $3 / $15 | Sonnet 5.5 |
| Claude 2 / 2.1 (`claude-2.0`, `claude-2.1`) | 2025-07-21 | $8 / $24 | Opus 5.5 |
| Claude Instant 1.x | 2024-11-06 | $0.80 / $2.40 | Haiku 5.5 |
| Claude 1.x | 2024-11-06 | $8 / $24 | Haiku 5.5 |

### Deprecated (still working)

| Model | State | Priced at (input / output per 1M) | Migrate to |
|-------|:-----:|:--------------------------------:|-----------|
| Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`) | Deprecated; retirement scheduled for 2026-11-30 | $3 / $15 | Sonnet 5.5 |
| Claude Mythos Preview (`claude-mythos-preview`) | Deprecated, no published retirement date | $25 / $125 | Mythos 5.2 or 5.1 (verification required) |

Opus 4.1, deprecated 2026-06-05, retired on 2026-08-05 and is listed under "Recently retired" above. Every other model Anthropic still serves reads **Active**.

### Historical pricing patterns (no longer in effect)

The following pricing constructs were real but have since been retired or restructured. Listed here for migration context if you're reading older guides:

- **"2x input, 1.5x output above 200K"** long-context premium -- applied to Opus 4.1 and older. Obsolete on Opus 5.5 / 5 / 4.8 / 4.7 / 4.6, Sonnet 5.5, Sonnet 5, and Sonnet 4.6, which bill 1M context at standard rates. Haiku 5.5 is the current exception, with its own tier at 100K prompt tokens (5x input and output above it).
- **Opus 4.1 ($15/$75)** -- original "Opus 4.x" pricing, 3x the $5/$25 Opus rates and 3.75x Opus 5.5. **Retired 2026-08-05** on the Claude API (still served on Bedrock and Google Cloud). Migrate to Opus 5.5.
- **6x Fast Mode on Opus 4.7 / 4.6 ($30/$150)** -- removed at the Opus 5 launch. Opus 4.7 now errors on `speed: "fast"`; Opus 4.6 silently serves standard speed at standard rates. Fast Mode is Fable 5.2, Mythos 5.2 and Opus 5.5 / 5 / 4.8 only, all at 2x their own base rate, and Opus 4.8's is removed on 2026-11-30.
- **Bedrock-only ARN-versioned IDs** like `anthropic.claude-opus-4-20250514-v1:0` -- still resolve via the legacy InvokeModel/Converse path, but the new Mantle endpoint uses cleaner provider-prefixed IDs (`anthropic.claude-opus-5`).
- **Single endpoint type on Bedrock** -- pre-Sonnet-4.5, all Bedrock traffic was effectively "global". The +10% regional premium is a 4.5+ generation construct.

### Snapshots that are still active (not retired, but not the headline tier)

These models are GA and priced but generally not the recommended target for new work -- listed under "Legacy" because they're previous-generation snapshots:

| Snapshot | Pricing (input / output per 1M) | Context | Earliest retirement | Why use |
|----------|:-------------------------------:|:-------:|:-------------------:|---------|
| Fable 5.1 | $10 / $50 | 1M | 2027-09-01 | Previous Fable flagship -- Fable 5.2 is 20% cheaper on every rate. Claude Code's `fable` alias now resolves to Fable 5.2 (v2.1.321+) and saved Fable 5.1 picks move to `fable` on Pro and Max; select it by id with `/model claude-fable-5-1` |
| Opus 5 | $5 / $25 | 1M | 2027-07-24 | Previous flagship -- Opus 5.5 is 20% cheaper per token. Pin only if you need thinking disabled or forced `tool_choice`, both of which Opus 5.5 rejects |
| Opus 4.8 | $5 / $25 | 1M | 2027-05-28 | Older flagship -- same price as Opus 5. Pin only if prompts are tuned to it, you need thinking off at `xhigh`/`max`, or you need Priority Tier (Opus 5.5 has none). Fallback target for Opus 5 cyber refusals. Its Fast Mode is removed on 2026-11-30 |
| Opus 4.7 | $5 / $25 | 1M | 2027-04-16 | Pinned workloads. Fast Mode removed (errors) |
| Opus 4.6 | $5 / $25 | 1M | 2027-02-05 | Stable snapshot of the previous-tokenizer Opus. Fast Mode silently downgrades |
| Opus 4.5 | $5 / $25 | 200K | 2026-11-24 | Pinned workloads only |
| Sonnet 5 | $2 / $10 | 1M | 2027-06-30 | Previous Sonnet flagship -- same price as Sonnet 5.5. Pin only if you need thinking disabled or forced `tool_choice`, both of which Sonnet 5.5 rejects |
| Sonnet 4.6 | $3 / $15 | 1M | 2027-02-17 | Pinned workloads -- migrate to Sonnet 5.5 |
| Sonnet 4.5 | $3 / $15 | 200K | Scheduled for 2026-11-30 (deprecated) | Deprecated -- migrate to Sonnet 5.5. Still the `sonnet` alias on Bedrock, Google Cloud and Foundry |
| Haiku 4.5 | $1 / $5 | 200K | None announced (2026-10-15 has passed) | Legacy -- Haiku 5.5 is 10x cheaper per token up to 100K prompt tokens. Still the `haiku` alias on Claude Platform on AWS, Bedrock, Google Cloud and Foundry |

> Authoritative source for all dates: [Anthropic model deprecations page](https://platform.claude.com/docs/en/about-claude/model-deprecations).

---

## All Strategies - Ranked by Impact

### Tier 1: High Impact (Do These First)

| # | Strategy | Savings | Effort | Explanation | Skip when / backfires when | Guide |
|---|----------|:-------:|:------:|-------------|----------------------------|-------|
| 1 | **Use cheaper models for simple tasks** | 97.5% per moved task (per token); [Anthropic measured](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence) 1/20 per correct GPQA Diamond answer | 1 min | Run `claude --model haiku` for formatting, simple fixes, file lookups, and boilerplate - Haiku 5.5 costs 1/40th of Opus 5.5 per token up to 100K prompt tokens (1/8th above); judge by cost per completed task, since a cheap attempt that fails still bills | The cheap model fails and you retry: both attempts bill. A Haiku 5.5 prompt over 100K tokens pays 5x. A mid-task `/model` switch rebuilds the cache, so switch at a task boundary or use a subagent | [Model Selection](guides/03-model-selection.md) |
| 2 | **Delegate work to subagents** | No Claude Code figure ([cookbook](https://platform.claude.com/cookbook/cost-optimization-cost-optimization) loop: 78%) | 5 min | Subagent tool calls get their own isolated context; large file searches and multi-file reads happen outside your main conversation, keeping your primary context small. Subagents, the built-in Explore included, run on your main model unless you set `model: haiku`. Pinned definitions to copy: [templates/agents/](templates/agents/) | A small one-off lookup: the subagent's own startup prompt costs more than searching in place. Work that needs the main conversation's context. Anthropic measured Haiku 5.5 subagents on Opus 5.5 at 32% lower cost per attempt and about 4 points lower pass rate ([guide 07](guides/07-mcp-agent-costs.md)) | [Workflow Patterns](guides/04-workflow-patterns.md) |
| 3 | **Use Plan Mode before coding** | No published figure | 0 min | Press `Shift+Tab` to toggle Plan Mode - Claude thinks through the approach before writing code, preventing expensive trial-and-error cycles that waste output tokens | A one-line fix: the plan is extra output with no retry to prevent | [Workflow Patterns](guides/04-workflow-patterns.md) |
| 4 | **Trim CLAUDE.md to under 200 lines** | No published figure | 15 min | CLAUDE.md loads in full at session start and rides along as input on *every turn*. Anthropic's guidance: "target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence." Move workflow-specific instructions into skills or path-scoped `.claude/rules/` so they load on demand | It is already short, or the cut removes rules Claude needs: a wrong turn costs more than cached lines do (150 lines is $0.022 per 50-turn Opus 5.5 session, see [Numbers Worth Memorizing](#numbers-worth-memorizing)) | [Context Optimization](guides/02-context-optimization.md) |
| 5 | **Preserve prompt cache** | A break can cost more than no caching: a 25-token status line at the front of the system prompt made one run $4.24 instead of $0.59 ([Anthropic](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence)) | 5 min | Cached input tokens cost 90% less (95% on Opus 5.5 and Sonnet 5.5, 97.5% on Fable 5.2 and Fable 5.1). What breaks the cache: switching models, changing effort (except on Opus 5.5, Sonnet 5.5, Haiku 5.5 and Fable 5.1 and later with an API key or subscription; on Bedrock, Google Cloud's Agent Platform or a Claude apps gateway it breaks on those too), toggling fast mode (fast and standard keep separate caches), compaction ([prompt caching](https://code.claude.com/docs/en/prompt-caching), read 2026-11-10). Editing CLAUDE.md mid-session does *not* break it (the edit applies after `/clear`, `/compact` or a restart). Keep conversation flow linear. The opt-in [hooks/cache-guard.sh](hooks/cache-guard.sh) shows what a `/model` switch or a stale resume will cost in cache re-writes before the request that pays it | Never skip it, but don't keep a stale, bloated session alive for its sake: past the TTL the cache is cold anyway | [Understanding Costs](guides/01-understanding-costs.md) |

### Tier 2: Medium Impact (Set Up Once)

| # | Strategy | Savings | Effort | Explanation | Skip when / backfires when | Guide |
|---|----------|:-------:|:------:|-------------|----------------------------|-------|
| 6 | **Add `Read(...)` deny rules** | No published figure | 2 min | Add `permissions.deny` rules such as `Read(./node_modules/**)` and `Read(./dist/**)` to `.claude/settings.json` to keep Claude's file tools (and `cat`/`head`/`tail` in Bash) out of dependencies, build output, lock files, and `.env`. Scoped Read rules do not invalidate the prompt cache. The [permissions docs](https://code.claude.com/docs/en/permissions) say a `.claudeignore` file has no effect -- move its patterns into Read deny rules. A Read deny also blocks Edit and Write on that path, and does not cover commands that read without naming a file, such as `grep -r pattern .` | The path holds files Claude must read or edit: the deny blocks Edit and Write there too | [Context Optimization](guides/02-context-optimization.md) |
| 7 | **Use `/compact` regularly** | 32% on [Anthropic's](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence) long triage run (39% for pruning stale tool results); nothing on short loops | 0 min | Run `/compact` when conversation gets long (20+ turns) to summarize history and reset context window - prevents the quadratic growth of re-sent history. Compact at a natural break while the cache is warm: a cold-cache `/compact` reprocesses the whole history uncached. With the 1-hour cache, Claude Code also compacts a 200K+ token conversation left idle about 54 minutes, before the cache expires (idle compaction, v2.1.299; `"idleCompaction": false` turns it off) | Short loops (nothing measured there), or the cache has gone cold: the summary request then reprocesses the whole history uncached, and the summary loses detail | [Context Optimization](guides/02-context-optimization.md) |
| 8 | **Set budget caps** | 0%* | 1 min | Use `claude -p --max-budget-usd 5` for scripted runs (print mode only), a Console workspace spend limit, or a PreToolUse budget hook ([hooks/budget-tracker.sh](hooks/budget-tracker.sh)) to prevent runaway sessions. Claude Code has no spend-cap setting in settings.json. Does not save tokens directly but prevents surprise bills | Saves nothing by itself; a hard cap can stop a scripted run halfway through a change | [Understanding Costs](guides/01-understanding-costs.md) |
| 9 | **Create custom slash commands** | No published figure (commands load only when invoked and keep the cache) | 10 min | Define reusable commands in `.claude/commands/` for repeated workflows - avoids re-explaining the same instructions across sessions, saving input tokens each time | One-off instructions you will not repeat | [Workflow Patterns](guides/04-workflow-patterns.md) |
| 10 | **Use batch operations** | Each avoided turn saves one cache read of the whole context: $0.01 at 50K tokens on Opus 5.5 (computed: 50,000 x $0.20/M) | 5 min | Group related changes into single prompts instead of one-at-a-time requests - "rename X in all 12 files" beats 12 individual "rename X in this file" turns | The batched prompt turns vague: vague requests "trigger broad scanning" ([costs page](https://code.claude.com/docs/en/costs)) | [Workflow Patterns](guides/04-workflow-patterns.md) |

### Tier 3: Ongoing Habits (Compound Over Time)

| # | Strategy | Savings | Effort | Explanation | Skip when / backfires when | Guide |
|---|----------|:-------:|:------:|-------------|----------------------------|-------|
| 11 | **Write concise prompts** | No published figure ([Anthropic](https://code.claude.com/docs/en/costs): vague requests "trigger broad scanning") | Ongoing | Be specific and direct - "Add null check to `processOrder` in `src/orders.ts` line 47" beats "Can you look at the orders file and maybe add some error handling?" | Too terse to act on: a clarifying turn or a wrong guess costs more than the words saved | [Context Optimization](guides/02-context-optimization.md) |
| 12 | **Avoid reading entire large files** | 1 - lines read / file length per read (50 of 2,000 lines: 97.5% fewer tokens for that read) | Ongoing | Point Claude to specific line ranges or functions instead of letting it `Read` a 2000-line file - use "read lines 100-150 of X" or reference functions by name. See [Read Code by Intent](#read-code-by-intent) | Claude needs the whole file to change it safely; many small reads of one file can add up past one full read | [Context Optimization](guides/02-context-optimization.md) |
| 13 | **Start new sessions for new tasks** | About 23% for an 80-turn day split into eight sessions (derived from this repo's cache-aware calculator model); `/clear` itself [costs nothing](https://code.claude.com/docs/en/costs) | Ongoing | Fresh sessions have minimal context; a 50-turn session carries all prior history as input - start clean when switching tasks to avoid paying for irrelevant context. Resuming an old idle conversation reads it uncached; since v2.1.304 Pro and Max plans warn when that would use a noticeable share of the 5-hour limit. With state to keep, first ask for a 40-line handoff in `.claude/handoff.md` while the cache is warm ([templates/commands/handoff.md](templates/commands/handoff.md)) | The next task needs the old context while its cache is warm: a cache read of that prefix (0.05x input on Opus 5.5) is cheaper than reading the same files into a new session | [Understanding Costs](guides/01-understanding-costs.md) |
| 14 | **Use memory files over inline repeats** | No published figure | 5 min | Put project conventions in CLAUDE.md once rather than repeating "use single quotes" or "always add tests" in every prompt - say it once, reference forever | One-off rules: everything in CLAUDE.md loads on every turn | [Context Optimization](guides/02-context-optimization.md) |
| 15 | **Monitor with `/usage`** | Awareness | 0 min | Run `/usage` periodically to see token consumption in your current session - knowing where tokens go is the first step to reducing them. Its warnings (max effort, workflows, always-on context, large tool results) each name a one-line fix, and `f` applies them (v2.1.305); `/cost` and `/stats` are aliases. Console and Enterprise orgs can pull usage and cost by model, workspace, API key or user from the [Usage and Cost Analytics API](https://platform.claude.com/docs/en/manage-claude/usage-cost-analytics-api) (beta since 2026-10-29). To watch it live: `claude-rate --statusline` (claude-rate 0.4.0 or later) as the `statusLine` command shows cache time left, what a cold re-cache would add at list price, context fill and 5-hour/7-day pace ([templates/settings/statusline.json](templates/settings/statusline.json)); `claude-rate --burn` is the terminal view | -- | [Understanding Costs](guides/01-understanding-costs.md) |

### Read Code by Intent

Narrow first, then read only what the answer needs. These are habits, unmeasured: no published figure.

| Intent | First | Then |
|--------|-------|------|
| Locate | Workspace symbol search, if a code intelligence plugin is installed; else the Grep tool in `files_with_matches` or `count` mode. On macOS, Linux and WSL, where Grep is off by default: `git grep -l` / `git grep -c` (tracked files only) | Matching lines in the few files that hit |
| Understand | The plugin's symbol list for the file, or the match's line numbers | `Read` with `offset`/`limit`; read the body before trusting a signature |
| Modify | The plugin's find-references for the callers, else Grep | `Edit`, not a rewrite |
| Debug | Grep the exact error string | Read the frames it points to |

Ask commands for compact output too: `git diff --stat`, `git log --oneline -n 20`, `git status --short`. On this repo at commit 8e337f0, `git log -20` prints 23,373 characters and `git log --oneline -20` prints 1,603 (counted by [scripts/measure-compact-flags.py](scripts/measure-compact-flags.py) with git's output settings pinned, run 2026-11-03; [benchmarks/search-ladder.md](benchmarks/search-ladder.md) has every row; one repo, one command, not a session saving).

---

## Model Selection Quick Decision

```
Is the task...
├── Hardest reasoning, longest agentic runs, budget allows 2x?          → Fable 5.2
├── Complex architecture, long agentic run, or hardest coding?         → Opus 5.5
├── Standard feature work, code review, writing tests?                 → Sonnet 5.5
├── Simple fix, formatting, boilerplate, file lookup?                  → Haiku 5.5 (keep the prompt under 100K)
└── Not sure?                                                          → Start with Sonnet 5.5
```

| Task | Model | Thinking effort |
|------|-------|-----------------|
| Rename-size change you review | Haiku 5.5 | `low` |
| Tests, docs, types, simple fixes | Haiku 5.5 | `medium` (default) |
| Feature with a clear scope | Sonnet 5.5 | `medium` (default) |
| Bug fix in an existing codebase, or other work where verification matters | Sonnet 5.5 or Opus 5.5 | `high` |
| Architecture, complex refactors | Opus 5.5 | `medium` (default), `high` where edge cases are likely |
| Finding security vulnerabilities | Opus 5.5 | `max`, tested on a sample first: Anthropic says it can show diminishing returns and overthink |

The effort column follows Anthropic's per-level table ([model config](https://code.claude.com/docs/en/model-config), read 2026-11-03); `medium` is the default on Opus 5.5, Sonnet 5.5 and Haiku 5.5 (and on Fable 5.2, read 2026-11-10), `xhigh` on Opus 4.7 and `high` on every other model that supports effort. The model column is this repo's routing.

**Switch models mid-session**: Type `/model` and select, or start with `claude --model sonnet`. The `sonnet` alias means Sonnet 5.5 only on the Anthropic API: on Bedrock, Google Cloud and Microsoft Foundry it is Sonnet 4.5 ($3/$15, 200K -- 1.5x the price for a smaller window, and now deprecated) and on Claude Platform on AWS it is Sonnet 4.6 ($3/$15, 1M), so pin `--model claude-sonnet-5-5` (Bedrock: `anthropic.claude-sonnet-5-5`) or set `ANTHROPIC_DEFAULT_SONNET_MODEL` (Claude Code v2.1.284+). The `haiku` alias splits the same way: Haiku 5.5 on the Anthropic API (Claude Code v2.1.293+), legacy Haiku 4.5 ($1/$5, 200K) on Claude Platform on AWS, Bedrock, Google Cloud and Foundry; pin it with `ANTHROPIC_DEFAULT_HAIKU_MODEL`, which also sets the model for background functionality.

> **Note**: Opus 5.5 is priced at $4/$20 -- 20% below Opus 5 / 4.8 / 4.7 / 4.6 ($5/$25). Switching down to Haiku 5.5 is 40x cheaper per token than Opus 5.5 up to 100K prompt tokens and 8x above (50x / 10x from the $5/$25 Opus models); legacy Haiku 4.5 ($1/$5) was only 4x. The Opus 4.7+ tokenizer (shared by Opus 5.5) produces about 30% more tokens for the same text ([Anthropic's pricing page](https://platform.claude.com/docs/en/about-claude/pricing)), so the same task costs about 30% more than it would on a pre-4.7 model at the same per-token rate. Anthropic's own models overview says to "start with Claude Opus 5.5 for most workloads"; the tree above starts with Sonnet 5.5 because it is half the per-token price.
>
> **Watch thinking on Opus 5.5 and Opus 5**: both think by default, and reasoning tokens bill as output ($20/1M on Opus 5.5, $25/1M on Opus 5). Opus 5.5 cannot turn thinking off -- lower `effort` instead (it defaults to `medium`). On Opus 5 you can send `thinking: {type: "disabled"}` (effort `high` or below). For mechanical work, dropping to Sonnet 5.5 is half the per-token price of Opus 5.5.

---

## Platform Comparison

| Feature | Anthropic API | Claude Platform on AWS | AWS Bedrock | Google Cloud (Google managed, formerly Vertex AI) | Claude Code |
|---------|:---:|:---:|:---:|:---:|:---:|
| Standard pricing | Base rates | Same (CCU billing) | Same (global) / +10% (regional) | Same (global) / +10% (regional) | Included in plan |
| Opus 5.5 availability | **Yes** | **Yes** | **Yes** (`anthropic.claude-opus-5-5`) | **Yes** | Via `/model` |
| Opus 5 availability | **GA** | **GA** | **GA** (`anthropic.claude-opus-5`) | **GA** | Via `/model` |
| Sonnet 5.5 availability | **Yes** | **Yes** | **Yes** (`anthropic.claude-sonnet-5-5`) | **Yes** | Via `/model` (v2.1.284+) |
| Sonnet 5 availability | GA | GA | GA | GA | Via `/model` |
| Haiku 5.5 availability | **Yes** | **Yes** | **Yes** (`anthropic.claude-haiku-5-5`) | **Yes** | `haiku` alias on the Anthropic API (v2.1.293+) |
| Haiku 4.5 availability (legacy) | GA | GA | GA | GA | Via `/model`; the `haiku` alias on every other provider |
| 1M context | Yes (Opus 5.5/5/4.8/4.7/4.6, Sonnet 5.5/5/4.6; Haiku 5.5 at a higher tier above 100K) | Yes | Yes | Yes | Yes |
| Fast Mode (2x) | **Yes** (Fable 5.2 and Opus 5.5 with no beta header; Opus 5 + 4.8 research preview, 4.8's removed 2026-11-30) | No | No | Fable 5.2 only, at Google's price (Fable 5.2 and Opus 5.5 on the Anthropic-managed Google Cloud offering) | Fable 5.2 (v2.1.321+) and Opus 5.5 / 5 / 4.8; usage credits only on a subscription |
| Batch API (50% off) | Yes | No | Yes | Yes | N/A |
| Prompt caching | Yes | Yes | Yes | Yes | Automatic |
| Data-residency premium | +10% (`inference_geo: "us"`, 4.6+ models) | +10% (`inference_geo: "us"`) | Bedrock regional pricing | Google Cloud regional pricing | -- |
| Fable 5.2 availability | **Yes** | **Yes** | **Yes** (`anthropic.claude-fable-5-2`) | **Yes** | `fable` alias (v2.1.321+; plan/API-key dependent) |
| Fable 5.1 availability (legacy) | GA | GA | GA | GA | By id: `/model claude-fable-5-1` |
| Mythos 5.2 | Verification required | -- | Verification required | Verification required | -- |
| Mythos 5.1 | Verification required | -- | Verification required | Verification required | -- |
| Mythos 5 | Verification required | Verification required | Verification required | Verification required | -- |

> **Bedrock / Google Cloud**: Same models, same capabilities. Global (cross-region) inference matches API pricing. Regional inference profiles add 10% ([Claude in Amazon Bedrock](https://platform.claude.com/docs/en/build-with-claude/claude-in-amazon-bedrock#regions): "a 10% pricing premium over global endpoints", read 2026-10-11). The +10% premium scope is **Sonnet 4.5+, Haiku 4.5+, Opus 4.5+, and all future models**; older models retain their existing pricing.
>
> **Opus 5.5 model IDs**: `anthropic.claude-opus-5-5` on Bedrock; `claude-opus-5-5` on the Claude API, Google Cloud, Microsoft Foundry, and Claude Platform on AWS.
>
> **Opus 5 on Bedrock**: **Generally available** via Claude in Amazon Bedrock (the Messages-API endpoint) with model ID `anthropic.claude-opus-5`. The legacy InvokeModel/Converse path with the `us.anthropic.claude-opus-5` cross-region inference profile works for backward compatibility. Google Cloud uses `claude-opus-5`. (Opus Fast Mode is not on Bedrock or Google Cloud (Google managed); Opus 5.5's runs on the Claude API, Claude Models on Google Cloud (Anthropic managed) and Microsoft Foundry. Fable 5.2's adds Google Cloud (Google managed) and is not on Bedrock either.)
>
> **Claude Platform on AWS**: Anthropic-operated alternative on AWS Marketplace, billed in **Claude Consumption Units (CCU)** at $0.01 per CCU. Token usage is rated in USD at standard per-model rates, then converted to CCUs. Typically gets same-day feature parity with the Anthropic API. Fast Mode and Batch API are NOT available on this platform.
>
> **Claude Models on Google Cloud (Anthropic managed)** (new 2026-10-22): the Claude API operated by Anthropic, reached through a Google Cloud project with Google Cloud IAM and billed through Google Cloud Marketplace; data residency is 1.1x, as on the first-party API ([overview of both Google Cloud offerings](https://platform.claude.com/docs/en/build-with-claude/claude-models-on-google-cloud/overview), read 2026-11-01). The table's Google Cloud column is the Google-managed offering, which Claude Code's docs call Google Cloud's Agent Platform.

---

## Cost Formula

```
Turn Cost = (Input Tokens x Input Price) + (Output Tokens x Output Price)

Where Input Tokens =
    System Prompt (~3,500 tokens, fixed)
  + CLAUDE.md (~10 tokens/line x number of lines)
  + Conversation History (grows each turn)
  + Tool Results (file contents, search results, command output)
  + MCP Responses (if using MCP servers)

Session Cost = Sum of all turns
             - Prompt Cache Savings (90% off repeated input at 0.1x;
                                     95% on Opus 5.5 / Sonnet 5.5,
                                     97.5% on Fable 5.2 and 5.1)
```

---

## Quick Copy-Paste Configs

### Minimal Read deny rules (`.claude/settings.json`)

A `.claudeignore` file has no effect: the [permissions docs](https://code.claude.com/docs/en/permissions) say so and tell you to move its entries into `Read` deny rules (read 2026-11-01). The documented way to keep Claude's file tools out of a path is `permissions.deny` with `Read(...)` rules:

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

Patterns use gitignore syntax: `./path` is relative to the project, `**` crosses directories, and a bare name such as `Read(.env)` matches at any depth. The rules also cover `cat`/`head`/`tail`/`sed` in Bash, but not commands that read without naming a file, such as `grep -r pattern .`. No published measurement exists for what they save -- it depends on how often Claude would otherwise open those files. Migrating a `.claudeignore`: `dir/` becomes `Read(./dir/**)`, any other line containing `/` becomes `Read(./line)` (strip a leading `/`), and a bare name or glob becomes `Read(line)`. Skip blank lines, `#` comments and `!` negations.

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
| Fable 5.2 output is ___ per 1M tokens | **$40** (2x Opus 5.5; legacy Fable 5.1: $50, 2.5x) |
| Fable 5.2 cache read is ___ per 1M tokens | **$0.20** (0.025x -- the deepest discount, and the same dollar rate as Opus 5.5's 0.05x; Fable 5.1: $0.25) |
| Opus 5.5 output is ___ per 1M tokens | **$20** (Opus 5 / 4.8: $25) |
| Opus 5.5 cache read is ___ per 1M tokens | **$0.20** (0.05x, 95% off) |
| Haiku 5.5 is ___ cheaper than Opus 5.5 per token, prompts up to 100K | **40x** (8x above 100K; 80x / 16x vs Fable 5.2, computed: $8 / $0.10 and $8 / $0.50; legacy Haiku 4.5 was 4x vs Opus 5.5) |
| Haiku 5.5 price tier switches at | **100,000 prompt tokens** -- one token over pays 5x on input and output |
| Opus 5.5 / Opus 5 / Sonnet 5.5 / Haiku 5.5 minimum cacheable prompt | **512 tokens** (half the 1,024 of Opus 4.8 and Sonnet 5, an eighth of Haiku 4.5's 4,096) |
| Output tokens cost ___ more than input | **5x** |
| Prompt cache discount | **90%** (95% on Opus 5.5 / Sonnet 5.5, 97.5% on Fable 5.2 / Mythos 5.2 / Fable 5.1 / Mythos 5.1) |
| CLAUDE.md loads on every ___ | **turn** |
| CLAUDE.md size guidance per file | **under 200 lines** (Anthropic's guidance). A CLAUDE.md loaded at launch is read whole and skipped above 4 MiB; since v2.1.309, files loaded on demand (subdirectory CLAUDE.md and CLAUDE.local.md with their imports, subdirectory and path-scoped rules) are cut at 40,000 characters each at a 200K window and 150,000 at 1M (200,000 on Opus 4.6 / Sonnet 4.6) ([memory](https://code.claude.com/docs/en/memory), read 2026-11-01) |
| Auto memory (`MEMORY.md`) loaded at session start | **first 200 lines or 25KB**, whichever comes first |
| 1 line of code is roughly ___ tokens | **~11** on the pre-4.7 basis, about 14 on the 4.7+ tokenizer (measured: this repo's 11,302 non-blank lines of TypeScript and Python are 119,917 cl100k tokens, 10.6 per line; plus about 30% per the [pricing page](https://platform.claude.com/docs/en/about-claude/pricing)) |
| Token estimation rule of thumb | **~1 token per 4 bytes** of text on pre-4.7 models; **about 2.5 characters per token** on the current tokenizer (1M tokens is roughly 2.5M characters, [models overview](https://platform.claude.com/docs/en/about-claude/models/overview)) |
| Opus 4.7+ tokenizer overhead vs older models | **about +30%** for the same text ([pricing page](https://platform.claude.com/docs/en/about-claude/pricing)) |
| 150-line CLAUDE.md per turn is roughly | **~1,500 tokens** at 10 per line (measured: this repo's 15 CLAUDE.md files are 20,161 cl100k tokens over 2,048 lines, 9.8 per line counting blank lines, 12.3 per non-blank line); about 30% more on the 4.7+ tokenizer |
| 50-turn session CLAUDE.md cost (Sonnet 4.6) | **$0.028** with caching (computed: 1,500 x $3.75/M once + 49 x 1,500 x $0.30/M); $0.225 if nothing were cached (50 x 1,500 x $3/M) |
| 50-turn session CLAUDE.md cost (Opus 5.5) | **$0.022** with caching (computed: 1,500 x $5/M once + 49 x 1,500 x $0.20/M; $0.046 on Opus 5); $0.30 if nothing were cached ($0.375 on Opus 5); add about 30% for the new tokenizer |
| Average tool result size | **No published average.** Anthropic's context-window explorer illustrates file reads of 1,100 to 2,400 tokens and a grep of 600 ("Token counts are illustrative", [context window](https://code.claude.com/docs/en/context-window)); this repo's calculator assumes 2,000 per file read. Caps: MCP tool output warns above 10,000 tokens and is cut at 25,000 by default (`MAX_MCP_OUTPUT_TOKENS`, [MCP docs](https://code.claude.com/docs/en/mcp)) |
| Bash output Claude receives inline | **about 30,000 characters** of a successful command, past that a saved-file path plus a 2,000-character preview; about **10,000** of a failing one, with no file path ([tools reference](https://code.claude.com/docs/en/tools-reference), read 2026-11-03). `bashOutputMaxChars` (v2.1.261+, 4,000 to 128,000) moves the success cap and is documented as a way to raise it; one `Read` returns at most 25,000 tokens. No published figure for what a lower cap saves |
| Compaction trigger threshold | **about 967K tokens** by default on 1M-window models (Fable, Sonnet 5 and later, Haiku 5.5, Opus 4.7 and later); `/autocompact` sets 100K to 1M ([model config](https://code.claude.com/docs/en/model-config)) |
| Idle compaction | A 200K+ token conversation left idle about **54 minutes** is compacted before its 1-hour cache expires, so the next message does not reprocess it all (v2.1.299; `CLAUDE_CODE_IDLE_COMPACT_MIN_TOKENS` moves the 200K minimum, `"idleCompaction": false` turns it off; [changelog](https://code.claude.com/docs/en/changelog), read 2026-11-01) |
| What /compact keeps | A summary of the conversation, plus re-reads of up to **5 files** Claude read or edited, most recently modified first; a file over 5,000 tokens comes back as a path only ([context window](https://code.claude.com/docs/en/context-window)). Invoked skill bodies come back at up to 5,000 tokens each and 25,000 in total, oldest dropped first (same page, read 2026-11-01), and the skill list is sent again (v2.1.304) |
| Fable 5.2 / 5.1 / 5 / Opus 5.5 / 5 / 4.8 / 4.7 / 4.6 / Sonnet 5.5 / Sonnet 5 / Haiku 5.5 max output per turn | **128K tokens** |
| Sonnet 4.6 / 4.5 / Haiku 4.5 max output per turn | **64K tokens** |

---

## Output Token Optimization

Output tokens cost 5x more than input across all models. Most strategies above target input -- these target the expensive side.

| Strategy | Savings (output) | How |
|----------|:----------------:|-----|
| **Use a brevity skill (e.g. caveman)** | 65% (the claim in caveman's GitHub description, not measured here). caveman's own [honest-numbers page](https://github.com/JuliusBrussee/caveman/blob/HEAD/docs/HONEST-NUMBERS.md) says earlier releases applied a fixed 65% ratio without a committed reviewed result, and measures /caveman at 3% and /ultracave at 35% fewer output tokens than an "Answer concisely." control (median, ten questions, Opus 5.5). The outside A/B it reports, LemonCrow on Opus 4.8 with 300 runs per arm, found 44.1% less billed output and 0.06% higher total cost (read 2026-11-03) | System prompt that strips filler, pleasantries, and hedging from responses. Technical accuracy unchanged. Thinking tokens and input are untouched, and the rules themselves add input: see [when cost-mode saves nothing](skills/cost-mode/README.md#when-cost-mode-saves-nothing). See [caveman](https://github.com/JuliusBrussee/caveman) |
| **"Be concise" in CLAUDE.md** | 39% fewer output tokens, 13% lower cost per run (read 2026-11-01) when [Anthropic](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence) asked for shorter answers | Add "Be concise. Skip explanations unless asked." to your CLAUDE.md. Simple but effective |
| **Batch outputs** | Each avoided turn saves one cache read of the whole context: $0.01 at 50K tokens on Opus 5.5 (computed: 50,000 x $0.20/M) | "Rename X in all files" (one response) vs 12 individual rename requests (12 responses) |
| **Suppress explanations** | 63% cheaper request when [Anthropic's cookbook](https://platform.claude.com/cookbook/cost-optimization-cost-optimization) shaped an open-ended prompt (4,096 to 61 output tokens) | "Just show the code, no explanation" or "diff only" for mechanical tasks |
| **Use Plan Mode wisely** | No published figure | Plan Mode output is cheaper than failed code generation + correction cycles |

> **Research backing**: A March 2026 study ([arXiv:2604.00025](https://arxiv.org/abs/2604.00025)) found that brevity constraints actually *improved* model accuracy by 26 percentage points on certain benchmarks. It tested 31 open models, not Claude, so treat it as a direction rather than a Claude measurement. Less verbose does not mean less correct.

### CLAUDE.md Compression

Your CLAUDE.md loads on every turn as input tokens. Applying brevity rules to it compounds savings:

```
BEFORE (74 chars):
"This project uses React with TypeScript. Always use functional components."

AFTER (47 chars, same info):
"React + TypeScript. Functional components only."
```

Every character saved in CLAUDE.md saves tokens on every turn of every session. At 30 turns/session and 3 sessions/day, a 1,000-character reduction (about 400 tokens at the current tokenizer's 2.5 characters per token) sends about 792,000 fewer input tokens over 22 working days (computed: 400 x 30 x 3 x 22). After each session's first turn those tokens bill as cache reads, so on Opus 5.5 that is about $0.29 a month (computed: 66 sessions x (400 x $5/M + 29 x 400 x $0.20/M)); the bigger win is adherence.

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
| Subagent templates (scout, reviewer, implementer) | [templates/agents/](templates/agents/) |
| Token Estimator Tool | [tools/token-estimator/](tools/token-estimator/) |
| Spend by session, project or day | `claude-rate --usage --by session` (claude-rate 0.4.0 or later, [tools/claude-rate/](tools/claude-rate/)) |
| claude-rate (local setup rater) | [tools/claude-rate/](tools/claude-rate/) |
| Caveman skill (output tokens) | [github.com/JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) |

---

*This cheatsheet covers the strategies. For the reasoning and benchmarks behind each one, read the full guides.*
