# Guide 06: Access Methods and Pricing

> **Not all paths to Claude cost the same.** Batch is 50% off, regional and US-only endpoints add 10%, and a flat subscription replaced over $15,000 of API-equivalent usage for one heavy user (n=1). Understanding the pricing differences between the Claude API (Anthropic API), Amazon Bedrock, Google Cloud (Google managed, formerly Vertex AI), the Anthropic-operated cloud offerings, and Claude subscriptions tells you which applies to your use case. (Sources: [Anthropic pricing page](https://platform.claude.com/docs/en/about-claude/pricing); the $15,000 figure is one developer's own tracker against about $800 of Max subscription, [ksred.com, 2026-02-23](https://www.ksred.com/claude-code-pricing-guide-which-plan-actually-saves-you-money/).)

Most teams pick a Claude access method based on convenience or existing cloud contracts -- not cost. This is a mistake. The same workload can cost 10% more on a regional endpoint than a global one, or 50% less through the Batch API. This guide breaks down every access path, its exact pricing, and when to use each one.

---

## Table of Contents

- [Platform Overview](#platform-overview)
- [Anthropic API (Direct) Pricing](#anthropic-api-direct-pricing)
- [AWS Bedrock Pricing](#aws-bedrock-pricing)
- [Claude Platform on AWS Pricing](#claude-platform-on-aws-pricing)
- [Google Cloud (Google Managed) Pricing](#google-cloud-google-managed-pricing)
- [Google Cloud (Anthropic Managed) Pricing](#google-cloud-anthropic-managed-pricing)
- [Claude Code Subscription Plans](#claude-code-subscription-plans)
- [Side-by-Side Platform Comparison](#side-by-side-platform-comparison)
- [When to Use Each Platform](#when-to-use-each-platform)
- [Cost Optimization Per Platform](#cost-optimization-per-platform)
- [Hidden Costs to Watch](#hidden-costs-to-watch)
- [Monthly Cost Projections](#monthly-cost-projections)
- [The Cheapest Path](#the-cheapest-path)
- [Key Takeaways](#key-takeaways)

---

## Platform Overview

There are six API platforms for Claude models, plus the Claude subscription plans:

| Platform | Access Type | Best For | Billing |
|----------|------------|----------|---------|
| **Claude API** (Anthropic API, first-party) | Direct REST API | Custom apps, full feature access (Fast Mode, Batch, Files, MCP connector, Managed Agents) | Pay-per-token, USD invoiced by Anthropic |
| **Claude Platform on AWS** | Anthropic-operated Claude API, reached through AWS | AWS-native teams that want Anthropic-operated infra + same-day feature parity | Pay-per-token, billed in **Claude Consumption Units (CCU)** at $0.01/CCU through AWS Marketplace |
| **Amazon Bedrock** (Mantle + legacy) | AWS-operated service | AWS-native teams, data residency, AWS security boundary | Pay-per-token (AWS billing) |
| **Google Cloud (Google managed)** | Google-operated, part of Google Cloud's Agent Platform | GCP-native teams, data residency (multi-region and regional endpoints) | Pay-per-token, invoiced by Google Cloud as Agent Platform usage |
| **Google Cloud (Anthropic managed)** (new 2026-10-22) | Anthropic-operated Claude API, reached through a Google Cloud project with Google Cloud IAM | GCP-native teams that want Claude API features (Batch, Files, Managed Agents, Fast Mode on Opus 5.5) | Pay-per-token, billed in CCU at $0.01/CCU through Google Cloud Marketplace |
| **Microsoft Foundry** | Anthropic-operated, hosted on Azure or on Anthropic infrastructure | Azure-native teams | Pay-per-token, billed in CCU at $0.01/CCU through the Azure Marketplace |
| **Claude subscription** (Pro, Max, Ultra, Team, Enterprise) | Claude apps + Claude Code (terminal, IDE, desktop, web) | Interactive development | Monthly subscription; annual billing on Pro, Team and Enterprise only |

Sources, read 2026-11-01: [pricing page](https://platform.claude.com/docs/en/about-claude/pricing#cloud-platform-pricing) (CCU billing on Claude Platform on AWS and Microsoft Foundry), [Claude Models on Google Cloud](https://platform.claude.com/docs/en/build-with-claude/claude-models-on-google-cloud/overview) (how the two Google Cloud offerings differ), [Claude Models on Google Cloud (Anthropic managed)](https://platform.claude.com/docs/en/build-with-claude/claude-models-on-google-cloud/anthropic-managed#billing) (CCU billing), [claude.com/pricing](https://claude.com/pricing) (plans).

The current models (Fable 5.1, Opus 5.5, Sonnet 5.5, Haiku 5.5) are on all six API platforms with the same intelligence ([models overview](https://platform.claude.com/docs/en/models/overview), read 2026-11-01). The differences are in pricing, infrastructure, compliance features, and billing integration. The four Anthropic-operated platforms serve the Claude API itself, so they get most features the same day; Bedrock and Google Cloud are partner-operated and do not offer the Message Batches API, Files API, code execution, web fetch, the advisor tool, Agent Skills, the MCP connector or Managed Agents ([Bedrock](https://platform.claude.com/docs/en/build-with-claude/claude-in-amazon-bedrock#features-not-supported) and [Google Cloud](https://platform.claude.com/docs/en/build-with-claude/claude-models-on-google-cloud/google-managed#features-not-supported) feature lists, read 2026-11-01). Microsoft Foundry has no Message Batches API or Managed Agents ([Foundry](https://platform.claude.com/docs/en/build-with-claude/claude-in-microsoft-foundry#claude-features-not-supported-for-claude-in-microsoft-foundry), read 2026-11-01). Fast Mode runs on the Claude API and, for Opus 5.5 only, on Google Cloud (Anthropic managed) and Foundry deployments hosted on Azure ([fast mode](https://platform.claude.com/docs/en/build-with-claude/fast-mode), read 2026-11-01).

---

## Anthropic API (Direct) Pricing

The Anthropic API is the baseline. All other platforms price relative to it.

### Standard Pricing (per 1M tokens, verified 2026-11-01)

| Model | Input | Output | Cache Hit | 5m Cache Write | 1h Cache Write | Context | Max Output |
|-------|:-----:|:------:|:---------:|:--------------:|:--------------:|:-------:|:----------:|
| **Fable 5.1** (most capable) | $10.00 | $50.00 | **$0.25** | $12.50 | $20.00 | 1M | 128K |
| **Fable 5** (legacy) | $10.00 | $50.00 | $1.00 | $12.50 | $20.00 | 1M | 128K |
| **Mythos 5.1** (verification required) | $10.00 | $50.00 | **$0.25** | $12.50 | $20.00 | 1M | 128K |
| **Mythos 5** (verification required, legacy) | $10.00 | $50.00 | $1.00 | $12.50 | $20.00 | 1M | 128K |
| **Opus 5.5** (recommended default Opus) | $4.00 | $20.00 | **$0.20** | $5.00 | $8.00 | 1M | 128K |
| **Opus 5** (legacy) | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1M | 128K |
| **Opus 4.8** (legacy) | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1M | 128K |
| **Opus 4.7** | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1M | 128K |
| **Opus 4.6** | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1M | 128K |
| **Opus 4.5** | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 200K | 64K |
| Opus 4.1 (retired 2026-08-05, still on Bedrock + Google Cloud) | $15.00 | $75.00 | $1.50 | $18.75 | $30.00 | 200K | 32K |
| **Opus 5.5 Fast Mode** (available, no beta header) | $8.00 (2x) | $40.00 (2x) | -- | -- | -- | 1M (included) | 128K |
| **Opus 5 Fast Mode** (research preview, beta header) | $10.00 (2x) | $50.00 (2x) | -- | -- | -- | 1M (included) | 128K |
| **Opus 4.8 Fast Mode** (research preview; deprecated, removal 2026-11-30) | $10.00 (2x) | $50.00 (2x) | -- | -- | -- | 1M (included) | 128K |
| **Sonnet 5.5** (recommended Sonnet) | $2.00 | $10.00 | **$0.10** | $2.50 | $4.00 | 1M | 128K |
| **Sonnet 5** (legacy) | $2.00 | $10.00 | $0.20 | $2.50 | $4.00 | 1M | 128K |
| **Sonnet 4.6** | $3.00 | $15.00 | $0.30 | $3.75 | $6.00 | 1M | 64K |
| **Sonnet 4.5** (deprecated; retirement scheduled for 2026-11-30) | $3.00 | $15.00 | $0.30 | $3.75 | $6.00 | 200K | 64K |
| **Haiku 5.5** (prompt <= 100K tokens) | $0.10 | $0.50 | **$0.01** | $0.125 | $0.20 | 1M | 128K |
| **Haiku 5.5** (prompt > 100K tokens) | $0.50 | $2.50 | $0.05 | $0.625 | $1.00 | 1M | 128K |
| **Haiku 4.5** (legacy) | $1.00 | $5.00 | $0.10 | $1.25 | $2.00 | 200K | 64K |
| **Mythos Preview** (deprecated, no retirement date) | $25.00 | $125.00 | $2.50 | $31.25 | $50.00 | 1M | -- |

> **Opus 5.5** (`claude-opus-5-5`, released 2026-09-22): the recommended default. Anthropic's models-overview page now says "start with Claude Opus 5.5 for most workloads"; Fable 5.1 is for demanding reasoning and long-horizon work. **$4/$20, 20% below Opus 5's $5/$25**, with cache hits at $0.20 (**0.05x** base input, 95% off), 5m / 1h cache writes at $5 / $8, Batch $2/$10, and Fast Mode at $8/$40 (out of research preview since 2026-10-15 with no beta header, on the Claude API, Google Cloud (Anthropic managed) and Microsoft Foundry hosted on Azure; [fast mode](https://platform.claude.com/docs/en/build-with-claude/fast-mode), read 2026-11-01). 1M context (default and max), 128K max output (300K on Batch via the `output-300k-2026-03-24` beta), min cacheable prompt 512, knowledge cutoff Jun 2026, same tokenizer as Opus 4.7+. Available on all six platforms: `claude-opus-5-5` on the Claude API, both Google Cloud offerings, Microsoft Foundry and Claude Platform on AWS; `anthropic.claude-opus-5-5` on Bedrock ([Opus 5.5 overview](https://platform.claude.com/docs/en/models/opus-5-5/overview), read 2026-11-01). Earliest retirement is not sooner than 2027-09-22.
>
> **Cost-relevant Opus 5.5 changes versus Opus 5**:
> - **Adaptive thinking is always on.** `thinking: {type: "disabled"}` and `thinking: {type: "enabled", budget_tokens}` both return 400; effort is the only control. Code that disabled thinking on Opus 5 now pays for thinking tokens (billed as output) it did not pay for before.
> - **Default effort is `medium`** (Opus 5 defaulted to `high`), so a request that omits effort now thinks less. Re-baseline cost after migrating.
> - **Forced `tool_choice` (`any` / `tool`) returns 400** -- use `auto` plus strict tool use or structured outputs. Non-default sampling params and assistant prefill also return 400; thinking blocks are tied to the model and conversation; `computer_20251124` is rejected on the Claude API and Google Cloud (use `computer_toolset_20260801`).
> - **No Priority Tier.** Opus 4.8 keeps it.
>
> **Sonnet 5.5** (`claude-sonnet-5-5`, released 2026-09-28): the current Sonnet flagship, at **$2/$10, the same as Sonnet 5**, with the same cache writes (5m / 1h $2.50 / $4.00) and Batch ($1/$5). Cache reads are no longer the same: on 2026-10-07 Anthropic cut Sonnet 5.5's cache hit from $0.20 to **$0.10 (0.05x base input, 95% off)**, half Sonnet 5's $0.20. Same tokenizer as Sonnet 5, so migrating costs nothing extra at the posted rate and halves the cache-read bill. 1M context at standard rates, 128K max output (300K on Batch via the `output-300k-2026-03-24` beta), min cacheable prompt **512** (Sonnet 5 was 1,024), knowledge cutoff Jun 2026, no Fast Mode. Available on all six platforms: `claude-sonnet-5-5` on the Claude API, both Google Cloud offerings, Microsoft Foundry and Claude Platform on AWS; `anthropic.claude-sonnet-5-5` on Bedrock ([What's new in Sonnet 5.5](https://platform.claude.com/docs/en/models/sonnet-5-5/whats-new-sonnet-5-5#availability), read 2026-11-01). Earliest retirement is not sooner than 2027-09-28. Sonnet 5 is now legacy (still Active, not deprecated).
>
> **Five breaking changes versus Sonnet 5** (each returns a 400 when old code is carried over):
> - `thinking: {type: "disabled"}` and manual `budget_tokens` return 400. Adaptive thinking is on by default (API default effort `high`; Claude Code defaults Sonnet 5.5 to `medium`, [model config](https://code.claude.com/docs/en/model-config), read 2026-11-01) and reasoning bills as output at $10/MTok. The lowest setting is `thinking: {type: "between_tools"}`, which turns off up-front thinking and is accepted only at `low`, `medium` and `high` effort (`xhigh`/`max` + `between_tools` = 400) -- send it on routine turns.
> - Forced `tool_choice` (`any` / `tool`) returns 400 -- use `auto` plus strict tool use or structured outputs.
> - Thinking blocks are tied to the model and conversation: keep conversations append-only, because replaying a Sonnet 5.5 thinking block after editing earlier history can return 400.
> - `computer_20251124` is rejected on the Claude API and Google Cloud (Bedrock still accepts it); use `computer_toolset_20260801`.
> - The advisor tool rejects four advisors for a Sonnet 5.5 executor: Opus 4.8, Opus 4.7, Sonnet 5 and Haiku 5.5 ([What's new in Sonnet 5.5](https://platform.claude.com/docs/en/models/sonnet-5-5/whats-new-sonnet-5-5#advisor-tool-pairings), read 2026-11-01).
>
> Non-default `temperature` / `top_p` / `top_k` also return 400. **Effort levels are recalibrated**: the same level does not produce the same amount of thinking as on Sonnet 5, so re-run your effort sweep instead of carrying a setting over (Anthropic's starting points: `high` in general, `medium` for well-specified agentic coding and multistep tool use).
>
> **Haiku 5.5** (`claude-haiku-5-5`, released 2026-10-07): the current Haiku and the **first model priced by prompt length**. A request whose prompt is **<= 100,000 tokens** pays **$0.10/$0.50** (cache hit $0.01, 5m / 1h writes $0.125 / $0.20, Batch $0.05/$0.25); a request **over 100,000 tokens** pays **$0.50/$2.50** on all of it (cache hit $0.05, writes $0.625 / $1.00, Batch $0.25/$1.25). Prompt length counts every input token, cache reads and cache writes included, and output bills at the tier the request falls in. **The cliff**: a 100,000-token prompt costs $0.010 of input, a 100,001-token prompt $0.050 (5x), so keep Haiku 5.5 prompts under 100K. Versus Haiku 4.5 ($1/$5) it is 10x cheaper per token at <= 100K and 2x above; it uses the newer Claude 4.7+ tokenizer (the same text is about 30% more tokens than on Haiku 4.5, per the [pricing page](https://platform.claude.com/docs/en/about-claude/pricing)), so per task that is roughly **7.7x cheaper at <= 100K** (computed: 10 / 1.3) and about 1.5x above (computed: 2 / 1.3). 1M context, 128K max output (300K on Batch via the `output-300k-2026-03-24` beta), min cacheable prompt **512** (Haiku 4.5: 4,096), adaptive thinking on by default at effort `medium`, knowledge cutoff Jun 2026, no Fast Mode. Available on all six platforms: `claude-haiku-5-5` on the Claude API, both Google Cloud offerings, Microsoft Foundry and Claude Platform on AWS; `anthropic.claude-haiku-5-5` on Bedrock ([models overview](https://platform.claude.com/docs/en/models/overview), read 2026-11-01). Earliest retirement is not sooner than 2027-10-07. Haiku 4.5 is now legacy and still Active: no retirement announced (its earliest date, 2026-10-15, has passed; [model deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations), read 2026-11-01).
>
> **Five breaking changes versus Haiku 4.5** (each returns a 400 when old code is carried over):
> - Manual extended thinking (`budget_tokens`) -- use adaptive thinking. On the API, `thinking: {type: "disabled"}` still works at `high` effort or below; Claude Code cannot turn thinking off on Haiku 5.5.
> - Non-default `temperature` / `top_p` / `top_k`.
> - Assistant prefill -- end `messages` with a user turn.
> - `computer_20250124` on the Claude API, Google Cloud and Amazon Bedrock -- use `computer_toolset_20260801` (on Bedrock, `computer_20251124`; [What's new in Haiku 5.5](https://platform.claude.com/docs/en/models/haiku-5-5/whats-new-haiku-5-5), read 2026-11-01).
> - Editing earlier turns invalidates thinking blocks -- keep conversations append-only.
>
> Also changed: responses can begin with `thinking` blocks (select content blocks by `type`), thinking text is omitted by default, and safety classifiers can decline (`stop_reason: "refusal"`, no server-side fallback). Forced tool use (`any` / `tool`) is still supported.
>
> **Claude Code `sonnet` and `haiku` alias cost gotcha**: both aliases resolve by provider, and only the Anthropic API maps them to Sonnet 5.5 and Haiku 5.5. Sonnet 5.5 needs Claude Code v2.1.284 or later; the `haiku` alias needs v2.1.293 or later to reach Haiku 5.5.
>
> | Provider | `sonnet` resolves to | Rate and context | `haiku` resolves to | Rate and context |
> |----------|----------------------|------------------|---------------------|------------------|
> | Anthropic API | **Sonnet 5.5** | $2/$10, 1M | **Haiku 5.5** | $0.10/$0.50 up to 100K prompt tokens, $0.50/$2.50 above; 1M |
> | Claude Platform on AWS | Sonnet 4.6 | $3/$15, 1M | Haiku 4.5 | $1/$5, 200K |
> | Amazon Bedrock, Google Cloud | **Sonnet 4.5** | $3/$15, 200K | **Haiku 4.5** | $1/$5, 200K |
> | Microsoft Foundry | **Sonnet 4.5** | $3/$15, 200K | **Haiku 4.5** | $1/$5, 200K |
>
> On Bedrock, Google Cloud and Foundry, `sonnet` therefore costs **1.5x Sonnet 5.5 for a smaller window**, and resolves to Sonnet 4.5, which is now deprecated (retirement scheduled for 2026-11-30). Pin it with `--model claude-sonnet-5-5` (Bedrock: `anthropic.claude-sonnet-5-5`) or `ANTHROPIC_DEFAULT_SONNET_MODEL`. Off the Anthropic API, `haiku` costs **10x Haiku 5.5 per token** for prompts up to 100K; pin `ANTHROPIC_DEFAULT_HAIKU_MODEL` to `claude-haiku-5-5` (Bedrock: `anthropic.claude-haiku-5-5`), which also sets the model Claude Code uses for background functionality.
>
> **Opus 5** (GA 2026-07-24, legacy since the Opus 5.5 launch): the previous Opus flagship, at the **identical posted price to Opus 4.8** ($5/$25). 1M context at standard rates across the whole window, 128K max output (300K on Batch via the `output-300k-2026-03-24` beta), knowledge cutoff May 2026. Earliest retirement is not sooner than 2027-07-24.
>
> **Cost-relevant Opus 5 behavior changes** (each one can move your bill even though the rate did not change):
> - **Adaptive thinking is ON by default** when you omit the `thinking` parameter. Reasoning tokens bill as **output** at $25/MTok, and `max_tokens` is a hard cap on thinking **plus** text. Raise `max_tokens` to 64K+ if you run `xhigh` or `max` effort. Effort levels are low/medium/high/xhigh/max, defaulting to `high` on the Claude API and in Claude Code.
> - `thinking: {type: "disabled"}` is allowed only at effort `high` or below. Combining it with `xhigh` or `max` returns a **400 error**.
> - **Minimum cacheable prompt drops to 512 tokens** (Opus 4.8 was 1,024), so shorter prefixes now qualify for the 90% cache-hit discount.
> - Ships cybersecurity safety classifiers. Cyber refusals can auto-fall-back to Opus 4.8 via the server-side `fallbacks` parameter with header `anthropic-beta: server-side-fallback-2026-07-01`.
> - Opus 5 **output runs longer than 4.8 by default** and it self-verifies. Re-tune verbosity instructions, and delete carried-over "double-check your work" prompts -- you now pay for that twice.
>
> **Opus 4.8 is now legacy**: the models-overview page has moved `claude-opus-4-8` into the Legacy accordion. Its retirement date is unchanged at not sooner than 2027-05-28, and the deprecations page still lists it as Active, so it is not deprecated and is not going away soon -- treat it as previous-generation and migrate new work to Opus 5.5. It keeps Priority Tier, which Opus 5.5 does not offer. Its Fast Mode is not staying: deprecated on 2026-10-30 and removed on 2026-11-30, after which `speed: "fast"` on `claude-opus-4-8` returns an error with no fallback ([release notes](https://platform.claude.com/docs/en/release-notes/overview), read 2026-11-01).

> **Fable 5 / Mythos 5** (GA 2026-06-09): the Mythos-class tier above Opus, both at $10/$50 (2x Opus 5). **Fable 5** went GA on the Claude API, Claude Platform on AWS, Bedrock, Google Cloud and Microsoft Foundry and includes safety classifiers that can refuse a request (`stop_reason: "refusal"`, HTTP 200; pre-output refusals are unbilled; the beta `fallbacks` parameter retries another model server-side and fallback credit refunds the cache-switch cost). **Mythos 5** is the same model without the classifiers. It launched for approved [Project Glasswing](https://www.anthropic.com/glasswing) customers; like Mythos 5.1 it now requires verification through Anthropic's verification programs, such as the [Cyber Verification Program](https://www.anthropic.com/news/cyber-verification-program), which on 2026-10-06 was expanded into Defense, Red Team and Specialized Access tiers, with Glasswing members moving to Specialized Access (read 2026-11-01). Both require 30-day data retention (no zero-data-retention option), have always-on adaptive thinking, and support the Batch API but not Fast Mode.
>
> **Mythos 5.1** is now "Verification required": available to organizations verified through Anthropic's verification programs, such as the Cyber Verification Program, and no longer described as Glasswing-only. Same specs and pricing as Fable 5.1. IDs: `claude-mythos-5-1` (Bedrock: `anthropic.claude-mythos-5-1`), offered on the Claude API, Bedrock, Google Cloud and Microsoft Foundry -- not Claude Platform on AWS.
>
> **Mythos Preview** was superseded by Mythos 5 and is **deprecated** -- still functional, no longer recommended, and Anthropic publishes no retirement date for it. It is the invite-only defensive-cybersecurity research preview for Glasswing partners (11 founding members plus 40+ critical-infrastructure organizations).

> **Sonnet 5 pricing is settled**: $2/$10 per MTok is now the standard rate. The launch pricing was labelled introductory through 2026-08-31, but Anthropic made it permanent and cancelled the increase to $3/$15, so budget $2/$10 indefinitely.

> **1M context at standard rates**: Fable 5.1, Mythos 5.1, Fable 5, Mythos 5, Opus 5.5, Opus 5, Opus 4.8, Opus 4.7, Opus 4.6, Sonnet 5.5, Sonnet 5, and Sonnet 4.6 charge the standard per-token rate across the full 1M window -- no long-context premium. Opus 4.5, Sonnet 4.5, Opus 4.1, and Haiku 4.5 are 200K-context only. (Microsoft Foundry used to cap Opus 4.8 at 200K; its context table now lists Opus 4.8 at 1M, [Foundry](https://platform.claude.com/docs/en/build-with-claude/claude-in-microsoft-foundry#context-window), read 2026-11-01.) **Haiku 5.5 is the exception**: it has a 1M window but is the one model from Claude 4.6 on priced by prompt length -- $0.10/$0.50 up to 100,000 prompt tokens, $0.50/$2.50 for the whole request above that.
>
> **Opus 4.7+ tokenizer**: The tokenizer introduced with Opus 4.7 (and used by Opus 4.8, Opus 5 and Opus 5.5) produces **about 30% more tokens** for the same text ([Anthropic's pricing page](https://platform.claude.com/docs/en/about-claude/pricing); the [Opus 4.7 launch post](https://www.anthropic.com/news/claude-opus-4-7) put it at roughly 1.0-1.35x by content type). The posted rate does not change with it, but effective cost rises proportionally. Budget accordingly. Haiku 5.5 uses the newer Claude 4.7+ tokenizer too: the same text is about 30% more tokens than on Haiku 4.5.
>
> **Minimum cacheable prompt length** (per model, in tokens): a `cache_control` block below the threshold is **silently ignored** -- no error, no discount, and you keep paying full input price.
>
> | Model | Minimum cacheable prompt |
> |-------|:------------------------:|
> | Fable 5.1, Mythos 5.1, Opus 5.5, Opus 5, Sonnet 5.5, Haiku 5.5, Fable 5, Mythos 5 | 512 |
> | Opus 4.8, Opus 4.1, Sonnet 5, Sonnet 4.6, Sonnet 4.5 | 1,024 |
> | Opus 4.7, Mythos Preview | 2,048 |
> | Opus 4.6, Opus 4.5, Haiku 4.5 (legacy) | 4,096 |
>
> **Tool-use overhead**: Tool definitions add a system-prompt token cost on every call. The base tool-use system prompt is **286 tokens** with `tool_choice: auto` or `none` and **406 tokens** with `any` or `tool` (Opus 5.5 and Sonnet 5.5 reject forced `any`/`tool`, so only the 286-token figure applies there; Haiku 5.5 supports forced tool use, so both apply; legacy Sonnet 5 is 354 / 474). Add this to your `tools` array (names + descriptions + schemas) when budgeting.

### Additional Pricing Modifiers

| Modifier | Effect | Details |
|----------|--------|---------|
| **Batch API** | 50% discount on input AND output | Non-real-time, async results. Stacks with prompt caching. NOT compatible with Fast Mode or Priority Tier. |
| **Data residency** (`inference_geo: "us"`) | 1.1x multiplier on every category | Applies to Opus 4.6, Sonnet 4.6, and all later models (including Opus 5.5, Opus 5, Sonnet 5.5, Sonnet 5 and Haiku 5.5) on the Claude API (1P), Claude Platform on AWS and Google Cloud (Anthropic managed); on Microsoft Foundry, US Data Zone Standard deployments pay the same 1.1x ([pricing page](https://platform.claude.com/docs/en/about-claude/pricing#data-residency-pricing), read 2026-11-01). Earlier models error if the parameter is set. |
| **Fast Mode** | 2x each model's base ($8 / $40 on Opus 5.5, $10 / $50 on Opus 5 and 4.8) | **Opus 5.5, Opus 5 and Opus 4.8 only**, all at 2x, `speed: "fast"`. **Opus 5.5**: available (out of research preview since 2026-10-15), no beta header, on the Claude API, Google Cloud (Anthropic managed) and Microsoft Foundry hosted on Azure, with a default fast-mode rate limit in the Start, Build and Scale tiers, so no access request. **Opus 5 and Opus 4.8**: research preview, Claude API only, header `anthropic-beta: fast-mode-2026-02-01`. **Opus 4.8 Fast Mode is deprecated (2026-10-30) and removed on 2026-11-30**; after that `speed: "fast"` on it returns an error. Up to 2.5x output tokens/sec (throughput, not time-to-first-token). Opus 4.7 with `speed: "fast"` **returns an error**; Opus 4.6 silently runs at standard speed and standard rates on the Claude API (`usage.speed` returns `"standard"`) and returns a 400 on Google Cloud (Anthropic managed). The old 6x tier no longer exists. Managed Agents: Claude API only. Not on Bedrock, Google Cloud, Claude Platform on AWS, the Batch API, or Priority Tier. Fast and standard speeds do not share cached prefixes, so each switch, including a fallback to standard after a fast-mode 429, reads the prefix uncached again. Dedicated rate limits surface in `anthropic-fast-*` response headers. ([fast mode](https://platform.claude.com/docs/en/build-with-claude/fast-mode), read 2026-11-01) |
| **Cache write (5-min TTL)** | 1.25x base input price | Content cached for 5 minutes. Pays off after 1 reuse. |
| **Cache write (1-hour TTL)** | 2x base input price | Content cached for 1 hour. Pays off after 2 reuses. |
| **Cache hit / refresh** | 0.1x base input price on most models; **0.05x on Opus 5.5 and Sonnet 5.5**; **0.025x on Fable 5.1 and Mythos 5.1** | 90% off vs uncached input on most models, 95% on Opus 5.5 and Sonnet 5.5, 97.5% on Fable 5.1 / Mythos 5.1. On Haiku 5.5 it is 0.1x of the request's own tier ($0.01 at <= 100K prompt tokens, $0.05 above). Read the per-model rate; never derive it as input x 0.1. |

### Batch API Pricing

The Batch API is the single biggest discount available. For any workload that does not need real-time responses:

| Model | Batch Input | Batch Output | Savings vs Standard |
|-------|:-----------:|:------------:|:-------------------:|
| **Fable 5.1** | $5.00 | $25.00 | 50% |
| **Fable 5** | $5.00 | $25.00 | 50% |
| **Mythos 5** | $5.00 | $25.00 | 50% |
| **Opus 5.5** | $2.00 | $10.00 | 50% |
| **Opus 5** (legacy) | $2.50 | $12.50 | 50% |
| **Opus 4.8** | $2.50 | $12.50 | 50% |
| **Opus 4.7** | $2.50 | $12.50 | 50% |
| **Opus 4.6** | $2.50 | $12.50 | 50% |
| **Opus 4.5** | $2.50 | $12.50 | 50% |
| **Opus 4.1** | $7.50 | $37.50 | 50% |
| **Sonnet 5.5** | $1.00 | $5.00 | 50% |
| **Sonnet 5** (legacy) | $1.00 | $5.00 | 50% |
| **Sonnet 4.6** | $1.50 | $7.50 | 50% |
| **Sonnet 4.5** (deprecated) | $1.50 | $7.50 | 50% |
| **Haiku 5.5** (prompt <= 100K tokens) | $0.05 | $0.25 | 50% |
| **Haiku 5.5** (prompt > 100K tokens) | $0.25 | $1.25 | 50% |
| **Haiku 4.5** (legacy) | $0.50 | $2.50 | 50% |

> Anthropic's Message Batches API runs on the Claude API, Claude Platform on AWS and Google Cloud (Anthropic managed) ([Claude Platform on AWS](https://platform.claude.com/docs/en/build-with-claude/claude-platform-on-aws#feature-support) and [Anthropic managed](https://platform.claude.com/docs/en/build-with-claude/claude-models-on-google-cloud/anthropic-managed#feature-support) feature lists, read 2026-11-01). It is not on Microsoft Foundry, Bedrock's Messages-API (Mantle) endpoint or Google Cloud (Google managed); there the 50% batch rate comes from the cloud's own batch service (Bedrock batch inference, Google Cloud batch prediction), which this pass did not re-check on AWS's or Google's pricing pages.

### Server-side tools (additional charges)

| Tool | Charge | Notes |
|------|--------|-------|
| **Web search** | $10 per 1,000 searches + token costs | Each search counts once regardless of result count. Errors are not billed. |
| **Web fetch** | Free (token costs only) | Use `max_content_tokens` to cap large pages. |
| **Code execution** | Free when the request includes `web_search_20260209` or `web_fetch_20260209` (or later); otherwise 1,550 free hours/org/month, then **$0.05 per hour per container** | 5-minute minimum execution time. Replaced by session runtime when using Managed Agents. |
| **Bash tool** | +325 input tokens on Claude 4.7 and later models (Opus 5.5, Sonnet 5.5 and Haiku 5.5 included); +244 on Claude 4.6 and earlier | Plus stdout/stderr token costs. |
| **Text editor tool** | `text_editor_20250728`: +974 input tokens on Claude 4.7 and later models, +745 on Claude 4.6 and earlier ([pricing page](https://platform.claude.com/docs/en/about-claude/pricing#text-editor-tool), read 2026-11-01) | Added to the request's input on top of the tool-use system prompt. |
| **Computer use tool** | +735 input tokens per tool definition + 466-499 system-prompt tokens | Plus screenshot vision tokens. |

### Claude Managed Agents (separate billing dimension)

Tokens billed at standard model rates (caching multipliers apply identically). **Plus** session runtime: **$0.08 per session-hour** of `running` status (not idle, rescheduling, or terminated). Replaces Code Execution container-hour billing -- you are not billed twice. Batch and partner-cloud pricing do **not** apply to Managed Agents sessions. Data residency does: an agent whose `model.inference_geo` is `"us"` bills its session tokens at 1.1x. Fast Mode applies when the agent's `model.speed` is `"fast"` (Managed Agents Fast Mode runs on the Claude API only). On Claude Platform on AWS, session tokens and runtime convert to CCUs. The worked example in Anthropic's docs now uses Opus 5.5: a 1-hour session with 50,000 input and 15,000 output tokens is $0.58, or $0.428 when 40,000 of the input tokens are cache reads ([pricing page](https://platform.claude.com/docs/en/about-claude/pricing#claude-managed-agents-pricing), read 2026-11-01).

### Tracking API spend and limits (new since 2026-10-09)

From the [release notes](https://platform.claude.com/docs/en/release-notes/overview), read 2026-11-01:

- **Usage and Cost Analytics API** (beta header `analytics-usage-cost-2026-08-24`, 2026-10-29): `/v1/organizations/analytics/usage` and `/v1/organizations/analytics/cost` report token usage and cost, filtered or grouped by model, workspace, API key and the user or service account behind each request. The older Usage and Cost API is now legacy, still supported. Claude Platform on AWS and Google Cloud (Anthropic managed) offer the new API; Bedrock and Google Cloud list the Usage and Cost API among their unsupported features.
- **OpenTelemetry export** (beta, 2026-10-14): traces Messages API requests and Managed Agents sessions into your observability platform. This is the Console-side export for API traffic. Claude Code's own client-side OpenTelemetry metrics (`claude_code.cost.usage`, `claude_code.token.usage`) are a separate feature, turned on with environment variables on each machine, for a fleet in managed settings ([monitoring docs](https://code.claude.com/docs/en/monitoring-usage), read 2026-11-03); see [Guide 05](05-team-budgeting.md) and [templates/settings/telemetry-team.json](../templates/settings/telemetry-team.json).
- **Request size**: the Messages and Token Counting APIs take up to 128 MB per request on the first-party Claude API, up from 32 MB (2026-10-28).
- **API version `2026-10-21`** and new major SDKs that send it by default (Python 2.0.0, TypeScript 1.0.0 and others), now licensed Apache 2.0 instead of MIT. Under that version `temperature`, `top_p` and `top_k` return a 400 on every model ([model deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations#api-parameter-deprecations), read 2026-11-01), so pin the version or drop those parameters before upgrading an SDK.

---

## AWS Bedrock Pricing

AWS Bedrock provides Claude access through two endpoint types with different pricing. **Fable 5.1 (the most capable widely released model) and Opus 5.5 (the recommended default Opus) are both available on Bedrock** as `anthropic.claude-fable-5-1` and `anthropic.claude-opus-5-5`, as are Sonnet 5.5 (`anthropic.claude-sonnet-5-5`) and Haiku 5.5 (`anthropic.claude-haiku-5-5`), alongside Fable 5, Opus 5 (`anthropic.claude-opus-5`), Opus 4.8, Opus 4.7 and Sonnet 5. Bedrock has two integration paths: the Claude in Amazon Bedrock (Mantle) Messages-API endpoint, and the legacy InvokeModel/Converse API. AWS sets access per model: Fable 5.1, Fable 5, Opus 4.8, Opus 4.7, Sonnet 5 and Haiku 4.5 are open to every Bedrock customer, Mythos 5.1 and Mythos 5 need verification, and Opus 5.5, Opus 5, Sonnet 5.5 and Haiku 5.5 follow the criteria in the Bedrock console's model access page ([Claude in Amazon Bedrock](https://platform.claude.com/docs/en/build-with-claude/claude-in-amazon-bedrock#access), read 2026-11-01).

### Global Endpoints

Global endpoints match Anthropic API pricing exactly:

| Model | Input | Output | Cache Hit |
|-------|:-----:|:------:|:---------:|
| **Fable 5.1** (open access, GA) | $10.00 | $50.00 | **$0.25** |
| **Fable 5** (legacy) | $10.00 | $50.00 | $1.00 |
| **Opus 5.5** (GA) | $4.00 | $20.00 | **$0.20** |
| **Opus 5** (legacy, GA) | $5.00 | $25.00 | $0.50 |
| **Opus 4.8** (open access, GA) | $5.00 | $25.00 | $0.50 |
| **Opus 4.7** (open access, GA) | $5.00 | $25.00 | $0.50 |
| **Opus 4.6** | $5.00 | $25.00 | $0.50 |
| **Sonnet 5.5** (GA) | $2.00 | $10.00 | **$0.10** |
| **Sonnet 4.6** | $3.00 | $15.00 | $0.30 |
| **Sonnet 4.5** (deprecated) | $3.00 | $15.00 | $0.30 |
| **Haiku 5.5** (GA, prompt <= 100K tokens) | $0.10 | $0.50 | $0.01 |
| **Haiku 5.5** (GA, prompt > 100K tokens) | $0.50 | $2.50 | $0.05 |
| **Haiku 4.5** (legacy) | $1.00 | $5.00 | $0.10 |
| **Mythos 5** (verification required) | $10.00 | $50.00 | $1.00 |
| **Mythos Preview** (deprecated; regional `us-east-1` only) | $25.00 | $125.00 | $2.50 |

### Regional Endpoints (us/eu/jp/apac/au inference profiles)

Regional endpoints carry a **10% premium** over global pricing. Scope: **Sonnet 4.5+, Haiku 4.5+, Opus 4.5+, and all later models** (Opus 5, Opus 5.5, Sonnet 5.5 and Haiku 5.5 included). Earlier models retain their existing pricing. Source: Anthropic's Bedrock page says "Regional endpoints carry a 10% pricing premium over global endpoints" and that global endpoints carry "No pricing premium" ([Claude in Amazon Bedrock](https://platform.claude.com/docs/en/build-with-claude/claude-in-amazon-bedrock#regions), read 2026-11-01); the [pricing page](https://platform.claude.com/docs/en/about-claude/pricing#cloud-platform-pricing) puts it the same way for "Claude 4.5 models and beyond". For Fable 5.1 the regional endpoint is `us-east-1` only (same page).

| Model | Regional Input | Regional Output | Premium |
|-------|:--------------:|:---------------:|:-------:|
| **Fable 5.1** | $11.00 | $55.00 | +10% |
| **Fable 5** | $11.00 | $55.00 | +10% |
| **Opus 5.5** | $4.40 | $22.00 | +10% |
| **Opus 5** (legacy) | $5.50 | $27.50 | +10% |
| **Opus 4.8** | $5.50 | $27.50 | +10% |
| **Opus 4.7** | $5.50 | $27.50 | +10% |
| **Opus 4.6** | $5.50 | $27.50 | +10% |
| **Opus 4.5** | $5.50 | $27.50 | +10% |
| **Sonnet 5.5** | $2.20 | $11.00 | +10% |
| **Sonnet 4.6** | $3.30 | $16.50 | +10% |
| **Sonnet 4.5** (deprecated) | $3.30 | $16.50 | +10% |
| **Haiku 5.5** (prompt <= 100K tokens) | $0.11 | $0.55 | +10% |
| **Haiku 5.5** (prompt > 100K tokens) | $0.55 | $2.75 | +10% |
| **Haiku 4.5** (legacy) | $1.10 | $5.50 | +10% |

### Bedrock Features

- **Batch inference**: AWS's own batch inference, not Anthropic's Message Batches API (the Mantle endpoint does not serve it); this guide prices it at the same 50% discount as the Claude API, which this pass did not re-check on AWS's pricing page
- **Available regions** (Mantle endpoint): 27 AWS regions including us-east-1, us-east-2, us-west-1, us-west-2, eu-west-1/2/3, eu-central-1/2, eu-north-1, eu-south-1/2, ap-northeast-1/2/3, ap-south-1/2, ap-southeast-1/2/3/4, ca-central-1, ca-west-1, sa-east-1, af-south-1, il-central-1, me-central-1
- **Endpoint types**: Global (dynamic routing across all regions, no premium), Regional (single region, +10%), or geographic inference profiles (US, EU, JP, AU at +10%)
- **Quotas**: Default 2M input TPM; you can request up to 5M input TPM and 500K output TPM without Anthropic approval ([Claude in Amazon Bedrock](https://platform.claude.com/docs/en/build-with-claude/claude-in-amazon-bedrock#quotas), read 2026-11-01). AWS sets RPM limits separately.
- **Authentication**: Bedrock service role (recommended), IAM assumed roles (12-hour max), or short-lived bearer tokens
- **Billing**: Through your AWS account, consolidated with other AWS services
- **Committed use discounts**: Available through AWS Savings Plans

### Bedrock Model IDs

The new **Claude in Amazon Bedrock (Mantle)** endpoint at `https://bedrock-mantle.{region}.api.aws/anthropic/v1/messages` uses the same Messages API shape as the first-party Anthropic API, with an `anthropic.` prefix on model IDs:

| Model | Mantle Model ID | Legacy Bedrock ID (InvokeModel/Converse) |
|-------|-----------------|------------------------------------------|
| Fable 5 | `anthropic.claude-fable-5` | `global.anthropic.claude-fable-5` (global inference profile; no `us.` CRIS profile exists) |
| Opus 5.5 | `anthropic.claude-opus-5-5` | Not listed on Anthropic's Opus 5.5 page; check the Bedrock console for inference profiles |
| Opus 5 (legacy) | `anthropic.claude-opus-5` | `us.anthropic.claude-opus-5` (cross-region inference profile) |
| Opus 4.8 | `anthropic.claude-opus-4-8` | `us.anthropic.claude-opus-4-8` (cross-region inference profile) |
| Opus 4.7 | `anthropic.claude-opus-4-7` | `us.anthropic.claude-opus-4-7` (cross-region inference profile) |
| Opus 4.6 | `anthropic.claude-opus-4-6` | `anthropic.claude-opus-4-6-v1` |
| Opus 4.5 | -- | `anthropic.claude-opus-4-5-20251101-v1:0` |
| Opus 4.1 | -- | `anthropic.claude-opus-4-1-20250805-v1:0` |
| Sonnet 5.5 | `anthropic.claude-sonnet-5-5` | Check the Bedrock console for inference profiles |
| Sonnet 4.6 | `anthropic.claude-sonnet-4-6` | `anthropic.claude-sonnet-4-6` |
| Sonnet 4.5 (deprecated) | -- | `anthropic.claude-sonnet-4-5-20250929-v1:0` |
| Haiku 5.5 | `anthropic.claude-haiku-5-5` | Check the Bedrock console for inference profiles |
| Haiku 4.5 (legacy) | `anthropic.claude-haiku-4-5` | `anthropic.claude-haiku-4-5-20251001-v1:0` |
| Mythos Preview (deprecated) | `anthropic.claude-mythos-preview` | (invitation only, through Project Glasswing) |

### Bedrock Mantle: features supported and NOT supported

**Supported**: Messages API, prompt caching, extended thinking, tool use (bash, computer use, memory tool, text editor), citations, structured outputs.

**NOT supported on Bedrock Mantle**: Files API and URL image/document sources, server-side tools (code execution, web search, web fetch, advisor), Agent Skills, MCP connector, programmatic tool calling, Message Batches API, Models API, Admin API, Compliance API, Usage and Cost API, Claude Managed Agents, server-side fallback (`fallbacks`), the `computer_toolset_20260801` / `browser_toolset_20260801` toolsets, Fast Mode ([Claude in Amazon Bedrock](https://platform.claude.com/docs/en/build-with-claude/claude-in-amazon-bedrock#features-not-supported), read 2026-11-01).

> **Key point**: Unless you have a data residency requirement, always use global endpoints on Bedrock. Regional costs 10% more, so global takes 9.1% off a regional bill (1 - 1/1.1) for zero effort.

---

## Claude Platform on AWS Pricing

Claude Platform on AWS is **Anthropic-operated** (different from partner-operated Bedrock). It bills through AWS Marketplace using **Claude Consumption Units (CCU)** at a fixed **$0.01 per CCU**. Token usage is rated in USD at standard per-model rates (identical to Anthropic API pricing), then converted to CCUs and metered hourly to AWS.

| Concept | Detail |
|---------|--------|
| **Billing unit** | Claude Consumption Unit (CCU) |
| **CCU price** | $0.01 per CCU (fixed; 100 CCU = $1.00) |
| **Conversion** | Token usage rated in USD at standard rates, then converted to CCUs |
| **Cadence** | Hourly metering, monthly invoices via AWS Marketplace |
| **Payment** | Postpaid only (no prepaid credits) |
| **Discounts** | Applied as fewer CCUs metered (negotiated through Anthropic account exec) |
| **Tax** | Pre-tax metering; AWS Marketplace handles tax |
| **Cost visibility** | Real-time breakdown in Claude Console (via AWS Console); AWS Cost Explorer shows aggregated CCU |

### Inference geography

For Opus 4.6, Sonnet 4.6, and later models (including Opus 5, Opus 5.5, Sonnet 5.5 and Haiku 5.5), setting `inference_geo: "us"` applies a **1.1x pricing multiplier** to all token categories. `inference_geo: "global"` (default) uses standard pricing.

### What's NOT available on Claude Platform on AWS

- Fast Mode
- The `computer_toolset_20260801` and `browser_toolset_20260801` toolsets, Anthropic's HIPAA-ready program, OAuth sign-in, and the legacy Usage and Cost API (the newer Usage and Cost Analytics API is available)
- Bedrock-style cloud-platform pricing (CCU model is unified)

Batch processing **is** available: the feature list includes it ([Claude Platform on AWS](https://platform.claude.com/docs/en/build-with-claude/claude-platform-on-aws#feature-support), read 2026-11-01), at the Claude API's 50% batch discount because CCUs are rated "at standard per-model, per-feature rates" ([pricing page](https://platform.claude.com/docs/en/about-claude/pricing#claude-platform-on-aws-pricing), read 2026-11-01). Earlier editions of this guide said Platform on AWS had no Batch.

### Why pick this over Bedrock?

- **Same-day feature parity** with the first-party Claude API, typically (Bedrock follows its own release schedule)
- **Anthropic-operated infrastructure** rather than partner-operated
- **AWS Marketplace billing** so usage rolls into your AWS bill but is governed by Anthropic's deprecation/feature schedule (not Bedrock's)
- Same model IDs as the Anthropic API (e.g. `claude-opus-5-5`), not Bedrock-style IDs
- A separate capacity pool from both the Claude API and Bedrock, so you can fail over between them

---

## Google Cloud (Google Managed) Pricing

Anthropic's docs now call this offering **Claude Models on Google Cloud (Google managed)**; it used to be "Claude on Vertex AI", and Google runs it as part of Google Cloud's Agent Platform (the name Claude Code's docs use). Claude Code still selects it with `CLAUDE_CODE_USE_VERTEX=1`, and Anthropic's SDK client for it is still `AnthropicVertex`. In this guide, "Google Cloud" on its own means this offering; the Anthropic-operated one is always written "Google Cloud (Anthropic managed)" ([Claude Models on Google Cloud](https://platform.claude.com/docs/en/build-with-claude/claude-models-on-google-cloud/overview), read 2026-11-01).

Google Cloud follows the same global vs. regional pricing structure as Bedrock, plus a **multi-region** endpoint type (`us` or `eu`) that Bedrock does not have.

### Global Endpoints

Global endpoints match Anthropic API pricing exactly:

| Model | Input | Output | Cache Hit |
|-------|:-----:|:------:|:---------:|
| **Opus 5.5** | $4.00 | $20.00 | **$0.20** |
| **Opus 5** (legacy) | $5.00 | $25.00 | $0.50 |
| **Opus 4.8** | $5.00 | $25.00 | $0.50 |
| **Opus 4.7** | $5.00 | $25.00 | $0.50 |
| **Opus 4.6** | $5.00 | $25.00 | $0.50 |
| **Opus 4.5** | $5.00 | $25.00 | $0.50 |
| **Sonnet 5.5** | $2.00 | $10.00 | **$0.10** |
| **Sonnet 4.6** | $3.00 | $15.00 | $0.30 |
| **Sonnet 4.5** (deprecated) | $3.00 | $15.00 | $0.30 |
| **Haiku 5.5** (prompt <= 100K tokens) | $0.10 | $0.50 | $0.01 |
| **Haiku 5.5** (prompt > 100K tokens) | $0.50 | $2.50 | $0.05 |
| **Haiku 4.5** (legacy) | $1.00 | $5.00 | $0.10 |

### Regional and Multi-Region Endpoints

Both regional endpoints (single GCP region) and multi-region endpoints (dynamic routing within a geography) carry a **10% premium**: "Multi-region and regional endpoints cost 10 percent more than global endpoints" ([Claude Models on Google Cloud (Google managed)](https://platform.claude.com/docs/en/build-with-claude/claude-models-on-google-cloud/google-managed#global-multi-region-and-regional-endpoints), read 2026-11-01). The same page says regional (single-region) endpoints serve Claude Sonnet 4.6 and earlier only; newer models use the global or multi-region endpoints, so for them the regional rows below are the multi-region price.

| Model | Regional/Multi-Region Input | Regional/Multi-Region Output | Premium |
|-------|:---------------------------:|:----------------------------:|:-------:|
| **Opus 5.5** | $4.40 | $22.00 | +10% |
| **Opus 5** (legacy) | $5.50 | $27.50 | +10% |
| **Opus 4.8** | $5.50 | $27.50 | +10% |
| **Opus 4.7** | $5.50 | $27.50 | +10% |
| **Opus 4.6** | $5.50 | $27.50 | +10% |
| **Opus 4.5** | $5.50 | $27.50 | +10% |
| **Sonnet 5.5** | $2.20 | $11.00 | +10% |
| **Sonnet 4.6** | $3.30 | $16.50 | +10% |
| **Sonnet 4.5** (deprecated) | $3.30 | $16.50 | +10% |
| **Haiku 5.5** (prompt <= 100K tokens) | $0.11 | $0.55 | +10% |
| **Haiku 5.5** (prompt > 100K tokens) | $0.55 | $2.75 | +10% |
| **Haiku 4.5** (legacy) | $1.10 | $5.50 | +10% |

### Google Cloud Model IDs

| Model | Agent Platform model ID |
|-------|---------------------|
| Opus 5.5 | `claude-opus-5-5` |
| Opus 5 (legacy) | `claude-opus-5` |
| Opus 4.8 | `claude-opus-4-8` |
| Opus 4.7 | `claude-opus-4-7` |
| Opus 4.6 | `claude-opus-4-6` |
| Opus 4.5 | `claude-opus-4-5@20251101` |
| Opus 4.1 (retired on the Claude API; Google lists it as deprecated) | `claude-opus-4-1@20250805` |
| Sonnet 5.5 | `claude-sonnet-5-5` |
| Sonnet 4.6 | `claude-sonnet-4-6` |
| Sonnet 4.5 (deprecated) | `claude-sonnet-4-5@20250929` |
| Haiku 5.5 | `claude-haiku-5-5` |
| Haiku 4.5 (legacy) | `claude-haiku-4-5@20251001` |

### Google Cloud Features

- **Provisioned throughput**: Needs a regional endpoint, so it covers only the models regional endpoints serve (Sonnet 4.6 and earlier)
- **Endpoint types**: Global (no premium), multi-region (+10%), regional (+10%)
- **Billing**: Google Cloud invoices it as Agent Platform usage, consolidated with other GCP services; Google sets the per-model prices on its [Generative AI pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing#claude-models) page
- **Lifecycle**: Google sets its own retirement dates, which can differ from the Claude API schedule (Opus 4, Sonnet 4 and Haiku 3.5, retired on the Claude API, are still listed here)
- **Not supported**: the Message Batches API, Files API, code execution, web fetch, the advisor tool, Agent Skills, the MCP connector, Managed Agents, server-side fallback and Fast Mode; request payloads are capped at 30 MB (the first-party Claude API now takes 128 MB)
- **Committed use**: GCP committed use discounts, per earlier editions of this guide; not re-checked on Google's pages on 2026-11-01

Source for the first five bullets: [Claude Models on Google Cloud (Google managed)](https://platform.claude.com/docs/en/build-with-claude/claude-models-on-google-cloud/google-managed), read 2026-11-01; the missing Fast Mode is from the [fast mode page](https://platform.claude.com/docs/en/build-with-claude/fast-mode) and the 128 MB limit from the [release notes](https://platform.claude.com/docs/en/release-notes/overview) (2026-10-28), both read 2026-11-01.

---

## Google Cloud (Anthropic Managed) Pricing

**Claude Models on Google Cloud (Anthropic managed)** launched on 2026-10-22: the Claude API operated by Anthropic and reached through your Google Cloud project. It is to Google Cloud what Claude Platform on AWS is to AWS. Requests go to `claude.googleapis.com`, Google Cloud IAM (`roles/claude.admin`, `roles/claude.user`, `roles/claude.viewer`) controls access, there are no API keys, and setup creates a new Anthropic organization for the project, separate from any you already have ([Anthropic managed](https://platform.claude.com/docs/en/build-with-claude/claude-models-on-google-cloud/anthropic-managed), [release notes](https://platform.claude.com/docs/en/release-notes/overview), read 2026-11-01).

| Concept | Detail |
|---------|--------|
| **Billing** | Google Cloud Marketplace. Anthropic meters usage and reports it to Google Cloud in Claude Consumption Units at **$0.01 per CCU**; the charges appear on your Google Cloud bill with no separate Anthropic invoice |
| **Per-token rates** | No separate rate card is published. The pricing page applies its Fast Mode and data-residency prices to this offering and keeps it out of the partner-cloud regional pricing, so this guide uses Claude API rates for it |
| **Location** | `global` only; there is no regional or multi-region premium |
| **Data residency** | `inference_geo: "us"` per request: **1.1x** on every token category, as on the Claude API ([pricing page](https://platform.claude.com/docs/en/about-claude/pricing#data-residency-pricing), read 2026-11-01) |
| **Fast Mode** | Opus 5.5 only, at $8/$40 |
| **Spend commitments** | Usage counts toward a Google Cloud spend commitment the way other Marketplace purchases do |
| **Rate limits** | Managed by Anthropic, not Google Cloud |
| **Cost visibility** | Usage and Cost pages in the Claude Console (opened from the Google Cloud console), or the Usage and Cost Analytics API |

**Works as on the Claude API**: the Message Batches API, Files API, Agent Skills, web search, web fetch, code execution, the memory and advisor tools, the MCP connector, prompt caching, server-side fallback, token counting, the Models API and Claude Managed Agents. **Not supported**: API keys, MCP tunnels, memory stores on self-hosted environments, and the pre-built self-hosted sandbox workers. Model IDs are the Claude API IDs (`claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`, `claude-fable-5-1`), including the dated IDs for models older than Claude 4.6.

**Pick it over Google Cloud (Google managed)** when you want Claude API features that the Google-managed offering lacks (Batch, Files, code execution, Managed Agents, Fast Mode) on your Google Cloud bill. Pick the Google-managed one when you need multi-region or regional endpoints, provisioned throughput, or Google-operated data handling. Max, Ultra and Team monthly API credits do not apply here: they cover the Claude API in the Claude Console org linked to the plan, not cloud platforms ([API credits for subscribers](https://platform.claude.com/docs/en/about-claude/api-credits-for-subscribers), read 2026-11-01).

---

## Claude Code Subscription Plans

Claude subscriptions bundle Claude, Claude Code and Cowork usage into predictable monthly (or annual) pricing. The plans are now **Free, Pro, Max, Ultra, Team and Enterprise**: "Max 5x" is now just **Max**, and "Max 20x" was renamed **Ultra** at the same $200 price, with existing subscribers moved automatically ([claude.com/pricing](https://claude.com/pricing), [What is the Ultra plan?](https://support.claude.com/en/articles/17728952-what-is-the-ultra-plan), read 2026-11-01). Claude Code is included on every paid plan and every Team seat, not on Free.

### Plan Comparison

| Plan | Monthly Price | Annual Price (effective monthly) | Usage Level | Per-Day Equivalent |
|------|:------------:|:--------------------------------:|:-----------:|:------------------:|
| **Pro** | $20/mo | **$200/yr ($16.67/mo, which the pricing page rounds to $17; 17% off)** | Baseline: a 5-hour window plus a weekly limit | $0.67/day monthly, $0.55/day annual |
| **Max** (formerly Max 5x) | $100/mo | Monthly only | 5x Pro usage every 5 hours and every week | $3.33/day |
| **Ultra** ($200, formerly Max 20x) | $200/mo | Monthly only | 10x Pro usage every week; no 5-hour limit on verified accounts | $6.67/day |
| **Team Standard** seat | $25/seat | $20/seat | 1.25x Pro per session, per member (not pooled); 2 to 150 seats | -- |
| **Team Premium** seat | $125/seat | $100/seat | 6.25x Pro per session, per member (not pooled) | -- |
| **Enterprise** | -- | $20/seat/month billed annually (20-seat minimum), **plus all usage at API rates** | No per-seat token allowance | -- |

*Computed: $200 / $240 = 0.833, so 17% off; per day = price / 30 (monthly) or $200 / 365 (annual). Plan facts from [claude.com/pricing](https://claude.com/pricing), [What is the Max plan?](https://support.claude.com/en/articles/11049741-what-is-the-max-plan), [What is the Ultra plan?](https://support.claude.com/en/articles/17728952-what-is-the-ultra-plan), [What is the Team plan?](https://support.claude.com/en/articles/9266767-what-is-the-team-plan) and [Enterprise billing](https://support.claude.com/en/articles/11526368-how-am-i-billed-for-my-enterprise-plan), read 2026-11-01. Ultra is not "20x Pro": Anthropic describes it as 10x Pro every week. The older Enterprise Standard/Premium seats are legacy.*

> **Annual Pro plan saves 17%** vs monthly. If you'll use Claude for more than 10 months in a year, annual is the cheaper choice (10 x $20 = $200). Math: $200/yr ÷ 12 = $16.67/mo vs $20/mo monthly = $40/yr saved.

> **Max, Ultra and Team include monthly API credits (since 2026-10-07)**: $100 on Max, $200 on Ultra, $20 per Team Standard seat and $100 per Team Premium seat (Team credits pooled, capped at $500 a month). They go to one Claude Console organization you link to the plan and pay for the Claude API there (Messages and Message Batches), the playground, Managed Agents and the Agent SDK (`claude -p` too, when run with an API key from that organization). They do **not** cover interactive Claude Code (terminal, IDE, desktop, web), usage credits, or Claude on Bedrock, Google Cloud or Foundry, and they expire at the end of each billing cycle with no rollover; new subscribers can claim after 7 days. Free, Pro and Enterprise are not eligible ([Help Center](https://support.claude.com/en/articles/17154008-monthly-api-credits-for-max-ultra-and-team-plans), [API credits for subscribers](https://platform.claude.com/docs/en/about-claude/api-credits-for-subscribers), read 2026-11-01). Details in [Guide 09](09-subscription-value.md#monthly-api-credits-on-max-and-team).

### What Is Included

- Desktop app access (macOS, Windows, Linux)
- Mobile app access (iOS, Android)
- CLI access (Claude Code)
- Prompt caching (automatic): Claude Code caches the main conversation for 1 hour while you are within plan usage, and for 5 minutes for subagents and usage-credit traffic ([prompt caching](https://code.claude.com/docs/en/prompt-caching), read 2026-11-01)
- Opus, Sonnet and Haiku models. Fable 5 and 5.1 are included for up to half of the weekly limit on Max, Ultra and Team Premium; Pro and Team Standard pay for Fable with usage credits ([Fable models on your plan](https://support.claude.com/en/articles/15424964-claude-fable-models-on-your-plan), read 2026-11-01)

### When You Exceed Plan Limits

Each plan has a 5-hour limit and a weekly limit, one pool shared by Claude, Claude Code and Cowork (verified Ultra accounts have only the weekly limit). When you hit one, you wait for the reset unless you have turned on **usage credits** (formerly "extra usage"): pay-as-you-go at standard API rates, charged on top of the subscription, with a monthly spend limit and optional auto-reload ([Manage usage credits](https://support.claude.com/en/articles/12429409-manage-usage-credits-for-paid-claude-plans), read 2026-11-01). This means:

- Past the limit, Opus 5.5 usage costs $4/$20 per MTok in usage credits (legacy Opus 5 / 4.8: $5/$25), and in Claude Code that traffic uses the 5-minute cache, not the 1-hour one
- **Usage bundles** prepay usage credits at a discount: a $50 bundle costs $45 (10% off), $250 costs $200 (20% off) and $1,000 costs $700 (30% off), up to $2,000 of bundles a month on Pro, Max and Ultra and $3,000 on Team ([Buy usage bundles](https://support.claude.com/en/articles/14246112-buy-usage-bundles), read 2026-11-01)
- Fast Mode in Claude Code is paid from usage credits only, "even if you have remaining usage on your plan" ([Claude Code fast mode](https://code.claude.com/docs/en/fast-mode), read 2026-11-01)
- Track your usage with `/usage` (`/cost` and `/stats` are aliases) to avoid surprise charges

### Plan Selection Math

Anthropic does not sell plans in tokens and publishes no token allowance per plan, so the only firm number is the API-equivalent break-even: how much Opus 5.5 output the plan price would buy at the API's $20 per MTok.

| Plan | Price | API-equivalent Opus 5.5 output at $20/MTok |
|:----:|:-----:|:------------------------------------------:|
| Pro | $20/mo | 1M output tokens |
| Max | $100/mo | 5M output tokens |
| Ultra | $200/mo | 10M output tokens |

*Computed: price / $20 per MTok. At legacy Opus 5's $25 output rate the same prices buy 0.8M, 4M and 8M. Real Claude Code turns also bill input and cache reads, so use these as a scale for comparing plans with API spend, not as plan limits.*

---

## Side-by-Side Platform Comparison

### Opus 5.5 Pricing Across All Platforms (per 1M tokens)

Opus 5.5 is available on all six platforms (Claude API, Claude Platform on AWS, Bedrock, both Google Cloud offerings, Microsoft Foundry). Regional rows apply the same +10% as the other models. Microsoft Foundry is not tabled: it rates usage at the Claude API's per-model rates, converts it to CCUs ($0.01 each) on your Azure bill, charges 1.1x on US Data Zone Standard deployments, and has no Message Batches API ([pricing page](https://platform.claude.com/docs/en/about-claude/pricing#claude-in-microsoft-foundry-pricing), read 2026-11-01).

| Platform | Endpoint | Input | Output | Cache Hit | Batch Input | Batch Output |
|----------|----------|:-----:|:------:|:---------:|:-----------:|:------------:|
| **Anthropic API** | Direct | $4.00 | $20.00 | $0.20 | $2.00 | $10.00 |
| **Claude Platform on AWS** | CCU billing (global) | $4.00 | $20.00 | $0.20 | $2.00 | $10.00 |
| **Claude Platform on AWS** | `inference_geo: "us"` | $4.40 | $22.00 | $0.22 | $2.20 | $11.00 |
| **Google Cloud (Anthropic managed)** | CCU billing (global) | $4.00 | $20.00 | $0.20 | $2.00 | $10.00 |
| **Google Cloud (Anthropic managed)** | `inference_geo: "us"` | $4.40 | $22.00 | $0.22 | $2.20 | $11.00 |
| **AWS Bedrock** | Global | $4.00 | $20.00 | $0.20 | $2.00 | $10.00 |
| **AWS Bedrock** | Regional | $4.40 | $22.00 | $0.22 | $2.20 | $11.00 |
| **Google Cloud (Google managed)** | Global | $4.00 | $20.00 | $0.20 | $2.00 | $10.00 |
| **Google Cloud (Google managed)** | Regional / Multi-region | $4.40 | $22.00 | $0.22 | $2.20 | $11.00 |

*How the rows are derived (applies to every table in this section): the Claude Platform on AWS and Google Cloud (Anthropic managed) rows use Claude API rates (see [Google Cloud (Anthropic Managed) Pricing](#google-cloud-anthropic-managed-pricing) for the basis), and their Batch cells use the Claude API's 50% batch discount. Every `inference_geo: "us"` cell, batch included, is computed as the global cell x 1.1, since the multiplier applies to "all token pricing categories" ([pricing page](https://platform.claude.com/docs/en/about-claude/pricing#data-residency-pricing), read 2026-11-01). The Bedrock and Google Cloud (Google managed) Batch cells assume each cloud's own batch service at 50% off, because neither offers Anthropic's Message Batches API; this pass did not re-check AWS's or Google's pricing pages.*

### Legacy Opus 5 / 4.8 / 4.7 / 4.6 Pricing Across All Platforms (per 1M tokens)

Opus 5, Opus 4.8, Opus 4.7, and Opus 4.6 share the same base pricing and are **GA on the Claude API, Claude Platform on AWS, AWS Bedrock and Google Cloud**. Google Cloud (Anthropic managed) is left out of this table because this pass found no per-model list of which older models it serves.

| Platform | Endpoint | Input | Output | Cache Hit | Batch Input | Batch Output |
|----------|----------|:-----:|:------:|:---------:|:-----------:|:------------:|
| **Anthropic API** | Direct | $5.00 | $25.00 | $0.50 | $2.50 | $12.50 |
| **Claude Platform on AWS** | CCU billing (global) | $5.00 | $25.00 | $0.50 | $2.50 | $12.50 |
| **Claude Platform on AWS** | `inference_geo: "us"` | $5.50 | $27.50 | $0.55 | $2.75 | $13.75 |
| **AWS Bedrock** | Global | $5.00 | $25.00 | $0.50 | $2.50 | $12.50 |
| **AWS Bedrock** | Regional | $5.50 | $27.50 | $0.55 | $2.75 | $13.75 |
| **Google Cloud (Google managed)** | Global | $5.00 | $25.00 | $0.50 | $2.50 | $12.50 |
| **Google Cloud (Google managed)** | Regional / Multi-region | $5.50 | $27.50 | $0.55 | $2.75 | $13.75 |

### Sonnet 5.5 Pricing Across All Platforms (per 1M tokens)

Sonnet 5.5 is available on all six platforms at Sonnet 5's input, output, cache-write and Batch rates; its cache hit has been $0.10 (0.05x) since 2026-10-07, half Sonnet 5's $0.20. Regional rows apply the same +10% as the other models.

| Platform | Endpoint | Input | Output | Cache Hit | Batch Input | Batch Output |
|----------|----------|:-----:|:------:|:---------:|:-----------:|:------------:|
| **Anthropic API** | Direct | $2.00 | $10.00 | $0.10 | $1.00 | $5.00 |
| **Claude Platform on AWS** | CCU billing (global) | $2.00 | $10.00 | $0.10 | $1.00 | $5.00 |
| **Claude Platform on AWS** | `inference_geo: "us"` | $2.20 | $11.00 | $0.11 | $1.10 | $5.50 |
| **Google Cloud (Anthropic managed)** | CCU billing (global) | $2.00 | $10.00 | $0.10 | $1.00 | $5.00 |
| **Google Cloud (Anthropic managed)** | `inference_geo: "us"` | $2.20 | $11.00 | $0.11 | $1.10 | $5.50 |
| **AWS Bedrock** | Global | $2.00 | $10.00 | $0.10 | $1.00 | $5.00 |
| **AWS Bedrock** | Regional | $2.20 | $11.00 | $0.11 | $1.10 | $5.50 |
| **Google Cloud (Google managed)** | Global | $2.00 | $10.00 | $0.10 | $1.00 | $5.00 |
| **Google Cloud (Google managed)** | Regional / Multi-region | $2.20 | $11.00 | $0.11 | $1.10 | $5.50 |

### Haiku 5.5 Pricing Across All Platforms (per 1M tokens)

Haiku 5.5 is available on all six platforms. Each request is priced on its own by prompt length: up to 100,000 prompt tokens (cache reads and writes count toward the limit) it pays the first row of each pair, above that the second row for the whole request. Regional rows apply the same +10% as the other models.

| Platform | Endpoint | Prompt tier | Input | Output | Cache Hit | Batch Input | Batch Output |
|----------|----------|-------------|:-----:|:------:|:---------:|:-----------:|:------------:|
| **Anthropic API** | Direct | <= 100K | $0.10 | $0.50 | $0.01 | $0.05 | $0.25 |
| **Anthropic API** | Direct | > 100K | $0.50 | $2.50 | $0.05 | $0.25 | $1.25 |
| **Claude Platform on AWS** | CCU billing (global) | <= 100K | $0.10 | $0.50 | $0.01 | $0.05 | $0.25 |
| **Claude Platform on AWS** | CCU billing (global) | > 100K | $0.50 | $2.50 | $0.05 | $0.25 | $1.25 |
| **Claude Platform on AWS** | `inference_geo: "us"` | <= 100K | $0.11 | $0.55 | $0.011 | $0.055 | $0.275 |
| **Claude Platform on AWS** | `inference_geo: "us"` | > 100K | $0.55 | $2.75 | $0.055 | $0.275 | $1.375 |
| **Google Cloud (Anthropic managed)** | CCU billing (global) | <= 100K | $0.10 | $0.50 | $0.01 | $0.05 | $0.25 |
| **Google Cloud (Anthropic managed)** | CCU billing (global) | > 100K | $0.50 | $2.50 | $0.05 | $0.25 | $1.25 |
| **Google Cloud (Anthropic managed)** | `inference_geo: "us"` | <= 100K | $0.11 | $0.55 | $0.011 | $0.055 | $0.275 |
| **Google Cloud (Anthropic managed)** | `inference_geo: "us"` | > 100K | $0.55 | $2.75 | $0.055 | $0.275 | $1.375 |
| **AWS Bedrock** | Global | <= 100K | $0.10 | $0.50 | $0.01 | $0.05 | $0.25 |
| **AWS Bedrock** | Global | > 100K | $0.50 | $2.50 | $0.05 | $0.25 | $1.25 |
| **AWS Bedrock** | Regional | <= 100K | $0.11 | $0.55 | $0.011 | $0.055 | $0.275 |
| **AWS Bedrock** | Regional | > 100K | $0.55 | $2.75 | $0.055 | $0.275 | $1.375 |
| **Google Cloud (Google managed)** | Global | <= 100K | $0.10 | $0.50 | $0.01 | $0.05 | $0.25 |
| **Google Cloud (Google managed)** | Global | > 100K | $0.50 | $2.50 | $0.05 | $0.25 | $1.25 |
| **Google Cloud (Google managed)** | Regional / Multi-region | <= 100K | $0.11 | $0.55 | $0.011 | $0.055 | $0.275 |
| **Google Cloud (Google managed)** | Regional / Multi-region | > 100K | $0.55 | $2.75 | $0.055 | $0.275 | $1.375 |

### Sonnet 4.6 Pricing Across All Platforms (per 1M tokens)

| Platform | Endpoint | Input | Output | Cache Hit | Batch Input | Batch Output |
|----------|----------|:-----:|:------:|:---------:|:-----------:|:------------:|
| **Anthropic API** | Direct | $3.00 | $15.00 | $0.30 | $1.50 | $7.50 |
| **AWS Bedrock** | Global | $3.00 | $15.00 | $0.30 | $1.50 | $7.50 |
| **AWS Bedrock** | Regional | $3.30 | $16.50 | -- | $1.65 | $8.25 |
| **Google Cloud (Google managed)** | Global | $3.00 | $15.00 | $0.30 | -- | -- |
| **Google Cloud (Google managed)** | Regional | $3.30 | $16.50 | -- | -- | -- |

### Haiku 4.5 (Legacy) Pricing Across All Platforms (per 1M tokens)

| Platform | Endpoint | Input | Output | Cache Hit | Batch Input | Batch Output |
|----------|----------|:-----:|:------:|:---------:|:-----------:|:------------:|
| **Anthropic API** | Direct | $1.00 | $5.00 | $0.10 | $0.50 | $2.50 |
| **AWS Bedrock** | Global | $1.00 | $5.00 | $0.10 | $0.50 | $2.50 |
| **AWS Bedrock** | Regional | $1.10 | $5.50 | -- | $0.55 | $2.75 |
| **Google Cloud (Google managed)** | Global | $1.00 | $5.00 | $0.10 | -- | -- |
| **Google Cloud (Google managed)** | Regional | $1.10 | $5.50 | -- | -- | -- |

---

## When to Use Each Platform

### Decision Tree

```
Start here: What is your primary use case?
|
+-- Interactive development (coding, debugging, exploration)
|   |
|   +-- Light usage (< 2 hrs/day) --> Claude Pro ($20/mo or $200/yr ≈ $16.67/mo)
|   +-- Medium usage (2-6 hrs/day) --> Claude Max ($100/mo)
|   +-- Heavy usage (6+ hrs/day) --> Claude Ultra ($200/mo, formerly Max 20x)
|
+-- Programmatic access (apps, pipelines, automation)
|   |
|   +-- Do you need AWS billing integration?
|   |   |
|   |   +-- Yes --> AWS Bedrock Global endpoints
|   |   +-- Yes + data residency --> AWS Bedrock Regional endpoints
|   |   +-- Yes + Claude API features (Batch, Files, Managed Agents) --> Claude Platform on AWS
|   |
|   +-- Do you need GCP billing integration?
|   |   |
|   |   +-- Yes --> Google Cloud (Google managed) Global endpoints
|   |   +-- Yes + data residency --> Google Cloud (Google managed) Multi-region or Regional endpoints
|   |   +-- Yes + Claude API features (Batch, Files, Managed Agents, Fast Mode) --> Google Cloud (Anthropic managed)
|   |
|   +-- No cloud preference --> Anthropic API (direct)
|       |
|       +-- Real-time needed? --> Standard API
|       +-- Can wait for results? --> Batch API (50% off)
|
+-- Data residency requirements (GDPR, HIPAA, SOC 2)
    |
    +-- AWS ecosystem --> Bedrock Regional (specific region)
    +-- GCP ecosystem --> Google Cloud (Google managed) Multi-region or Regional
    +-- Anthropic-operated --> US-only inference (`inference_geo: "us"`, 1.1x on Claude 4.6+ models)
```

### Platform Recommendations by Scenario

| Scenario | Recommended Platform | Why |
|----------|---------------------|-----|
| Solo developer, daily coding | Claude Max ($100) | Predictable cost, all-in-one |
| Team of 5, mixed usage | Claude Code Pro (each) + API for automation | $100/mo team + per-use for scripts |
| Production app with Claude | Anthropic API (Batch where possible) | Cheapest per-token, 50% batch discount |
| AWS-native team, no residency needs | Bedrock Global | Same pricing, AWS billing integration |
| AWS team, EU data must stay in EU | Bedrock Regional (eu-west-1) | 10% premium, but meets GDPR requirements |
| GCP-native team | Google Cloud (Google managed) Global | Same pricing, GCP billing integration |
| GCP-native team that needs Batch, Files or Managed Agents | Google Cloud (Anthropic managed) | Claude API features on the Google Cloud bill (CCU billing through Google Cloud Marketplace) |
| High-volume batch processing | Anthropic Batch API | 50% off everything, can't beat it |
| Latency-critical application | Anthropic API (standard) or Fast Mode | Fast Mode is 2x cost on Opus 5.5, Opus 5 and Opus 4.8 (the only models that support it; Opus 4.8's ends 2026-11-30) but highest output throughput |

---

## Cost Optimization Per Platform

### Strategy 1: Use Global Endpoints (Regional Costs 10% More)

This is the easiest win for Bedrock and Google Cloud users. Unless you have a hard data residency requirement, always use global endpoints.

| Endpoint Type | Opus 5.5 Input | Opus 5.5 Output | Annual Cost (10M input + 10M output tokens/mo) |
|---------------|:----------:|:-----------:|:---------------------------:|
| Global | $4.00 | $20.00 | $2,880 |
| Regional | $4.40 | $22.00 | $3,168 |
| **Savings** | | | **$288/year** |

*Computed: 12 x (10 x $4 + 10 x $20) = $2,880; x 1.1 = $3,168. The equal input/output split is an assumption; the premium is 10% of whatever the bill is. On legacy Opus 5 ($5/$25) the same rows are $3,600 and $3,960, a $360/year saving.*

For a team of 5 developers each using 10M input + 10M output tokens/month on Opus 5.5, switching from regional to global saves **$1,440/year** (5 x $288).

### Strategy 2: Use Batch API for Non-Real-Time Workloads (Save 50%)

The Batch API is the single most impactful discount. Any workload that can tolerate asynchronous processing should use it.

**Good candidates for Batch API**:
- Code review pipelines
- Documentation generation
- Test case generation
- Data analysis and summarization
- Migration scripts (analyze-then-transform)
- Nightly quality checks

**Not suitable for Batch API**:
- Interactive coding sessions
- Real-time chat interfaces
- Latency-sensitive features

| Processing Mode | Opus 5.5 Input | Opus 5.5 Output | Job of 10M input + 10M output tokens |
|-----------------|:----------:|:-----------:|:-------------:|
| Standard | $4.00 | $20.00 | $240.00 |
| Batch | $2.00 | $10.00 | $120.00 |
| **Savings** | | | **$120.00 per job** |

*Computed: 10 x $4 + 10 x $20 = $240; Batch is "a 50% discount on both input and output tokens" ([pricing page](https://platform.claude.com/docs/en/about-claude/pricing#batch-processing)), so it halves any input/output split. The earlier "$300 for a 10M token job" was this same 10M-in, 10M-out job (20M tokens) at legacy Opus 5's $5/$25; 10M tokens in total cannot cost $300 at those rates (all-output is $250). Anthropic's cookbook measured Batch on a real run at $0.7379 to $0.3653, 50.5% less ([cost-optimization cookbook](https://platform.claude.com/cookbook/cost-optimization-cost-optimization)).*

### Strategy 3: Watch Cumulative Context Growth (Long Context Is Now Free, But Cache Write Costs Grow With It)

**Good news**: Opus 5.5, Opus 5, Opus 4.8, Opus 4.7, Opus 4.6, Sonnet 5.5, Sonnet 5, and Sonnet 4.6 all bill the full 1M context window at **standard per-token rates**. There is no longer a 2x input / 1.5x output premium for crossing the 200K threshold. (This earlier pricing applied to Opus 4.1 and older.)

**The exception is Haiku 5.5**, the one model from Claude 4.6 on that is priced by prompt length. A request over 100,000 prompt tokens -- counting cache reads and cache writes -- pays $0.50/$2.50 on all of its tokens instead of $0.10/$0.50, even when part of the prompt is a cache hit. A 100,000-token prompt costs $0.010 of input; a 100,001-token prompt costs $0.050. On Haiku 5.5, long context is a 5x step, not a flat rate.

**The catch**: While the rate is flat, the absolute token count still grows with context. A 500K-token input at $5/MTok is $2.50 per call -- small per call, but it adds up across a long session, and every fresh cache write on that content costs 1.25x (5-minute) or 2x (1-hour) the input price in absolute dollars.

| Scenario | Input Tokens | Input Cost (Opus 5) | Output Cost (10K output) |
|----------|:------------:|:---------------------:|:------------------------:|
| Standard (under 200K) | 150,000 | $0.75 | $0.25 |
| Long context (over 200K) | 500,000 | $2.50 | $0.25 |
| **Difference** | | **3.3x more** (proportional only) | same |

**How to keep context from ballooning**:
- Keep CLAUDE.md concise (see [Guide 02](02-context-optimization.md))
- Use `permissions.deny` `Read(...)` rules in `.claude/settings.json` to keep Claude Code's file tools out of build output, dependencies and lock files (the [permissions page](https://code.claude.com/docs/en/permissions) says a `.claudeignore` file has no effect and to move its entries into Read deny rules, read 2026-11-01; a Read deny also blocks Edit and Write on that path, but not commands such as `grep -r pattern .` that read without naming a file; no published measurement exists for what Read rules save, it depends on how often Claude would otherwise open those files)
- Start new sessions when context grows too large
- Use subagents to isolate expensive operations (see [Guide 04](04-workflow-patterns.md))
- Remember: the Opus 4.7+ tokenizer (also used by Opus 4.8, Opus 5 and Opus 5.5) makes the same source text about 30% more tokens than it used to be ([Anthropic's pricing page](https://platform.claude.com/docs/en/about-claude/pricing)), so "size" thresholds shift lower.
- On Opus 5.5, thinking is always on (it cannot be disabled) and reasoning tokens bill as output at $20/MTok, so lower the effort level when a task does not need reasoning. On legacy Opus 5, thinking is on by default at $25/MTok; drop the effort level, or set `thinking: {type: "disabled"}` at effort `high` or below.

### Strategy 4: Avoid Fast Mode Unless Latency Is Critical (Save 50%)

Fast Mode is 2x each model's standard rate ($8/$40 per MTok on Opus 5.5, $10/$50 on Opus 5 and 4.8) and is supported on **Opus 5.5, Opus 5 and Opus 4.8 only**: available on Opus 5.5 (Claude API, Google Cloud (Anthropic managed), Foundry hosted on Azure), research preview on Opus 5 and Opus 4.8 (Claude API only), and removed from Opus 4.8 on 2026-11-30 ([fast mode](https://platform.claude.com/docs/en/build-with-claude/fast-mode), read 2026-11-01). Use it only when response latency directly impacts revenue or user experience.

| Mode | Opus Input | Opus Output | 1M token session |
|------|:----------:|:-----------:|:----------------:|
| Standard (Opus 5.5) | $4.00 | $20.00 | $24.00 |
| Fast Mode (Opus 5.5) | $8.00 | $40.00 | $48.00 |
| Standard (Opus 5 / 4.8) | $5.00 | $25.00 | $30.00 |
| Fast Mode (Opus 5 or Opus 4.8) | $10.00 | $50.00 | $60.00 |
| **Difference** | | | **$24.00 more per session on Opus 5.5, $30.00 on Opus 5 / 4.8** |

> Opus 4.7 with `speed: "fast"` returns an error rather than falling back to standard, and Opus 4.6 silently runs at standard speed and standard rates. The old 6x Fast Mode tier ($30/$150) no longer exists on any model.

> **Rule of thumb**: If you are using Fast Mode for interactive development in Claude Code, you are almost certainly overpaying. Standard latency is fast enough for coding workflows. On a subscription, Claude Code bills Fast Mode from usage credits even when plan usage remains, and fast and standard speed keep separate caches, so each toggle can re-read the whole conversation uncached ([Claude Code fast mode](https://code.claude.com/docs/en/fast-mode), read 2026-11-01).

### Strategy 5: Cache Effectively (Save 90%, 95% or 97.5% on Repeated Input)

Prompt caching gives you a 90% discount on input tokens that have been seen before on most models, 95% on Opus 5.5 and Sonnet 5.5 (0.05x) and 97.5% on Fable 5.1 and Mythos 5.1 (0.025x). The key is to structure your requests so that stable content (system prompts, reference documents, schemas) comes first and changes as little as possible between requests.

| Token Type | Opus Price | Relative Cost |
|------------|:----------:|:-------------:|
| Standard input | $5.00 | 1x |
| Cache hit | $0.50 | 0.1x (90% off) |
| Cache write (5-min) | $6.25 | 1.25x |
| Cache write (1-hour) | $10.00 | 2x |

> Prices above are legacy Opus 5 / 4.8. On Opus 5.5 the same rows are $4.00 input, **$0.20 hit (0.05x, 95% off)**, $5.00 5-minute write and $8.00 1-hour write -- the writes keep the 1.25x / 2x multipliers, only the hit multiplier changes.

**Caching best practices**:
- Place stable content at the beginning of prompts
- Use 5-min TTL for content that changes infrequently
- Use 1-hour TTL only for content reused across many requests
- The cache write cost is paid once; the savings compound over every subsequent request
- Respect the per-model minimum cacheable prompt length. Opus 5.5, Opus 5, Sonnet 5.5 and Haiku 5.5 need only **512 tokens** (down from 1,024 on Opus 4.8 and Sonnet 5, 2,048 on Opus 4.7, and 4,096 on Opus 4.6 and Haiku 4.5), so prefixes that were too short to cache before now qualify. Below the threshold the `cache_control` block is silently ignored -- no error, no discount.

---

## Hidden Costs to Watch

### 1. The Opus 4.7+ Tokenizer Inflates Effective Cost

Opus 4.7 introduced a new tokenizer (also used by Opus 4.8, Opus 5 and Opus 5.5) that produces **about 30% more tokens** for the exact same text compared to Opus 4.6 and earlier models; Anthropic adds that "the exact increase depends on the content and workload shape" ([pricing page](https://platform.claude.com/docs/en/about-claude/pricing)). The posted per-token rate does not change with it ($5/$25 on Opus 4.7 through 5, $4/$20 on Opus 5.5), but the same prompt now converts into more billable tokens.

```
Example: The same 10,000-character CLAUDE.md file, on Opus 4.7 ($5/MTok input)

With Opus 4.6 tokenizer: ~2,500 tokens  -> cost: $0.0125 input
With Opus 4.7 tokenizer: ~3,250 tokens  -> cost: $0.016 input  (2,500 x 1.3)

Over a 50-turn session that sends CLAUDE.md every turn, the 750 extra tokens cost:
  uncached:  750 x 50 x $5/1M                          = $0.19
  cached (Claude Code's default; 1 write, 49 hits):
             750 x $6.25/1M + 750 x 49 x $0.50/1M      = $0.023
```

> **Takeaway**: When budgeting for Opus 5.5, 5, 4.8, or 4.7, multiply your Opus 4.6 per-task token estimates by about 1.3 (Anthropic's pricing page) for a realistic projection. The step-change in coding quality usually pays for itself, but the accounting matters when setting budget caps.

### 1b. Opus 5 Thinks by Default and Talks Longer

On **Opus 5.5** the rule is stricter: adaptive thinking is always on and cannot be disabled, reasoning bills as output at $20/MTok, and effort (default `medium`) is the only control. Code that turned thinking off on Opus 5 pays for thinking after migrating; code that never set effort now thinks less than it did on Opus 5. Re-baseline either way.

Two Opus 5 defaults inflate output token counts at the same $25/MTok rate:

- **Adaptive thinking is on** whenever you omit the `thinking` parameter, and reasoning tokens bill as output. Effort defaults to `high` on the Claude API and in Claude Code. `max_tokens` caps thinking plus visible text together, so an `xhigh` or `max` run with a low `max_tokens` truncates instead of finishing -- raise it to 64K+.
- **Responses are longer than Opus 4.8's** by default, and Opus 5 self-verifies its own work. Any "double-check your work" or "verify before answering" instruction carried over from an Opus 4.8 prompt now pays for that behavior twice. Delete those lines and re-tune verbosity instructions when you migrate.

### 2. Regional Endpoint Premium

The 10% premium on regional endpoints applies to every token ([Claude in Amazon Bedrock](https://platform.claude.com/docs/en/build-with-claude/claude-in-amazon-bedrock#regions) and [Claude Models on Google Cloud (Google managed)](https://platform.claude.com/docs/en/build-with-claude/claude-models-on-google-cloud/google-managed#global-multi-region-and-regional-endpoints), read 2026-11-01). Over time, this adds up significantly.

| Usage Level | Monthly Tokens (in + out) | Global Cost | Regional Cost | Annual Premium |
|-------------|:------------------------:|:-----------:|:-------------:|:--------------:|
| Light | 5M in + 5M out | $120 | $132 | $144 |
| Medium | 20M in + 20M out | $480 | $528 | $576 |
| Heavy | 100M in + 100M out | $2,400 | $2,640 | $2,880 |

*Computed at Opus 5.5 rates: Light = 5 x $4 + 5 x $20 = $120 a month, x 1.1 regional, premium x 12. The equal input/output split is an assumption; the premium is 10% of the bill at any split. On legacy Opus 5 ($5/$25) the rows are $150, $600 and $3,000 global, and $180, $720 and $3,600 a year in premium.*

### 3. US Data Residency Premium

The 1.1x multiplier for US data residency (`inference_geo: "us"` on the Claude API, Claude Platform on AWS and Google Cloud (Anthropic managed); a US Data Zone Standard deployment on Microsoft Foundry) applies to Claude 4.6 and later models (including Opus 5.5, 5, 4.8, 4.7, Sonnet 5.5 and Haiku 5.5, whose over-100K tier is multiplied too; [pricing page](https://platform.claude.com/docs/en/about-claude/pricing#data-residency-pricing), read 2026-11-01):

| Model | Standard Input | US Residency Input | Extra Cost |
|-------|:--------------:|:------------------:|:----------:|
| Opus 5.5 | $4.00 | $4.40 | +$0.40/MTok |
| Opus 5.5 | $20.00 (output) | $22.00 (output) | +$2.00/MTok |
| Opus 5 / 4.8 / 4.7 / 4.6 | $5.00 | $5.50 | +$0.50/MTok |
| Opus 5 / 4.8 / 4.7 / 4.6 | $25.00 (output) | $27.50 (output) | +$2.50/MTok |
| Sonnet 5.5 | $2.00 | $2.20 | +$0.20/MTok |
| Sonnet 5.5 | $10.00 (output) | $11.00 (output) | +$1.00/MTok |
| Haiku 5.5 (prompt <= 100K) | $0.10 | $0.11 | +$0.01/MTok |
| Haiku 5.5 (prompt <= 100K) | $0.50 (output) | $0.55 (output) | +$0.05/MTok |
| Haiku 5.5 (prompt > 100K) | $0.50 | $0.55 | +$0.05/MTok |
| Haiku 5.5 (prompt > 100K) | $2.50 (output) | $2.75 (output) | +$0.25/MTok |

This is the same 10% premium as regional endpoints on Bedrock and Google Cloud. If you are already paying for regional endpoints for data residency, adding US data residency on the Anthropic API side doubles the compliance premium.

### 4. Cache Write Costs

Cache writes are not free. The 5-min TTL costs 1.25x the input price, and the 1-hour TTL costs 2x. If your content changes frequently (breaking the cache), you pay the write penalty repeatedly without getting the read benefit.

```
Bad pattern (cache breaks every turn):
  Turn 1: 100K tokens x $6.25/MTok (cache write) = $0.625
  Turn 2: 100K tokens x $6.25/MTok (cache write again) = $0.625
  Turn 3: 100K tokens x $6.25/MTok (cache write again) = $0.625
  Total: $1.875 for 3 turns

Good pattern (cache holds):
  Turn 1: 100K tokens x $6.25/MTok (cache write) = $0.625
  Turn 2: 100K tokens x $0.50/MTok (cache hit) = $0.050
  Turn 3: 100K tokens x $0.50/MTok (cache hit) = $0.050
  Total: $0.725 for 3 turns (2.6x cheaper)
```

### 5. Fast Mode + Cache: Stacks but Switching Invalidates

Prompt-caching multipliers (1.25x 5m write, 2x 1h write, and each model's hit multiplier) DO stack on top of Fast Mode rates. So an Opus 5.5 Fast Mode cache hit is $8 × 0.05 = $0.40 / MTok of input, and an Opus 5 or Opus 4.8 one is $10 × 0.1 = $1.00 / MTok -- still cheaper than uncached Fast Mode input. **However**, Fast and Standard speeds do NOT share cached prefixes. If you toggle between speeds within a session, every switch invalidates the cache and you pay a full cache-write again, and so does a fallback from fast to standard after a fast-mode 429 ([fast mode](https://platform.claude.com/docs/en/build-with-claude/fast-mode#retries-and-fallbacks), read 2026-11-01). Pick a speed and stick with it for the full conversation.

---

## Monthly Cost Projections

### Scenario: Solo Developer, Medium Usage

Assumptions: 20 working days/month, 30 turns/day, average 5K input + 2K output tokens per turn (after caching). That is 600 turns: 3.0M input and 1.2M output tokens a month, each API row computed as 3.0M x input rate + 1.2M x output rate.

| Platform | Configuration | Monthly Cost |
|----------|--------------|:------------:|
| **Claude Code Pro (annual)** | $200/yr ≈ $16.67/mo | **$17** |
| **Claude Code Pro (monthly)** | $20/mo subscription | $20 |
| **Claude Max** | $100/mo subscription | $100 |
| **Anthropic API** | Opus 5.5, standard (3.0M x $4 + 1.2M x $20) | $36 |
| **Anthropic API** | Opus 5 (legacy), standard (3.0M x $5 + 1.2M x $25) | $45 |
| **Anthropic API** | Sonnet 5.5 (3.0M x $2 + 1.2M x $10) | $18 |
| **Anthropic API** | Haiku 5.5 (3.0M x $0.10 + 1.2M x $0.50) | $0.90 |
| **Bedrock Global** | Opus 5.5 (same rates as the Anthropic API) | $36 |
| **Bedrock Regional** | Opus 5.5 (+10%) | $39.60 |

> At these light per-turn counts, Pro beats Opus 5.5 on the API ($20 vs $36) but not Sonnet 5.5 ($18) or Haiku 5.5 ($0.90). Real Claude Code turns resend the whole conversation (billed as cache reads), so heavy days cost far more: Anthropic's [costs page](https://code.claude.com/docs/en/costs) puts the average at around $13 per developer per active day and $150-250 per developer per month. At that level a subscription is cheaper, because it absorbs the cost of prompt caching, system prompts, and tool-use overhead.

### Scenario: Production Application, High Volume

Assumptions: 1M requests/month, average 2K input + 500 output tokens per request.

| Platform | Configuration | Monthly Cost |
|----------|--------------|:------------:|
| **Anthropic API** | Opus 5.5, standard | $18,000 |
| **Anthropic API** | Opus 5.5, batch | $9,000 |
| **Anthropic API** | Sonnet 5.5, standard | $9,000 |
| **Anthropic API** | Sonnet 5.5, batch | $4,500 |
| **Anthropic API** | Haiku 5.5, standard (2K prompts, <= 100K tier) | $450 |
| **Anthropic API** | Haiku 5.5, batch | $225 |
| **Bedrock Global** | Haiku 5.5, batch | $225 |
| **Bedrock Regional** | Haiku 5.5, batch | $247.50 |
| **Anthropic API** | Haiku 4.5 (legacy), standard | $4,500 |
| **Anthropic API** | Haiku 4.5 (legacy), batch | $2,250 |
| **Bedrock Global** | Haiku 4.5 (legacy), batch | $2,250 |
| **Bedrock Regional** | Haiku 4.5 (legacy), batch | $2,475 |

> Computed: 1M requests x 2K = 2,000M input tokens and 1M x 500 = 500M output tokens a month. Opus 5.5: 2,000 x $4 + 500 x $20 = $18,000; Sonnet 5.5: 2,000 x $2 + 500 x $10 = $9,000; batch halves each. (Earlier editions priced these rows at legacy Opus 5's $5/$25, $22,500 standard and $11,250 batch, and at Sonnet 4.6's $3/$15, $13,500 and $6,750.) Haiku 5.5 rows: 2,000M input x $0.10 + 500M output x $0.50 = $200 + $250 = $450; batch halves it to $225; Bedrock regional adds 10% ($247.50). Every request here is 2K tokens, far under the 100K tier line. If the 2K / 500 token counts were measured on Haiku 4.5, the same text is about 30% more tokens on Haiku 5.5, so budget about $585 standard ($450 x 1.3) -- still 7.7x below Haiku 4.5's $4,500.

### Scenario: Team of 5 Developers

Assumptions: Each developer uses Claude Code for ~4 hrs/day, plus a shared automation pipeline.

| Configuration | Monthly Cost |
|---------------|:------------:|
| 5x Claude Pro + Anthropic API for automation | $100 + API costs |
| Team, 5 Standard seats | $100 billed annually, $125 monthly |
| Team, 5 Premium seats | $500 billed annually, $625 monthly |
| 5x Claude Max | $500 |
| 5x Claude Ultra | $1,000 |
| Pure API (5 developers at Anthropic's average of $150-250 per developer per month, [costs page](https://code.claude.com/docs/en/costs)) | $750 to $1,250 |

*Computed: seats x price. Team seat prices ($20 / $25 Standard, $100 / $125 Premium per seat a month) are from [claude.com/pricing](https://claude.com/pricing), read 2026-11-01; Team needs at least 2 seats and its usage limits are per member, not pooled, but its monthly API credits pool ($20 per Standard, $100 per Premium seat, capped at $500). Pure API: 5 x $150 and 5 x $250.*

---

## The Cheapest Path

Here is the concrete recommendation for minimizing Claude costs, ordered by impact:

### For Interactive Development

1. **Use Claude Code subscriptions** -- the subscription model is almost always cheaper than API rates for interactive work
2. **Start with Pro ($20/mo, or $200/yr for 17% off)** and upgrade only if you consistently hit limits
3. **Use Haiku 5.5 for routine tasks** -- 40x cheaper per token than Opus 5.5 while the prompt stays at or under 100K tokens (8x above); Anthropic measured it at about a twentieth of Opus 5.5's cost per correct GPQA Diamond answer (and about a tenth of Sonnet 5.5's), at 85% accuracy vs 91% for each ([cost-optimization guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence), read 2026-11-01)
4. **Keep sessions short** -- start new sessions rather than letting context grow past 200K

### For Programmatic / Application Use

1. **Use the Batch API** for everything that does not need real-time responses -- **50% off**
2. **Use global endpoints** on Bedrock and Google Cloud -- regional costs **10% more**, so global takes 9.1% off a regional bill (computed: 1 - 1/1.1)
3. **Use Haiku 5.5** as your default model, keep its prompts under 100K tokens, and route to Sonnet/Opus only when complexity demands it
4. **Cache aggressively** -- structure prompts so stable content comes first. On Anthropic's API, agent loops read a median 84.2% of their input from cache (upper quartile 91.7%; 14 days ending 2026-08-23, 303,003 organization-days from 106,487 organizations), about 72% of coding organization-days read 80% or more, and the top decile of coding reads 95.9% or more; well below that, something in your prefix is changing ([cost-optimization guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence), read 2026-11-01).
5. **Watch cumulative context growth** -- 1M context is priced at standard rates on Opus 5.5/5/4.8/4.7/4.6 and Sonnet 5.5/5/4.6 (no premium; Haiku 5.5 is the exception and bills $0.50/$2.50 once a prompt passes 100K tokens), but absolute token count still grows with context, and the Opus 4.7+ tokenizer (used by Opus 4.8, Opus 5 and Opus 5.5) inflates the count further
6. **Never use Fast Mode** unless you have proven that standard latency is hurting your business metrics

### The Optimal Stack

For most teams, the cheapest configuration is:

```
Interactive work:  Claude Max ($100/mo per developer)
Automation:        Anthropic Batch API with Haiku 5.5 ($0.05/$0.25 per MTok, prompts up to 100K)
Complex tasks:     Anthropic API with Sonnet 5.5 ($2/$10 per MTok)
Rare, hard tasks:  Anthropic API with Opus 5.5 ($4/$20 per MTok)
Data residency:    Bedrock Regional or Google Cloud Multi-region / Regional (accept the 10% premium)
```

This gives you predictable costs for daily work, the cheapest possible rate for batch processing, and the flexibility to scale up to more capable models only when needed.

---

## Regional and Country-Specific Pricing

### Claude Code Subscriptions: No PPP Pricing

[claude.com/pricing](https://claude.com/pricing) lists every plan in **USD** with no purchasing power parity (PPP) or country-specific prices, and notes that prices exclude applicable tax (read 2026-11-01). Whether you're in the US, India, Brazil, or Japan, the rates are the same:

| Plan | Monthly | Annual (effective monthly) |
|------|:-------:|:-------------------------:|
| Pro | $20/mo | $200/yr ($16.67/mo, 17% off) |
| Max | $100/mo | -- (monthly only) |
| Ultra (formerly Max 20x) | $200/mo | -- (monthly only) |
| Team Standard / Premium seat | $25 / $125 per seat | $20 / $100 per seat |

This means the effective cost relative to local purchasing power varies significantly by country. For developers in regions with lower costs of living, the API pay-per-token model with cheaper models (Haiku 5.5 at $0.10/$0.50 up to 100K prompt tokens) may be more cost-effective than a subscription.

### Cloud Provider Committed-Use Discounts

If you access Claude through AWS Bedrock or Google Cloud, cloud-level discounts can stack on top of token pricing. This pass did not re-check the first two bullets on AWS's or Google's pages, so confirm them with your account team:

- **AWS Savings Plans**: Commit to consistent usage for 1 or 3 years for additional discounts on Bedrock
- **GCP Committed Use Discounts (CUDs)**: Similar committed-use pricing on Google Cloud (Google managed)
- **AWS/GCP credits**: Startup programs, migration credits, and enterprise agreements can offset Claude costs

The two Anthropic-operated marketplace offerings have their own levers: Google Cloud (Anthropic managed) usage counts toward a Google Cloud spend commitment the way other Marketplace purchases do, and Claude Platform on AWS applies an Anthropic private offer accepted in AWS Marketplace as fewer CCUs ([Anthropic managed](https://platform.claude.com/docs/en/build-with-claude/claude-models-on-google-cloud/anthropic-managed#billing), [pricing page](https://platform.claude.com/docs/en/about-claude/pricing#claude-platform-on-aws-pricing), read 2026-11-01). Cloud discounts do not apply to the first-party Claude API or Claude subscriptions.

### Off-Peak 2x Usage Events

Anthropic has run one documented off-peak promotion: from 2026-03-13 to 2026-03-28 it doubled 5-hour usage outside a weekday 8 AM - 2 PM ET peak (Help Center article 14063676, now offline; see [Off-Peak 2x in the cheatsheet](../cheatsheet.md#model-lifecycle)). No promotion is running: none appears on the pricing page or the Help Center usage articles (read 2026-11-01), and the peak window is not a standing schedule. If a promotion returns with the same window, developers in India and Asia-Pacific gain the most, since their entire workday falls outside it; a UK 9-to-5 overlaps it for 4 of 8 hours and a Central European one for 3 ([Guide 09](09-subscription-value.md#time-zone-advantage)).

---

## Key Takeaways

1. **Global endpoints on Bedrock and Google Cloud are the same price as the Anthropic API** -- use them if you need cloud billing integration without paying more
2. **Regional endpoints cost 10% more everywhere** -- only use them for data residency compliance. Scope = Sonnet 4.5+, Haiku 4.5+, Opus 4.5+, and all later models (Opus 5.5, Sonnet 5.5 and Haiku 5.5 included).
3. **The Batch API saves 50%** -- the single biggest discount available, for any workload that can wait
4. **1M context bills at standard rates on Opus 5.5/5/4.8/4.7/4.6 and Sonnet 5.5/5/4.6** -- no long-context premium. (Earlier "2x over 200K" applied to Opus 4.1 and older.) Haiku 5.5 is the exception: over 100K prompt tokens the whole request bills at $0.50/$2.50. Absolute cost still grows with token count, so trim aggressively anyway.
5. **Fast Mode is 2x standard on Opus 5.5 ($8/$40, available with no beta header), Opus 5 and Opus 4.8 ($10/$50, research preview) only**, and Opus 4.8's is removed on 2026-11-30. Opus 4.7 errors on `speed: "fast"`, Opus 4.6 silently runs standard on the Claude API, and the old 6x tier is gone. Almost never worth it for development work.
6. **Pro plan annual saves 17%** -- $200/yr vs $240/yr monthly equivalent, no usage difference. Max ($100, formerly Max 5x) and Ultra ($200, formerly Max 20x) are monthly only.
7. **Claude Platform on AWS** and its Google counterpart, **Google Cloud (Anthropic managed)** (launched 2026-10-22), bill CCUs at $0.01/CCU through the cloud's marketplace but match per-token rates -- pick them over Bedrock or Google Cloud (Google managed) for same-day Claude API features, Batch included. Fast Mode runs only on the Google one, for Opus 5.5.
6. **Cache hits save 90% on most models, 95% on Opus 5.5 and Sonnet 5.5, and 97.5% on Fable 5.1 / Mythos 5.1** -- structure your prompts to maximize cache reuse
7. **Claude Code subscriptions beat API rates for interactive development** -- the math almost always works out in favor of a subscription
8. **The cheapest token is the one you don't send** -- all the strategies in this repo (context optimization, model selection, workflow patterns) compound with platform-level savings
9. **Opus 5.5 (released 2026-09-22) costs $4/$20, 20% below Opus 5's $5/$25** (and Opus 4.8's), with cache hits at 0.05x instead of 0.1x, on all six platforms. Thinking is always on and default effort is `medium`, so your output token count can move in either direction; forced `tool_choice`, prefill and non-default sampling params now return 400, and there is no Priority Tier. Migrate, then re-baseline cost per task.
10. **Sonnet 5.5 (released 2026-09-28) costs what Sonnet 5 did, except cache reads** -- $2/$10, same cache writes and Batch, same tokenizer, but cache hits at $0.10 (0.05x) since 2026-10-07, half Sonnet 5's $0.20 -- and halves the cache floor to 512. Carried-over code can 400 (`thinking: disabled`, forced `tool_choice`, `computer_20251124` on the Claude API and Google Cloud), and effort levels are recalibrated, so re-run your effort sweep. In Claude Code on Bedrock, Google Cloud or Foundry, the `sonnet` alias still means Sonnet 4.5 at $3/$15 with 200K context, and Sonnet 4.5 is deprecated (retirement scheduled for 2026-11-30): pin `claude-sonnet-5-5` (Bedrock: `anthropic.claude-sonnet-5-5`) or you pay 1.5x for a smaller window.
11. **Haiku 5.5 (released 2026-10-07) is the first model priced by prompt length** -- $0.10/$0.50 up to 100K prompt tokens, $0.50/$2.50 above, with cache reads and writes counted toward the 100K. At or under the line it is 10x cheaper per token than legacy Haiku 4.5 (about 7.7x per task, computed: 10 / 1.3, after its about 30% larger token count) and 40x cheaper than Opus 5.5. Carried-over Haiku 4.5 code can 400 (`budget_tokens`, non-default sampling params, prefill, `computer_20250124` on the Claude API, Google Cloud and Bedrock). In Claude Code the `haiku` alias reaches Haiku 5.5 only on the Anthropic API (v2.1.293+); elsewhere pin `ANTHROPIC_DEFAULT_HAIKU_MODEL`.

---

*Next: Return to the [README](../README.md) for the full guide index, or see [Guide 01](01-understanding-costs.md) for the fundamentals of Claude billing.*
