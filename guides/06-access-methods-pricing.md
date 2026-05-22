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

There are five main ways to access Claude models:

| Platform | Access Type | Best For | Billing |
|----------|------------|----------|---------|
| **Anthropic API** (first-party) | Direct REST API | Custom apps, full feature access (Fast Mode, Batch, Files, MCP connector, Managed Agents) | Pay-per-token, USD invoiced by Anthropic |
| **Claude Platform on AWS** | Anthropic-operated on AWS Marketplace | AWS-native teams that want Anthropic-operated infra + same-day feature parity | Pay-per-token, billed in **Claude Consumption Units (CCU)** at $0.01/CCU through AWS Marketplace |
| **AWS Bedrock** (Mantle + legacy) | Partner-operated AWS service | AWS-native teams, data residency, AWS security boundary | Pay-per-token (AWS billing) |
| **Google Vertex AI** | Managed GCP service | GCP-native teams, data residency | Pay-per-token (GCP billing) |
| **Microsoft Foundry** | Anthropic-operated on Azure | Azure-native teams | Pay-per-token through Azure |
| **Claude Code** subscription | CLI + Desktop + Mobile | Interactive development | Monthly or annual subscription |

All platforms provide access to the same Claude models with the same intelligence. The differences are in pricing, infrastructure, compliance features, and billing integration. Some features (Fast Mode, Batch API, MCP connector, Files API, server-side tools, Managed Agents) are first-party-only.

---

## Anthropic API (Direct) Pricing

The Anthropic API is the baseline. All other platforms price relative to it.

### Standard Pricing (per 1M tokens, verified 2026-05-22)

| Model | Input | Output | Cache Hit | 5m Cache Write | 1h Cache Write | Context | Max Output |
|-------|:-----:|:------:|:---------:|:--------------:|:--------------:|:-------:|:----------:|
| **Opus 4.7** (current) | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1M | 128K |
| **Opus 4.6** | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1M | 128K |
| **Opus 4.5** | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 200K | 64K |
| **Opus 4.1** | $15.00 | $75.00 | $1.50 | $18.75 | $30.00 | 200K | 32K |
| **Opus 4.7 / 4.6 Fast Mode** (beta) | $30.00 (6x) | $150.00 (6x) | -- | -- | -- | 1M (included) | 128K |
| **Sonnet 4.6** | $3.00 | $15.00 | $0.30 | $3.75 | $6.00 | 1M | 64K |
| **Sonnet 4.5** | $3.00 | $15.00 | $0.30 | $3.75 | $6.00 | 200K | 64K |
| **Haiku 4.5** | $1.00 | $5.00 | $0.10 | $1.25 | $2.00 | 200K | 64K |
| **Mythos Preview** (Glasswing, invite-only) | $25.00 | $125.00 | $2.50 | $31.25 | $50.00 | 1M | -- |

> **Mythos Preview** is a separate research-preview model for defensive cybersecurity research only, accessible to [Project Glasswing](https://anthropic.com/glasswing) partners (11 founding: AWS, Anthropic, Apple, Broadcom, Cisco, CrowdStrike, Google, JPMorganChase, Linux Foundation, Microsoft, NVIDIA, Palo Alto Networks; plus 40+ critical-infrastructure organizations and open-source maintainers). $100M of complimentary credits were committed by Anthropic during the preview. No self-serve signup. If you're not in the program, this row is for reference only.

> **1M context at standard rates**: Opus 4.7, Opus 4.6, and Sonnet 4.6 charge the standard per-token rate across the full 1M window — no long-context premium. Opus 4.5, Sonnet 4.5, Opus 4.1, and Haiku 4.5 are 200K-context only.
>
> **Opus 4.7 tokenizer**: New tokenizer uses up to **35% more tokens** for the same text. The posted $5/$25 rate is unchanged but effective cost rises proportionally. Budget accordingly.
>
> **Tool-use overhead**: Tool definitions add a system-prompt token cost on every call. Current models add **346 tokens** for `tool_choice: auto` or `none`, **313 tokens** for `any` or `tool`. Add this to your `tools` array (names + descriptions + schemas) when budgeting.

### Additional Pricing Modifiers

| Modifier | Effect | Details |
|----------|--------|---------|
| **Batch API** | 50% discount on input AND output | Non-real-time, async results. Stacks with prompt caching. NOT compatible with Fast Mode or Priority Tier. |
| **Data residency** (`inference_geo: "us"`) | 1.1x multiplier on every category | Applies to Opus 4.6, Sonnet 4.6, and all later models on Claude API (1P) and Claude Platform on AWS. Earlier models error if the parameter is set. |
| **Fast Mode** (beta) | 6x rates ($30 / $150 per MTok) | Opus 4.7 and Opus 4.6 only. Header `anthropic-beta: fast-mode-2026-02-01`, `speed: "fast"`. Up to 2.5x output tokens/sec. |
| **Cache write (5-min TTL)** | 1.25x base input price | Content cached for 5 minutes. Pays off after 1 reuse. |
| **Cache write (1-hour TTL)** | 2x base input price | Content cached for 1 hour. Pays off after 2 reuses. |
| **Cache hit / refresh** | 0.1x base input price | 90% off vs uncached input. |

### Batch API Pricing

The Batch API is the single biggest discount available. For any workload that does not need real-time responses:

| Model | Batch Input | Batch Output | Savings vs Standard |
|-------|:-----------:|:------------:|:-------------------:|
| **Opus 4.7** | $2.50 | $12.50 | 50% |
| **Opus 4.6** | $2.50 | $12.50 | 50% |
| **Opus 4.5** | $2.50 | $12.50 | 50% |
| **Opus 4.1** | $7.50 | $37.50 | 50% |
| **Sonnet 4.6** | $1.50 | $7.50 | 50% |
| **Sonnet 4.5** | $1.50 | $7.50 | 50% |
| **Haiku 4.5** | $0.50 | $2.50 | 50% |

> Batch API is NOT available on Claude Platform on AWS. It IS available on Anthropic API, Bedrock, and Vertex AI.

### Server-side tools (additional charges)

| Tool | Charge | Notes |
|------|--------|-------|
| **Web search** | $10 per 1,000 searches + token costs | Each search counts once regardless of result count. Errors are not billed. |
| **Web fetch** | Free (token costs only) | Use `max_content_tokens` to cap large pages. |
| **Code execution** | Free with web search/fetch in same request; otherwise 1,550 free hours/org/month, then **$0.05 per hour per container** | 5-minute minimum execution time. Replaced by session runtime when using Managed Agents. |
| **Bash tool** | +245 input tokens per call | Plus stdout/stderr token costs. |
| **Text editor tool** | +700 input tokens per call | `text_editor_20250429` for Claude 4.x. |
| **Computer use tool** | +735 input tokens per tool definition + 466-499 system-prompt tokens | Plus screenshot vision tokens. |

### Claude Managed Agents (separate billing dimension)

Tokens billed at standard model rates (caching multipliers apply identically). **Plus** session runtime: **$0.08 per session-hour** of `running` status (not idle, rescheduling, or terminated). Replaces Code Execution container-hour billing — you are not billed twice. Batch, Fast Mode, data residency, and partner-cloud pricing do **not** apply to Managed Agents sessions.

---

## AWS Bedrock Pricing

AWS Bedrock provides Claude access through two endpoint types with different pricing. As of 2026-05-22, **Opus 4.7 is generally available and open to all Bedrock customers** (no waitlist). Anthropic also offers two Bedrock integration paths: the new Claude in Amazon Bedrock (Mantle) endpoint, and the legacy InvokeModel/Converse API.

### Global Endpoints

Global endpoints match Anthropic API pricing exactly:

| Model | Input | Output | Cache Hit |
|-------|:-----:|:------:|:---------:|
| **Opus 4.7** (open access, GA) | $5.00 | $25.00 | $0.50 |
| **Opus 4.6** | $5.00 | $25.00 | $0.50 |
| **Sonnet 4.6** | $3.00 | $15.00 | $0.30 |
| **Sonnet 4.5** | $3.00 | $15.00 | $0.30 |
| **Haiku 4.5** | $1.00 | $5.00 | $0.10 |
| **Mythos Preview** (invite-only, regional `us-east-1` only) | $25.00 | $125.00 | $2.50 |

### Regional Endpoints (us/eu/jp/apac/au inference profiles)

Regional endpoints carry a **10% premium** over global pricing. Scope: **Sonnet 4.5+, Haiku 4.5+, Opus 4.5+, and all later models**. Earlier models retain their existing pricing.

| Model | Regional Input | Regional Output | Premium |
|-------|:--------------:|:---------------:|:-------:|
| **Opus 4.7** | $5.50 | $27.50 | +10% |
| **Opus 4.6** | $5.50 | $27.50 | +10% |
| **Opus 4.5** | $5.50 | $27.50 | +10% |
| **Sonnet 4.6** | $3.30 | $16.50 | +10% |
| **Sonnet 4.5** | $3.30 | $16.50 | +10% |
| **Haiku 4.5** | $1.10 | $5.50 | +10% |

### Bedrock Features

- **Batch inference**: Supported, 50% discount (same as Anthropic API)
- **Available regions** (Mantle endpoint): 27 AWS regions including us-east-1, us-east-2, us-west-1, us-west-2, eu-west-1/2/3, eu-central-1/2, eu-north-1, eu-south-1/2, ap-northeast-1/2/3, ap-south-1/2, ap-southeast-1/2/3/4, ca-central-1, ca-west-1, sa-east-1, af-south-1, il-central-1, me-central-1
- **Endpoint types**: Global (dynamic routing across all regions, no premium), Regional (single region, +10%), or geographic inference profiles (US, EU, JP, AU at +10%)
- **Quotas**: Default 2M input TPM, up to 4M without Anthropic approval. AWS sets RPM limits separately.
- **Authentication**: Bedrock service role (recommended), IAM assumed roles (12-hour max), or short-lived bearer tokens
- **Billing**: Through your AWS account, consolidated with other AWS services
- **Committed use discounts**: Available through AWS Savings Plans

### Bedrock Model IDs

The new **Claude in Amazon Bedrock (Mantle)** endpoint at `https://bedrock-mantle.{region}.api.aws/anthropic/v1/messages` uses the same Messages API shape as the first-party Anthropic API, with an `anthropic.` prefix on model IDs:

| Model | Mantle Model ID | Legacy Bedrock ID (InvokeModel/Converse) |
|-------|-----------------|------------------------------------------|
| Opus 4.7 | `anthropic.claude-opus-4-7` | `us.anthropic.claude-opus-4-7` (cross-region inference profile) |
| Opus 4.6 | `anthropic.claude-opus-4-6` | `anthropic.claude-opus-4-6-v1` |
| Opus 4.5 | -- | `anthropic.claude-opus-4-5-20251101-v1:0` |
| Opus 4.1 | -- | `anthropic.claude-opus-4-1-20250805-v1:0` |
| Sonnet 4.6 | `anthropic.claude-sonnet-4-6` | `anthropic.claude-sonnet-4-6` |
| Sonnet 4.5 | -- | `anthropic.claude-sonnet-4-5-20250929-v1:0` |
| Haiku 4.5 | `anthropic.claude-haiku-4-5` | `anthropic.claude-haiku-4-5-20251001-v1:0` |
| Mythos Preview | `anthropic.claude-mythos-preview` | (Bedrock Marketplace allowlist required) |

### Bedrock Mantle: features supported and NOT supported

**Supported**: Messages API, prompt caching, extended thinking, tool use (bash, computer use, memory tool, text editor), citations, structured outputs.

**NOT supported on Bedrock Mantle**: Files API, server-side tools (code execution, web search, web fetch, advisor), Agent Skills, MCP connector, programmatic tool calling, Message Batches API, Models API, Admin API, Compliance API, Usage and Cost API, Claude Managed Agents, Fast Mode.

> **Key point**: Unless you have a data residency requirement, always use global endpoints on Bedrock. You save 10% for zero effort.

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

For Opus 4.6, Sonnet 4.6, and later models, setting `inference_geo: "us"` applies a **1.1x pricing multiplier** to all token categories. `inference_geo: "global"` (default) uses standard pricing.

### What's NOT available on Claude Platform on AWS

- Fast Mode (first-party API only)
- Batch API (sessions are interactive, no batch mode)
- Bedrock-style cloud-platform pricing (CCU model is unified)

### Why pick this over Bedrock?

- **Same-day feature parity** with the first-party Anthropic API (Bedrock typically lags)
- **Anthropic-operated infrastructure** rather than partner-operated
- **AWS Marketplace billing** so usage rolls into your AWS bill but is governed by Anthropic's deprecation/feature schedule (not Bedrock's)
- Same model IDs as the Anthropic API (e.g. `claude-opus-4-7`), not Bedrock-style IDs

---

## Google Cloud Vertex AI Pricing

Vertex AI follows the same global vs. regional pricing structure as Bedrock, plus a **multi-region** endpoint type unique to Vertex.

### Global Endpoints

Global endpoints match Anthropic API pricing exactly:

| Model | Input | Output | Cache Hit |
|-------|:-----:|:------:|:---------:|
| **Opus 4.7** | $5.00 | $25.00 | $0.50 |
| **Opus 4.6** | $5.00 | $25.00 | $0.50 |
| **Opus 4.5** | $5.00 | $25.00 | $0.50 |
| **Sonnet 4.6** | $3.00 | $15.00 | $0.30 |
| **Sonnet 4.5** | $3.00 | $15.00 | $0.30 |
| **Haiku 4.5** | $1.00 | $5.00 | $0.10 |

### Regional and Multi-Region Endpoints

Both regional endpoints (single GCP region) and multi-region endpoints (dynamic routing within a geography) carry a **10% premium**:

| Model | Regional/Multi-Region Input | Regional/Multi-Region Output | Premium |
|-------|:---------------------------:|:----------------------------:|:-------:|
| **Opus 4.7** | $5.50 | $27.50 | +10% |
| **Opus 4.6** | $5.50 | $27.50 | +10% |
| **Opus 4.5** | $5.50 | $27.50 | +10% |
| **Sonnet 4.6** | $3.30 | $16.50 | +10% |
| **Sonnet 4.5** | $3.30 | $16.50 | +10% |
| **Haiku 4.5** | $1.10 | $5.50 | +10% |

### Vertex AI Model IDs

| Model | Vertex AI Model ID |
|-------|---------------------|
| Opus 4.7 | `claude-opus-4-7` |
| Opus 4.6 | `claude-opus-4-6` |
| Opus 4.5 | `claude-opus-4-5@20251101` |
| Opus 4.1 | `claude-opus-4-1@20250805` |
| Sonnet 4.6 | `claude-sonnet-4-6` |
| Sonnet 4.5 | `claude-sonnet-4-5@20250929` |
| Haiku 4.5 | `claude-haiku-4-5@20251001` |

### Vertex AI Features

- **Provisioned throughput**: Available on regional endpoints for guaranteed capacity
- **Endpoint types**: Global (no premium), multi-region (+10%), regional (+10%)
- **Billing**: Through your GCP account, consolidated with other GCP services
- **Committed use**: Available through GCP CUDs (committed use discounts)

---

## Claude Code Subscription Plans

Claude Code subscriptions bundle access into predictable monthly (or annual) pricing.

### Plan Comparison

| Plan | Monthly Price | Annual Price (effective monthly) | Usage Level | Per-Day Equivalent |
|------|:------------:|:--------------------------------:|:-----------:|:------------------:|
| **Pro** | $20/mo | **$200/yr (~$16.67/mo, ~17% off)** | Baseline | ~$0.67/day (annual) |
| **Max 5x** | $100/mo | (annual not currently published) | 5x Pro usage | ~$3.33/day |
| **Max 20x** | $200/mo | (annual not currently published) | 20x Pro usage | ~$6.67/day |

> **Annual Pro plan saves 17%** vs monthly. If you'll use Claude for >2 months in a year, annual is a no-brainer. Math: $200/yr ÷ 12 = $16.67/mo vs $20/mo monthly = $40/yr saved.

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

### Opus 4.7 / 4.6 Pricing Across All Platforms (per 1M tokens)

Both Opus 4.7 and Opus 4.6 share the same base pricing and are **GA across every platform** (Anthropic API, Claude Platform on AWS, AWS Bedrock, Google Vertex AI).

| Platform | Endpoint | Input | Output | Cache Hit | Batch Input | Batch Output |
|----------|----------|:-----:|:------:|:---------:|:-----------:|:------------:|
| **Anthropic API** | Direct | $5.00 | $25.00 | $0.50 | $2.50 | $12.50 |
| **Claude Platform on AWS** | CCU billing (global) | $5.00 | $25.00 | $0.50 | -- (no Batch) | -- |
| **Claude Platform on AWS** | `inference_geo: "us"` | $5.50 | $27.50 | $0.55 | -- | -- |
| **AWS Bedrock** | Global | $5.00 | $25.00 | $0.50 | $2.50 | $12.50 |
| **AWS Bedrock** | Regional | $5.50 | $27.50 | $0.55 | $2.75 | $13.75 |
| **Google Vertex AI** | Global | $5.00 | $25.00 | $0.50 | $2.50 | $12.50 |
| **Google Vertex AI** | Regional / Multi-region | $5.50 | $27.50 | $0.55 | $2.75 | $13.75 |

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
|   +-- Light usage (< 2 hrs/day) --> Claude Code Pro ($20/mo or $200/yr ≈ $16.67/mo)
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

### Strategy 3: Watch Cumulative Context Growth (Long Context Is Now Free, But Cache Write Costs Grow With It)

**Good news**: Opus 4.7, Opus 4.6, and Sonnet 4.6 now bill the full 1M context window at **standard per-token rates**. There is no longer a 2x input / 1.5x output premium for crossing the 200K threshold. (This earlier pricing applied to Opus 4.1 and older.)

**The catch**: While the rate is flat, the absolute token count still grows with context. A 500K-token input at $5/MTok is $2.50 per call -- small per call, but it adds up across a long session, and every fresh cache write on that content costs 1.25-2x more in absolute dollars.

| Scenario | Input Tokens | Input Cost (Opus 4.7) | Output Cost (10K output) |
|----------|:------------:|:---------------------:|:------------------------:|
| Standard (under 200K) | 150,000 | $0.75 | $0.25 |
| Long context (over 200K) | 500,000 | $2.50 | $0.25 |
| **Difference** | | **3.3x more** (proportional only) | same |

**How to keep context from ballooning**:
- Keep CLAUDE.md concise (see [Guide 02](02-context-optimization.md))
- Use `.claudeignore` to prevent large files from loading
- Start new sessions when context grows too large
- Use subagents to isolate expensive operations (see [Guide 04](04-workflow-patterns.md))
- Remember: Opus 4.7's new tokenizer makes the same source text ~20-35% more tokens than it used to be, so "size" thresholds shift lower.

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

### 1. Opus 4.7's New Tokenizer Inflates Effective Cost

Opus 4.7 introduced a new tokenizer that can use up to **35% more tokens** for the exact same text compared to Opus 4.6 and earlier models. The posted per-token rate is unchanged ($5/$25), but the same prompt now converts into more billable tokens.

```
Example: The same 10,000-character CLAUDE.md file

With Opus 4.6 tokenizer: ~2,500 tokens  -> cost: $0.0125 input
With Opus 4.7 tokenizer: ~3,375 tokens  -> cost: $0.017 input  (+35%)

Over a 50-turn session with CLAUDE.md reloaded every turn,
the difference compounds to ~$0.22 extra just for CLAUDE.md alone.
```

> **Takeaway**: When budgeting for Opus 4.7, multiply your Opus 4.6 per-task cost estimates by 1.2-1.35 for a realistic projection. The step-change in coding quality usually pays for itself, but the accounting matters when setting budget caps.

### 2. Regional Endpoint Premium

The 10% premium on regional endpoints applies to every token. Over time, this adds up significantly.

| Usage Level | Monthly Tokens (in + out) | Global Cost | Regional Cost | Annual Premium |
|-------------|:------------------------:|:-----------:|:-------------:|:--------------:|
| Light | 5M | $150 | $165 | $180 |
| Medium | 20M | $600 | $660 | $720 |
| Heavy | 100M | $3,000 | $3,300 | $3,600 |

### 3. US Data Residency Premium

The 1.1x multiplier for US data residency (`inference_geo: us-only` on the Claude API) applies to Opus 4.7 and newer models:

| Model | Standard Input | US Residency Input | Extra Cost |
|-------|:--------------:|:------------------:|:----------:|
| Opus 4.7 / 4.6 | $5.00 | $5.50 | +$0.50/MTok |
| Opus 4.7 / 4.6 | $25.00 (output) | $27.50 (output) | +$2.50/MTok |

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

### 5. Fast Mode + Cache: Stacks but Switching Invalidates

Prompt-caching multipliers (1.25x 5m write, 2x 1h write, 0.1x hit) DO stack on top of Fast Mode rates. So a Fast Mode cache hit is $30 × 0.1 = $3.00 / MTok of input — still cheaper than uncached Fast Mode input. **However**, Fast and Standard speeds do NOT share cached prefixes. If you toggle between speeds within a session, every switch invalidates the cache and you pay a full cache-write again. Pick a speed and stick with it for the full conversation.

---

## Monthly Cost Projections

### Scenario: Solo Developer, Medium Usage

Assumptions: 20 working days/month, 30 turns/day, average 5K input + 2K output tokens per turn (after caching).

| Platform | Configuration | Monthly Cost |
|----------|--------------|:------------:|
| **Claude Code Pro (annual)** | $200/yr ≈ $16.67/mo | **$17** |
| **Claude Code Pro (monthly)** | $20/mo subscription | $20 |
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
2. **Start with Pro ($20/mo, or $200/yr for 17% off)** and upgrade only if you consistently hit limits
3. **Use Haiku for routine tasks** -- 5x cheaper than Opus, handles 80% of coding tasks
4. **Keep sessions short** -- start new sessions rather than letting context grow past 200K

### For Programmatic / Application Use

1. **Use the Batch API** for everything that does not need real-time responses -- **50% off**
2. **Use global endpoints** on Bedrock and Vertex AI -- **10% savings** over regional
3. **Use Haiku** as your default model and route to Sonnet/Opus only when complexity demands it
4. **Cache aggressively** -- structure prompts so stable content comes first, aim for 70%+ cache hit rates
5. **Watch cumulative context growth** -- 1M context is priced at standard rates on Opus 4.7/4.6 and Sonnet 4.6 (no premium), but absolute token count still grows with context, and Opus 4.7's new tokenizer inflates the count further
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

## Regional and Country-Specific Pricing

### Claude Code Subscriptions: No PPP Pricing

As of 2026-05, Claude Code subscriptions are priced in **USD globally** with no purchasing power parity (PPP) or country-specific pricing. Whether you're in the US, India, Brazil, or Japan, the rates are the same:

| Plan | Monthly | Annual (effective monthly) |
|------|:-------:|:-------------------------:|
| Pro | $20/mo | $200/yr (~$16.67/mo, 17% off) |
| Max 5x | $100/mo | -- |
| Max 20x | $200/mo | -- |

This means the effective cost relative to local purchasing power varies significantly by country. For developers in regions with lower costs of living, the API pay-per-token model with cheaper models (Haiku at $1/$5) may be more cost-effective than a subscription.

### Cloud Provider Committed-Use Discounts

If you access Claude through AWS Bedrock or Google Vertex AI, you can stack cloud-level discounts on top of token pricing:

- **AWS Savings Plans**: Commit to consistent usage for 1 or 3 years for additional discounts on Bedrock
- **GCP Committed Use Discounts (CUDs)**: Similar committed-use pricing on Vertex AI
- **AWS/GCP credits**: Startup programs, migration credits, and enterprise agreements can offset Claude costs

These discounts are not available through the Anthropic API directly or Claude Code subscriptions.

### Off-Peak 2x Usage Events

Anthropic periodically runs promotional events that double usage limits during off-peak hours (see [Off-Peak 2x in README](../README.md#off-peak-2x-usage-promotional-events)). During these events, developers outside the US get the most benefit since their entire workday falls outside US peak hours (8 AM - 2 PM ET).

---

## Key Takeaways

1. **Global endpoints on Bedrock and Vertex AI are the same price as the Anthropic API** -- use them if you need cloud billing integration without paying more
2. **Regional endpoints cost 10% more everywhere** -- only use them for data residency compliance. Scope = Sonnet 4.5+, Haiku 4.5+, Opus 4.5+.
3. **The Batch API saves 50%** -- the single biggest discount available, for any workload that can wait
4. **1M context bills at standard rates on Opus 4.7/4.6 and Sonnet 4.6** -- no long-context premium. (Earlier "2x over 200K" applied to Opus 4.1 and older.) Absolute cost still grows with token count, so trim aggressively anyway.
5. **Fast Mode is 6x standard pricing** -- supported on Opus 4.7 AND 4.6 (beta). Almost never worth it for development work.
6. **Pro plan annual saves 17%** -- $200/yr vs $240/yr monthly equivalent, no usage difference.
7. **Claude Platform on AWS** uses CCU billing at $0.01/CCU but matches per-token rates -- pick it over Bedrock for same-day Anthropic feature parity (no Fast Mode or Batch though).
6. **Cache hits save 90%** -- structure your prompts to maximize cache reuse
7. **Claude Code subscriptions beat API rates for interactive development** -- the math almost always works out in favor of a subscription
8. **The cheapest token is the one you don't send** -- all the strategies in this repo (context optimization, model selection, workflow patterns) compound with platform-level savings

---

*Next: Return to the [README](../README.md) for the full guide index, or see [Guide 01](01-understanding-costs.md) for the fundamentals of Claude billing.*
