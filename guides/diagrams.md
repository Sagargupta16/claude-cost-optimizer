# Visual Optimization Diagrams

Mermaid flowcharts for key cost optimization decisions. These render natively on GitHub.

---

## Table of Contents

- [Model Selection Decision Tree](#model-selection-decision-tree)
- [Session Cost Optimization Flowchart](#session-cost-optimization-flowchart)
- [Cost Tier Strategy Map](#cost-tier-strategy-map)

---

## Model Selection Decision Tree

Use this to pick the right model before starting a task. Starting with Sonnet is always a safe default.

```mermaid
flowchart TD
    A[What type of task?] --> B{Complex architecture,\ndebugging, or\nmulti-file refactor?}
    B -- Yes --> C[Use Opus 4.6\n$5/$25 per 1M tokens]
    B -- No --> D{Standard feature work,\ncode review, or\nwriting tests?}
    D -- Yes --> E[Use Sonnet 4.6\n$3/$15 per 1M tokens]
    D -- No --> F{Simple fix, formatting,\nboilerplate, or\nfile lookup?}
    F -- Yes --> G[Use Haiku 4.5\n$1/$5 per 1M tokens]
    F -- No --> H[Not sure?\nStart with Sonnet 4.6]

    style C fill:#f4e0d0,stroke:#c97a4a
    style E fill:#d0e8f4,stroke:#4a8ac9
    style G fill:#d0f4d5,stroke:#4ac96a
    style H fill:#d0e8f4,stroke:#4a8ac9
```

### Quick Reference

| Complexity | Model | Cost (Input/Output per 1M) | Examples |
|------------|-------|:--------------------------:|----------|
| High | Opus 4.6 | $5 / $25 | Architecture design, complex debugging, large refactors |
| Medium | Sonnet 4.6 | $3 / $15 | Feature implementation, code review, test writing |
| Low | Haiku 4.5 | $1 / $5 | Formatting, renaming, boilerplate, lookups |

---

## Session Cost Optimization Flowchart

Follow this checklist at the start of every Claude Code session to minimize waste.

```mermaid
flowchart LR
    A[Start Session] --> B{CLAUDE.md\n> 150 lines?}
    B -- Yes --> C[Trim CLAUDE.md\nto under 150 lines]
    C --> D
    B -- No --> D{.claudeignore\nexists?}
    D -- No --> E[Create .claudeignore\nExclude node_modules,\ndist, lock files]
    E --> F
    D -- Yes --> F[Choose model\nbased on task]
    F --> G{Task is\ncomplex?}
    G -- Yes --> H[Use Plan Mode\nbefore coding]
    H --> I
    G -- No --> I[Work on task]
    I --> J[Monitor with /usage]
    J --> K{Context\ngetting large?}
    K -- Yes --> L[Run /compact]
    L --> M
    K -- No --> M{Starting a\nnew task?}
    M -- Yes --> N[Start fresh session\nto reset context]
    M -- No --> J
```

### Key Checkpoints

1. **CLAUDE.md size** -- Every line loads on every turn. Keep it under 150 lines to avoid recurring token waste.
2. **.claudeignore** -- Prevents Claude from reading large generated or vendored files.
3. **Model selection** -- Match model to task complexity (see decision tree above).
4. **Plan Mode** -- For complex tasks, plan first to avoid expensive iterative dead ends.
5. **/compact** -- Summarizes conversation history to reduce context size mid-session.
6. **Fresh sessions** -- New tasks should get new sessions. Stale context from prior tasks is pure waste.

---

## Cost Tier Strategy Map

Which strategies matter most depends on your monthly spend. Focus on high-impact changes first.

```mermaid
flowchart TD
    A[Monthly Claude Code Spend] --> B{Less than\n$50/month?}
    B -- Yes --> C[Tier 1: Basics]
    B -- No --> D{$50 to\n$200/month?}
    D -- Yes --> E[Tier 2: Intermediate]
    D -- No --> F[Tier 3: Full Optimization]

    C --> C1[Select models by task complexity]
    C --> C2[Trim CLAUDE.md to under 150 lines]
    C --> C3[Use /compact when context grows]

    E --> E1[Everything in Tier 1]
    E --> E2[Add .claudeignore for all projects]
    E --> E3[Delegate to subagents for searches]
    E --> E4[Build /compact and Plan Mode habits]

    F --> F1[Everything in Tiers 1 and 2]
    F --> F2[Set per-developer budgets]
    F --> F3[Run usage analyzer weekly]
    F --> F4[Use token estimator before large prompts]
    F --> F5[Evaluate API/Batch for bulk workloads]

    style C fill:#d0f4d5,stroke:#4ac96a
    style E fill:#f4ead0,stroke:#c9a84a
    style F fill:#f4d0d0,stroke:#c94a4a
```

### Strategy Summary by Tier

| Tier | Monthly Spend | Focus Areas | Expected Savings |
|------|:------------:|-------------|:----------------:|
| 1 - Basics | < $50 | Model selection, CLAUDE.md trimming, /compact | 15-30% |
| 2 - Intermediate | $50-200 | Add .claudeignore, subagents, Plan Mode habits | 30-45% |
| 3 - Full Optimization | > $200 | Team budgets, usage analyzer, token estimator, Batch API | 40-60% |

---

## Related Guides

- [Model Selection](03-model-selection.md) -- Detailed model comparison with cost-per-task data
- [Context Optimization](02-context-optimization.md) -- CLAUDE.md trimming and .claudeignore setup
- [Workflow Patterns](04-workflow-patterns.md) -- Plan Mode, subagents, and /compact usage
- [Team Budgeting](05-team-budgeting.md) -- Per-developer budgets and ROI tracking
