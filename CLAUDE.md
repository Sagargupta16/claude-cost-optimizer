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
- `benchmarks/`, `templates/`, `cheatsheet.md` - Measurements, configs, quick reference; `benchmarks/METHOD.md` sets the rules for any measured number, and `benchmarks/cost-mode-eval/` is the cost-mode harness (built, not run)
- `tools/` - 8 CLI tools (usage-analyzer is retired and points to `claude-rate --usage --by session`); see [`tools/README.md`](tools/README.md)
- `hooks/` - budget-tracker (dollar caps), cost-logger and session-summary, wired up in `.claude/settings.json`; cache-guard, handoff-loader and output-trim are opt-in through `hooks/settings-example.json`
- `site/` - React + Vite + TS site (calculator, badge checker, analyzer) on GitHub Pages
- `case-studies/` - Submission template only; no stories published yet
- `docs/pricing-data.md` - Pricing source of truth; `docs/pricing-reference.md` - the user-facing pricing tables and migration notes (moved out of the README)
- `docs/diagrams/` - The README's two orrery figures, each a spec plus the light/dark SVGs rendered from it: `toolkit.yaml` (where each tool runs; re-render after adding or moving a tool) and `build.yaml` (pricing source, rate copies, distribution, CI checks; re-render after changing any of those)
- `scripts/` - Consistency checks run by CI (`check-rate-values.py` compares every code copy of the rates against `rate.py`; `eval-output-filter.py` replays the output-trim fixtures), `check-live-pricing.py` (the weekly drift alarm), `measure-compact-flags.py` (the table in `benchmarks/search-ladder.md`), plus `capture-screenshots.py` for the README images and the social preview
- Tests: `site/src/utils/*.test.ts` (vitest, `npm test`, incl. `repoAnalyzer.test.ts`), `tools/claude-rate/tests/` (6 unittest files), `scripts/tests/` (unittest), `tools/mcp-cost-server/test/` (node:test over stdio)

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
rate or model list. It is separate because this file loads in full every session, so a smaller
one costs fewer tokens and is followed better (Anthropic's guidance: under 200 lines).

Verified **2026-10-09**. The facts most often got wrong:

- **Opus 5.5 ($4/$20) is the current Opus flagship**; Opus 5 ($5/$25) is legacy.
- **Sonnet 5.5 ($2/$10) is the current Sonnet flagship.** Sonnet 5 (legacy) has the same $2/$10,
  permanently (the rise to $3/$15 was cancelled), but Sonnet 5.5's cache read is half: $0.10 vs $0.20.
- **Haiku 5.5 is priced by prompt length**: $0.10/$0.50 up to 100,000 prompt tokens (cache reads
  and writes count), $0.50/$2.50 above, on the whole request. Never quote one Haiku 5.5 rate.
- **Cache hit has three multipliers: 0.1x base input, except Fable 5.1 and Mythos 5.1 (0.025x)
  and Opus 5.5 and Sonnet 5.5 (0.05x).** Never derive a cache rate as `input * 0.1`; read the per-model rate.
- **Session estimates are cache-aware.** The calculator, repo analyzer, claude-rate and the MCP server
  bill each turn the way Claude Code caches: the previous request is a cache read, only the new part a
  5-minute write (1.25x); turn 1 writes everything. Never reintroduce a flat "70% cache hit" rate.
- **The 4.7+ tokenizer makes about 30% more tokens** (pricing page); every such model uses 1.3.
  Sonnet 4.6 and earlier use the old tokenizer. Opus 4.5 cut $15/$75 to $5/$25, so Opus 5.5 is not
  the first Opus price cut.
- **No vague ranges.** Every saving is a sourced or computed number with its source or formula.
- **Plan names (2026-11-01)**: Free, Pro, Max ($100, was "Max 5x"), Ultra ($200, was "Max 20x"; 10x Pro
  weekly, no 5-hour limit when verified), Team, Enterprise. "Extra usage" is now "usage credits".
- **Google Cloud names**: Anthropic's docs say "Claude Models on Google Cloud (Google managed)" for what
  was Vertex AI, plus "(Anthropic managed)" since 2026-10-22. Keep env var names like `CLAUDE_CODE_USE_VERTEX`.
- **Hooks**: `Stop` fires every turn, `SessionEnd` once; a message for the user goes in `systemMessage`.
- **Drift alarm**: the weekly `pricing-drift.yml` runs `scripts/check-live-pricing.py` and opens or updates a
  "Live pricing drift" issue when `rate.py` and the live pricing page differ.

After a rate change, update every file listed at the end of that doc, then run
`python scripts/check-pricing-sync.py` and `python scripts/check-rate-values.py`. CI runs both on every PR.

