# CLAUDE.md - claude-cost-optimizer

> This file stacks on top of the workspace root at `C:\Code\GitHub\`:
> - Root [`CLAUDE.md`](../../CLAUDE.md) -- voice, rules, routing map, references, skills, slash commands, conventions.
> - Root [`MEMORY.md`](../../MEMORY.md) -- live facts across repos.
> - Root [`STATUS.md`](../../STATUS.md) -- live PR/CI/security dashboard.
> - [`.claude/resources/`](../../.claude/resources/README.md) -- deep reference for collaboration, workflow, git, OSS, debugging, voice.
>
> Read those first. The guidance below only adds **repo-specific context** -- it does not override anything in the root.

## Purpose

This repo is an installable Claude Code skill and a documentation/tooling project for reducing Claude Code costs. Install: `npx skills add Sagargupta16/claude-cost-optimizer`.

## File Structure

- `skills/cost-mode/` - The installable skill; `SKILL.md` is the source of truth
- `plugins/`, `.claude-plugin/`, `.agents/plugins/` - Distribution copies and registries
- `guides/` - Deep-dive guides 00-11 + `diagrams.md`
- `benchmarks/`, `templates/`, `cheatsheet.md` - Measurements, configs, quick reference
- `tools/` - 8 CLI tools; see [`tools/README.md`](tools/README.md) for the list
- `hooks/` - Budget-enforcement and cost-logging hooks (wired up in `.claude/settings.json`)
- `site/` - React + Vite + TS site (calculator, badge checker, analyzer) on GitHub Pages
- `case-studies/` - Submission template only; no stories published yet
- `docs/pricing-data.md` - Pricing source of truth
- `scripts/` - Consistency checks run by CI

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

Rates, model IDs, context windows, cache behaviour, and retirement dates live in
[`docs/pricing-data.md`](docs/pricing-data.md) -- the source of truth. Read it before changing any
rate or model list. It is separate because inlining it made this file 14,224 chars, and anything
past 4,000 is truncated, so most of it never loaded.

Verified **2026-09-05**. The two facts most often got wrong:

- **Sonnet 5 is $2/$10 permanently.** The rise to $3/$15 on 2026-09-01 was cancelled.
- **Cache hit is 0.1x base input except on Fable 5.1 and Mythos 5.1, which read at 0.025x.**
  Never derive a cache rate as `input * 0.1`; read the per-model rate.

After a rate change, update every file listed at the end of that doc, then run
`python scripts/check-pricing-sync.py`. CI runs it on every PR.

