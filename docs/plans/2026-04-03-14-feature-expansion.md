# 14-Feature Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform claude-cost-optimizer from a documentation-only repo into a complete cost optimization toolkit with interactive tools, automation, community features, and ecosystem integrations.

**Architecture:** Each of the 14 features is independent and can be built in parallel. Documentation tasks (guides, templates) are pure markdown. Tool tasks (hooks, calculator, badge generator) are standalone scripts. Project tasks (MCP server, VS Code extension) are self-contained packages in their own directories.

**Tech Stack:** Markdown, HTML/CSS/JS (calculator), Python 3.10+ (tools), Node.js/TypeScript (MCP server, VS Code extension), GitHub Actions YAML, Claude Code hooks (JSON config + shell scripts).

---

## Task 1: Claude Code Budget Hooks

**Files:**
- Create: `hooks/budget-tracker.sh`
- Create: `hooks/session-summary.sh`
- Create: `hooks/README.md`
- Create: `hooks/settings-example.json`

Provide working, copy-paste Claude Code hook configurations that enforce budget limits and track costs. Hooks use Claude Code's native hook system (configured in `~/.claude/settings.json` or `.claude/settings.json`).

---

## Task 2: Interactive HTML Cost Calculator

**Files:**
- Create: `docs/calculator/index.html`
- Create: `docs/calculator/style.css`
- Create: `docs/calculator/calculator.js`

Single-page app deployable via GitHub Pages. Inputs: model, avg turns/session, CLAUDE.md line count, sessions/day, MCP server count. Outputs: current monthly cost, optimized monthly cost, savings breakdown. Uses current March 2026 pricing from CLAUDE.md.

---

## Task 3: Awesome-List Submission Preparation

**Files:**
- Create: `docs/awesome-list-submissions.md`

Prepare ready-to-submit descriptions for awesome-claude-code, awesome-claude-skills, and everything-claude-code. Include the exact markdown line to add and which section it belongs in. User submits the PRs manually.

---

## Task 4: Mermaid Decision Tree Diagrams

**Files:**
- Modify: `guides/03-model-selection.md` (add Mermaid diagram)
- Modify: `cheatsheet.md` (add Mermaid diagram)
- Create: `guides/diagrams.md` (optimization strategy flowchart)

Convert the text-based decision trees into rendered Mermaid diagrams that display on GitHub.

---

## Task 5: MCP Server for Cost Estimation

**Files:**
- Create: `tools/mcp-cost-server/package.json`
- Create: `tools/mcp-cost-server/tsconfig.json`
- Create: `tools/mcp-cost-server/src/index.ts`
- Create: `tools/mcp-cost-server/README.md`

A lightweight MCP server providing two tools: `estimate_tokens` (estimate token count and cost for text) and `session_cost` (estimate current session spend based on turn count and model). Uses `@modelcontextprotocol/sdk`.

---

## Task 6: Claude Code /optimize Skill

**Files:**
- Create: `tools/optimize-command/optimize.md`
- Create: `tools/optimize-command/README.md`

A Claude Code custom command (`.claude/commands/optimize.md`) that analyzes a project's CLAUDE.md size, .claudeignore presence, settings config, and MCP server count, then recommends specific cost-saving changes.

---

## Task 7: Guide 08 - Prompt Caching Deep Dive

**Files:**
- Create: `guides/08-prompt-caching.md`

Covers: how Claude's prompt caching works, cache breakpoints, TTL (5-min vs 1-hour), cache invalidation triggers, multi-turn cache behavior, what breaks the cache, ROI math (breakeven after N cache hits), and advanced patterns for maximizing cache hit rates.

---

## Task 8: Case Studies Directory + Templates

**Files:**
- Create: `case-studies/README.md`
- Create: `case-studies/TEMPLATE.md`
- Create: `.github/ISSUE_TEMPLATE/case-study.md`

A community-driven directory for real optimization stories. Issue template for submissions, markdown template for write-ups. Format: project type, before/after metrics, what changed, lessons learned.

---

## Task 9: Efficiency Badge Generator

**Files:**
- Create: `tools/badge-generator/generate.py`
- Create: `tools/badge-generator/README.md`

Python CLI that analyzes a project directory and generates a cost-efficiency grade (A+ to F) based on: CLAUDE.md line count, .claudeignore presence/quality, settings.json config, MCP server count. Outputs a shields.io badge URL and markdown snippet.

---

## Task 10: GitHub Action for Cost Tracking

**Files:**
- Create: `.github/workflows/cost-audit.yml`
- Create: `tools/actions/claude-cost-audit/action.yml`
- Create: `tools/actions/claude-cost-audit/audit.py`

A reusable GitHub Action that checks CLAUDE.md size, .claudeignore quality, and settings config in a PR, then comments with a cost impact summary. Also includes a scheduled pricing freshness checker.

---

## Task 11: Guide 09 - Maximizing Subscription Value

**Files:**
- Create: `guides/09-subscription-value.md`

Covers: Pro ($20/mo) vs Max 5x ($100/mo) vs Max 20x ($200/mo) value analysis, usage patterns for each tier, when to upgrade/downgrade, how to estimate which plan fits, getting maximum value from included usage, off-peak strategies, and when API billing makes more sense.

---

## Task 12: Community Benchmark Leaderboard

**Files:**
- Create: `benchmarks/leaderboard.md`
- Create: `.github/ISSUE_TEMPLATE/leaderboard-entry.md`

A crowdsourced table of cost-per-task results. Categories: component creation, bug fixing, test writing, refactoring, code review. Each entry: task, model, tokens used, cost, optimization techniques applied.

---

## Task 13: Stack Templates (Go, Rust, Django, Rails, Java Spring)

**Files:**
- Create: `templates/CLAUDE.md/by-stack/go.md`
- Create: `templates/CLAUDE.md/by-stack/rust.md`
- Create: `templates/CLAUDE.md/by-stack/django.md`
- Create: `templates/CLAUDE.md/by-stack/rails.md`
- Create: `templates/CLAUDE.md/by-stack/java-spring.md`

Cost-optimized CLAUDE.md templates for each stack, following the same format as existing templates (react-vite.md, nextjs.md, etc.). Under 100 lines each, with stack-specific commands and conventions.

---

## Task 14: VS Code Extension

**Files:**
- Create: `tools/vscode-extension/package.json`
- Create: `tools/vscode-extension/tsconfig.json`
- Create: `tools/vscode-extension/src/extension.ts`
- Create: `tools/vscode-extension/src/costEstimator.ts`
- Create: `tools/vscode-extension/src/statusBar.ts`
- Create: `tools/vscode-extension/README.md`

A VS Code extension that shows estimated token count and cost in the status bar for the active file, provides a command to estimate CLAUDE.md per-turn cost, and highlights when CLAUDE.md exceeds the 150-line threshold.

---

## Final: Update README, CHANGELOG, CLAUDE.md

- Add new sections to README for all new content
- Update CHANGELOG with version 1.2.0
- Update CLAUDE.md file structure section
- Update CONTRIBUTING.md with new contribution types
