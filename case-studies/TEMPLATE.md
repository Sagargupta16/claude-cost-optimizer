# Case Study: [Your Title Here]

> One-sentence summary of the optimization and its result.

## Project Overview

| Attribute | Details |
|-----------|---------|
| **Project type** | <!-- e.g., SaaS web app, CLI tool, data pipeline, monorepo --> |
| **Tech stack** | <!-- e.g., React + TypeScript, FastAPI + Python, MERN --> |
| **Codebase size** | <!-- e.g., ~45K lines across 320 files --> |
| **Team size** | <!-- e.g., 3 developers using Claude Code --> |
| **Claude Code plan** | <!-- e.g., Max 5x ($100/mo) --> |
| **Primary model used** | <!-- e.g., Opus 4.6, Sonnet 4.6, Haiku 4.5 --> |
| **Duration of test** | <!-- e.g., 2 weeks before, 2 weeks after --> |

## Before Optimization

Describe how Claude Code was being used before any optimizations were applied.

### Baseline Metrics

| Metric | Value |
|--------|------:|
| Average session cost | $<!-- e.g., 2.40 --> |
| Average turns per session | <!-- e.g., 45 --> |
| Sessions per day | <!-- e.g., 6 --> |
| Estimated daily cost | $<!-- e.g., 14.40 --> |
| Estimated monthly cost | $<!-- e.g., 316.80 --> |
| CLAUDE.md line count | <!-- e.g., 280 --> |
| .claudeignore | <!-- YES / NO --> |
| MCP servers connected | <!-- e.g., 5 --> |

### Pain Points

<!-- Describe the cost-related problems you were experiencing. Examples:
- Hitting usage limits mid-afternoon
- High token counts from unnecessary file reads
- CLAUDE.md bloat causing repeated overhead
- Running Opus for tasks that Haiku could handle
-->

1. <!-- Pain point 1 -->
2. <!-- Pain point 2 -->
3. <!-- Pain point 3 -->

## What Changed

List every optimization you applied, in the order you applied them.

### Optimization 1: [Name]

<!-- Describe what you changed, why, and how. Include config snippets if relevant. -->

### Optimization 2: [Name]

<!-- Describe what you changed, why, and how. -->

### Optimization 3: [Name]

<!-- Describe what you changed, why, and how. -->

<!-- Add more sections as needed. -->

## After Optimization

### Updated Metrics

| Metric | Before | After | Change |
|--------|-------:|------:|:------:|
| Average session cost | $<!-- --> | $<!-- --> | <!-- e.g., -42% --> |
| Average turns per session | <!-- --> | <!-- --> | <!-- --> |
| Sessions per day | <!-- --> | <!-- --> | <!-- --> |
| Estimated daily cost | $<!-- --> | $<!-- --> | <!-- --> |
| Estimated monthly cost | $<!-- --> | $<!-- --> | <!-- --> |
| CLAUDE.md line count | <!-- --> | <!-- --> | <!-- --> |
| MCP servers connected | <!-- --> | <!-- --> | <!-- --> |
| Input tokens per turn (avg) | <!-- --> | <!-- --> | <!-- --> |
| Output quality (subjective) | <!-- e.g., Good --> | <!-- e.g., Same --> | <!-- --> |

### Token Breakdown (if available)

| Component | Before (tokens/turn) | After (tokens/turn) | Change |
|-----------|--------------------:|-------------------:|:------:|
| System prompt | <!-- --> | <!-- --> | <!-- --> |
| CLAUDE.md | <!-- --> | <!-- --> | <!-- --> |
| Conversation history | <!-- --> | <!-- --> | <!-- --> |
| File reads | <!-- --> | <!-- --> | <!-- --> |
| MCP server schemas | <!-- --> | <!-- --> | <!-- --> |
| Output | <!-- --> | <!-- --> | <!-- --> |

## Results Summary

| Metric | Value |
|--------|------:|
| **Total monthly savings** | $<!-- e.g., 158.40 --> |
| **Percentage reduction** | <!-- e.g., 50% --> |
| **Time to implement** | <!-- e.g., 2 hours --> |
| **Output quality impact** | <!-- e.g., No change / Slight improvement / Minor decrease --> |

## Lessons Learned

<!-- Share what you learned from this process. What would you tell someone starting the same optimization? -->

### What Worked Best

<!-- Which optimization had the highest impact? Why? -->

### What Didn't Work (or Wasn't Worth It)

<!-- Did you try anything that had minimal effect or caused problems? -->

### Advice for Others

<!-- What would you recommend to someone with a similar project? -->

---

*Submitted by: [your name or GitHub handle]*
*Date: [submission date]*
