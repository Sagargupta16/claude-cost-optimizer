# Claude Code Cost Optimization Cheatsheet

> One-page quick reference. Print it, bookmark it, pin it. Every strategy links to a detailed guide.

---

## Token Pricing At a Glance

| Model | Input / 1M tokens | Output / 1M tokens | Cache Hit / 1M | Relative Cost |
|-------|:-----------------:|:-------------------:|:-----------------:|:-------------:|
| **Opus 4.6** | $5.00 | $25.00 | $0.50 | 1x (baseline) |
| **Sonnet 4.6** | $3.00 | $15.00 | $0.30 | **~1.7x cheaper** |
| **Haiku 4.5** | $1.00 | $5.00 | $0.10 | **5x cheaper** |
| **Opus 4.6 (1M context)** | $10.00 (2x) | $37.50 (1.5x) | $1.00 | 2x baseline |
| **Sonnet 4.6 (1M context)** | $6.00 (2x) | $22.50 (1.5x) | $0.60 | ~1.2x baseline |
| **Opus 4.6 (Fast Mode)** | $30.00 (6x) | $150.00 (6x) | N/A | 6x baseline |

> Output tokens cost **5x more** than input tokens across all models. Reducing Claude's verbosity is high-leverage.
>
> **1M context**: Applies when input exceeds 200K tokens. ALL tokens are billed at the premium rate (not just those over 200K). Haiku 4.5 does not support 1M context.
>
> **Fast Mode**: Opus 4.6 only (research preview). 6x standard rates but includes 1M context at no extra long-context charge. Not available with Batch API.
>
> **Plans**: Pro $20/mo, Max 5x $100/mo, Max 20x $200/mo. **Batch API**: 50% discount. **Cache write**: 1.25x (5-min TTL), 2x (1-hour TTL).
>
> **Off-Peak 2x Usage**: Anthropic periodically runs promotional events that double usage limits outside peak hours (typically 8 AM - 2 PM ET) and on all weekends. If you're outside the US, your entire workday likely falls in the 2x window. Watch the [Anthropic blog](https://www.anthropic.com/news) for announcements.
>
> **CLI Cost Controls**: `--max-budget-usd <amount>` caps spending per session. `--fallback-model <model>` auto-switches to a cheaper model when the primary is overloaded.

---

## All Strategies - Ranked by Impact

### Tier 1: High Impact (Do These First)

| # | Strategy | Savings | Effort | Explanation | Guide |
|---|----------|:-------:|:------:|-------------|-------|
| 1 | **Use cheaper models for simple tasks** | 20-40% | 1 min | Run `claude --model haiku` for formatting, simple fixes, file lookups, and boilerplate - Haiku handles ~70% of routine work at 1/5th the cost of Opus | [Model Selection](guides/03-model-selection.md) |
| 2 | **Delegate work to subagents** | 20-40% | 5 min | Subagent tool calls get their own isolated context; large file searches and multi-file reads happen outside your main conversation, keeping your primary context small | [Workflow Patterns](guides/04-workflow-patterns.md) |
| 3 | **Use Plan Mode before coding** | 15-25% | 0 min | Press `Shift+Tab` to toggle Plan Mode - Claude thinks through the approach before writing code, preventing expensive trial-and-error cycles that waste output tokens | [Workflow Patterns](guides/04-workflow-patterns.md) |
| 4 | **Trim CLAUDE.md to under 150 lines** | 10-20% | 15 min | Every line of CLAUDE.md is loaded as input tokens on *every single turn* - 300 lines across 50 turns means you pay for those lines 50 times; cut ruthlessly | [Context Optimization](guides/02-context-optimization.md) |
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
├── Complex architecture, debugging, or multi-file refactor? → Opus 4.6
├── Standard feature work, code review, writing tests?      → Sonnet 4.6
├── Simple fix, formatting, boilerplate, file lookup?       → Haiku 4.5
└── Not sure?                                               → Start with Sonnet 4.6
```

**Switch models mid-session**: Type `/model` and select, or start with `claude --model sonnet`.

> **Note**: Opus 4.6 is now priced at $5/$25 - the same price Sonnet used to be. The gap between models is smaller, so switching down to Haiku ($1/$5) provides a 5x savings, not 19x as it was historically.

---

## Platform Comparison

| Feature | Anthropic API | AWS Bedrock | Google Vertex AI | Claude Code |
|---------|:---:|:---:|:---:|:---:|
| Standard pricing | Base rates | Same (global) / +10% (regional) | Same (global) / +10% (regional) | Included in plan |
| 1M context | Yes (Opus, Sonnet) | Yes | Yes | Yes |
| Fast Mode | Yes (Opus only) | Check availability | Check availability | Yes (`/fast`) |
| Batch API (50% off) | Yes | Yes | Yes | N/A |
| Prompt caching | Yes | Yes | Yes | Automatic |
| Max context | 1M | 1M | 1M | 1M |

> **Bedrock / Vertex**: Same models, same capabilities. Global (cross-region) inference matches API pricing. Regional inference profiles add ~10%. Choose based on your cloud provider, compliance needs, and existing infrastructure.

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
| Opus 4.6 output is ___ per 1M tokens | **$25** |
| Haiku 4.5 is ___ cheaper than Opus 4.6 on input | **5x** |
| Output tokens cost ___ more than input | **5x** |
| Prompt cache discount | **90%** |
| CLAUDE.md loads on every ___ | **turn** |
| CLAUDE.md max size per file | **4,000 characters** (truncated beyond) |
| Total instruction file budget | **12,000 characters** (across all CLAUDE.md files) |
| 1 line of code is roughly ___ tokens | **~10** |
| Token estimation rule of thumb | **~1 token per 4 bytes** of text |
| 150-line CLAUDE.md per turn is roughly | **~1,050 tokens** |
| 50-turn session CLAUDE.md cost (Sonnet 4.6) | **~$0.16** |
| 50-turn session CLAUDE.md cost (Opus 4.6) | **~$0.26** |
| Average tool result size | **500-5,000 tokens** |
| Compaction trigger threshold | **~10,000 tokens** of compactable content |
| Messages preserved after /compact | **4 most recent** |
| Opus 4.6 max output per turn | **32K tokens** |
| Sonnet/Haiku max output per turn | **64K tokens** |

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
| Understanding Costs (deep dive) | [guides/01-understanding-costs.md](guides/01-understanding-costs.md) |
| Context Optimization | [guides/02-context-optimization.md](guides/02-context-optimization.md) |
| Model Selection Guide | [guides/03-model-selection.md](guides/03-model-selection.md) |
| Workflow Patterns | [guides/04-workflow-patterns.md](guides/04-workflow-patterns.md) |
| Team Budgeting | [guides/05-team-budgeting.md](guides/05-team-budgeting.md) |
| CLAUDE.md Templates | [templates/CLAUDE.md/](templates/CLAUDE.md/) |
| Token Estimator Tool | [tools/token-estimator/](tools/token-estimator/) |
| Usage Analyzer Tool | [tools/usage-analyzer/](tools/usage-analyzer/) |

---

*This cheatsheet covers the strategies. For the reasoning and benchmarks behind each one, read the full guides.*
