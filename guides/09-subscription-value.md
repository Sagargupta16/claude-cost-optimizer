# Guide 09: Maximizing Subscription Plan Value

> **Your Claude Code subscription is a fixed monthly cost -- the value you extract from it is entirely up to you.** The gap between a well-used Pro plan and an oversized Ultra plan ($200, formerly Max 20x) is $2,160 a year ($200 - $20 = $180 a month, x 12).

A Claude Code subscription is the fixed-price way to pay for Claude Code. Unlike API billing (pay-per-token), subscriptions give you a fixed monthly budget with a usage allowance. This guide covers how to choose the right plan, squeeze maximum value from it, and know when to change tiers.

---

## Table of Contents

- [Understanding Claude Code Plans](#understanding-claude-code-plans)
- [How Plan Usage Works](#how-plan-usage-works)
  - [Blocked by a Limit Right Now](#blocked-by-a-limit-right-now)
  - [Pace Your Limits](#pace-your-limits)
- [Choosing the Right Plan](#choosing-the-right-plan)
- [Getting Maximum Value From Each Plan](#getting-maximum-value-from-each-plan)
- [When to Upgrade](#when-to-upgrade)
- [When to Downgrade](#when-to-downgrade)
- [When API Billing Makes More Sense](#when-api-billing-makes-more-sense)
- [Worked Examples](#worked-examples)
- [Off-Peak Strategies](#off-peak-strategies)
- [Subscription + API Hybrid Approach](#subscription--api-hybrid-approach)
- [Monthly Review Checklist](#monthly-review-checklist)
- [Key Takeaways](#key-takeaways)

---

## Understanding Claude Code Plans

Claude Code is included on three individual plans, Pro, Max and Ultra, and on every Team seat and Enterprise; Free does not include it ([claude.com/pricing](https://claude.com/pricing), read 2026-11-01). A plan's usage is one pool shared by Claude, Claude Code and Cowork, and it is separate from Anthropic API billing, which is pay-per-token. Team and Enterprise seats are covered in [Team and Enterprise Seats](#team-and-enterprise-seats) below.

### Plan Overview

| Plan | Monthly Price | Annual Price (effective monthly) | Usage Relative to Pro | Per-Day Equivalent | Models Included |
|------|:------------:|:--------------------------------:|:---------------------:|:------------------:|:---------------:|
| **Pro** | $20/mo | **$200/yr (~$16.67/mo, 17% off)** | 1x (baseline) | $0.67/day monthly, $0.56/day annual | Opus 5.5, Sonnet 5.5, Haiku 5.5; Fable paid with usage credits |
| **Max** | $100/mo | Monthly only | 5x Pro every 5 hours and every week | $3.33/day | Opus 5.5, Sonnet 5.5, Haiku 5.5; Fable included up to half the weekly limit |
| **Ultra** | $200/mo | Monthly only | 10x Pro every week; no 5-hour limit on a verified account | $6.67/day | Opus 5.5, Sonnet 5.5, Haiku 5.5; Fable included up to half the weekly limit |

> Sources, read 2026-11-01: [claude.com/pricing](https://claude.com/pricing), [What is the Max plan?](https://support.claude.com/en/articles/11049741-what-is-the-max-plan), [What is the Ultra plan?](https://support.claude.com/en/articles/17728952-what-is-the-ultra-plan), [Claude Fable models on your plan](https://support.claude.com/en/articles/15424964-claude-fable-models-on-your-plan). Per-day figures are computed at 30 days a month: $20 / 30, $16.67 / 30, $100 / 30, $200 / 30. Max 20x was renamed Ultra at the same price, and existing subscribers moved automatically. Anthropic verifies Ultra accounts automatically from account and payment history; until then a temporary 5-hour limit applies, and if Settings > Usage shows no Current session bar, the account is verified. Ultra also has a separate weekly limit for Fable.

> **Per unit of weekly usage, the three plans now cost the same**: $20 for each 1x of Pro's weekly limit (computed: $20 / 1, $100 / 5, $200 / 10), or $16.67 on annual Pro. Ultra's extra $100 over Max buys twice Max's weekly limit (10x / 5x) and, on a verified account, no 5-hour limit -- not cheaper usage.

> **Annual Pro saves $40/year (17%)** -- $200 up front vs $240 paid monthly; the pricing page rounds it to $17/month. If you'll use Claude Code for more than 10 months in a year, annual is the cheaper choice (computed: $200 / $20). Max and Ultra are billed monthly only; Team is billed monthly or annually and Enterprise annually.

<a id="monthly-api-credits-on-max-and-team"></a>

### Monthly API Credits on Max, Ultra and Team

Since 2026-10-07, Max, Ultra (then Max 20x) and Team plans include a monthly credit for the Claude API ([API credits for Max, Ultra, and Team plans](https://platform.claude.com/docs/en/about-claude/api-credits-for-subscribers), read 2026-11-01):

| Plan | Monthly API credit |
|------|:------------------:|
| **Max** | $100 |
| **Ultra** | $200 |
| **Team, Standard seat** | $20 per seat |
| **Team, Premium seat** | $100 per seat |

- **What it pays for**: the Claude API (in the Claude Console only), Claude Managed Agents, the Claude Agent SDK and the playground -- and `claude -p` or the Agent SDK when you run them with an API key from the linked Console organization, because that bills as Agent SDK usage ([Help Center](https://support.claude.com/en/articles/17154008-monthly-api-credits-for-max-ultra-and-team-plans), read 2026-11-01).
- **What it does not pay for**: interactive Claude Code in the terminal, IDE, desktop or web; `claude -p` while you are signed in with your plan (that draws on your plan limits); runs started by the Claude Code GitHub Action, an IDE extension or the desktop app, which count as Claude Code usage even with `-p`; usage credits (formerly extra usage); and Claude on Bedrock, Google Cloud (Google managed, formerly Vertex AI), Microsoft Foundry or Claude Platform on AWS.
- **No rollover**: credits expire at the end of each billing cycle. A month you don't use them is a month they are gone.
- **Team pooling**: Team credits are pooled per month and capped at **$500**. The cap is reached at 25 Standard seats ($500 / $20) or 5 Premium seats ($500 / $100); seats beyond that add no credit.
- **Eligibility**: new subscribers can claim after 7 days. Free, Pro and Enterprise are not eligible.

What it changes: on Max and Ultra, the plan now prepays part of an API bill you may already have. If you run your own scripts or pipelines on the Claude API through the Console, your out-of-pocket API spend drops by up to the credit -- $100 a month on Max, $200 on Ultra. It does **not** stretch your Claude Code allowance and does not lower the cost of interactive Claude Code work, which the credit cannot touch. If you already spend $200 or more a month on the Claude API through the Console, Ultra costs the same in total as Max, so its larger weekly limit and missing 5-hour limit come free (computed for monthly API spend S of $200 or more: Max $100 + (S - $100) = S, Ultra $200 + (S - $200) = S). Between $100 and $200 of API spend, Ultra costs $200 - S more than Max.

### Team and Enterprise Seats

Every Team seat and Enterprise includes Claude Code ([claude.com/pricing](https://claude.com/pricing), [What is the Team plan?](https://support.claude.com/en/articles/9266767-what-is-the-team-plan), [How am I billed for my Enterprise plan?](https://support.claude.com/en/articles/11526368-how-am-i-billed-for-my-enterprise-plan), read 2026-11-01):

| Seat | Price | Usage |
|------|:-----:|-------|
| **Team, Standard** | $20/mo billed annually, $25 monthly | 1.25x Pro's usage per session; Fable paid with usage credits |
| **Team, Premium** | $100/mo billed annually, $125 monthly | 6.25x Pro's usage per session; Fable up to half the weekly limit |
| **Enterprise (new seat)** | $20/seat/mo billed annually, 20-seat minimum | No per-seat allowance: all usage billed at API rates |

Team takes 2 to 150 seats, and each member's limits are their own, not pooled. Enterprise's earlier Standard and Premium seats are legacy. Team and Enterprise budgeting is covered in [Guide 05](05-team-budgeting.md).

### What All Plans Include

- CLI access (Claude Code terminal interface)
- Desktop app access (macOS, Windows, Linux)
- Mobile app access (iOS, Android)
- Access to all current model tiers (Opus 5.5, Sonnet 5.5, Haiku 5.5, plus legacy Opus 5/4.8/4.7/4.6, Sonnet 5/4.6 and Haiku 4.5); Sonnet 5.5 needs Claude Code v2.1.284 or later, and the `haiku` alias reaches Haiku 5.5 from v2.1.293. Fable (5.2, 5.1 and 5 alike) is included up to half the weekly limit on Max, Ultra and Team Premium, and billed to usage credits on Pro and Team Standard ([Fable models on your plan](https://support.claude.com/en/articles/15424964-claude-fable-models-on-your-plan), read 2026-11-10). For the Fable 5.2 launch, Pro and Team Standard get every Fable model included, up to half the weekly limit, from 2026-11-09 through 2026-11-16 11:59 pm PT plus one Fable limit reset that expires then; Max, Ultra and Team Premium get one Fable reset (under 6 months subscribed), two (6 to 12 months) or three (over 12 months), expiring 2027-03-08 11:59 pm PT. A reset gives back the weekly usage spent on Fable and refills the 5-hour window; it does not raise the limit ([Fable 5.2 launch offers](https://support.claude.com/en/articles/17506494-claude-fable-5-2-launch-offers), read 2026-11-10). From v2.1.321 the `fable` alias means Fable 5.2 (a Claude apps gateway session still gets Fable 5), saved `claude-fable-5-1` picks move to `fable` at once on Pro and Max and on Team and Enterprise when the organization allows it, and `/model claude-fable-5-1` still reaches legacy Fable 5.1 ([model config](https://code.claude.com/docs/en/model-config), read 2026-11-10). Where Fable bills to usage credits, which charge API rates, Fable 5.2 costs 20% less than Fable 5.1 per token ($8/$40 against $10/$50; [pricing page](https://platform.claude.com/docs/en/about-claude/pricing), read 2026-11-10)
- Automatic prompt caching, with a **one-hour cache TTL on the main conversation** while you are within plan usage, so a long break costs a subscriber less. Subagents get five minutes even on a subscription, and so do API-key users, cloud providers and subscribers once they draw on usage credits ([prompt caching](https://code.claude.com/docs/en/prompt-caching), read 2026-11-01) -- see [Guide 08](08-prompt-caching.md#how-claude-code-picks-the-cache-ttl)
- All Claude Code features (tool use, file editing, subagents, MCP servers, plugins, agent skills)

### What Plans Do NOT Include

- Anthropic API access beyond the monthly API credit (separate billing, pay-per-token; Max includes $100 and Ultra $200 a month of Console API credit, Pro includes none -- see [Monthly API Credits on Max, Ultra and Team](#monthly-api-credits-on-max-ultra-and-team))
- Batch API (50% discount, API-only)
- Fast Mode inside the plan allowance: in Claude Code, subscribers pay for fast mode with usage credits only, and fast and standard speed keep separate caches, so each toggle can re-read the conversation uncached. Fable 5.2 has it from Claude Code v2.1.321: run `/fast` while Fable 5.2 is the model ([Claude Code fast mode](https://code.claude.com/docs/en/fast-mode), read 2026-11-10). The rates are 2x each model's base: Fable 5.2 and Mythos 5.2 at $16/$80 (no beta header), Opus 5.5 at $8/$40 (generally available since 2026-10-15), Opus 5 and Opus 4.8 at $10/$50 (research preview; Opus 4.8's fast mode is deprecated and is removed on 2026-11-30) ([fast mode](https://platform.claude.com/docs/en/build-with-claude/fast-mode), read 2026-11-10). Fable 5.1 has none, Opus 4.7 errors on `speed: "fast"`, Opus 4.6 silently runs standard; the old 6x tier no longer exists
- Server-side tools billed separately (web search $10/1k, code execution $0.05/hour beyond 1,550 free hours)
- Claude Managed Agents session runtime ($0.08/session-hour, API-only)
- Provisioned throughput (Bedrock and Google Cloud) or committed-spend incentives (sales-assisted Enterprise, [claude.com/pricing](https://claude.com/pricing), read 2026-11-01)

---

## How Plan Usage Works

### Usage Allowance Model

Each plan has a usage allowance. Max is 5x Pro's every 5 hours and every week; Ultra is 10x Pro's every week, with no 5-hour limit on a verified account ([claude.com/pricing](https://claude.com/pricing), read 2026-11-01). The allowance is one pool shared by Claude, Claude Code and Cowork. The key mechanics:

- **Usage is measured in tokens** -- both input and output tokens count toward your allowance
- **Model choice affects burn rate** -- Opus consumes more of your allowance per turn than Haiku
- **When you hit a limit, you stop until the window resets** -- Claude Code's message names the 5-hour limit (called the "session limit" before v2.1.312) or the weekly limit, with the reset time. Those two are shared across all models, so `/model` does not get you back in; after a model-specific "You've hit your Opus limit", switching to another model family does ([costs page](https://code.claude.com/docs/en/costs), [changelog](https://code.claude.com/docs/en/changelog), read 2026-11-01)
- **Allowances reset on a rolling 5-hour window plus a weekly window**, not monthly on your billing date. A verified Ultra account has only the weekly window
- **Resuming an old conversation can take a large share at once** -- its cache has expired, so the first message re-reads the whole conversation. From v2.1.304, Pro and Max users are warned when resuming an inactive conversation would use a noticeable share of the 5-hour limit, and can resume anyway or start a new conversation that looks up the old one when you refer to it ([changelog](https://code.claude.com/docs/en/changelog), read 2026-11-01)
- **Idle compaction** (terminal v2.1.299, VS Code and the desktop Code tab v2.1.314): a conversation of 200,000 or more tokens left idle for about 54 minutes is compacted before its one-hour cache expires, so your next message sends a summary instead of the whole conversation. It needs the one-hour TTL, which a subscriber gets within plan usage. The compaction itself uses tokens while you are away; turn it off with `"idleCompaction": false` or the Idle compaction row in `/config` (v2.1.302), or move the threshold with `CLAUDE_CODE_IDLE_COMPACT_MIN_TOKENS` ([settings reference](https://code.claude.com/docs/en/settings-reference#idlecompaction), read 2026-11-01)

> **Important caveat**: Exact token allocations per plan are not publicly documented by Anthropic. The multipliers (5x Pro on Max, 10x Pro a week on Ultra) are relative to Pro, but the absolute token counts are not disclosed, and the pricing page says how fast you reach a limit depends on the model, how long your chats are and how large your files are. What we know beyond that is based on observed usage patterns and community reports.

### Rate Limiting vs. Overage

Unlike API billing, where every token has a price, subscription plans meter usage in windows ([Claude Code costs docs](https://code.claude.com/docs/en/costs), read 2026-11-01):

| Situation | What Happens |
|-----------|--------------|
| Within allowance | Full speed, no per-token charge |
| 5-hour or weekly limit reached | Requests stop until that window resets; the message shows when |
| Model-specific limit reached (e.g. "Opus limit") | Switch to a model outside that family with `/model` and keep working |
| Usage credits turned on | Work continues past the limit, billed from usage credits at standard API rates up to the monthly spend limit you set (`/usage-credits`) |

Your subscription cost stays fixed unless you turn on usage credits (formerly called extra usage), and you set their monthly spend limit yourself, with optional auto-reload ([Manage usage credits](https://support.claude.com/en/articles/12429409-manage-usage-credits-for-paid-claude-plans), read 2026-11-01). Usage credits can also be prepaid as usage bundles at a discount: $50 of usage for $45, $250 for $200 and $1,000 for $700, up to $2,000 of bundles a month on Pro, Max and Ultra; bundle credit applies only once you are past your plan's limits with usage credits on ([Buy usage bundles](https://support.claude.com/en/articles/14246112-buy-usage-bundles), read 2026-11-01). The trade-off of staying inside the plan is that a heavy day hits the 5-hour or weekly window and stops you until it resets. On Claude Code v2.1.234 or later, Claude Code can wait out the reset and continue the interrupted task automatically.

### Blocked by a Limit Right Now

Find your message below. The first four points repeat the rules above with a link to each; the last two are new here and cite their sources.

- **5-hour or weekly limit**: shared across all models, so `/model` does not get you back in; the message gives the reset time ([Usage Allowance Model](#usage-allowance-model)).
- **A model-specific limit** ("Opus limit"): switch to a model outside that family with `/model` ([table above](#rate-limiting-vs-overage)).
- **Keep working now**: run `/usage-credits` if usage credits are on; the work bills at API rates up to the monthly spend limit you set ([table above](#rate-limiting-vs-overage)).
- **Do not resume an old conversation right after the reset** unless you need it verbatim: its cache has expired, so the first message re-reads all of it ([Usage Allowance Model](#usage-allowance-model)).
- **Wait it out in the session**: on v2.1.234 or later, an interactive session signed in with a claude.ai subscription waits and then continues the interrupted task on its own after the reset. The `autoContinueAtUsageLimit` setting controls it (default `true`; read from user and managed settings, and a project or local settings file that sets it turns the feature off when neither of those does). Keep the session open: exiting ends the wait. After three automatic continuations it stops, and `/rate-limit-options` lets you start a wait yourself or cancel one ([interactive mode](https://code.claude.com/docs/en/interactive-mode), [settings reference](https://code.claude.com/docs/en/settings-reference#autocontinueatusagelimit), read 2026-11-03).
- **A spend limit message** (individual, organization or team budget): your usage credits reached a spend limit, so the fix is to raise it, not to wait. On Pro, Max and Ultra, when you reach the limit with usage credits left, Claude Code prompts you to raise or remove it without leaving the CLI; on Team and Enterprise an admin raises it under Organization settings > Usage. When the message also names a plan reset time, waiting until then works too ([costs page](https://code.claude.com/docs/en/costs), read 2026-11-03).

To count how often this happens, `claude-rate --usage` (claude-rate 0.4.0 or later) counts the rate-limit and billing errors recorded in your local transcripts, by week (`limit_hits` in its `--json` output). Claude Code deletes transcripts older than `cleanupPeriodDays`, 30 days by default, so the count covers at most that window ([costs page](https://code.claude.com/docs/en/costs), read 2026-11-03).

### Pace Your Limits

A subscriber's status line gets the plan windows as input: `rate_limits.five_hour` and `rate_limits.seven_day`, each with `used_percentage` (0 to 100) and `resets_at` (Unix epoch seconds), for Pro, Max and Ultra after the session's first response. Either window can be absent (a verified Ultra account has no 5-hour limit), and Claude Code drops a window once its reset time passes ([status line docs](https://code.claude.com/docs/en/statusline), read 2026-11-03). Pace compares what you have used with how much of the window has gone by:

```
elapsed share = (window length - (resets_at - now)) / window length
                window length: 18,000 s (5 hours) or 604,800 s (7 days)
pace          = used_percentage - 100 x elapsed share
                above 0: you are using the window faster than an even rate
```

For example, 62% of the 5-hour window used with 1 hour 40 minutes to the reset: elapsed share = (18,000 - 6,000) / 18,000 = 66.7%, so pace = 62 - 66.7 = -4.7 points, a little behind an even rate.

`claude-rate --statusline` (claude-rate 0.4.0 or later) reads that same input and prints the 5-hour and weekly windows in your status line; [templates/settings/statusline.json](../templates/settings/statusline.json) has the settings snippet. On an API key, Bedrock or Google Cloud there are no plan windows, and `claude-rate --burn MINUTES` instead shows list-price spend over the last `MINUTES` minutes (default 60) from your local transcripts: the total, the same as a rate per hour, the split by model and the costliest session (`--watch SECONDS`, 15 or more, redraws it). On a subscription those dollars are API-equivalent list price, a measure of how fast you are burning, not of how much allowance is left: Anthropic does not publish plan limits in tokens.

### How Model Choice Affects Allowance Consumption

Not all tokens are equal when it comes to your plan allowance. More capable models consume your allowance faster:

| Model | Relative Allowance Cost | Practical Impact |
|-------|:-----------------------:|-----------------|
| **Haiku 5.5** | Lowest | Stretches your plan the furthest. API rate $0.10/$0.50 up to 100K prompt tokens, $0.50/$2.50 above; thinking is on by default (effort `medium`) and Claude Code cannot turn it off |
| **Sonnet 5.5** | Medium | Good balance of capability and allowance efficiency |
| **Opus 5.5** | Highest | Burns through allowance fastest (Opus-4.7-generation tokenizer, about 30% more tokens than pre-4.7 models for the same text per [Anthropic's pricing page](https://platform.claude.com/docs/en/about-claude/pricing), plus thinking is always on and cannot be disabled) |

> **Key insight**: A Pro plan user who defaults to Haiku for routine tasks and only switches to Opus for complex work can get significantly more done than one who runs Opus for everything. This is the single highest-leverage optimization for subscription plans.

### The Opus 5.5 Thinking Effect

Opus 5.5 (released 2026-09-22) changes the burn-rate picture in a way that matters more on a subscription than on the API, because you cannot see the bill move:

- **Thinking is always on.** Anthropic's costs page says it plainly: "You can't turn off thinking on Opus 5.5, Sonnet 5.5, Haiku 5.5, or the Fable models, which always use extended thinking." Those reasoning tokens are billed and counted as **output**. If you had thinking disabled on Opus 5, the same task now consumes more allowance on Opus 5.5.
- **Effort level is the only throttle, and its default dropped.** Effort runs low/medium/high/xhigh/max and defaults to `medium` on Opus 5.5 (Opus 5 defaulted to `high`), so a request that omits effort thinks less than it did on Opus 5. Use `/effort` to go lower for routine work. `MAX_THINKING_TOKENS` does not help here: it only affects fixed-budget models, and adaptive models ignore it. Two newer controls matter on a plan: typing `ultrathink` runs that turn at `xhigh` on Opus 5.5, Sonnet 5.5, Haiku 5.5, Fable 5.2 and Fable 5.1 (v2.1.311, Fable 5.2 from v2.1.321; `CLAUDE_CODE_DISABLE_ULTRATHINK` turns the keyword off from v2.1.316), and the `maxEffortLevel` setting caps effort on any plan and provider, so higher levels run at the cap ([changelog](https://code.claude.com/docs/en/changelog), [model config](https://code.claude.com/docs/en/model-config#organization-effort-limits), read 2026-11-01).
- **On Fable 5.2, set effort rather than asking for less thinking.** Claude Code starts Fable 5.2 at `medium` (the API default is `high`). In Anthropic's testing a prompt line asking for less thinking does not stop it thinking at `medium` or above, and at `high` or above it thinks before almost every reply, so lower the effort for easy turns ([what's new in Fable 5.2](https://platform.claude.com/docs/en/models/fable-5-2/whats-new-fable-5-2), [model config](https://code.claude.com/docs/en/model-config), read 2026-11-10).
- **Changing effort is cache-safe on current models.** With a subscription or an API key, effort changes on Fable 5.1 and later (Fable 5.2 included), Opus 5.5, Sonnet 5.5 and Haiku 5.5 keep the prompt cache, so dropping to `low` mid-session does not cost a cache rebuild. On Amazon Bedrock, Google Cloud's Agent Platform or a Claude apps gateway, with `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS` set, or under a HIPAA configuration, an effort change rebuilds the cache as on other models ([prompt caching](https://code.claude.com/docs/en/prompt-caching), read 2026-11-10).
- **Output runs longer on Opus 5 than on 4.8.** If you are still on legacy Opus 5: it writes more than 4.8 for the same prompt and self-verifies, so any carried-over "double-check your work" instruction in your CLAUDE.md pays twice -- delete those lines.

> **Practical impact on a subscription**: re-baseline after migrating. If you moved to Opus 5.5 and started hitting rate limits sooner without changing your habits, thinking you used to switch off is the likely cause. Lower the effort level before you upgrade your plan.

---

## Choosing the Right Plan

### Decision Framework

The right plan depends on three factors: how many hours per day you use Claude Code, the complexity of your tasks (which determines model choice), and how sensitive you are to rate-limiting.

### Pro ($20/mo or $200/yr) Is Right If:

- You use Claude Code casually -- a few sessions per day, not all day
- Most of your work is simple to moderate complexity (Haiku and Sonnet territory)
- You are learning Claude Code and building habits before committing more
- You have flexibility to wait if you hit rate limits
- **Expected usage**: 3-5 moderate sessions per day, ~15-25 turns each

### Max ($100/mo) Is Right If:

- Claude Code is your primary development tool throughout the workday
- You handle a mix of simple and complex tasks daily
- You use Opus regularly for architecture decisions, complex debugging, or multi-file refactoring
- Rate-limiting during a workday would hurt your productivity
- **Expected usage**: 5-10 sessions per day, mixed models, some 30+ turn sessions

### Ultra ($200/mo) Is Right If:

- You use Claude Code heavily all day -- it is central to your workflow
- You hit Max's 5-hour limit regularly: a verified Ultra account has no 5-hour limit, only a weekly one
- You run out of Max's weekly limit: Ultra's is twice Max's (10x Pro against 5x Pro)
- You do complex multi-file refactoring, large codebase navigation, and deep debugging frequently
- You are a team lead doing code review, feature development, and mentoring with Claude
- You want more Fable (the `fable` alias means Fable 5.2 from Claude Code v2.1.321): both plans include it up to half the weekly limit, so Ultra's Fable allowance is twice Max's (computed: half of 10x against half of 5x Pro's weekly limit)
- **Expected usage**: 10+ sessions per day, frequent Opus usage, long sessions

### Plan Selection Quick Reference

| Usage Pattern | Daily Sessions | Avg Turns/Session | Primary Model | Recommended Plan |
|---------------|:--------------:|:-----------------:|:-------------:|:----------------:|
| Casual learner | 2-3 | 10-15 | Haiku/Sonnet | Pro ($20) |
| Part-time developer | 3-5 | 15-25 | Sonnet | Pro ($20) |
| Full-time, moderate | 5-8 | 20-30 | Sonnet/Opus | Max ($100) |
| Full-time, heavy | 8-12 | 25-40 | Opus/Sonnet | Max ($100) |
| Power user | 10+ | 30-50 | Opus | Ultra ($200) |
| Team lead, all day | 12+ | Mixed | All models | Ultra ($200) |

The session and turn counts here and in the "Is Right If" lists are illustrative, not measured: Anthropic publishes plan limits as multiples of Pro, not as sessions or tokens.

### Cost-Per-Session Intuition

Another way to think about plan value -- what does each session cost you?

| Plan | Monthly Cost | If 5 sessions/day (110/mo) | If 10 sessions/day (220/mo) | If 15 sessions/day (330/mo) |
|------|:------------:|:--------------------------:|:---------------------------:|:---------------------------:|
| **Pro** | $20 | $0.18/session | $0.09/session | $0.06/session |
| **Max** | $100 | $0.91/session | $0.45/session | $0.30/session |
| **Ultra** | $200 | $1.82/session | $0.91/session | $0.61/session |

The more sessions you run, the cheaper each one becomes. But this only matters if you are actually using those sessions productively -- idle capacity is wasted money.

---

## Getting Maximum Value From Each Plan

### Pro ($20/mo) Optimization Strategies

On Pro, every token matters. Your allowance is limited, so efficiency is critical.

**1. Default to Haiku for routine tasks**

Set Haiku as your default model and only switch up when needed:

```bash
# In your Claude Code settings or CLAUDE.md:
# "Default to Haiku 5.5 for all tasks. Only use Sonnet for component creation,
# bug fixes involving multiple files, and test writing. Only use Opus for
# architecture decisions, complex debugging, and multi-file refactoring."
```

This shifts routine work onto the model that draws least on your plan. Anthropic does not publish how each model counts against plan limits, so this guide gives no multiplier.

**2. Use Plan Mode to reduce wasted output tokens**

Plan Mode (Shift+Tab, or start in it with `--permission-mode plan`) analyzes before implementing. This prevents the costly trial-and-error cycle where Claude writes code, finds it does not work, and rewrites it multiple times.

```bash
# Without plan mode: 10 turns, 3 false starts, lots of wasted output
claude "refactor the auth module"

# With plan mode: 2 turns to plan + 4 turns to implement
claude --permission-mode plan "refactor the auth module"
```

**3. Keep CLAUDE.md lean**

On Pro, a bloated CLAUDE.md eats into your limited allowance every single turn. Keep it under 100 lines. See [Guide 02](02-context-optimization.md) for how.

**4. Compact at natural breaks, clear between tasks**

`/compact` reads the whole conversation it summarizes, so compacting a large context is itself a large request; when you want a fresh start rather than continuity, `/clear` costs nothing ([costs page](https://code.claude.com/docs/en/costs), read 2026-11-01). Anthropic's advice is to pick model and effort at the top of a session and save `/compact` for natural breaks between tasks ([prompt caching](https://code.claude.com/docs/en/prompt-caching), read 2026-11-01).

**5. Watch for off-peak promotions, but none is running**

Anthropic's one documented off-peak event doubled 5-hour usage outside the weekday peak from 2026-03-13 to 2026-03-28, and none was running on 2026-11-01 (see [Off-Peak Strategies](#off-peak-strategies)). If another runs, move heavier work into its off-peak hours.

**6. Start new sessions instead of extending old ones**

Session cost grows quadratically. Five 10-turn sessions are cheaper (in terms of allowance) than one 50-turn session doing the same work. The same goes for coming back to an old conversation: when Claude Code warns that resuming it would use a noticeable share of your 5-hour limit (v2.1.304), take the new-conversation option unless you need the old context verbatim.

### Max ($100/mo) Optimization Strategies

With 5x Pro's headroom, you can afford to be less aggressive about token pinching. Focus on workflow efficiency instead.

**1. Use Opus freely for complex tasks -- but not for everything**

You have room to use Opus when it matters (architecture, debugging, complex refactoring), but do not leave it as your default for all tasks. Anthropic does not publish how each model draws on plan limits, so no model split can be called the right target for your allowance. Priced at API rates, a 60/30/10 split of 30-turn sessions across Haiku 5.5, Sonnet 5.5 and Opus 5.5 costs $0.20 per session against $0.74 all on Opus 5.5, 73% less (computed at this repo's calculator defaults with Claude Code's prompt caching: 0.6 x $0.0230 + 0.3 x $0.3709 + 0.1 x $0.7419). `/usage` flags any behavior that accounts for 10% or more of your recent usage ([costs page](https://code.claude.com/docs/en/costs)); start with what it flags.

**2. Leverage subagents more aggressively**

Subagents (spawned via tool use) run in isolated contexts, which means they do not inflate your main session's context. With Max's headroom, the overhead of spawning subagents is worth it for the context isolation benefit. Each ordinary subagent starts its own cache on the 5-minute TTL even on a subscription, while a fork reads the parent's cache on its first request ([prompt caching](https://code.claude.com/docs/en/prompt-caching), read 2026-11-01). See [Guide 04](04-workflow-patterns.md).

**3. Run longer sessions when needed**

Unlike Pro, you can afford 30-40 turn sessions without as much concern about rate limits. Use this for complex feature work that benefits from continuity.

**4. Focus on workflow patterns over token counting**

The optimization strategies that matter most at this tier:
- Plan Mode before implementation (saves turns, not just tokens)
- Batch related changes into single prompts
- Use custom commands for repetitive workflows
- Keep your `permissions.deny` `Read(...)` rules up to date (`.claudeignore` is not a Claude Code feature; see [Guide 02](02-context-optimization.md))

**5. Invest in CLAUDE.md quality**

A well-crafted CLAUDE.md pays dividends on Max because Claude makes better decisions with better context -- fewer wasted turns, fewer misunderstandings, more correct implementations on the first try. The time you spend writing a good CLAUDE.md compounds across hundreds of sessions per month.

### Ultra ($200/mo) Optimization Strategies

At this tier, your time is more expensive than your tokens. Optimize for productivity, not frugality.

**1. Use Opus as default for complex projects**

If you are working on a large codebase, multi-service architecture, or anything requiring deep reasoning, Opus as the default model is justified. Switch to Sonnet only for clearly routine work (formatting, simple renames, boilerplate).

**2. Invest heavily in CLAUDE.md and file-read exclusion (`permissions.deny` `Read(...)` rules) quality**

At Ultra's volume the compounding effect is significant. If a well-tuned CLAUDE.md saves 2 turns per session, and you run 15 sessions per day, that is 30 saved turns daily -- roughly 660 per month. Each saved turn means less allowance consumed and less time waiting.

**3. Set up custom commands for your most common workflows**

At this volume of usage, even small per-session time savings add up:

```bash
# Example custom commands that save time and tokens
/quick-fix     # Minimal-token bug fix pattern
/review        # Structured code review
/test          # Detect framework and run tests
/commit        # Review changes and create commit
```

See [Templates > Commands](../templates/commands/) for ready-to-use examples.

**4. Use multiple concurrent sessions**

A verified Ultra account has no 5-hour limit, so parallel sessions draw only on the weekly limit. If you are waiting for a long operation in one session, start another for a different task, and check `/usage` so parallel work does not use up the week early.

**5. Do not micro-optimize tokens -- optimize outcomes**

At $200/mo, spending 10 minutes optimizing a prompt to save $0.05 in tokens is a bad trade. Focus on:
- Getting correct results on the first try (clear, specific prompts)
- Using the right model for the task (not the cheapest one)
- Keeping sessions focused (one task per session)

---

## When to Upgrade

### Upgrade Signals

| Signal | What It Means | Recommended Action |
|--------|--------------|-------------------|
| Hitting rate limits 3+ times per day | Your usage exceeds your plan's allowance | Upgrade to next tier |
| Spending more than 30 min/day waiting for rate limits | Rate limits are costing you productive time | Upgrade -- your time is worth more than the tier difference |
| Using API billing alongside subscription to avoid limits | You are paying twice | Upgrade the subscription or switch to API-only |
| Consistently using Opus but on Pro plan | Opus burns through Pro allowance fast | Upgrade to Max, or switch to Sonnet/Haiku defaults |
| Productivity drops late in the week | You are burning through the weekly allowance too early | Upgrade, or optimize model selection to stretch current plan |
| Hitting Max's 5-hour limit, rarely the weekly one | The 5-hour window, not the weekly total, is what stops you | Ultra (a verified account has no 5-hour limit), or usage credits for the overflow |
| Short of usage only a few days a month | Overflow, not a bigger baseline | Usage credits at API rates, or a usage bundle, instead of a tier jump |

### The Upgrade Math

Think about the upgrade decision in terms of your hourly rate:

| Your Hourly Rate | Time Lost to Rate Limits (hrs/mo) | Value of Lost Time | Upgrade Cost (Pro to Max) |
|:----------------:|:---------------------------------:|:-------------------:|:------------------------:|
| $25/hr | 2 hrs | $50 | $80 |
| $50/hr | 2 hrs | $100 | $80 |
| $75/hr | 2 hrs | $150 | $80 |
| $100/hr | 1 hr | $100 | $80 |

At $50/hr, losing more than 1.6 hours a month to rate limits makes the Pro-to-Max upgrade pay for itself (computed: $80 / $50). The Max-to-Ultra step is $100 a month, so it pays at 2 hours a month at $50/hr or 1 hour at $100/hr (computed: $100 / hourly rate). That $100 buys twice Max's weekly limit and, on a verified account, no 5-hour limit; if you only run short a few days a month, usage credits for those days may cost less than the step.

---

## When to Downgrade

Upgrading gets most of the attention, but downgrading when appropriate is equally important for cost optimization.

### Downgrade Signals

| Signal | What It Means | Recommended Action |
|--------|--------------|-------------------|
| Rarely hitting rate limits, frequently idle | You are paying for capacity you do not use | Downgrade to the next lower tier |
| Usage dropped after a project ended | Temporary spike is over | Downgrade (you can always upgrade again) |
| Optimized your workflow and now using far fewer tokens | Efficiency improvements freed up headroom | Downgrade and pocket the savings |
| Switched to mostly Haiku usage | Haiku burns through allowance much slower | Pro plan may be sufficient now |

### The Downgrade Math

| Current Plan | Monthly Cost | Downgrade To | Monthly Savings | Annual Savings |
|:------------:|:------------:|:------------:|:---------------:|:--------------:|
| Ultra | $200 | Max | $100 | $1,200 |
| Max | $100 | Pro | $80 | $960 |
| Ultra | $200 | Pro | $180 | $2,160 |

> **Tip**: Subscription changes typically take effect at the next billing cycle. If you know a quiet period is coming (holiday, between projects, vacation), downgrade in advance.

---

## When API Billing Makes More Sense

Claude Code subscriptions are not always the best deal. Here are scenarios where API billing wins:

### API Billing Is Better When:

**1. Your usage is very spiky**

If you use Claude Code heavily for 2 weeks, then barely touch it for 2 weeks, a subscription charges you for the idle weeks. API billing charges only for what you use.

```
Spiky usage example:
  Week 1-2: Heavy use, ~$80 worth of tokens
  Week 3-4: Light use, ~$5 worth of tokens
  
  Subscription cost: $100/mo (Max)
  API cost:          $85/mo (actual usage)
  Savings:           $15/mo with API billing
```

A third option for spiky months is Pro with usage credits turned on: the plan covers the light weeks, and the heavy weeks overflow into usage credits at API rates, up to the spend limit you set.

**2. You need predictable per-token billing for business expense tracking**

Some organizations need line-item billing tied to specific projects or cost centers. API billing gives you per-request cost attribution. Subscriptions are a single monthly charge.

**3. You are building automated pipelines**

Claude Code subscriptions are designed for interactive use. If you are running automated code review, CI/CD integrations, or batch processing, the API is the right tool -- and the Batch API gives you a 50% discount on top of that. On Max, Ultra and Team, the monthly API credit also pays for `claude -p` run with an API key from the linked Console organization (see [Monthly API Credits on Max, Ultra and Team](#monthly-api-credits-on-max-ultra-and-team)).

**4. You need the Batch API discount**

The Batch API offers 50% off standard rates for non-time-sensitive workloads. This is not available through Claude Code subscriptions. For high-volume batch work, the savings are substantial:

| Model | Standard API | Batch API | Savings |
|-------|:-----------:|:---------:|:-------:|
| Opus 5.5 (output) | $20.00/MTok | $10.00/MTok | 50% |
| Opus 5 / 4.8 / 4.7 / 4.6, legacy (output) | $25.00/MTok | $12.50/MTok | 50% |
| Sonnet 5.5 (output) | $10.00/MTok | $5.00/MTok | 50% |
| Sonnet 5, legacy (output) | $10.00/MTok | $5.00/MTok | 50% |
| Sonnet 4.6 (output) | $15.00/MTok | $7.50/MTok | 50% |
| Haiku 5.5, prompt <= 100K (output) | $0.50/MTok | $0.25/MTok | 50% |
| Haiku 5.5, prompt > 100K (output) | $2.50/MTok | $1.25/MTok | 50% |
| Haiku 4.5, legacy (output) | $5.00/MTok | $2.50/MTok | 50% |

**5. Your usage is extremely light**

If you only use Claude Code occasionally (a few times per week), even Pro at $20/mo may be more than the equivalent API cost.

```
Light usage example:
  10 sessions/month, 20 turns each, Sonnet 5.5
  Token cost at API rates: 10 x $0.2387 = $2.39
    (one 20-turn session at this repo's calculator defaults,
     billed with Claude Code's prompt caching)

  Pro subscription: $20/mo
  API cost:         $2.39/mo
  Savings:          $17.61/mo with API billing
```

### Subscription vs. API Break-Even Estimates

Computed for one workload: 30-turn Sonnet 5.5 sessions at this repo's calculator defaults (3,500-token system prompt, 100-line CLAUDE.md at 10 tokens per line, two MCP servers, one 2,000-token file read, 1,500 tokens of history per turn, 500 output tokens per turn), billed the way Claude Code caches a conversation: $0.3709 per session, over 22 working days. Other model mixes, session lengths and cache hit rates move the line: the same session costs $0.7419 on Opus 5.5 and $0.0230 on Haiku 5.5.

| Plan | Break-Even (API Equivalent) | Below This = API Cheaper |
|------|:-----------------------------------:|:------------------------:|
| Pro ($20) | $20 of API usage/month | < 2.5 Sonnet 5.5 sessions/day (54/month; 1.2/day on Opus 5.5) |
| Max ($100) | $100 of API usage/month | < 12.3 Sonnet 5.5 sessions/day (270/month; 6.1/day on Opus 5.5) |
| Ultra ($200) | $200 of API usage/month | < 24.5 Sonnet 5.5 sessions/day (539/month; 12.3/day on Opus 5.5) |

> **Note**: the session cost above already includes Claude Code's own overhead in this repo's model: its system prompt (3,500 tokens) and two MCP servers' tool definitions. It leaves out background requests: session recap and idle compaction can use tokens while you are idle, and prompt suggestions send a short request after each response, mostly cache reads; the costs page gives no per-session figure for them ([costs page](https://code.claude.com/docs/en/costs), read 2026-11-01). The table compares prices only: Anthropic does not publish plan limits in tokens, so whether a plan's allowance covers that many sessions is not something this math can tell you. For scale, Anthropic's enterprise average is around $13 per developer per active day and $150-250 per developer per month at API rates ([costs page](https://code.claude.com/docs/en/costs)), more than Max's $100.

> **Max and Ultra API credits change the comparison only for Console API spend.** The break-even above is about interactive Claude Code, and the monthly credit ($100 on Max, $200 on Ultra) cannot be spent on it. Where it matters is if you also pay for the Claude API through the Console: the plan then costs you its price minus whatever of the credit you use. Max with $60 of monthly Console API usage costs $100 - $60 = $40 more than the API bill you already had; with $100 or more of usage, Max adds nothing on top, and with $200 or more neither does Ultra. The credit does not roll over, so unused credit is not savings, and API traffic on Bedrock, Google Cloud, Foundry or Claude Platform on AWS does not count.

> **Opus 5.5 moves this break-even in both directions -- re-measure.** Its posted price is $4/$20, 20% below Opus 5's $5/$25, which pulls API-side cost down. But thinking is always on (it cannot be disabled) and reasoning tokens bill as output at $20/MTok. If your API-side estimate was built with thinking off, your real per-session output spend on Opus 5.5 is higher than that estimate -- so you cross the subscription break-even at fewer sessions per day than the table above implies. If you simply omitted effort on Opus 5, the new `medium` default thinks less than Opus 5's `high` did. Re-measure against actual Opus 5.5 usage before concluding that API billing is cheaper for you. On the API you can claw cost back by lowering the effort level; on a subscription the same lever stretches your allowance instead.

**Your own ratio.** `claude-rate --usage --plan pro|max|ultra` (claude-rate 0.4.0 or later) divides the API-equivalent list-price spend in your local Claude Code transcripts, scaled to 30 days (spend x 30 / days covered, over the last 30 days by default), by that plan's monthly price ($20, $100, $200). Above 1 means the plan cost less than list price for that work; it says nothing about whether the work fits the plan's limits, which Anthropic does not publish in tokens. It sees only Claude Code transcripts on this machine, while a plan's usage is one pool shared by Claude, Claude Code and Cowork ([Usage Allowance Model](#usage-allowance-model)), so work on other devices and in the other apps is missing from it. On an API key, Bedrock or Google Cloud there is no plan to compare.

---

## Worked Examples

### Example 1: Solo Freelancer

**Profile:**
- Uses Claude Code ~4 hours per day, 5 days per week
- Mix of React frontend and Node.js backend work
- Typical day: 6 sessions, ~25 turns each
- Tasks: component creation, bug fixes, test writing, occasional architecture work
- Model mix: 50% Sonnet, 30% Haiku, 20% Opus

**Analysis:**

| Factor | Assessment |
|--------|-----------|
| Daily sessions | 6 (moderate-to-heavy) |
| Total daily turns | ~150 |
| Opus usage | 20% -- meaningful but not dominant |
| Rate limit risk on Pro | High -- would likely hit limits by mid-afternoon |
| Rate limit risk on Max | Low -- comfortable headroom most days |

**Recommendation: Max ($100/mo)**

Pro at $20 would rate-limit this developer frequently, costing them productive hours. Ultra at $200 is more capacity than needed. Max hits the sweet spot -- enough headroom for productive days, with room for occasional heavy sessions.

**Monthly value calculation:**
- 22 working days x 6 sessions x 25 turns = 3,300 turns per month
- At $100/mo, that is ~$0.03 per turn -- excellent value for mixed Sonnet/Opus usage

### Example 2: Backend Developer at a Startup

**Profile:**
- Uses Claude Code ~8 hours per day
- Large Python codebase with complex business logic
- Typical day: 12+ sessions, some exceeding 50 turns with Opus
- Tasks: feature development, complex debugging, database migrations, API design
- Model mix: 40% Opus, 40% Sonnet, 20% Haiku

**Analysis:**

| Factor | Assessment |
|--------|-----------|
| Daily sessions | 12+ (heavy) |
| Total daily turns | ~300+ |
| Opus usage | 40% -- heavy, for complex reasoning tasks |
| Rate limit risk on Max | Moderate-to-high, especially on Opus-heavy days |
| Rate limit risk on Ultra | Low -- no 5-hour limit on a verified account, and twice Max's weekly limit |

**Recommendation: Ultra ($200/mo)**

With 40% Opus usage across 12+ daily sessions, this developer would run through Max's 5-hour windows quickly. Ultra removes the 5-hour limit on a verified account and doubles the weekly limit (10x Pro against Max's 5x), the headroom needed for sustained heavy usage without productivity-killing rate limits.

**Monthly value calculation:**
- 22 working days x 12 sessions x ~25 avg turns = 6,600 turns per month
- At $200/mo, that is ~$0.03 per turn
- If 2 hours per month of rate-limit waiting is avoided at $50/hr, the $100 premium over Max pays for itself (computed: 2 x $50 = $100)

### Example 3: Part-Time Developer

**Profile:**
- Uses Claude Code ~1 hour per day, mostly on weekends
- Side projects, learning new frameworks, exploring ideas
- Typical day: 2-3 sessions, ~15 turns each
- Tasks: small features, learning exercises, quick prototypes
- Model mix: 60% Haiku, 30% Sonnet, 10% Opus

**Analysis:**

| Factor | Assessment |
|--------|-----------|
| Daily sessions | 2-3 (light) |
| Total daily turns | ~35-45 |
| Opus usage | 10% -- rare, for occasional complex questions |
| Rate limit risk on Pro | Low -- Haiku-heavy usage stretches allowance well |

**Recommendation: Pro ($20/mo)**

Light usage with a Haiku-dominant model mix means Pro provides plenty of capacity. Upgrading to Max would be paying for 5x the usage with no benefit.

**Monthly value calculation:**
- ~10 active days x 3 sessions x 15 turns = 450 turns per month
- At $20/mo, that is ~$0.04 per turn
- Even if this developer doubled their usage on some weekends, Pro would handle it comfortably

### Example 4: Team Lead at a Mid-Size Company

**Profile:**
- Uses Claude Code ~6 hours per day
- Split between own coding, code review, and mentoring tasks
- Typical day: 8 sessions -- 4 for own work (Opus-heavy), 4 for review (Sonnet)
- Tasks: architecture decisions, PR review, feature specs, debugging production issues
- Model mix: 35% Opus, 45% Sonnet, 20% Haiku

**Analysis:**

| Factor | Assessment |
|--------|-----------|
| Daily sessions | 8 (moderate-to-heavy) |
| Total daily turns | ~200 |
| Opus usage | 35% -- substantial for architecture and debugging |
| Code review load | Significant -- uses Sonnet for most reviews |
| Rate limit risk on Max | Moderate, might hit limits on busy review days |

**Recommendation: Max ($100/mo), with upgrade to Ultra if rate limits become frequent**

Start with Max. If code review load increases or the team lead takes on more architecture work, upgrade to Ultra. The $100 difference is justified only if rate limits cause regular productivity loss. If this lead's company is on a Team plan, the same choice is a Standard or Premium seat (see [Team and Enterprise Seats](#team-and-enterprise-seats)).

---

## Off-Peak Strategies

### How Off-Peak Promotions Work

Anthropic has run one documented off-peak promotion: from 2026-03-13 to 2026-03-28 it doubled 5-hour usage outside the weekday 8 AM - 2 PM ET peak (Help Center article 14063676, now offline). **No promotion was running on 2026-11-01**: none appears on [claude.com/pricing](https://claude.com/pricing) or in the Help Center usage articles. Treat that event as history, not as a standing schedule.

During that event:
- **Peak hours** (normal limits): 8 AM - 2 PM ET on weekdays
- **Off-peak** (5-hour usage doubled): every hour outside that peak

Check the [Anthropic news page](https://www.anthropic.com/news) and the [Claude Help Center](https://support.claude.com) for any current promotion. A verified Ultra account has no 5-hour limit, so an event that doubles 5-hour usage changes nothing for it.

### Time Zone Advantage

During that event the whole workday in India and Asia-Pacific fell in the off-peak window, and in Europe three to four of eight hours did. Each row below is arithmetic on the 8 AM - 2 PM ET weekday peak on the event's dates, against a 9 AM - 5 PM (8-hour) workday. The US had moved to daylight time on 2026-03-08 (EDT, UTC-4) while the UK (GMT, UTC+0) and Central Europe (CET, UTC+1) did not change clocks until 2026-03-29, so the peak sat an hour earlier in European clocks than it would for most of the year:

| Time Zone | Your 9 AM - 5 PM | Fell in US Peak? | Effective Benefit |
|-----------|:-----------------:|:-----------------:|:----------------:|
| US West (PDT) | Partial overlap | Yes (5-11 AM PDT = peak) | 75% of workday was 2x (peak 9-11 AM; 6 of 8 hours off-peak) |
| US East (EDT) | Significant overlap | Yes (8 AM - 2 PM EDT = peak) | 37.5% of workday was 2x (peak 9 AM - 2 PM; 3 of 8 hours off-peak) |
| UK (GMT) | Significant overlap | Yes (12-6 PM GMT = peak) | 37.5% of workday was 2x (peak 12-5 PM; 3 of 8 hours off-peak) |
| Central Europe (CET) | Partial overlap | Yes (1-7 PM CET = peak) | 50% of workday was 2x (peak 1-5 PM; 4 of 8 hours off-peak) |
| India (IST) | No overlap | No (5:30-11:30 PM IST) | 100% of workday was 2x |
| China/Singapore (SGT) | No overlap | No (8 PM - 2 AM SGT) | 100% of workday was 2x |
| Japan/Korea (JST) | No overlap | No (9 PM - 3 AM JST) | 100% of workday was 2x |
| Australia (AEDT) | No overlap | No (11 PM - 5 AM AEDT) | 100% of workday was 2x |

Computed: the peak was 12:00 to 18:00 UTC, shifted by each zone's offset on those dates (PDT -7, EDT -4, GMT 0, CET +1, IST +5:30, SGT +8, JST +9, AEDT +11). For most of the year the UK and Central Europe sit 5 and 6 hours ahead of US Eastern, so the same window would land an hour later in their clocks.

> **What it meant**: during the event, a developer in India, East Asia or Australia had the doubled 5-hour limit all workday: Pro's 5-hour window was 2x its usual size and Max's was 10x Pro's (computed: 2 x 1x, 2 x 5x). The documented change was to 5-hour usage; whether weekly limits rose too is not in a source this guide could still read, so do not count on a doubled week.

### Practical Off-Peak Tactics

**For Pro plan users (where every bit of headroom matters), if a promotion runs again:**
- Schedule complex Opus-heavy work for its off-peak hours
- Use peak hours for lighter tasks (Haiku, quick lookups, small edits)
- If you are in the US, shift heavier sessions to early morning or evening

**For Max and Ultra users:**
- Off-peak promotions are a nice bonus, but do not restructure your workflow around them
- They are temporary and unpredictable -- building your habits around them is fragile
- Use them as found headroom for experimental or exploratory work you might otherwise skip
- On a verified Ultra account, a promotion that doubles only 5-hour usage adds nothing

> **Important**: Do not plan your entire workflow around off-peak availability. Promotions are temporary. Build habits that work at normal rates, and treat off-peak bonuses as a nice surplus.

---

## Subscription + API Hybrid Approach

Some developers get the best value by combining a subscription for interactive work with API billing for automated tasks.

### When a Hybrid Approach Makes Sense

| Interactive Work | Automated Work | Recommendation |
|-----------------|---------------|----------------|
| Heavy | None | Subscription only |
| Heavy | Light automation | Subscription + small API usage |
| Heavy | Heavy batch jobs | Subscription + Batch API |
| Light | Heavy automation | API only (skip subscription) |
| Moderate | Moderate automation | Subscription + API, review monthly |

### Common Hybrid Patterns

**Pattern 1: Subscription for coding + API for CI/CD**
- Claude Code Max for daily interactive development
- Anthropic API with Haiku 5.5 for automated PR review in CI pipelines (keep each request under 100K prompt tokens)
- Batch API with Sonnet for nightly code quality scans

**Pattern 2: Subscription for interactive + API for batch processing**
- Claude Code Pro for interactive exploratory work
- Batch API with Haiku 5.5 for large-scale data processing, migration scripts, or documentation generation

**Pattern 3: Subscription for team + API for shared tooling**
- Each developer on Claude Code Max, or on a Team Standard or Premium seat
- Shared API key for team automation (Slack bots, internal tools, code review pipelines); on a Team plan, the pooled monthly API credit (capped at $500) pays for it when it calls the Claude API through the linked Console organization

### Cost Tracking for Hybrid Setups

When using both subscription and API billing, track costs separately:

```
Monthly Cost Tracking:
├── Subscription: $100 (Max) -- fixed, predictable
├── API Usage:
│   ├── CI/CD pipeline (Haiku):     ~$15/mo
│   ├── Batch processing (Sonnet):  ~$25/mo
│   └── Ad-hoc API calls:           ~$5/mo
└── Total: ~$145/mo
```

With the Max monthly API credit, the ~$45 of API usage above is covered if it runs on the Claude API through the Claude Console: out-of-pocket drops from ~$145 to $100, and the other $55 of credit ($100 - $45) expires unused at the end of the cycle. If the CI/CD job runs `claude -p` with an API key from the linked Console organization, the credit covers it too, because that bills as Agent SDK usage. It does not cover a job started by the Claude Code GitHub Action (Claude Code usage, even with `-p`), `claude -p` signed in with your plan (that draws on your plan limits), or anything on Bedrock, Google Cloud, Foundry or Claude Platform on AWS ([Help Center](https://support.claude.com/en/articles/17154008-monthly-api-credits-for-max-ultra-and-team-plans), read 2026-11-01).

Review this breakdown monthly. If your Console API costs consistently exceed Max's $100 credit, price Ultra: at $200 or more a month of Console API usage it costs the same in total as Max and adds twice the weekly limit (see [Monthly API Credits on Max, Ultra and Team](#monthly-api-credits-on-max-ultra-and-team)). Otherwise ask whether the API's per-token billing is genuinely more efficient for those specific tasks.

---

## Monthly Review Checklist

Run through this checklist at the end of each billing cycle to ensure you are on the right plan and getting maximum value.

### 1. Check Rate Limit Frequency

How often did you hit rate limits this month? `claude-rate --usage` (claude-rate 0.4.0 or later) counts them by week from your local transcripts, so you can answer from data rather than memory (see [Blocked by a Limit Right Now](#blocked-by-a-limit-right-now)).

| Frequency | Interpretation | Action |
|-----------|---------------|--------|
| Never | Plan has plenty of headroom | Consider downgrading if this is consistent for 2+ months |
| 1-2 times total | Occasional spikes, acceptable | Stay on current plan |
| 1-2 times per week | Regular but manageable | Optimize model selection, or consider upgrading |
| Daily | Plan is too small for your usage | Upgrade to the next tier |

### 2. Review Your Model Usage Mix

Check what percentage of your usage went to each model. Use `/usage` in Claude Code (`/cost` and `/stats` open the same screen): its plan usage breakdown attributes usage to skills, subagents, plugins and MCP servers, so you can see which one is eating the allowance. The breakdown covers the last 24 hours or 7 days of this machine's session history only, not other devices or claude.ai ([costs page](https://code.claude.com/docs/en/costs), read 2026-11-01).

| Current Mix | Optimization Opportunity |
|-------------|------------------------|
| Mostly Opus | Can you shift routine tasks to Sonnet/Haiku? |
| Mostly Sonnet | Are there simple tasks that Haiku could handle? |
| Mostly Haiku | You are already efficient -- focus on workflow, not model choice |
| Even split | Good balance, focus on ensuring the right model is used for each task type |

`/usage` flags any behavior that accounts for 10% or more of your recent usage; start with what it flags ([Claude Code costs docs](https://code.claude.com/docs/en/costs)). It warns about max effort, workflows, always-on context and large tool results (v2.1.299) and shows large cache misses (v2.1.311), and from v2.1.305 each warning is a one-line fix that pressing `f` applies where Claude Code can, such as an `/effort` change ([changelog](https://code.claude.com/docs/en/changelog), read 2026-11-01).

### 3. Review Your Most Expensive Sessions

Look for sessions with unusually high token consumption. Common culprits:
- Sessions over 40 turns without using `/compact`
- Large file reads that inflated context unnecessarily
- Trial-and-error coding without Plan Mode
- Unused MCP servers (with default tool search only their tool names and server instructions load, but full schemas load when tool search is off; disable unused ones with `/mcp`, and check `/context` for what is consuming space)
- Idle sessions that keep spending: scheduled `/loop` tasks, cross-session messages (`crossSessionInbound: hold`), and goal check-ins (at most 3 idle check-ins per goal since v2.1.246; `CLAUDE_CODE_GOAL_CHECKIN_MINUTES=0` turns them off). Prompt suggestions also send a request after each response, mostly cache reads, and can be turned off. Session recap and idle compaction can also use tokens while you are idle; the costs page gives no figure for them ([Claude Code costs docs](https://code.claude.com/docs/en/costs), read 2026-11-01)

For per-session dollars, `claude-rate --usage --by session` (claude-rate 0.4.0 or later) lists the last 30 days of sessions in your local transcripts with their list-price spend, cache reads and writes included.

### 4. Compare Month-Over-Month

Track these metrics monthly:
- Number of rate limit hits
- Average session length (turns)
- Model usage distribution
- Subjective productivity (are you getting more done?)

If rate limits are trending up but productivity is flat, you need better optimization -- not a plan upgrade. If rate limits are trending up and productivity is also up, a plan upgrade is justified.

### 5. Decide on Plan Changes

| Situation | Decision |
|-----------|---------|
| Rate limits increasing, productivity increasing | Upgrade -- growth is real |
| Rate limits increasing, productivity flat | Optimize first (model selection, workflow patterns) |
| Rate limits stable, productivity increasing | Stay -- optimization is working |
| Rate limits rare, usage declining | Downgrade -- save the money |
| New project starting next month (heavier workload) | Upgrade proactively |
| Project ending next month (lighter workload) | Downgrade proactively |

---

## Key Takeaways

1. **Exact token allowances per plan are not publicly documented.** Max is 5x Pro every 5 hours and every week, and Ultra 10x Pro every week with no 5-hour limit on a verified account, but absolute numbers are not disclosed. Choose your plan based on observed rate-limit behavior, not on trying to calculate exact token budgets.

2. **Model selection is the highest-leverage optimization for subscription plans.** Defaulting to Haiku for routine tasks and reserving Opus for complex work stretches your allowance dramatically -- regardless of which plan you are on.

   On Opus 5.5, effort level is the second lever: thinking is always on (you can't turn it off) and reasoning tokens count as output. The default is already `medium`, so drop to `low` for routine work to slow your burn rate -- and on Fable 5.1 and later, Opus 5.5, Sonnet 5.5 and Haiku 5.5 the change keeps your prompt cache (not on Bedrock, Google Cloud's Agent Platform or a Claude apps gateway).

3. **Rate-limit cost is measured in your time, not in dollars.** If rate limits cost you more productive time per month than the upgrade price, upgrade. For most professional developers, the threshold is surprisingly low: at $50/hr, 1.6 hours of lost time a month pays for Pro to Max and 2 hours for Max to Ultra (computed: $80 / $50, $100 / $50).

4. **Subscriptions beat API billing for interactive development in most cases.** The subscription absorbs overhead costs (system prompts, caching, tool schemas) that would be billed separately on the API. Only switch to API if your usage is very light, very spiky, or primarily automated.

5. **Off-peak promotions are a bonus, not a strategy.** The one documented event (2026-03-13 to 2026-03-28) doubled 5-hour usage off-peak, and none was running on 2026-11-01. If another runs, take advantage of it -- especially if you are outside the US. But do not build your workflow around them. They are temporary and subject to change.

6. **Review your plan monthly.** Check rate-limit frequency, model usage mix, and productivity trends. Both upgrading too late and staying on an oversized plan cost you money.

7. **The hybrid approach (subscription + API) works well for developers who do both interactive coding and automated pipeline work.** Track both costs separately and review the split monthly. On Max and Ultra, the monthly API credit ($100 on Max, $200 on Ultra; Team $20 / $100 per seat, pooled and capped at $500) pays the first part of your Console API bill, including `claude -p` run with an API key from the linked Console organization -- but not interactive Claude Code, and it does not roll over.

8. **On any plan, the optimization fundamentals still apply.** Keep CLAUDE.md lean, use Plan Mode, leverage subagents, start new sessions for new tasks, and use `/compact` at natural breaks. These strategies compound whether you are on Pro or Ultra.

---

*See also: [Guide 06 - Access Methods & Pricing](06-access-methods-pricing.md) for detailed comparison of subscription vs API vs Bedrock vs Google Cloud pricing. Return to the [README](../README.md) for the full guide index.*
