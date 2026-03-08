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

Current Claude API pricing (2025): Opus $15/$75, Sonnet $3/$15, Haiku $0.80/$4 per 1M input/output tokens.

Update pricing references across all files when rates change.
