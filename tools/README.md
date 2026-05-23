# Tools

CLI tools and utilities for measuring, tracking, and reducing Claude Code costs.

## Quick Reference

| Tool | Language | Purpose | Install |
|------|----------|---------|---------|
| [**claude-rate**](claude-rate/) | Python (stdlib only) | **Local Claude / AI setup rater** -- 7 categories, 0-100 score, A+ to F grade, copy-pasteable fixes, monthly-cost projection per model | `npx -y @sagargupta16/claude-rate .` or `curl \| sh` |
| [Token Estimator](token-estimator/) | Python | Estimate token count and cost for files | `pip install tiktoken` |
| [Usage Analyzer](usage-analyzer/) | Python | Analyze session data for cost hotspots | stdlib only |
| [Badge Generator](badge-generator/) | Python | Grade project config (A+ to F) -- precursor to claude-rate, 4-category | stdlib only |
| [MCP Cost Server](mcp-cost-server/) | TypeScript | In-session cost estimation via MCP | `npm install` |
| [VS Code Extension](vscode-extension/) | TypeScript | Status bar token/cost display | `npm install` |
| [/optimize Command](optimize-command/) | Markdown | Claude Code custom command for auditing | Copy to `.claude/commands/` |
| [GitHub Action](actions/claude-cost-audit/) | Python | CI cost audit for PRs | Use in workflow YAML |

## Running Python Tools

All Python tools require Python 3.10+. The token estimator needs `tiktoken`:

```bash
pip install -r ../requirements.txt
```

The other Python tools use stdlib only -- no install needed.

```bash
# Rate the entire project's Claude/AI setup (recommended starting point)
python claude-rate/rate.py .
# Or via npx (no clone needed):
npx -y @sagargupta16/claude-rate .

# Estimate tokens for a file
python token-estimator/estimate.py path/to/file.py

# Analyze usage data
python usage-analyzer/analyze.py ~/.claude/projects/

# Grade a project (legacy, 4-category)
python badge-generator/generate.py /path/to/project
```

## Running TypeScript Tools

```bash
# MCP Cost Server
cd mcp-cost-server && npm install && npm run build

# VS Code Extension
cd vscode-extension && npm install && npm run compile
```

## Web Tools

The browser-based tools require no installation:

- [Cost Calculator](https://sagargupta16.github.io/claude-cost-optimizer/calculator)
- [Badge Checker](https://sagargupta16.github.io/claude-cost-optimizer/badge)
- [Repo Analyzer](https://sagargupta16.github.io/claude-cost-optimizer/analyzer)
