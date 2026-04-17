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

Current Claude API pricing (April 2026):

- **Opus 4.7** (current flagship): $5/$25 per 1M input/output. 1M context. 128K max output. Cache hit $0.50. Adaptive thinking. **New tokenizer** may use up to 35% more tokens than prior models.
- **Opus 4.6** (legacy per Anthropic docs): $5/$25. 1M context. 128K max output. Cache hit $0.50. Only model supporting **Fast Mode** (6x = $30/$150 research preview).
- **Sonnet 4.6**: $3/$15. 1M context. 64K max output. Cache hit $0.30.
- **Haiku 4.5**: $1/$5. 200K context. 64K max output. Cache hit $0.10.

**Important pricing corrections vs earlier docs**:
- 1M context on Opus 4.7, Opus 4.6, and Sonnet 4.6 is at **standard rates** -- no long-context premium. (Earlier "2x input, 1.5x output over 200K" is obsolete.)
- Batch API: 50% discount. Cache writes: 1.25x (5-min), 2x (1-hour).
- Regional endpoints (Bedrock/Vertex) on Sonnet 4.5+ and Haiku 4.5+: +10%. Data residency (`inference_geo: us-only`) on Opus 4.7+: +10%.

**Bedrock model IDs**: Opus 4.7 = `us.anthropic.claude-opus-4-7` (cross-region inference; currently research preview). Opus 4.6 = `us.anthropic.claude-opus-4-6-v1`.

Update pricing references across ALL files (README, guides/00-10, cheatsheet, benchmarks, site/src/utils/pricing.ts, tools/*/estimate.py) when rates change.
