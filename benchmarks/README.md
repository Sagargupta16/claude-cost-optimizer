# Benchmarks

> Estimated cost data for Claude Code development tasks, measured across real usage patterns.

## How to Read These Benchmarks

Each benchmark file compares costs along a specific dimension: task type, model choice, or context size. Every table entry includes:

- **Input tokens** — tokens sent to Claude (system prompt + CLAUDE.md + conversation history + file contents + tool results). You pay for these every turn.
- **Output tokens** — tokens Claude generates (responses, tool calls, code). These cost 5x more per token than input.
- **Estimated cost** — calculated from the token counts using published pricing (see below).
- **Quality notes** — subjective assessment of output correctness, completeness, and adherence to project conventions.

### Pricing Reference

All cost calculations use the following rates (April 2026):

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Cache Hit (per 1M tokens) |
|-------|:---------------------:|:----------------------:|:-------------------------:|
| Opus 4.7 (current) | $5.00 | $25.00 | $0.50 |
| Opus 4.6 (legacy) | $5.00 | $25.00 | $0.50 |
| Sonnet 4.6 | $3.00 | $15.00 | $0.30 |
| Haiku 4.5 | $1.00 | $5.00 | $0.10 |

Batch API pricing is 50% off the standard rates above. Opus 4.7's new tokenizer can use up to 35% more tokens for the same text, so expect ~20-35% higher absolute costs vs Opus 4.6 for identical workloads.

### What "Estimated" Means

These benchmarks are **estimates based on real usage patterns**, not deterministic measurements. Every Claude Code session varies depending on:

- Exact prompt wording and follow-up turns
- Size and complexity of the codebase being worked on
- Contents of CLAUDE.md and other context files
- Whether prompt caching is active (cached input tokens cost 90% less)
- Network conditions and retries

We report ranges where possible. The numbers are designed to show **relative differences** between approaches rather than exact dollar amounts you will see on your bill.

### Prompt Caching Effects

Claude Code automatically caches stable content (system prompt, CLAUDE.md, earlier conversation turns) between turns. This means:

- **First turn** of a session is always the most expensive because nothing is cached yet.
- **Subsequent turns** benefit from caching — input tokens for unchanged content cost ~90% less.
- The benchmarks below show **pre-cache** token counts (worst case). Your actual costs will often be lower due to caching, especially in longer sessions.
- Strategies that keep content stable between turns (like a well-structured CLAUDE.md) benefit more from caching than strategies that change context frequently.

---

## Methodology

### How Benchmarks Were Collected

1. **Task definition** — Each benchmark scenario starts with a clearly described development task (e.g., "Add a React button component with tests").
2. **Environment setup** — A representative codebase is used (React + TypeScript for frontend tasks, Node.js for backend tasks, Python for ML tasks).
3. **Controlled runs** — The task is performed multiple times with different configurations (e.g., with/without CLAUDE.md optimization, with different models) to isolate the variable being measured.
4. **Token counting** — Input and output tokens are recorded from Claude Code's `/usage` output or the API response metadata.
5. **Cost calculation** — Total cost = (input_tokens / 1M * input_rate) + (output_tokens / 1M * output_rate).
6. **Quality assessment** — Output is reviewed for correctness, completeness, style adherence, and whether follow-up turns were needed to fix issues.

### Assumptions

- **Session length**: Unless otherwise stated, benchmarks assume a single-task session (Claude Code launched, task completed, session ended).
- **CLAUDE.md size**: The "optimized" baseline uses the Standard template (~100 lines, ~700 tokens). The "unoptimized" baseline uses a bloated CLAUDE.md (~300 lines, ~2,100 tokens).
- **Codebase size**: A medium-sized project (~50 files, ~15,000 lines of code) unless noted otherwise.
- **Turns**: A "turn" is one user message + one Claude response (which may include multiple tool calls).

### Limitations

- Results vary across codebases, prompt styles, and Claude model versions.
- Token counts can shift as Anthropic updates models and Claude Code internals.
- Quality ratings are subjective — your team's standards may differ.
- Prompt caching makes real-world costs lower than raw token counts suggest, but caching behavior is not fully deterministic.

---

## Benchmark Files

| File | Question Answered |
|------|-------------------|
| [Task Comparison](task-comparison.md) | How much do I save by applying optimization strategies to common tasks? |
| [Model Comparison](model-comparison.md) | Which model gives the best cost-to-quality ratio for each task type? |
| [Context Size Impact](context-size-impact.md) | How much does CLAUDE.md size and file reading affect my costs over a session? |

---

## Contributing Your Own Benchmarks

We welcome community benchmark submissions. Your real-world data makes these estimates more accurate.

### How to Contribute

1. **Pick a scenario** — either reproduce an existing benchmark or define a new one.
2. **Record your data** — run the task and capture:
   - Token counts (use `/usage` in Claude Code or check the API response)
   - Model used
   - CLAUDE.md size (line count and approximate token count)
   - Number of turns to complete the task
   - Brief quality assessment
3. **Submit a PR or issue** — use the [Benchmark Result](../.github/ISSUE_TEMPLATE/benchmark-result.md) issue template, or open a PR adding your data to the relevant benchmark file.

### Benchmark Submission Format

When submitting results, please include:

```markdown
### [Your Scenario Name]

**Environment:**
- Model: [Opus 4.7 / Opus 4.6 / Sonnet 4.6 / Haiku 4.5]
- CLAUDE.md: [line count] lines (~[token count] tokens)
- Codebase: [language/framework], [approximate size]
- Date: [YYYY-MM-DD]

**Results:**
| Metric | Value |
|--------|-------|
| Turns to complete | X |
| Input tokens (total) | X,XXX |
| Output tokens (total) | X,XXX |
| Estimated cost | $X.XX |
| Quality (1-5) | X |

**Notes:**
[Any observations about the run — retries needed, quality issues, caching effects, etc.]
```

### Guidelines for Good Benchmarks

- **Be specific** — "Add a React form with validation" is better than "build a feature."
- **Report failures** — if the task required retries or manual correction, note that. Failed attempts are still valuable data.
- **Include your CLAUDE.md** — or at least its line count and a summary of its sections. This is a major variable.
- **Run multiple times if possible** — variance between runs helps calibrate estimates.
- **Note your Claude Code version** — found via `claude --version`. Model behavior can change between releases.

---

## Interpreting the Numbers

### Cost Estimates Are Directional

The primary value of these benchmarks is **relative comparison**, not absolute cost prediction. If benchmark A costs $0.12 and benchmark B costs $0.04, the takeaway is that B's approach is roughly 3x cheaper — not that you will pay exactly $0.12 or $0.04.

### When to Optimize

Not every session needs optimization. Use these benchmarks to identify your highest-impact changes:

- If you run 50+ turns per session, **context size optimization** has the biggest payoff.
- If you use Opus for everything, **model selection** is your biggest lever.
- If you frequently do simple tasks (renames, formatting, small fixes), **switching to Haiku** for those tasks alone can cut monthly costs by 20-40%.

### Cost vs. Quality Tradeoffs

Some optimizations reduce cost at the expense of quality or developer experience. The benchmarks note these tradeoffs explicitly. For example:

- Haiku is 5x cheaper than Opus but struggles with complex architectural reasoning.
- A minimal CLAUDE.md saves tokens but may require more follow-up turns to correct style violations.
- Subagent delegation reduces main context bloat but adds overhead for simple tasks.

Choose the combination that fits your budget and quality bar.
