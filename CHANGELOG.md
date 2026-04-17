# Changelog

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
- **Upcoming retirements table** in cheatsheet and README: Haiku 3 retires 2026-04-19, Sonnet 4 / Opus 4 retire 2026-06-15.
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
