# Changelog

## [1.3.0] - 2026-04-06

### Added
- **Installable cost-mode skill**: `npx skills add Sagargupta16/claude-cost-optimizer` then `/cost-mode`
- Plugin structure (.claude-plugin/, plugins/, skills/, .agents/) for Claude Code marketplace
- Three intensity levels for cost-mode: lite (20-40%), standard (40-60%), strict (60-70%)
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
