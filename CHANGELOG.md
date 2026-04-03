# Changelog

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
