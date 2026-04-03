# Tools

CLI tools and utilities for measuring, tracking, and reducing Claude Code costs.

## Quick Reference

| Tool | Language | Purpose | Install |
|------|----------|---------|---------|
| [Token Estimator](token-estimator/) | Python | Estimate token count and cost for files | `pip install tiktoken` |
| [Usage Analyzer](usage-analyzer/) | Python | Analyze session data for cost hotspots | stdlib only |
| [Badge Generator](badge-generator/) | Python | Grade project config (A+ to F) | stdlib only |
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
# Estimate tokens for a file
python token-estimator/estimate.py path/to/file.py

# Analyze usage data
python usage-analyzer/analyze.py ~/.claude/projects/

# Grade a project
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
