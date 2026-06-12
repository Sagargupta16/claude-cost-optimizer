# Changelog

## [1.9.0] - 2026-06-12

### Added
- **Claude Fable 5 support** (`claude-fable-5`) across all pricing tables, guides, tools, and the web calculator. Fable 5 is Anthropic's most capable widely released model -- a new Mythos-class tier above Opus at **$10/$50 per 1M input/output (2x Opus 4.8)**. 1M context at standard rates, 128K max output, cache hit $1, 5m-write $12.50, 1h-write $20, Batch $5/$25. Always-on adaptive thinking (`thinking: disabled` not supported; depth via `effort`). Safety classifiers can decline requests: HTTP 200 + `stop_reason: "refusal"`, pre-output refusals unbilled, beta `fallbacks` param + fallback credit for retries. No Fast Mode. Requires 30-day data retention. GA 2026-06-09 on Claude API, Claude Platform on AWS, Bedrock (`anthropic.claude-fable-5`), Vertex AI, and Microsoft Foundry.
- **Claude Mythos 5 entry** (`claude-mythos-5`): same specs and pricing as Fable 5 but without the safety classifiers; limited availability to approved Project Glasswing customers. Successor to Mythos Preview. Flagged `inviteOnly` in the site registry (reference tables only, hidden from calculator selection).
- `fable` model alias in token-estimator, usage-analyzer, mcp-cost-server (tool enums + compare output), VS Code extension, and claude-rate cost projections.
- Fable 5 routing guidance: cheatsheet decision tree, guide 03 quick-reference card, guide 10 "Tier 2+" block, cost-mode skill model-routing table (downshift suggestion when running routine work on Fable 5), calculator and usage-analyzer recommendations for Fable-heavy usage.

### Changed
- **Mythos Preview marked retiring 2026-06-30** (announced with the Mythos 5 launch) -- lifecycle flipped to `legacy`, pricing rows annotated, retirement tables updated across README, cheatsheet, and CLAUDE.md. The token-estimator `mythos` alias now prices Mythos 5 ($10/$50) instead of Mythos Preview ($25/$125).
- Opus 4.8 repositioned from "most capable model" to "Opus-tier flagship" in copy across README, cheatsheet, guides, and the site registry; "most capable" now refers to Fable 5.
- usage-analyzer model detection extended: recognizes `fable`/`mythos` and distinguishes `opus-4.7` / `opus-4.6` from the `opus` alias; the Opus-share hotspot check now matches all Opus variants.
- All pricing references re-verified against Anthropic docs on 2026-06-12; "verified" dates bumped from 2026-06-06.
- Plugin-identity versions bumped to 1.9.0; plugin distribution copy of the cost-mode skill re-synced.

## [1.8.0] - 2026-06-06

### Added
- **Claude Opus 4.8 support** (`claude-opus-4-8`) across all pricing tables, guides, tools, and the web calculator. Opus 4.8 is Anthropic's new flagship and most capable model at $5/$25 per 1M input/output (same posted price as Opus 4.7 / 4.6). 1M context at standard rates (200K on Microsoft Foundry), 128K max output, adaptive thinking only, `effort` defaults to `high` on all surfaces, knowledge cutoff Jan 2026. Earliest retirement 2027-05-28. Bedrock ID `anthropic.claude-opus-4-8`.
- **Per-model Fast Mode pricing.** Promoted the single `FAST_MODE_MULTIPLIER` constant to a per-model `fastModeMultiplier` field on `ModelPricing` (site) and per-model entries in the standalone tool tables. Opus 4.8 Fast Mode is **2x** ($10/$50); Opus 4.7 / 4.6 remain **6x** ($30/$150). Opus 4.6 Fast Mode is deprecated as of the 4.8 launch (removed ~30 days later, then falls back to standard speed). Opus 4.8 Fast Mode is Claude API + Managed Agents only.
- `opus-4-7` model entry in `site/src/utils/pricing.ts` and the standalone tool tables.

### Changed
- **Default `opus` alias now resolves to Opus 4.8** in the site calculator, MCP cost server, VS Code extension, token-estimator, usage-analyzer, and claude-rate. Opus 4.7 / 4.6 / 4.5 and Sonnet 4.5 are now flagged `legacy`.
- Renamed the site `ModelId` `opus-legacy` key to `opus-4-6` and added an explicit `opus-4-7` entry; the Fast Mode UI label and savings recommendation are now computed from the per-model multiplier instead of a hardcoded "6x / 83%".
- Per-model tool-use system-prompt overhead documented in CLAUDE.md (Opus 4.8 = 290/410, Opus 4.7 = 675/804, Opus 4.6 + Sonnet 4.6 = 497/589) -- replaces the stale flat "346 / 313 tokens".
- Batch API extended-output note added (up to 300K output on Opus 4.8/4.7/4.6 + Sonnet 4.6 via `output-300k-2026-03-24`).
- Opus 4.1 marked deprecated with a firm 2026-08-05 retirement date (announced 2026-06-05). Migration targets across README + cheatsheet updated to Opus 4.8.
- All pricing references re-verified against Anthropic docs on 2026-06-06; "verified" dates bumped from 2026-05-22.
- **Reconciled plugin-identity versions to 1.8.0.** `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, and `plugins/cost-mode/.codex-plugin/plugin.json` were stuck at 1.5.0 while the changelog had advanced to 1.7.0 -- bumped all three to match this release.

### Security
- **Updated `react-router-dom` to 7.17.0** in `site/` (was resolving to 7.14.0), clearing 3 Dependabot alerts: turbo-stream deserialization RCE (high), `__manifest` DoS (high), and protocol-relative open redirect (moderate).
- **Updated transitive `hono` to 4.12.23 and `qs` to 6.15.2** in `tools/mcp-cost-server/` (via `pnpm update`, both within existing semver ranges), clearing 5 Dependabot alerts: Set-Cookie injection, mount-prefix routing, IPv6 deny-rule bypass, JWT scheme acceptance (all moderate), and `qs.stringify` DoS (moderate). `npm audit` and `pnpm audit` both report 0 vulnerabilities.

## [1.7.0] - 2026-05-22

### Added
- **`claude-rate` CLI** at `tools/claude-rate/`. Local rater that scans a project directory and grades the Claude/AI setup across 7 categories (CLAUDE.md size discipline, .claudeignore coverage, settings.json model+budget+permissions, MCP server count, hooks, security/secrets hygiene, optimizer tooling). Returns 0-100 score, A+ to F letter grade, per-category breakdown with text bar charts, monthly-cost projection on every active model tier, copy-pasteable fix suggestions, and a shields.io badge URL.
  - **Three runners**: `npx -y @sagargupta16/claude-rate .`, `curl | sh` one-shot, persistent `curl | sh -- --install`. Plus direct `python rate.py`.
  - **Stdlib only** (Python 3.10+). No `pip install` needed for the rater itself.
  - **Flags**: `--fix` (copy-pasteable fix list), `--strict` (CI gate, exits 1 below grade B), `--json` (machine-readable output), `--version`.
  - **Why local?** Inspects things the deployed web analyzer can't see: real MCP server count from `.mcp.json`, hooks in settings.json, .claudeignore coverage gaps vs files actually on disk, accidentally-committed secrets (`sk-...`, `AKIA...`, `ghp_...`), missing `.env` entries in `.gitignore`, cost-mode skill installation status, custom slash command count.
  - Files: `tools/claude-rate/rate.py` (single-file Python CLI), `tools/claude-rate/bin/claude-rate.js` (npx shim that locates Python and forwards args), `tools/claude-rate/install.sh` (POSIX one-shot/persistent installer), `tools/claude-rate/package.json` (npm distribution metadata), `tools/claude-rate/README.md` (full docs with example output and CI snippet).
- **README "Rate your setup" section** -- new top-level entry point. Local `claude-rate` is the recommended path; web tools (analyzer, calculator, badge) remain available for browser-only / public-repo flows.
- **Legacy & Retired Models section** in README. Self-contained migration reference covering recently-retired models (Opus 3, Sonnet 3.7, Haiku 3 / 3.5, Sonnet 3.5 v1/v2, Sonnet 3, Claude 2.x, Claude 1.x, Instant 1.x), deprecated-soon models (Sonnet 4 / Opus 4 retiring 2026-06-15), still-callable older snapshots (Opus 4.5, Opus 4.1, Sonnet 4.5), and historical pricing patterns no longer in effect (the obsolete "2x over 200K" long-context premium, single-endpoint Bedrock, ARN-versioned-only model IDs). Cheatsheet got an expanded version of this in 1.6.0; this PR adds it to README too with last-known pricing for every retired tier.
- `tools/README.md` quick-reference table updated to lead with `claude-rate` as the recommended starting point.

## [1.5.0] - 2026-05-20

### Added
- Added repository-level `SECURITY.md` and `.github/pull_request_template.md` to align with community standard practices.

### Changed
- Resolved 3-way version drift across repository files, standardizing on version 1.5.0.

### Fixed
- Fixed uncommitted `CLAUDE.md` duplicate H1 header by merging headers and keeping the stacking blockquote intact.

## [1.4.0] - 2026-04-17

### Added
- **Claude Opus 4.7 support** across all tools, guides, pricing tables, and the web calculator. Opus 4.7 is Anthropic's current flagship (April 2026) at $5/$25 per 1M input/output -- same posted pricing as legacy Opus 4.6.
- **Claude Mythos Preview entry** in pricing tables, token-estimator, and the site's model registry. $25/$125 per MTok. Invite-only via [Project Glasswing](https://anthropic.com/glasswing) for defensive cybersecurity research. Added `inviteOnly` flag on ModelPricing so Mythos appears in reference tables but is filtered out of the calculator/analyzer selection UIs.
- `opus-legacy` model option in site/src/utils/pricing.ts (maps to Opus 4.6) to keep Fast Mode accessible for users who need it.
- `fastModeCapable` flag on ModelPricing type; calculator now scopes Fast Mode UI to the model that actually supports it (Opus 4.6) instead of hardcoding to `model === 'opus'`.
- Tokenizer overhead warning: Opus 4.7 introduced a new tokenizer that may use up to 35% more tokens for the same source text. Guides now recommend budgeting 20-35% higher for Opus 4.7 tasks vs Opus 4.6.
- Bedrock model ID reference table in guides/06 (includes `us.anthropic.claude-opus-4-7` cross-region profile + research-preview caveat).
- New Mermaid diagrams in guides/diagrams.md: "Claude Model Family (April 2026)" showing all GA + research-preview models with cost tiers, and "Pricing Modifier Stack" showing how cache/batch/regional/fast-mode multipliers compose.
- **Thinking modes table** in cheatsheet: clarifies Opus 4.7 uses adaptive thinking only (no extended thinking), Sonnet 4.6 supports both, Haiku 4.5 is extended-only.
- **Upcoming retirements table** in cheatsheet and README: Haiku 3 retires 2026-04-20 (corrected from April 19 in 1.6.0), Sonnet 4 / Opus 4 retire 2026-06-15.
- Published benchmark numbers (CyberGym, SWE-bench Verified/Pro, Terminal-Bench) in guides/03 comparing Opus 4.6 vs Mythos Preview.

### Changed
- **1M context pricing corrected**: Opus 4.7, Opus 4.6, and Sonnet 4.6 now bill the full 1M window at **standard per-token rates**. The earlier "2x input, 1.5x output over 200K" documentation was obsolete and applied only to Opus 4.1 and older. Removed the "Long Context Threshold Trap" anti-pattern section since it no longer applies.
- All pricing tables updated to April 2026 (was March 2026).
- `Max Output` column for Opus updated to 128K (was incorrectly listed as 32K).
- Default `opus` alias in the site calculator now refers to Opus 4.7; the calculator surface supports both.
- Regional endpoint +10% premium clarified to apply specifically to Sonnet 4.5+ and Haiku 4.5+ (global pricing structure changed with that generation).
- Data residency +10% multiplier clarified as `inference_geo: us-only` on Opus 4.7 and newer, not a blanket "Opus and above" rule.

### Fixed
- Token estimator Python CLI: removed obsolete `opus_4.6_1m` entry; added legacy `opus_4_6` explicitly.
- Cheatsheet: corrected max output per turn values and the historical Haiku-to-Opus cost ratio explanation.
- Benchmarks headers now include explicit "measured on Opus 4.6" note since Opus 4.7 benchmarks are not yet collected.
- **Comprehensive factual sweep**: updated every remaining "Opus 4.6" default-recommendation reference to "Opus 4.7" across guides/09-subscription-value.md (plan model lineup, allowance table, Batch API table), guides/08-prompt-caching.md (cache pricing table), guides/06-access-methods-pricing.md ("stay under 200K" tip rewritten for current standard-rate 1M context, March→April 2026 date), benchmarks/context-size-impact.md (file read budget table, context window reference), benchmarks/model-comparison.md (decision tree, recommendation labels), and benchmarks/leaderboard.md (pricing note).
- **Diagrams rewritten** (guides/diagrams.md): replaced `\n` line breaks with `<br/>` inside quoted labels (GitHub renders these correctly, `\n` showed as literal text), dropped inline `<b>` tags that GitHub's sanitizer strips, switched from inline `style` to `classDef` + `class` syntax, wrapped model groupings in `subgraph` blocks for proper boxed regions. All 5 diagrams validated via `@mermaid-js/mermaid-cli@11.12.0`.
- **Issue templates** (`.github/ISSUE_TEMPLATE/leaderboard-entry.md`, `case-study.md`): added Opus 4.7 option.
- **Case study template** (`case-studies/TEMPLATE.md`): added Opus 4.7 to example model list.
- **Context size benchmark**: corrected the "200K token context window" claim to reflect that Opus 4.7/4.6/Sonnet 4.6 are 1M and Haiku 4.5 is 200K.

## [1.3.0] - 2026-04-06

### Added
- **Installable cost-mode skill**: `npx skills add Sagargupta16/claude-cost-optimizer` then `/cost-mode`
- Plugin structure (.claude-plugin/, plugins/, skills/, .agents/) for Claude Code marketplace
- Three intensity levels for cost-mode: lite (20-40% output reduction), standard (40-60%), strict (60-70%)
- Guide 00: Getting Started in 5 Minutes -- zero to optimized in 5 steps
- Guide 10: Three-Tier Task Routing -- skip LLM for Tier 0, Haiku for Tier 1, Opus for Tier 2
- Repo Analyzer page -- paste a GitHub URL to get full cost audit, grade, and recommendations
- "Try it on our repo" prefilled demo on Analyzer page
- cost-logger.sh hook -- logs estimated tokens and cost per tool call
- Output Token Optimization section in cheatsheet (5 strategies + arXiv reference)
- Community Tools section in README referencing caveman project
- Before/after cost comparison example in README (61% savings)
- Star History chart in README with dark/light mode support
- SEO meta tags (Open Graph, Twitter Card, canonical URL, keywords)
- tools/README.md with quick reference table
- GitHub Discussions enabled on the repository

### Changed
- Repo transformed from docs-only to installable skill + docs
- README install command featured at the top
- Home page hero links to Repo Analyzer
- Repo Analyzer shows results for repos with no config files (was showing error)
- Cheatsheet links table updated with all new guides and tools
- CLAUDE.md updated with new file structure and skill directories
- Home page guide count updated to 10

## [1.2.0] - 2026-04-03

### Added
- Guide 08: Prompt Caching Deep Dive - cache mechanics, TTL economics, ROI math
- Guide 09: Maximizing Subscription Value - plan comparison, upgrade/downgrade signals
- Visual decision tree diagrams (Mermaid) for model selection, session optimization, cost tiers
- React site (Vite + React 19 + TypeScript) with cost calculator and badge checker for GitHub Pages
- MCP cost estimation server with estimate_cost, session_estimate, compare_models tools
- Claude Code budget enforcement hooks (budget-tracker, session-summary)
- Efficiency badge generator (A+ to F grading, shields.io badge output)
- VS Code extension for token count and cost estimation in status bar
- GitHub Action for automated cost auditing on PRs
- /optimize custom command for project cost-efficiency analysis
- Case studies directory with submission template and issue template
- Community benchmark leaderboard with seed data
- 5 new stack-specific CLAUDE.md templates: Go, Rust, Django, Rails, Java Spring Boot
- Leaderboard entry issue template
- Case study issue template
- Awesome-list submission preparation guide
- GitHub Pages deployment workflow (deploy-site.yml)
- Issue template config with quick-link cards

### Changed
- Simplified CONTRIBUTING.md with contribution ladder (Level 1-6) and "Your First PR in 5 Steps"
- Updated CLAUDE.md file size guidance with precise limits (4K chars/file, 12K total) based on community research
- Updated compaction docs with thresholds (10K tokens trigger, 4 messages preserved)
- Updated prompt caching guide with static/dynamic boundary explanation
- Updated hooks with correct JSON payload format and exit code semantics
- Updated cheatsheet with 7 new entries (character limits, compaction, output caps, token estimation)
- Cleaned up duplicate calculator files (replaced vanilla JS with React site)

## [1.1.0] - 2026-03-16

- Add regional pricing, PPP note, and cloud discount info
- Add off-peak 2x usage documentation
- Update 1M context from beta to native, add README badges

## [1.0.0] - 2026-03-08

- Add 1M context pricing, Fast Mode, and access methods guide
- Update all pricing to March 2026 (Opus 4.6, Haiku 4.5)
- Initial release: Claude Cost Optimizer
