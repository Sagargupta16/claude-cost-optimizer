---
name: Benchmark Result
about: Submit cost benchmark data for Claude Code usage
title: "[BENCHMARK] "
labels: benchmark, community
assignees: ''
---

## Task Description

<!-- What development task did you benchmark? Be specific.
(e.g., "Refactoring a 500-line Express.js API router into separate modules") -->

## Setup

<!-- Describe your environment and configuration: -->
- **Project type**: <!-- e.g., React + TypeScript, Python FastAPI, etc. -->
- **CLAUDE.md size**: <!-- approximate line count -->
- **Claude Code version**: <!-- if known -->
- **Plan**: <!-- Pro / Max / API -->
- **Operating system**: <!-- e.g., macOS, Linux, Windows -->
- **Other relevant config**: <!-- .claudeignore, custom commands, MCP servers, etc. -->

## Methodology

<!-- How did you conduct the benchmark?
- Did you run the same task multiple times?
- How did you measure tokens/cost?
- What did you control for? (same prompt, same codebase, etc.)
- Any tools used for measurement?
-->

## Results

<!-- Fill in or adapt this table. Add/remove rows and columns as needed. -->

| Metric | Baseline | Optimized | Change |
|--------|:--------:|:---------:|:------:|
| Total input tokens | | | |
| Total output tokens | | | |
| Number of turns | | | |
| Estimated cost | | | |
| Task completion time | | | |
| Quality of output | | | |

## Model Used

<!-- Check all that apply: -->
- [ ] Opus 4
- [ ] Sonnet 4
- [ ] Haiku 3.5
- [ ] Multiple (describe in observations)

## Observations

<!-- What did you learn? Include:
- What optimization(s) were you testing?
- Were there quality differences between baseline and optimized?
- Any surprises or unexpected results?
- Would you recommend this approach to others?
-->

## Raw Data

<!-- Optional: paste or link to raw session data, token logs, or screenshots.
If the data is large, consider linking to a gist or file. -->

## Reproducibility

<!-- Can others reproduce this benchmark? -->
- [ ] Fully reproducible (instructions and code provided)
- [ ] Partially reproducible (general approach described)
- [ ] Not easily reproducible (one-off observation)

## Additional Context

<!-- Anything else relevant: caveats, related benchmarks, follow-up plans, etc. -->
