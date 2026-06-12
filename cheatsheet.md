# Claude Code Cost Optimization Cheatsheet

> One-page quick reference. Print it, bookmark it, pin it. Every strategy links to a detailed guide.
>
> **Pricing verified: 2026-06-06.** Sources: [platform pricing](https://platform.claude.com/docs/en/about-claude/pricing), [models overview](https://platform.claude.com/docs/en/about-claude/models/overview), [model deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations), [fast mode](https://platform.claude.com/docs/en/build-with-claude/fast-mode).

---

## Token Pricing At a Glance

| Model | Input / 1M tokens | Output / 1M tokens | Cache Hit / 1M | 5m Cache Write | 1h Cache Write | Context | Max Output | Relative Cost |
|-------|:-----------------:|:-------------------:|:--------------:|:--------------:|:--------------:|:-------:|:----------:|:-------------:|
| **Opus 4.8** (current) | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1M | 128K | 1x (baseline) |
| **Opus 4.7** | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1M | 128K | 1x (baseline) |
| **Opus 4.6** | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 1M | 128K | 1x (baseline) |
| **Opus 4.5** | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 | 200K | 64K | 1x (baseline) |
| **Opus 4.1** | $15.00 | $75.00 | $1.50 | $18.75 | $30.00 | 200K | 32K | 3x baseline |
| **Sonnet 4.6** | $3.00 | $15.00 | $0.30 | $3.75 | $6.00 | 1M | 64K | **~1.7x cheaper** |
| **Sonnet 4.5** | $3.00 | $15.00 | $0.30 | $3.75 | $6.00 | 200K | 64K | **~1.7x cheaper** |
| **Haiku 4.5** | $1.00 | $5.00 | $0.10 | $1.25 | $2.00 | 200K | 64K | **5x cheaper** |
| **Opus 4.8 (Fast Mode)** | $10.00 (2x) | $50.00 (2x) | N/A | -- | -- | 1M | 128K | 2x baseline |
| **Opus 4.7 / 4.6 (Fast Mode)** | $30.00 (6x) | $150.00 (6x) | N/A | -- | -- | 1M | 128K | 6x baseline |
| **Mythos Preview** (invite-only, Glasswing) | $25.00 | $125.00 | $2.50 | $31.25 | $50.00 | 1M | -- | 5x baseline output |

> Output tokens cost **5x more** than input tokens across all current models. Reducing Claude's verbosity is high-leverage.
>
> **1M context on Opus 4.8 / 4.7 / 4.6 / Sonnet 4.6 is at standard rates** -- no long-context premium. (Earlier "2x over 200K" pricing is obsolete.) **Haiku 4.5, Sonnet 4.5, Opus 4.5, and Opus 4.1 are 200K-context only.**
>
> **Cache pricing math**: 5m write = 1.25x base input; 1h write = 2x base input; cache hit/refresh = 0.1x base input. So a 5m cache pays off after 1 reuse, a 1h cache after 2 reuses. Multipliers stack with Batch (50% off) and data residency (+10%).
>
> **Opus 4.8 / 4.7 tokenizer**: The new tokenizer (Opus 4.7 and later) uses **up to 35% more tokens** for the same text. Effective per-task cost is higher than posted pricing implies. Budget accordingly when comparing 4.8 / 4.7 to 4.6 / Sonnet 4.6.
>
> **Opus 4.8 status**: Current flagship and most capable model. $5/$25 -- same price as 4.7 / 4.6. Adaptive thinking only; effort defaults to `high`. Fast Mode is cheaper here (2x) than on 4.7 / 4.6 (6x). Pick 4.8 for new work; pin 4.7 / 4.6 only if prompts are tuned to an older snapshot.
>
> **Mythos Preview**: Invitation-only research model for defensive cybersecurity under [Project Glasswing](https://anthropic.com/glasswing). 5x Opus 4.8's output rate ($125/MTok). Not for general development -- access restricted to ~50 approved critical-infrastructure organizations. Benchmarks: CyberGym 83.1%, SWE-bench Pro 77.8% (both significantly above Opus 4.6).
>
> **Fast Mode (research preview)**: Available on **Opus 4.8, Opus 4.7, and Opus 4.6** via the `fast-mode-2026-02-01` beta header (`speed: "fast"`). Per-model premium: **Opus 4.8 = 2x ($10 / $50 per MTok)**, **Opus 4.7 / 4.6 = 6x ($30 / $150 per MTok)** (4.6 Fast Mode deprecated as of the 4.8 launch). Up to **2.5x output tokens/second** -- speed gain is on OTPS, not time-to-first-token. Opus 4.8 Fast Mode is Claude API + Managed Agents only. NOT available on Claude Platform on AWS, NOT compatible with Batch API or Priority Tier. Switching speeds invalidates prompt cache. [Join the waitlist](https://claude.com/fast-mode).
>
> **Subscriptions**: Pro **$20/mo** (or **$200/yr ≈ $16.67/mo**, ~17% off). Max 5x $100/mo. Max 20x $200/mo. **Batch API**: 50% off both input and output. **Regional endpoints** (Bedrock / Vertex AI / Claude API `inference_geo: "us"`, scope = Sonnet 4.5+, Haiku 4.5+, Opus 4.5+, and all future models): +10% premium.

### Thinking Modes by Model

| Model | Extended thinking | Adaptive thinking |
|-------|:-----------------:|:-----------------:|
| Opus 4.8 | No | Yes |
| Opus 4.7 | No | Yes |
| Opus 4.6 | Yes | Yes |
| Opus 4.5 | Yes | -- |
| Sonnet 4.6 | Yes | Yes |
| Sonnet 4.5 | Yes | -- |
| Haiku 4.5 | Yes | No |
| Mythos Preview | Yes | -- |

> **Extended thinking** adds explicit reasoning tokens you pay for as output. **Adaptive thinking** lets the model decide when and how much to think based on task difficulty -- no separate billing flag. Opus 4.7 replaced extended thinking with adaptive thinking + the `xhigh` effort level; Opus 4.8 keeps the same surface but defaults `effort` to `high`.

### Model Lifecycle (verified 2026-06-06)

**Recently retired** (requests will fail):

| Model | Retired on | Migrate to |
|-------|:---------:|-----------|
| Opus 3 (`claude-3-opus-20240229`) | 2026-01-05 | Opus 4.8 |
| Sonnet 3.7 (`claude-3-7-sonnet-20250219`) | 2026-02-19 | Sonnet 4.6 |
| Haiku 3.5 (`claude-3-5-haiku-20241022`) | 2026-02-19 (still on Bedrock + Vertex AI) | Haiku 4.5 |
| Haiku 3 (`claude-3-haiku-20240307`) | 2026-04-20 | Haiku 4.5 |

**Upcoming retirements**:

| Model | Retirement date | Migration target |
|-------|:--------------:|-----------------|
| Sonnet 4 (`claude-sonnet-4-20250514`) | **June 15, 2026** | Sonnet 4.6 |
| Opus 4 (`claude-opus-4-20250514`) | **June 15, 2026** | Opus 4.8 |
| Opus 4.1 (`claude-opus-4-1-20250805`) | **August 5, 2026** | Opus 4.8 |
| Sonnet 4.5 (`claude-sonnet-4-5-20250929`) | Not before 2026-09-29 | Sonnet 4.6 |
| Haiku 4.5 (`claude-haiku-4-5-20251001`) | Not before 2026-10-15 | (current) |
| Opus 4.5 (`claude-opus-4-5-20251101`) | Not before 2026-11-24 | Opus 4.8 |
| Opus 4.6 (`claude-opus-4-6`) | Not before 2027-02-05 | Opus 4.8 |
| Sonnet 4.6 (`claude-sonnet-4-6`) | Not before 2027-02-17 | (current) |
| Opus 4.7 (`claude-opus-4-7`) | Not before 2027-04-16 | Opus 4.8 |
| Opus 4.8 (`claude-opus-4-8`) | Not before 2027-05-28 | (current) |

> **If you still call Sonnet 4 or Opus 4 model IDs, you have until June 15, 2026** to migrate -- about 9 days out.
>
> **Off-Peak 2x Usage**: Anthropic periodically runs promotional events that double usage limits outside peak hours (typically 8 AM - 2 PM ET) and on all weekends. If you're outside the US, your entire workday likely falls in the 2x window. Watch the [Anthropic blog](https://www.anthropic.com/news) for announcements.
>
> **CLI Cost Controls**: `--max-budget-usd <amount>` caps spending per session. `--fallback-model <model>` auto-switches to a cheaper model when the primary is overloaded.

---

## Legacy & Retired Models (reference only)

> Migration context for code still pinned to older model IDs. **Do not use these for new work** -- prices, IDs, and capabilities are kept here for archive value only.

### Recently retired (requests now fail)

| Model | Retired on | Last priced at (input / output per 1M) | Migrate to |
|-------|:---------:|:--------------------------------------:|-----------|
| Claude Opus 3 (`claude-3-opus-20240229`) | 2026-01-05 | $15 / $75 | Opus 4.8 |
| Claude Sonnet 3.7 (`claude-3-7-sonnet-20250219`) | 2026-02-19 | $3 / $15 | Sonnet 4.6 |
| Claude Haiku 3.5 (`claude-3-5-haiku-20241022`) | 2026-02-19 (still on Bedrock + Vertex AI) | $0.80 / $4 | Haiku 4.5 |
| Claude Haiku 3 (`claude-3-haiku-20240307`) | 2026-04-20 | $0.25 / $1.25 | Haiku 4.5 |
| Claude Sonnet 3.5 v1 (`claude-3-5-sonnet-20240620`) | 2025-10-28 | $3 / $15 | Sonnet 4.6 |
| Claude Sonnet 3.5 v2 (`claude-3-5-sonnet-20241022`) | 2025-10-28 | $3 / $15 | Sonnet 4.6 |
| Claude Sonnet 3 (`claude-3-sonnet-20240229`) | 2025-07-21 | $3 / $15 | Sonnet 4.6 |
| Claude 2 / 2.1 (`claude-2.0`, `claude-2.1`) | 2025-07-21 | $8 / $24 | Opus 4.8 |
| Claude Instant 1.x | 2024-11-06 | $0.80 / $2.40 | Haiku 4.5 |
| Claude 1.x | 2024-11-06 | $8 / $24 | Haiku 4.5 |

### Deprecated (still working, retiring soon)

| Model | Deprecated on | Retirement date | Last priced at (input / output per 1M) | Migrate to |
|-------|:------------:|:---------------:|:--------------------------------------:|-----------|
| Claude Sonnet 4 (`claude-sonnet-4-20250514`) | 2026-04-14 | **2026-06-15** | $3 / $15 | Sonnet 4.6 |
| Claude Opus 4 (`claude-opus-4-20250514`) | 2026-04-14 | **2026-06-15** | $15 / $75 | Opus 4.8 |
| Claude Opus 4.1 (`claude-opus-4-1-20250805`) | 2026-06-05 | **2026-08-05** | $15 / $75 | Opus 4.8 |

### Historical pricing patterns (no longer in effect)

The following pricing constructs were real but have since been retired or restructured. Listed here for migration context if you're reading older guides:

- **"2x input, 1.5x output above 200K"** long-context premium -- applied to Opus 4.1 and older. Obsolete on Opus 4.8 / 4.7 / 4.6 and Sonnet 4.6, which bill 1M context at standard rates.
- **Opus 4.1 ($15/$75)** -- original "Opus 4.x" pricing. Deprecated (retires 2026-08-05) and priced at 3x current Opus rates. Migrate to 4.8 unless you have a specific compatibility need.
- **Bedrock-only ARN-versioned IDs** like `anthropic.claude-opus-4-20250514-v1:0` -- still resolve via the legacy InvokeModel/Converse path, but the new Mantle endpoint uses cleaner provider-prefixed IDs (`anthropic.claude-opus-4-8`).
- **Single endpoint type on Bedrock** -- pre-Sonnet-4.5, all Bedrock traffic was effectively "global". The +10% regional premium is a 4.5+ generation construct.

### Snapshots that are still active (not retired, but not the headline tier)

These models are GA and priced but generally not the recommended target for new work -- listed under "Legacy" because they're previous-generation snapshots:

| Snapshot | Pricing (input / output per 1M) | Context | Earliest retirement | Why use |
|----------|:-------------------------------:|:-------:|:-------------------:|---------|
| Opus 4.7 | $5 / $25 | 1M | 2027-04-16 | Previous flagship -- pin if not yet re-tuned for 4.8 |
| Opus 4.6 | $5 / $25 | 1M | 2027-02-05 | Stable snapshot of the previous-tokenizer Opus |
| Opus 4.5 | $5 / $25 | 200K | 2026-11-24 | Pinned workloads only |
| Opus 4.1 | $15 / $75 | 200K | 2026-08-05 | Compatibility only -- 3x more expensive, deprecated |
| Sonnet 4.5 | $3 / $15 | 200K | 2026-09-29 | Pinned workloads only |

> Authoritative source for all dates: [Anthropic model deprecations page](https://platform.claude.com/docs/en/about-claude/model-deprecations).

---

## All Strategies - Ranked by Impact

### Tier 1: High Impact (Do These First)

| # | Strategy | Savings | Effort | Explanation | Guide |
|---|----------|:-------:|:------:|-------------|-------|
| 1 | **Use cheaper models for simple tasks** | 20-40% | 1 min | Run `claude --model haiku` for formatting, simple fixes, file lookups, and boilerplate - Haiku handles ~70% of routine work at 1/5th the cost of Opus | [Model Selection](guides/03-model-selection.md) |
| 2 | **Delegate work to subagents** | 20-40% | 5 min | Subagent tool calls get their own isolated context; large file searches and multi-file reads happen outside your main conversation, keeping your primary context small | [Workflow Patterns](guides/04-workflow-patterns.md) |
| 3 | **Use Plan Mode before coding** | 15-25% | 0 min | Press `Shift+Tab` to toggle Plan Mode - Claude thinks through the approach before writing code, preventing expensive trial-and-error cycles that waste output tokens | [Workflow Patterns](guides/04-workflow-patterns.md) |
| 4 | **Trim CLAUDE.md to under 4,000 characters** | 10-20% | 15 min | Every line loads as input tokens on *every turn*. Content beyond 4,000 chars/file is silently truncated. Total budget across all instruction files: 12,000 chars. Cut ruthlessly | [Context Optimization](guides/02-context-optimization.md) |
| 5 | **Preserve prompt cache** | 10-25% | 5 min | Cached input tokens cost 90% less; keep CLAUDE.md and system context stable between turns - avoid editing CLAUDE.md mid-session, and keep conversation flow linear | [Understanding Costs](guides/01-understanding-costs.md) |

### Tier 2: Medium Impact (Set Up Once)

| # | Strategy | Savings | Effort | Explanation | Guide |
|---|----------|:-------:|:------:|-------------|-------|
| 6 | **Configure `.claudeignore`** | 5-15% | 2 min | Prevent Claude from indexing `node_modules/`, `dist/`, `.git/`, lock files, and build artifacts - these add thousands of tokens when Claude searches your project | [Context Optimization](guides/02-context-optimization.md) |
| 7 | **Use `/compact` regularly** | 10-20% | 0 min | Run `/compact` when conversation gets long (20+ turns) to summarize history and reset context window - prevents the exponential cost growth of long sessions | [Context Optimization](guides/02-context-optimization.md) |
| 8 | **Set budget caps** | 0%* | 1 min | Use `claude --max-budget-usd 5` or configure in settings to prevent runaway sessions - does not save tokens directly but prevents surprise bills | [Understanding Costs](guides/01-understanding-costs.md) |
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
├── Complex architecture, long agentic run, or hardest coding? → Opus 4.8
├── Standard feature work, code review, writing tests?         → Sonnet 4.6
├── Simple fix, formatting, boilerplate, file lookup?          → Haiku 4.5
└── Not sure?                                                  → Start with Sonnet 4.6
```

**Switch models mid-session**: Type `/model` and select, or start with `claude --model sonnet`.

> **Note**: Opus 4.8 is priced at $5/$25 - the same as Opus 4.7 / 4.6, and the same price Sonnet used to be. The gap between models is smaller, so switching down to Haiku ($1/$5) provides a 5x savings, not 19x as it was historically. The Opus 4.7+ tokenizer can bump effective cost up to 35%, narrowing the gap further.

---

## Platform Comparison

| Feature | Anthropic API | Claude Platform on AWS | AWS Bedrock | Google Vertex AI | Claude Code |
|---------|:---:|:---:|:---:|:---:|:---:|
| Standard pricing | Base rates | Same (CCU billing) | Same (global) / +10% (regional) | Same (global) / +10% (regional) | Included in plan |
| Opus 4.8 availability | **GA** | **GA** | **GA** | **GA** | Via `/model` |
| Sonnet 4.6 availability | GA | GA | GA | GA | Via `/model` |
| Haiku 4.5 availability | GA | GA | GA | GA | Via `/model` |
| 1M context | Yes (Opus 4.8/4.7/4.6, Sonnet 4.6) | Yes | Yes | Yes | Yes |
| Fast Mode (research preview) | **Yes (Opus 4.8 2x, 4.7/4.6 6x)** | No | No | No | (depends on plan) |
| Batch API (50% off) | Yes | No | Yes | Yes | N/A |
| Prompt caching | Yes | Yes | Yes | Yes | Automatic |
| Data-residency premium | +10% (`inference_geo: "us"`, 4.6+ models) | +10% (`inference_geo: "us"`) | Bedrock regional pricing | Vertex regional pricing | -- |
| Mythos Preview | Invite-only | -- | Invite-only (us-east-1) | -- | -- |

> **Bedrock / Vertex**: Same models, same capabilities. Global (cross-region) inference matches API pricing. Regional inference profiles add ~10%. The +10% premium scope is **Sonnet 4.5+, Haiku 4.5+, Opus 4.5+, and all future models**; older models retain their existing pricing.
>
> **Opus 4.8 on Bedrock**: **Generally available** via Claude in Amazon Bedrock (the Messages-API endpoint) with model ID `anthropic.claude-opus-4-8`. The legacy InvokeModel/Converse path with `us.anthropic.claude-opus-4-8` cross-region inference profile works for backward compatibility. (Opus 4.8 Fast Mode is Claude API + Managed Agents only -- not on Bedrock.)
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
             - Prompt Cache Savings (up to 90% on repeated input)
```

---

## Quick Copy-Paste Configs

### Minimal `.claudeignore`

```
node_modules/
dist/
build/
.next/
coverage/
*.lock
package-lock.json
yarn.lock
pnpm-lock.yaml
*.min.js
*.min.css
*.map
.git/
*.pyc
__pycache__/
.env
.env.*
*.log
```

### Budget-Conscious Launch Command

```bash
# Daily development with budget cap
claude --model sonnet --max-budget-usd 5

# Quick fixes with cheapest model
claude --model haiku --max-budget-usd 1

# Complex work with Opus but capped
claude --model opus --max-budget-usd 20
```

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
1. Start session       → claude --model sonnet --max-budget-usd 5
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
| Opus 4.8 output is ___ per 1M tokens | **$25** |
| Haiku 4.5 is ___ cheaper than Opus on input | **5x** |
| Output tokens cost ___ more than input | **5x** |
| Prompt cache discount | **90%** |
| CLAUDE.md loads on every ___ | **turn** |
| CLAUDE.md max size per file | **4,000 characters** (truncated beyond) |
| Total instruction file budget | **12,000 characters** (across all CLAUDE.md files) |
| 1 line of code is roughly ___ tokens | **~10** |
| Token estimation rule of thumb | **~1 token per 4 bytes** of text |
| Opus 4.7+ tokenizer overhead vs older models | **up to +35%** |
| 150-line CLAUDE.md per turn is roughly | **~1,050 tokens** |
| 50-turn session CLAUDE.md cost (Sonnet 4.6) | **~$0.16** |
| 50-turn session CLAUDE.md cost (Opus 4.8, pre-cache) | **~$0.26** (factor +35% for new tokenizer) |
| Average tool result size | **500-5,000 tokens** |
| Compaction trigger threshold | **~10,000 tokens** of compactable content |
| Messages preserved after /compact | **4 most recent** |
| Opus 4.8 / 4.7 / 4.6 max output per turn | **128K tokens** |
| Sonnet / Haiku 4.5 max output per turn | **64K tokens** |

---

## Output Token Optimization

Output tokens cost 5x more than input across all models. Most strategies above target input -- these target the expensive side.

| Strategy | Savings (output) | How |
|----------|:----------------:|-----|
| **Use a brevity skill (e.g. caveman)** | 50-75% | System prompt that strips filler, pleasantries, and hedging from responses. Technical accuracy unchanged. See [caveman](https://github.com/JuliusBrussee/caveman) |
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
4. **Set a hard cap**: `claude --max-budget-usd 2` for the next session
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
| CLAUDE.md Templates | [templates/CLAUDE.md/](templates/CLAUDE.md/) |
| Token Estimator Tool | [tools/token-estimator/](tools/token-estimator/) |
| Usage Analyzer Tool | [tools/usage-analyzer/](tools/usage-analyzer/) |
| claude-rate (local setup rater) | [tools/claude-rate/](tools/claude-rate/) |
| Caveman skill (output tokens) | [github.com/JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) |

---

*This cheatsheet covers the strategies. For the reasoning and benchmarks behind each one, read the full guides.*
