# CLAUDE.md - claude-cost-optimizer

## Purpose

This repo is an installable Claude Code skill and a documentation/tooling project for reducing Claude Code costs. Install: `npx skills add Sagargupta16/claude-cost-optimizer`.

## File Structure

- `skills/cost-mode/` - Installable Claude Code skill (SKILL.md is single source of truth)
- `plugins/cost-mode/` - Plugin distribution copy with .codex-plugin metadata
- `.claude-plugin/` - Plugin identity and marketplace registration
- `.agents/plugins/` - Agent registry
- `guides/` - Deep-dive optimization guides (00-10 + visual diagrams)
- `benchmarks/` - Real-world cost measurement data and community leaderboard
- `templates/` - Copy-paste CLAUDE.md configs (10 stacks), settings, and commands
- `tools/` - 7 CLI tools (token-estimator, usage-analyzer, badge-generator, mcp-cost-server, vscode-extension, optimize-command, GitHub Action)
- `hooks/` - Claude Code hooks for budget enforcement and cost logging
- `site/` - React + Vite + TypeScript site (calculator, badge checker, repo analyzer) for GitHub Pages
- `case-studies/` - Community optimization stories
- `docs/` - Awesome-list submission prep
- `cheatsheet.md` - One-page quick reference

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

Update pricing references across ALL files (README, guides/01-09, cheatsheet, benchmarks, site/src/utils/pricing.ts, tools/*/estimate.py) when rates change.
