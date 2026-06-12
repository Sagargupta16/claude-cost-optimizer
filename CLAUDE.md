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

Current Claude API pricing (verified 2026-06-12):

- **Fable 5** (most capable widely released model, `claude-fable-5`): **$10/$50 per 1M input/output** -- a new Mythos-class price tier, 2x Opus 4.8's rates. 1M context at standard rates. 128K max output. Cache hit $1, 5m-write $12.50, 1h-write $20. Batch $5/$25. Adaptive thinking is **always on** (`thinking: {type: "disabled"}` not supported; control depth with `effort`). Safety classifiers can decline requests: HTTP 200 with `stop_reason: "refusal"`; **pre-output refusals are not billed**; beta `fallbacks` param retries server-side, and fallback credit refunds the prompt-cache cost of switching models. **No Fast Mode.** Requires 30-day data retention (not available under zero data retention). Uses the 4.7 tokenizer (~30% more tokens than pre-4.7 models). GA 2026-06-09 on Claude API, Claude Platform on AWS, Bedrock (`anthropic.claude-fable-5`), Vertex AI, and Microsoft Foundry.
- **Mythos 5** (limited availability, Glasswing, `claude-mythos-5`): same specs and pricing as Fable 5 ($10/$50) but **without the safety classifiers**. Successor to Mythos Preview. Approved Project Glasswing customers only -- not GA.
- **Opus 4.8** (Opus-tier flagship, `claude-opus-4-8`): $5/$25 per 1M input/output. 1M context (200K on Microsoft Foundry). 128K max output. Cache hit $0.50, 5m-write $6.25, 1h-write $10. Adaptive thinking only; effort defaults to `high` on all surfaces. **Fast Mode supported (2x = $10/$50)**. **New tokenizer** may use up to 35% more tokens than pre-4.7 models. Knowledge cutoff Jan 2026. Earliest retirement 2027-05-28.
- **Opus 4.7** (legacy, `claude-opus-4-7`): $5/$25. 1M context. 128K max output. Cache hit $0.50, 5m-write $6.25, 1h-write $10. Adaptive thinking only. **Fast Mode supported (6x = $30/$150)**. New tokenizer. Earliest retirement 2027-04-16.
- **Opus 4.6** (legacy, `claude-opus-4-6`): $5/$25. 1M context. 128K max output. Cache hit $0.50, 5m-write $6.25, 1h-write $10. Extended + adaptive thinking. **Fast Mode deprecated** as of the 4.8 launch (removed ~30 days later, then falls back to standard speed). Earliest retirement 2027-02-05.
- **Opus 4.5** (legacy): $5/$25. 200K context. 64K max output. Cache hit $0.50. Extended thinking only. No Fast Mode. Earliest retirement 2026-11-24.
- **Opus 4.1** (deprecated): $15/$75. 200K context. 32K max output. Cache hit $1.50. Extended thinking only. Retires 2026-08-05.
- **Sonnet 4.6**: $3/$15. 1M context. 64K max output. Cache hit $0.30. Extended + adaptive thinking. Earliest retirement 2027-02-17.
- **Sonnet 4.5** (legacy): $3/$15. 200K context. 64K max output. Cache hit $0.30. Extended thinking. Earliest retirement 2026-09-29.
- **Haiku 4.5**: $1/$5. 200K context. 64K max output. Cache hit $0.10. Extended thinking. Earliest retirement 2026-10-15.
- **Mythos Preview** (invite-only, Glasswing, `claude-mythos-preview`): $25/$125. 1M context. Cache hit $2.50. **Retires 2026-06-30** -- migrate to Mythos 5.

**Important pricing facts**:
- 1M context on Fable 5, Mythos 5, Opus 4.8, Opus 4.7, Opus 4.6, and Sonnet 4.6 is at **standard rates** -- no long-context premium. Opus 4.5, Sonnet 4.5, Opus 4.1, and Haiku 4.5 are 200K-only.
- Batch API: 50% discount on both input AND output. Cache writes: 1.25x base input (5-min), 2x base input (1-hour). Cache hit = 0.1x base input. Batch supports up to **300K output** on Opus 4.8/4.7/4.6 + Sonnet 4.6 via `output-300k-2026-03-24` beta header.
- Regional endpoints (Bedrock/Vertex/Claude API `inference_geo: "us"`) on Sonnet 4.5+, Haiku 4.5+, Opus 4.5+, and all later models: +10%.
- **Fast Mode (research preview)**: Opus 4.8, Opus 4.7, Opus 4.6 only. **Per-model premium: Opus 4.8 = 2x ($10/$50); Opus 4.7 + 4.6 = 6x ($30/$150)** (4.6 Fast Mode deprecated). Up to 2.5x OTPS (output tokens/sec, not TTFT). NOT compatible with Batch, Priority Tier, or Claude Platform on AWS. Opus 4.8 Fast Mode is Claude API + Managed Agents only (no Bedrock/Vertex/Foundry). Header `anthropic-beta: fast-mode-2026-02-01`, `speed: "fast"`. Switching speeds invalidates the prompt cache.
- **Server-side tools**: Web search $10/1k searches + tokens. Web fetch free + tokens. Code execution free w/ web search-or-fetch; else 1,550 free hr/org/month + $0.05/hr/container. Bash +245 tokens. Text editor +700 tokens. Computer use +735 tokens + 466-499 system prompt tokens.
- **Tool-use overhead** (per-model system-prompt tokens): Opus 4.8 = 290 (`auto`/`none`) / 410 (`any`/`tool`). Opus 4.7 = 675 / 804. Opus 4.6 + Sonnet 4.6 = 497 / 589. Plus the `tools` schema, `tool_use`, and `tool_result` block tokens.
- **Claude Managed Agents**: standard token rates + **$0.08/session-hour** of `running` time. Replaces Code Execution container-hour billing.

**Bedrock**: Fable 5 GA via Claude in Amazon Bedrock (Messages-API endpoint), model ID `anthropic.claude-fable-5` (legacy InvokeModel/Converse path: `global.anthropic.claude-fable-5` -- the `us.` CRIS profile does not exist for Fable 5). Opus 4.8 GA, model ID `anthropic.claude-opus-4-8`. Opus 4.7 = `anthropic.claude-opus-4-7`. Opus 4.6 = `anthropic.claude-opus-4-6` (Mantle) or `anthropic.claude-opus-4-6-v1` (legacy). Legacy InvokeModel/Converse path uses cross-region `us.anthropic.claude-opus-4-*` IDs for backward compat.

**Subscriptions**: Pro $20/mo or **$200/yr (~$16.67/mo, 17% off)**. Max 5x $100/mo. Max 20x $200/mo.

**Recently retired** (will fail): Haiku 3 (`claude-3-haiku-20240307`) retired 2026-04-20. Haiku 3.5 (`claude-3-5-haiku-20241022`) retired 2026-02-19 (still on Bedrock + Vertex AI). Sonnet 3.7 (`claude-3-7-sonnet-20250219`) retired 2026-02-19. Opus 3 (`claude-3-opus-20240229`) retired 2026-01-05.

**Upcoming retirement**: Sonnet 4 (`claude-sonnet-4-20250514`) and Opus 4 (`claude-opus-4-20250514`) retire **2026-06-15**. Mythos Preview (`claude-mythos-preview`) retires **2026-06-30** (migrate to Mythos 5). Opus 4.1 (`claude-opus-4-1-20250805`) retires 2026-08-05.

Update pricing references across ALL files (README, guides/00-10, cheatsheet, benchmarks, site/src/utils/pricing.ts, tools/*/estimate.py) when rates change.