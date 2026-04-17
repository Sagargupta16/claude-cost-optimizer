# Guide 05: Team Budgeting

> **Claude Code costs scale linearly with team size — unless you manage them.** A team of 5 without budgets can spend $200-800/month. With the strategies in this guide, the same team spends $100-300/month.

Individual optimization matters, but team-level cost management is where the real financial discipline happens. This guide covers budgets, tracking, ROI analysis, and scaling strategies for teams of all sizes.

---

## Table of Contents

- [Setting Per-Developer Monthly Budgets](#setting-per-developer-monthly-budgets)
- [Monthly Cost Estimation Formula](#monthly-cost-estimation-formula)
- [Tracking Usage Across Team Members](#tracking-usage-across-team-members)
- [Claude Code vs Claude API vs Manual Coding](#claude-code-vs-claude-api-vs-manual-coding)
- [ROI Calculation Template](#roi-calculation-template)
- [Cost Allocation by Project and Task Type](#cost-allocation-by-project-and-task-type)
- [Scaling Strategies as Your Team Grows](#scaling-strategies-as-your-team-grows)
- [Onboarding New Team Members Cost-Efficiently](#onboarding-new-team-members-cost-efficiently)
- [Budget Alert Systems](#budget-alert-systems)
- [Monthly Budget Review Process](#monthly-budget-review-process)

---

## Setting Per-Developer Monthly Budgets

### Why Per-Developer Budgets Work

A shared team budget creates a tragedy of the commons: everyone assumes someone else will be careful. Per-developer budgets create individual accountability without micromanaging how each person uses the tool.

### Budget Tiers by Role

Not every developer uses Claude Code the same way. Set budgets based on role and typical usage:

| Role | Typical Usage | Recommended Budget | Rationale |
|------|---------------|:------------------:|-----------|
| **Junior Developer** | High-frequency simple tasks, learning | $30-60/month | Lots of small queries; should use Haiku 4.5 heavily |
| **Mid-Level Developer** | Mixed task complexity | $50-100/month | Component creation, bug fixes, test writing |
| **Senior Developer** | Lower frequency, higher complexity | $60-120/month | Architecture work, complex debugging (Opus 4.7 usage) |
| **Tech Lead** | Architecture, reviews, planning | $70-150/month | Higher Opus 4.7 usage justified for strategic decisions |
| **DevOps/Platform** | Infrastructure, CI/CD, automation | $30-60/month | Mostly config generation, script writing |

> **Note**: These budgets reflect April 2026 pricing where Opus 4.7 (and legacy 4.6) is significantly cheaper ($5/$25 per MTok) than Opus 4.1 ($15/$75). Budget tiers are lower across the board compared to the old Opus pricing. Opus 4.7's new tokenizer uses up to 35% more tokens for the same text, so budgeting for it slightly higher than you would for 4.6 is wise.

### Setting the Initial Budget

Start with a **two-week calibration period**:

1. Have each developer use Claude Code normally for 2 weeks
2. Track their actual spending (see [Tracking Usage](#tracking-usage-across-team-members))
3. Set the budget at **120% of their calibrated spending** (gives 20% headroom)
4. Review and adjust after the first full month

### Budget Enforcement Philosophy

Budgets should be **guardrails, not handcuffs**:

- **Soft limit (80% of budget)**: Developer receives a notification. No action required.
- **Warning (100% of budget)**: Developer reviews remaining work for the month. Considers switching to cheaper models or manual work for routine tasks.
- **Hard limit (120% of budget)**: Requires team lead approval to continue. Triggers a review of usage patterns.

Do not set hard limits at 100% — this causes developers to stop using the tool entirely when they approach the limit, even for high-ROI tasks. The 120% hard limit lets them finish critical work while still flagging overuse.

---

## Monthly Cost Estimation Formula

### The Basic Formula

```
Monthly Cost = Daily Tasks x Avg Cost Per Task x Working Days

Where:
  Daily Tasks      = Number of Claude Code interactions per day
  Avg Cost Per Task = Weighted average across model tiers
  Working Days     = Typically 22 per month
```

### Detailed Estimation

For a more accurate estimate, break down by task type:

```
Monthly Cost = (Simple Tasks x Simple Cost) +
               (Medium Tasks x Medium Cost) +
               (Complex Tasks x Complex Cost)

Where (per developer per day):
  Simple Tasks  = ~15-25 tasks/day   x $0.01 avg (Haiku 4.5)  = $0.15-0.25/day
  Medium Tasks  = ~8-15 tasks/day    x $0.07 avg (Sonnet 4.6)  = $0.56-1.05/day
  Complex Tasks = ~2-5 tasks/day     x $0.13 avg (Opus 4.7)    = $0.26-0.65/day

  Daily Total   = $0.97-1.95/day
  Monthly Total = $21-43/developer (optimized)
```

> **Note**: The Opus average cost per complex task has dropped from ~$0.40 (at old Opus 4.1 $15/$75 pricing) to ~$0.13 (at current $5/$25 pricing for Opus 4.7 and 4.6). This significantly reduces the cost of architecture, debugging, and multi-file work.

### Estimation Worksheet

Fill in your team's numbers:

```
TEAM COST ESTIMATION WORKSHEET

Team size:                    _____ developers
Working days/month:           _____ (default: 22)

Per Developer (daily averages):
  Simple tasks (Haiku 4.5):   _____ tasks x $0.01 = $_____ /day
  Medium tasks (Sonnet 4.6):  _____ tasks x $0.07 = $_____ /day
  Complex tasks (Opus 4.7):   _____ tasks x $0.13 = $_____ /day

  Daily subtotal:             $_____ /day
  Monthly subtotal:           $_____ x 22 = $_____ /month

Team Monthly Total:           $_____ x _____ developers = $_____ /month

Add 20% buffer:              $_____ x 1.2 = $_____ /month (budgeted)
```

### Example: Team of 5

```
Junior Dev (2):      $40/month x 2  = $80
Mid-Level Dev (2):   $65/month x 2  = $130
Tech Lead (1):       $100/month x 1 = $100

Subtotal:            $310/month
Buffer (20%):        $62/month
Budgeted Total:      $372/month

Compare to unoptimized: 5 developers x $110/month = $550/month
Savings: $178/month = $2,136/year
```

---

## Tracking Usage Across Team Members

### Method 1: Claude Code's Built-In Usage

Each developer can check their usage with the `/usage` command in Claude Code. This shows the current session's token consumption.

For historical data, use the Anthropic Console (console.anthropic.com) if your team uses API-based billing.

### Method 2: Usage Analyzer Tool

This repo includes a [Usage Analyzer](../tools/usage-analyzer/README.md) that parses Claude Code's local usage data:

```bash
# Individual developer report
python tools/usage-analyzer/analyze.py ~/.claude/projects/ --period monthly

# Example output:
# Month: 2026-03
# Total tokens: 2,450,000 input / 890,000 output
# Estimated cost: $52.30
# Top projects: webapp ($26.10), api-service ($17.20), scripts ($9.00)
# Model split: Haiku 45%, Sonnet 40%, Opus 15%
```

### Method 3: Team Dashboard

For teams using Anthropic's API with organization billing, create a simple tracking system:

```
Weekly Team Report Template:

Developer       | This Week | Month-to-Date | Budget | % Used
----------------|:---------:|:-------------:|:------:|:------:
Alice (Jr)      | $9.40     | $28.20        | $50    | 56%
Bob (Mid)       | $14.90    | $48.10        | $80    | 60%
Carol (Sr)      | $17.30    | $69.40        | $100   | 69%
Dave (Mid)      | $12.60    | $41.80        | $80    | 52%
Eve (Lead)      | $22.10    | $88.50        | $130   | 68%

Team Total      | $76.30    | $276.00       | $440   | 63%
```

### Key Metrics to Track

| Metric | What It Tells You | Target |
|--------|-------------------|--------|
| **Cost per developer per day** | Individual efficiency | $1.00-2.50 (optimized) |
| **Model distribution** | Are devs using the right models? | 40% Haiku, 40% Sonnet, 20% Opus |
| **Tokens per task** | Are prompts efficient? | Decreasing over time |
| **Cost per commit** | Cost of productive output | $0.30-1.50 |
| **Opus usage %** | Over-reliance on expensive model | Under 25% of total tasks |

---

## Claude Code vs Claude API vs Manual Coding

### When to Use Each

Not every task should go through Claude Code. Here is a decision framework for teams:

| Approach | Best For | Typical Cost | Speed |
|----------|----------|:------------:|:-----:|
| **Claude Code** | Interactive development, multi-file changes, exploration | $0.01-0.50/task | Fast (for complex work) |
| **Claude API** (direct) | Batch processing, CI/CD pipelines, automated code review | $0.005-0.30/call | Variable |
| **Manual coding** | Trivial changes, domain-expert knowledge, creative design | $0 (but developer time) | Depends on task |

### Decision Matrix

```
Is the task repetitive and automated?
├── YES → Claude API (batch processing, CI pipelines)
└── NO ↓

Does the task require interactive back-and-forth with code?
├── YES → Claude Code
└── NO ↓

Is the task trivial (< 30 seconds to do manually)?
├── YES → Manual coding
└── NO ↓

Does the task require deep domain knowledge only the developer has?
├── YES → Manual coding (with Claude Code for boilerplate parts)
└── NO → Claude Code
```

### Cost Comparison for Common Workflows

| Workflow | Claude Code | Claude API | Manual | Recommendation |
|----------|:-----------:|:----------:|:------:|----------------|
| Code review (PR) | $0.10-0.30 | $0.05-0.15 | 15-30 min | API (automated in CI) |
| Generate test suite | $0.08-0.25 | $0.04-0.12 | 30-60 min | Claude Code |
| Fix linting errors | $0.02-0.05 | N/A | 2-5 min | Manual (use lint --fix) |
| Write documentation | $0.05-0.15 | $0.03-0.08 | 20-45 min | Claude Code |
| Scaffold new service | $0.10-0.35 | N/A | 15-30 min | Claude Code |
| Update dependency versions | $0.02-0.05 | N/A | 5 min | Manual (Renovate/Dependabot) |

---

## ROI Calculation Template

### The Core ROI Formula

```
ROI = (Value of Time Saved - Claude Code Costs) / Claude Code Costs x 100%

Where:
  Value of Time Saved = Hours Saved x Developer Hourly Rate
  Claude Code Costs   = Monthly token spend + subscription costs
```

### Detailed ROI Worksheet

```
MONTHLY ROI CALCULATION

1. TIME SAVINGS
   Tasks accelerated by Claude Code:         _____ tasks/month
   Average time saved per task:               _____ minutes
   Total time saved:                          _____ hours/month
   Developer fully-loaded hourly rate:        $_____ /hour
   Value of time saved (A):                   $_____ /month

2. QUALITY IMPROVEMENTS (optional, harder to quantify)
   Bugs prevented by AI-assisted code review: _____ /month
   Average cost per production bug:           $_____
   Bug prevention value (B):                  $_____ /month

3. CLAUDE CODE COSTS
   Monthly token spend:                       $_____ /month
   Subscription cost (Pro $20/mo, Max 5x $100/mo, Max 20x $200/mo): $_____ /month
   Total Claude Code cost (C):                $_____ /month

4. ROI CALCULATION
   Total value:     A + B =                   $_____ /month
   Total cost:      C     =                   $_____ /month
   Net benefit:     (A + B) - C =             $_____ /month
   ROI:             ((A + B) - C) / C x 100 = _____%
```

### Example ROI Calculation

**Scenario**: Mid-level developer, $75/hour fully-loaded rate

```
TIME SAVINGS:
  200 tasks/month x 12 minutes saved per task = 40 hours saved
  40 hours x $75/hour = $3,000 value

CLAUDE CODE COSTS:
  Token spend: $60/month
  Pro plan: $20/month (or Max 5x: $100/month, Max 20x: $200/month)
  Total: $80/month (Pro) or $160/month (Max 5x) or $260/month (Max 20x)

ROI:
  ($3,000 - $80) / $80 = 3,650% ROI (Pro plan)
  ($3,000 - $160) / $160 = 1,775% ROI (Max 5x plan)
  ($3,000 - $260) / $260 = 1,054% ROI (Max 20x plan)

NET BENEFIT:
  $2,920/month per developer (Pro plan)
  $2,840/month per developer (Max 5x plan)
  $2,740/month per developer (Max 20x plan)
```

Even with conservative estimates (half the tasks, half the time saved), the ROI is still over 500%. The question is not whether Claude Code is worth it — it is how to maximize the ROI by minimizing waste.

### ROI by Task Type

| Task Type | Avg Time Saved | Claude Code Cost | ROI (at $75/hr) |
|-----------|:--------------:|:----------------:|:----------------:|
| Test writing | 25 min | $0.10 | 31,150% |
| Bug fixing | 20 min | $0.12 | 20,733% |
| Component creation | 30 min | $0.08 | 46,775% |
| Code review | 15 min | $0.06 | 31,150% |
| Documentation | 20 min | $0.05 | 49,900% |
| Architecture planning | 45 min | $0.27 | 20,733% |
| Simple refactoring | 10 min | $0.02 | 62,400% |

> Even the lowest-ROI task (architecture planning) returns over 200x the investment.

---

## Cost Allocation by Project and Task Type

### Why Allocate Costs?

Cost allocation helps you:
1. **Identify expensive projects** that may need optimization
2. **Justify Claude Code spend** to stakeholders on a per-project basis
3. **Budget accurately** for future projects based on historical data
4. **Find patterns** (e.g., "testing tasks cost 3x more than expected")

### Allocation Framework

```
Organization
├── Team A
│   ├── Project: E-commerce Platform
│   │   ├── Feature development:  45% ($120/month)
│   │   ├── Bug fixes:            20% ($53/month)
│   │   ├── Testing:              15% ($40/month)
│   │   ├── Code review:          10% ($27/month)
│   │   └── Documentation:        10% ($27/month)
│   │   Total: $267/month
│   │
│   └── Project: Internal Tools
│       ├── Feature development:  50% ($33/month)
│       ├── Bug fixes:            25% ($17/month)
│       └── Testing:              25% ($17/month)
│       Total: $67/month
│
└── Team B
    └── Project: Mobile API
        ├── Feature development:  40% ($80/month)
        ├── Performance work:     25% ($50/month)
        ├── Bug fixes:            20% ($40/month)
        └── Testing:              15% ($30/month)
        Total: $200/month
```

### Tracking Cost by Project

Use project-level `.claude/` configurations to naturally separate costs:

```
~/projects/
├── ecommerce/
│   └── .claude/
│       └── settings.json    ← Project-specific settings
├── internal-tools/
│   └── .claude/
│       └── settings.json
└── mobile-api/
    └── .claude/
        └── settings.json
```

Then use the Usage Analyzer to generate per-project reports:

```bash
python tools/usage-analyzer/analyze.py ~/.claude/projects/ --group-by project
```

### Cost Per Feature Estimation

When planning sprints, estimate Claude Code costs alongside development time:

```
Feature: User notification preferences
  - Frontend component (Sonnet 4.6, ~$0.10)
  - API endpoint (Sonnet 4.6, ~$0.07)
  - Database migration (Haiku 4.5, ~$0.02)
  - Unit tests (Sonnet 4.6, ~$0.10)
  - Integration test (Sonnet 4.6, ~$0.07)
  - Code review assist (Haiku 4.5, ~$0.03)
  Estimated Claude Code cost: ~$0.39

Feature: Payment system overhaul
  - Architecture design (Opus 4.7, ~$0.27)
  - 5 service refactors (Sonnet 4.6, ~$0.40)
  - Database migration (Opus 4.7 plan + Sonnet 4.6 impl, ~$0.25)
  - Test suite (Sonnet 4.6, ~$0.25)
  - Security review (Opus 4.7, ~$0.20)
  Estimated Claude Code cost: ~$1.37
```

---

## Scaling Strategies as Your Team Grows

### Phase 1: Small Team (2-5 developers)

**Priority**: Establish good habits early.

| Action | Impact |
|--------|--------|
| Set Sonnet 4.6 as the team default model | Prevents Opus overuse from day one |
| Share a standard CLAUDE.md template | Consistent costs across the team |
| Create a shared command library | Standardized workflows, pre-set models |
| Weekly informal cost review | Catch problems early |

**Expected cost**: $100-300/month total.

### Phase 2: Growing Team (5-15 developers)

**Priority**: Systematize and automate.

| Action | Impact |
|--------|--------|
| Implement per-developer budgets | Individual accountability |
| Create role-based budget tiers | Fair budgets by usage pattern |
| Automate usage tracking | Weekly reports without manual effort |
| Build an internal "tips" channel | Peer-driven optimization |
| Conduct monthly cost reviews | Identify trends and outliers |

**Expected cost**: $300-900/month total.

### Phase 3: Large Team (15-50+ developers)

**Priority**: Governance and optimization at scale.

| Action | Impact |
|--------|--------|
| Centralized Claude Code configuration | Consistent settings across all projects |
| Cost allocation by department/project | Accurate chargebacks |
| Automated budget alerts | Proactive cost management |
| Quarterly optimization audits | Systematic waste reduction |
| Internal training program | New hires start optimized |
| Custom tooling for usage analytics | Deep visibility into spending patterns |
| Negotiate enterprise pricing | Volume discounts |

**Expected cost**: $900-3,500/month total.

### Cost Scaling: Optimized vs Unoptimized

| Team Size | Unoptimized | Optimized | Monthly Savings |
|:---------:|:-----------:|:---------:|:---------------:|
| 5 | $550 | $250 | $300 |
| 10 | $1,100 | $450 | $650 |
| 20 | $2,200 | $850 | $1,350 |
| 50 | $5,500 | $2,000 | $3,500 |

At 50 developers, cost optimization saves **$42,000/year**.

> **Note**: These numbers reflect Opus 4.7/4.6 pricing ($5/$25 per MTok). The absolute cost of "unoptimized" usage is significantly lower than it was at old Opus 4.1 pricing ($15/$75), but the percentage savings from optimization remain substantial. Opus 4.7's new tokenizer pushes the absolute dollar totals ~20-35% higher vs 4.6 for identical workloads.

---

## Onboarding New Team Members Cost-Efficiently

### The Onboarding Cost Problem

New team members using Claude Code for the first time tend to:
1. Use Opus for everything (it is the most capable, so why not?)
2. Write vague prompts that trigger clarification loops
3. Not use plan mode, leading to iterative waste
4. Not know about /compact, leading to bloated sessions
5. Ask Claude Code questions they could answer with documentation

A new developer's first month is typically **2-3x more expensive** than their steady-state usage.

### The Onboarding Checklist

Give every new team member this checklist on their first day with Claude Code:

```
CLAUDE CODE ONBOARDING CHECKLIST

Day 1: Setup
  [ ] Install Claude Code and verify it works
  [ ] Copy the team's standard CLAUDE.md to your project(s)
  [ ] Copy the team's .claudeignore template
  [ ] Set your default model to Sonnet 4.6 (not Opus)
  [ ] Install the team's shared command library

Day 1: Read These Guides (30 minutes total)
  [ ] Guide 03: Model Selection (know when to use each model)
  [ ] Guide 04: Workflow Patterns (plan mode, /compact, batch operations)
  [ ] This guide's ROI section (understand the economics)

Week 1: Practice
  [ ] Use Haiku 4.5 for at least 50% of your tasks
  [ ] Use plan mode for any task touching 3+ files
  [ ] Use /compact after every planning phase
  [ ] Write one complete prompt (no follow-up corrections needed)
  [ ] Track your daily spend and compare to team averages

Week 2: Optimize
  [ ] Create 3 personal commands for your most common tasks
  [ ] Review your Week 1 spending and identify waste
  [ ] Pair with an experienced team member for one session
  [ ] Achieve a day where your model split is 40%+ Haiku
```

### Pair Programming for Cost Efficiency

Have new team members pair with an experienced Claude Code user for their first complex task. The experienced user can:
- Demonstrate when to use each model
- Show the plan-then-execute workflow
- Point out when a task does not need Claude Code at all
- Share personal tips and shortcuts

One 30-minute pairing session can save hundreds of dollars over the new hire's first month.

### First-Month Budget Strategy

| Week | Budget Multiplier | Rationale |
|------|:-----------------:|-----------|
| Week 1 | 1.5x normal | Learning period, expect some waste |
| Week 2 | 1.3x normal | Getting comfortable, less waste |
| Week 3 | 1.1x normal | Should be approaching normal efficiency |
| Week 4 | 1.0x normal | Full budget, normal expectations |

Do not penalize new hires for higher costs in their first two weeks. The learning investment pays for itself within the first month.

---

## Budget Alert Systems

### Tier 1: Manual Tracking (Small Teams)

For teams of 2-5, a simple spreadsheet and weekly check-in is sufficient:

```
Weekly Budget Check (5 minutes per developer):
1. Run: /usage (in Claude Code)
2. Check against weekly budget (monthly budget / 4.3)
3. If over 80%: review remaining tasks for the week
4. If over 100%: discuss with team lead
```

### Tier 2: Automated Alerts (Growing Teams)

Set up automated notifications when developers approach budget limits:

```bash
# Example: Simple budget alert script
# Run daily via cron or CI

#!/bin/bash
BUDGET_MONTHLY=80  # dollars
ALERT_THRESHOLD=0.8 # 80%

current_spend=$(python tools/usage-analyzer/analyze.py \
  ~/.claude/projects/ --period mtd --output json | jq '.total_cost')

budget_used=$(echo "$current_spend / $BUDGET_MONTHLY" | bc -l)

if (( $(echo "$budget_used > $ALERT_THRESHOLD" | bc -l) )); then
  echo "ALERT: Claude Code spend at ${budget_used}% of monthly budget"
  # Send Slack notification, email, etc.
fi
```

### Tier 3: Dashboard and Governance (Large Teams)

For teams of 15+, build or adopt a dashboard that shows:

```
TEAM CLAUDE CODE DASHBOARD

Real-Time Metrics:
├── Total spend MTD: $847 / $1,400 budget (60%)
├── Projected month-end: $1,290 (within budget)
├── Developers over 80% budget: 2 of 18
└── Cost trend: -12% vs last month

Per-Developer View:
├── [Green]  Alice: $28 / $50 (56%)
├── [Green]  Bob: $48 / $80 (60%)
├── [Yellow] Carol: $83 / $100 (83%) ← approaching limit
├── [Green]  Dave: $36 / $80 (45%)
└── [Red]    Eve: $140 / $130 (108%) ← over budget

Alerts This Week:
├── Carol hit 80% threshold on Tuesday
├── Eve exceeded budget on Thursday (approved by team lead)
└── Team Opus usage increased 15% (investigate)
```

### Alert Configuration Template

```json
{
  "budget_alerts": {
    "per_developer": {
      "soft_warning": 0.6,
      "warning": 0.8,
      "critical": 1.0,
      "hard_limit": 1.2
    },
    "team_total": {
      "soft_warning": 0.7,
      "warning": 0.85,
      "critical": 0.95
    },
    "notifications": {
      "soft_warning": ["slack_dm"],
      "warning": ["slack_dm", "slack_channel"],
      "critical": ["slack_dm", "slack_channel", "email_lead"],
      "hard_limit": ["slack_dm", "slack_channel", "email_lead", "email_finance"]
    },
    "check_frequency": "daily"
  }
}
```

---

## Monthly Budget Review Process

### The 30-Minute Monthly Review

Once a month, the team lead should run a structured budget review. Here is the agenda:

```
MONTHLY CLAUDE CODE BUDGET REVIEW (30 minutes)

1. Numbers (5 min)
   - Total team spend vs budget
   - Per-developer spend vs budget
   - Month-over-month trend

2. Model Distribution (5 min)
   - Team-wide model split (target: 40% Haiku, 40% Sonnet, 20% Opus)
   - Identify anyone over 30% Opus usage
   - Discuss whether Opus usage was justified

3. Outliers (10 min)
   - Who spent the most? Why? (new feature? debugging session? inefficiency?)
   - Who spent the least? Are they underutilizing the tool?
   - Any single sessions that were unusually expensive?

4. Optimizations (5 min)
   - New commands or templates created this month
   - Tips shared in the team channel
   - Patterns to adopt or avoid

5. Next Month (5 min)
   - Budget adjustments needed?
   - Any planned large tasks that will spike costs?
   - New team members joining? (factor in onboarding costs)
```

### Budget Adjustment Triggers

Increase a developer's budget when:
- They are consistently hitting >90% and their usage is justified
- They are taking on a new project with higher complexity
- They are mentoring/pairing and using Claude Code in teaching sessions

Decrease a developer's budget when:
- They are consistently under 50% (the budget is not serving as a useful signal)
- They have moved to less Claude-intensive work
- Optimization improvements have structurally reduced their costs

### What Good Looks Like

After 3 months of active cost management, a well-optimized team should see:

| Metric | Month 1 | Month 3 | Target |
|--------|:-------:|:-------:|:------:|
| Average cost/developer | $80 | $45 | $35-60 |
| Model split (Haiku/Sonnet/Opus) | 20/50/30 | 40/40/20 | 40/40/20 |
| Average turns per task | 8 | 4 | 3-5 |
| Budget utilization | 110% | 75% | 60-85% |
| Developer satisfaction | "Expensive" | "Worth it" | "Essential" |

---

## Summary

| Strategy | Monthly Savings (team of 5) | Effort |
|----------|:---------------------------:|:------:|
| Per-developer budgets | $50-150 | Low |
| Model routing guidelines | $100-200 | Low |
| Shared command library | $30-70 | Medium (one-time) |
| Automated usage tracking | $30-80 | Medium (one-time) |
| Onboarding program | $50-100 | Medium (one-time) |
| Monthly budget reviews | $30-60 | Low (recurring) |
| **Combined** | **$290-660** | — |

The investment in team cost management pays for itself within the first month. After that, it is pure savings.

---

## Next Steps

- Set up per-developer budgets this week using the tier recommendations above
- Run the ROI calculation for your team to justify the tool to stakeholders
- Create a shared CLAUDE.md template and command library
- Schedule your first monthly budget review
- Read the [README Quick Start](../README.md#quick-start-5-minutes-no-skill-needed) section for individual-level optimizations that complement team-level management

---

*[Back to README](../README.md) | [Previous: Workflow Patterns](04-workflow-patterns.md)*
