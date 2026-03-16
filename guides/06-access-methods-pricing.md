# Guide 06: Access Methods and Pricing

> **Not all paths to Claude cost the same.** Understanding the pricing differences between Anthropic API, AWS Bedrock, Google Vertex AI, and Claude Code subscriptions can save you 10-50% depending on your use case.

Most teams pick a Claude access method based on convenience or existing cloud contracts — not cost. This is a mistake. The same workload can cost 10% more on a regional endpoint than a global one, or 50% less through the Batch API. This guide breaks down every access path, its exact pricing, and when to use each one.

---

## Table of Contents

- [Platform Overview](#platform-overview)
- [Anthropic API (Direct) Pricing](#anthropic-api-direct-pricing)
- [AWS Bedrock Pricing](#aws-bedrock-pricing)
- [Google Cloud Vertex AI Pricing](#google-cloud-vertex-ai-pricing)
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

There are four main ways to access Claude models:

| Platform | Access Type | Best For | Billing |
|----------|------------|----------|---------|
| **Anthropic API** | Direct REST API | Custom apps, programmatic access | Pay-per-token |
| **AWS Bedrock** | Managed AWS service | AWS-native teams, data residency | Pay-per-token (AWS billing) |
| **Google Vertex AI** | Managed GCP service | GCP-native teams, data residency | Pay-per-token (GCP billing) |
| **Claude Code** | CLI + Desktop + Mobile | Interactive development, quick tasks | Monthly subscription |

All four platforms provide access to the same Claude models with the same capabilities. The differences are in pricing, infrastructure, compliance features, and billing integration.

---

## Anthropic API (Direct) Pricing

The Anthropic API is the baseline. All other platforms price relative to it.

### Standard Pricing (per 1M tokens)

| Model | Input | Output | Cache Hit | Context Window | Max Output |
|-------|:-----:|:------:|:---------:|:--------------:|:----------:|
| **Opus 4.6** | $5.00 | $25.00 | $0.50 | 1M | 128K |
| **Opus 4.6 (1M context, >200K input)** | $10.00 (2x) | $37.50 (1.5x) | $1.00 | 1M | 128K |
| **Opus 4.6 Fast Mode** (research preview) | $30.00 (6x) | $150.00 (6x) | -- | 200K | 128K |
| **Sonnet 4.6** | $3.00 | $15.00 | $0.30 | 1M | 64K |
| **Sonnet 4.6 (1M context, >200K input)** | $6.00 (2x) | $22.50 (1.5x) | $0.60 | 1M | 64K |
| **Haiku 4.5** | $1.00 | $5.00 | $0.10 | 200K | 64K |

### Additional Pricing Modifiers

| Modifier | Effect | Details |
|----------|--------|---------|
| **Batch API** | 50% discount on all models | Non-real-time processing, results returned asynchronously |
| **US data residency** | 1.1x multiplier | Applies to Opus 4.6 and above |
| **Cache write (5-min TTL)** | 1.25x input price | Content cached for 5 minutes |
| **Cache write (1-hour TTL)** | 2x input price | Content cached for 1 hour |

### Batch API Pricing

The Batch API is the single biggest discount available. For any workload that does not need real-time responses:

| Model | Batch Input | Batch Output | Savings vs Standard |
|-------|:-----------:|:------------:|:-------------------:|
| **Opus 4.6** | $2.50 | $12.50 | 50% |
| **Sonnet 4.6** | $1.50 | $7.50 | 50% |
| **Haiku 4.5** | $0.50 | $2.50 | 50% |

---

## AWS Bedrock Pricing

AWS Bedrock provides Claude access through two endpoint types with different pricing.

### Global Endpoints (`global.anthropic.claude-*`)

Global endpoints match Anthropic API pricing exactly:

| Model | Input | Output | Cache Hit |
|-------|:-----:|:------:|:---------:|
| **Opus 4.6** | $5.00 | $25.00 | $0.50 |
| **Sonnet 4.6** | $3.00 | $15.00 | $0.30 |
| **Haiku 4.5** | $1.00 | $5.00 | $0.10 |

### Regional Endpoints (us/eu/jp/apac)

Regional endpoints carry a **10% premium** over global pricing:

| Model | Regional Input | Regional Output | Premium |
|-------|:--------------:|:---------------:|:-------:|
| **Opus 4.6** | $5.50 | $27.50 | +10% |
| **Sonnet 4.6** | $3.30 | $16.50 | +10% |
| **Haiku 4.5** | $1.10 | $5.50 | +10% |

### Bedrock Features

- **Batch inference**: Supported, 50% discount (same as Anthropic API)
- **Available regions**: us-east-1, us-west-2, eu-west-1, and others
- **Cross-region inference**: Global endpoints route to the nearest region automatically
- **Billing**: Through your AWS account, consolidated with other AWS services
- **Committed use discounts**: Available through AWS Savings Plans

> **Key point**: Unless you have a data residency requirement, always use global endpoints on Bedrock. You save 10% for zero effort.

---

## Google Cloud Vertex AI Pricing

Vertex AI follows the same global vs. regional pricing structure as Bedrock.

### Global Endpoints

Global endpoints match Anthropic API pricing exactly:

| Model | Input | Output | Cache Hit |
|-------|:-----:|:------:|:---------:|
| **Opus 4.6** | $5.00 | $25.00 | $0.50 |
| **Sonnet 4.6** | $3.00 | $15.00 | $0.30 |
| **Haiku 4.5** | $1.00 | $5.00 | $0.10 |

### Regional Endpoints

Regional endpoints carry the same **10% premium**:

| Model | Regional Input | Regional Output | Premium |
|-------|:--------------:|:---------------:|:-------:|
| **Opus 4.6** | $5.50 | $27.50 | +10% |
| **Sonnet 4.6** | $3.30 | $16.50 | +10% |
| **Haiku 4.5** | $1.10 | $5.50 | +10% |

### Vertex AI Features

- **Provisioned throughput**: Available on regional endpoints for guaranteed capacity
- **Available regions**: us-east1, europe-west1, and others
- **Billing**: Through your GCP account, consolidated with other GCP services
- **Committed use**: Available through GCP CUDs (committed use discounts)

---

## Claude Code Subscription Plans

Claude Code subscriptions bundle access into predictable monthly pricing.

### Plan Comparison

| Plan | Monthly Price | Usage Level | Per-Day Equivalent |
|------|:------------:|:-----------:|:------------------:|
| **Pro** | $20/mo | Baseline | ~$0.67/day |
| **Max 5x** | $100/mo | 5x Pro usage | ~$3.33/day |
| **Max 20x** | $200/mo | 20x Pro usage | ~$6.67/day |

### What Is Included

- Desktop app access (macOS, Windows, Linux)
- Mobile app access (iOS, Android)
- CLI access (Claude Code)
- Prompt caching (automatic)
- Access to all models (Opus, Sonnet, Haiku)

### When You Exceed Plan Limits

Token usage beyond your plan's included allocation is billed at standard API rates. This means:

- If you burn through your Max 20x allocation early in the month, additional usage costs $5/$25 per MTok (Opus) at API rates
- Heavy interactive development sessions can exceed even Max 20x limits
- Track your usage with `/usage` to avoid surprise overage

### Plan Selection Math

| Monthly Token Usage (Opus output) | Best Plan | Effective Cost |
|:---------------------------------:|:---------:|:--------------:|
| < 0.8M output tokens | Pro ($20) | $20/mo flat |
| 0.8M - 4M output tokens | Max 5x ($100) | $100/mo flat |
| 4M - 8M output tokens | Max 20x ($200) | $200/mo flat |
| > 8M output tokens | Max 20x + overage | $200 + API rates |

> **Note**: These are approximate thresholds. Actual included token allocations may vary and are subject to change.

---

## Side-by-Side Platform Comparison

### Opus 4.6 Pricing Across All Platforms (per 1M tokens)

| Platform | Endpoint | Input | Output | Cache Hit | Batch Input | Batch Output |
|----------|----------|:-----:|:------:|:---------:|:-----------:|:------------:|
| **Anthropic API** | Direct | $5.00 | $25.00 | $0.50 | $2.50 | $12.50 |
| **AWS Bedrock** | Global | $5.00 | $25.00 | $0.50 | $2.50 | $12.50 |
| **AWS Bedrock** | Regional | $5.50 | $27.50 | -- | $2.75 | $13.75 |
| **Google Vertex AI** | Global | $5.00 | $25.00 | $0.50 | -- | -- |
| **Google Vertex AI** | Regional | $5.50 | $27.50 | -- | -- | -- |

### Sonnet 4.6 Pricing Across All Platforms (per 1M tokens)

| Platform | Endpoint | Input | Output | Cache Hit | Batch Input | Batch Output |
|----------|----------|:-----:|:------:|:---------:|:-----------:|:------------:|
| **Anthropic API** | Direct | $3.00 | $15.00 | $0.30 | $1.50 | $7.50 |
| **AWS Bedrock** | Global | $3.00 | $15.00 | $0.30 | $1.50 | $7.50 |
| **AWS Bedrock** | Regional | $3.30 | $16.50 | -- | $1.65 | $8.25 |
| **Google Vertex AI** | Global | $3.00 | $15.00 | $0.30 | -- | -- |
| **Google Vertex AI** | Regional | $3.30 | $16.50 | -- | -- | -- |

### Haiku 4.5 Pricing Across All Platforms (per 1M tokens)

| Platform | Endpoint | Input | Output | Cache Hit | Batch Input | Batch Output |
|----------|----------|:-----:|:------:|:---------:|:-----------:|:------------:|
| **Anthropic API** | Direct | $1.00 | $5.00 | $0.10 | $0.50 | $2.50 |
| **AWS Bedrock** | Global | $1.00 | $5.00 | $0.10 | $0.50 | $2.50 |
| **AWS Bedrock** | Regional | $1.10 | $5.50 | -- | $0.55 | $2.75 |
| **Google Vertex AI** | Global | $1.00 | $5.00 | $0.10 | -- | -- |
| **Google Vertex AI** | Regional | $1.10 | $5.50 | -- | -- | -- |

---

## When to Use Each Platform

### Decision Tree

```
Start here: What is your primary use case?
|
+-- Interactive development (coding, debugging, exploration)
|   |
|   +-- Light usage (< 2 hrs/day) --> Claude Code Pro ($20/mo)
|   +-- Medium usage (2-6 hrs/day) --> Claude Code Max 5x ($100/mo)
|   +-- Heavy usage (6+ hrs/day) --> Claude Code Max 20x ($200/mo)
|
+-- Programmatic access (apps, pipelines, automation)
|   |
|   +-- Do you need AWS billing integration?
|   |   |
|   |   +-- Yes --> AWS Bedrock Global endpoints
|   |   +-- Yes + data residency --> AWS Bedrock Regional endpoints
|   |
|   +-- Do you need GCP billing integration?
|   |   |
|   |   +-- Yes --> Google Vertex AI Global endpoints
|   |   +-- Yes + data residency --> Google Vertex AI Regional endpoints
|   |
|   +-- No cloud preference --> Anthropic API (direct)
|       |
|       +-- Real-time needed? --> Standard API
|       +-- Can wait for results? --> Batch API (50% off)
|
+-- Data residency requirements (GDPR, HIPAA, SOC 2)
    |
    +-- AWS ecosystem --> Bedrock Regional (specific region)
    +-- GCP ecosystem --> Vertex AI Regional (specific region)
    +-- Anthropic --> US data residency option (1.1x Opus+)
```

### Platform Recommendations by Scenario

| Scenario | Recommended Platform | Why |
|----------|---------------------|-----|
| Solo developer, daily coding | Claude Code Max 5x | Predictable cost, all-in-one |
| Team of 5, mixed usage | Claude Code Pro (each) + API for automation | $100/mo team + per-use for scripts |
| Production app with Claude | Anthropic API (Batch where possible) | Cheapest per-token, 50% batch discount |
| AWS-native team, no residency needs | Bedrock Global | Same pricing, AWS billing integration |
| AWS team, EU data must stay in EU | Bedrock Regional (eu-west-1) | 10% premium, but meets GDPR requirements |
| GCP-native team | Vertex AI Global | Same pricing, GCP billing integration |
| High-volume batch processing | Anthropic Batch API | 50% off everything, can't beat it |
| Latency-critical application | Anthropic API (standard) or Fast Mode | Fast Mode is 6x cost but lowest latency |

---

## Cost Optimization Per Platform

### Strategy 1: Use Global Endpoints (Save 10% vs Regional)

This is the easiest win for Bedrock and Vertex AI users. Unless you have a hard data residency requirement, always use global endpoints.

| Endpoint Type | Opus Input | Opus Output | Annual Cost (10M tokens/mo) |
|---------------|:----------:|:-----------:|:---------------------------:|
| Global | $5.00 | $25.00 | $3,600 |
| Regional | $5.50 | $27.50 | $3,960 |
| **Savings** | | | **$360/year** |

For a team of 5 developers each using 10M output tokens/month, switching from regional to global saves **$1,800/year**.

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

| Processing Mode | Opus Input | Opus Output | 10M token job |
|-----------------|:----------:|:-----------:|:-------------:|
| Standard | $5.00 | $25.00 | $300.00 |
| Batch | $2.50 | $12.50 | $150.00 |
| **Savings** | | | **$150.00 per job** |

### Strategy 3: Avoid 1M Context Unless Needed (Save 50-100% on Input)

The 1M context window activates automatically when input exceeds 200K tokens. When it does, **all input tokens** in the request are charged at 2x, and **all output tokens** are charged at 1.5x. This is not a marginal surcharge on the tokens above 200K -- it is a multiplier on the entire request.

| Scenario | Input Tokens | Input Cost (Opus) | Output Cost (Opus, 10K output) |
|----------|:------------:|:-----------------:|:------------------------------:|
| Standard (under 200K) | 150,000 | $0.75 | $0.25 |
| 1M context (over 200K) | 250,000 | $2.50 | $0.375 |
| **Difference** | | **3.3x more** | **1.5x more** |

**How to stay under 200K**:
- Keep CLAUDE.md concise (see [Guide 02](02-context-optimization.md))
- Use `.claudeignore` to prevent large files from loading
- Start new sessions when context grows too large
- Use subagents to isolate expensive operations (see [Guide 04](04-workflow-patterns.md))

### Strategy 4: Avoid Fast Mode Unless Latency Is Critical (Save 83%)

Fast Mode costs 6x standard pricing. That is $30/$150 per MTok for Opus. Use it only when response latency directly impacts revenue or user experience.

| Mode | Opus Input | Opus Output | 1M token session |
|------|:----------:|:-----------:|:----------------:|
| Standard | $5.00 | $25.00 | $30.00 |
| Fast Mode | $30.00 | $150.00 | $180.00 |
| **Difference** | | | **$150.00 more per session** |

> **Rule of thumb**: If you are using Fast Mode for interactive development in Claude Code, you are almost certainly overpaying. Standard latency is fast enough for coding workflows.

### Strategy 5: Cache Effectively (Save Up to 90% on Repeated Input)

Prompt caching gives you a 90% discount on input tokens that have been seen before. The key is to structure your requests so that stable content (system prompts, reference documents, schemas) comes first and changes as little as possible between requests.

| Token Type | Opus Price | Relative Cost |
|------------|:----------:|:-------------:|
| Standard input | $5.00 | 1x |
| Cache hit | $0.50 | 0.1x (90% off) |
| Cache write (5-min) | $6.25 | 1.25x |
| Cache write (1-hour) | $10.00 | 2x |

**Caching best practices**:
- Place stable content at the beginning of prompts
- Use 5-min TTL for content that changes infrequently
- Use 1-hour TTL only for content reused across many requests
- The cache write cost is paid once; the savings compound over every subsequent request

---

## Hidden Costs to Watch

### 1. The Long Context Threshold Trap

When your input crosses 200K tokens, the 1M context pricing kicks in. The critical detail: **all tokens in the request get the multiplied rate**, not just the tokens above 200K.

```
Example: 210,000 input tokens with Opus 4.6

What you might expect:
  200,000 tokens x $5.00/MTok = $1.00
  + 10,000 tokens x $10.00/MTok = $0.10
  Total: $1.10

What actually happens:
  210,000 tokens x $10.00/MTok = $2.10  (ALL tokens at 2x rate)

The difference: $2.10 vs $1.10 = almost 2x more than expected
```

> **Takeaway**: If you are near the 200K boundary, it is cheaper to trim your input below 200K than to go slightly over. Going from 199K to 201K tokens doubles your entire input cost.

### 2. Regional Endpoint Premium

The 10% premium on regional endpoints applies to every token. Over time, this adds up significantly.

| Usage Level | Monthly Tokens (in + out) | Global Cost | Regional Cost | Annual Premium |
|-------------|:------------------------:|:-----------:|:-------------:|:--------------:|
| Light | 5M | $150 | $165 | $180 |
| Medium | 20M | $600 | $660 | $720 |
| Heavy | 100M | $3,000 | $3,300 | $3,600 |

### 3. US Data Residency Premium

The 1.1x multiplier for US data residency on Opus 4.6 and above means:

| Model | Standard Input | US Residency Input | Extra Cost |
|-------|:--------------:|:------------------:|:----------:|
| Opus 4.6 | $5.00 | $5.50 | +$0.50/MTok |
| Opus 4.6 | $25.00 (output) | $27.50 (output) | +$2.50/MTok |

This is the same 10% premium as regional endpoints on Bedrock/Vertex. If you are already paying for regional endpoints for data residency, adding US data residency on the Anthropic API side doubles the compliance premium.

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

### 5. Fast Mode Has No Cache Hits

Fast Mode does not support cache hits. Every token is charged at the full 6x rate. This makes long conversations in Fast Mode extraordinarily expensive.

---

## Monthly Cost Projections

### Scenario: Solo Developer, Medium Usage

Assumptions: 20 working days/month, 30 turns/day, average 5K input + 2K output tokens per turn (after caching).

| Platform | Configuration | Monthly Cost |
|----------|--------------|:------------:|
| **Claude Code Pro** | $20/mo subscription | $20 |
| **Claude Code Max 5x** | $100/mo subscription | $100 |
| **Anthropic API** | Opus, standard | $360 |
| **Anthropic API** | Opus, with caching (~70% hit rate) | $144 |
| **Anthropic API** | Sonnet, with caching | $86 |
| **Anthropic API** | Haiku, with caching | $29 |
| **Bedrock Global** | Opus, with caching | $144 |
| **Bedrock Regional** | Opus, with caching | $158 |

> For interactive development, Claude Code subscriptions are almost always cheaper than raw API usage, because the subscription absorbs the cost of prompt caching, system prompts, and tool-use overhead.

### Scenario: Production Application, High Volume

Assumptions: 1M requests/month, average 2K input + 500 output tokens per request.

| Platform | Configuration | Monthly Cost |
|----------|--------------|:------------:|
| **Anthropic API** | Opus, standard | $22,500 |
| **Anthropic API** | Opus, batch | $11,250 |
| **Anthropic API** | Sonnet, standard | $13,500 |
| **Anthropic API** | Sonnet, batch | $6,750 |
| **Anthropic API** | Haiku, standard | $4,500 |
| **Anthropic API** | Haiku, batch | $2,250 |
| **Bedrock Global** | Haiku, batch | $2,250 |
| **Bedrock Regional** | Haiku, batch | $2,475 |

### Scenario: Team of 5 Developers

Assumptions: Each developer uses Claude Code for ~4 hrs/day, plus a shared automation pipeline.

| Configuration | Monthly Cost |
|---------------|:------------:|
| 5x Claude Code Pro + Anthropic API for automation | $100 + API costs |
| 5x Claude Code Max 5x | $500 |
| 5x Claude Code Max 20x | $1,000 |
| Pure API (Opus, 5 developers) | ~$1,800 |
| Pure API (Sonnet, 5 developers) | ~$1,080 |

---

## The Cheapest Path

Here is the concrete recommendation for minimizing Claude costs, ordered by impact:

### For Interactive Development

1. **Use Claude Code subscriptions** -- the subscription model is almost always cheaper than API rates for interactive work
2. **Start with Pro ($20/mo)** and upgrade only if you consistently hit limits
3. **Use Haiku for routine tasks** -- 5x cheaper than Opus, handles 80% of coding tasks
4. **Keep sessions short** -- start new sessions rather than letting context grow past 200K

### For Programmatic / Application Use

1. **Use the Batch API** for everything that does not need real-time responses -- **50% off**
2. **Use global endpoints** on Bedrock and Vertex AI -- **10% savings** over regional
3. **Use Haiku** as your default model and route to Sonnet/Opus only when complexity demands it
4. **Cache aggressively** -- structure prompts so stable content comes first, aim for 70%+ cache hit rates
5. **Stay under 200K input tokens** -- the 2x multiplier at the threshold is a steep cliff, not a gradual slope
6. **Never use Fast Mode** unless you have proven that standard latency is hurting your business metrics

### The Optimal Stack

For most teams, the cheapest configuration is:

```
Interactive work:  Claude Code Max 5x ($100/mo per developer)
Automation:        Anthropic Batch API with Haiku ($0.50/$2.50 per MTok)
Complex tasks:     Anthropic API with Sonnet ($3/$15 per MTok)
Rare, hard tasks:  Anthropic API with Opus ($5/$25 per MTok)
Data residency:    Bedrock/Vertex Regional (accept the 10% premium)
```

This gives you predictable costs for daily work, the cheapest possible rate for batch processing, and the flexibility to scale up to more capable models only when needed.

---

## Key Takeaways

1. **Global endpoints on Bedrock and Vertex AI are the same price as the Anthropic API** -- use them if you need cloud billing integration without paying more
2. **Regional endpoints cost 10% more everywhere** -- only use them for data residency compliance
3. **The Batch API saves 50%** -- the single biggest discount available, for any workload that can wait
4. **1M context doubles your input cost on all tokens** -- stay under 200K whenever possible
5. **Fast Mode is 6x standard pricing** -- almost never worth it for development work
6. **Cache hits save 90%** -- structure your prompts to maximize cache reuse
7. **Claude Code subscriptions beat API rates for interactive development** -- the math almost always works out in favor of a subscription
8. **The cheapest token is the one you don't send** -- all the strategies in this repo (context optimization, model selection, workflow patterns) compound with platform-level savings

---

*Next: Return to the [README](../README.md) for the full guide index, or see [Guide 01](01-understanding-costs.md) for the fundamentals of Claude billing.*
