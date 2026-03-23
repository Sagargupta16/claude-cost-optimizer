# CLAUDE.md — claude-cost-optimizer

## Purpose

This repo is a documentation and tooling project for reducing Claude Code costs. It contains markdown guides, benchmarks, templates, and Python CLI tools.

## File Structure

- `guides/` — Deep-dive optimization guides (markdown)
- `benchmarks/` — Real-world cost measurement data (markdown)
- `templates/` — Copy-paste CLAUDE.md configs, settings, and commands
- `tools/token-estimator/` — Python CLI for estimating token counts and costs
- `tools/usage-analyzer/` — Python CLI for analyzing Claude session data
- `cheatsheet.md` — One-page quick reference

## Writing Conventions

- Use plain, direct language. Avoid filler and marketing speak.
- All cost claims must include expected savings percentages and evidence.
- Keep markdown files well-structured with clear headings.
- Tables are preferred over long prose for comparisons and data.
- Code examples should be copy-pasteable and tested.

## Python Tools

- Target Python 3.10+.
- Use only standard library plus tiktoken (for token-estimator).
- Include argparse, shebang lines, and docstrings.
- Handle errors gracefully with clear messages.

## Pricing Data

Current Claude API pricing (March 2026): Opus 4.6 $5/$25, Sonnet 4.6 $3/$15, Haiku 4.5 $1/$5 per 1M input/output tokens. Cache hit: Opus $0.50, Sonnet $0.30, Haiku $0.10. Batch API: 50% discount. Fast Mode: 6x standard rates. Long context (>200K input): 2x input, 1.5x output.

Context windows: Opus 4.6 = 1M, Sonnet 4.6 = 1M, Haiku 4.5 = 200K.

Update pricing references across ALL files (README, guides/01-06, cheatsheet, benchmarks) when rates change.
