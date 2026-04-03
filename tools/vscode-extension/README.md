# Claude Cost Estimator - VS Code Extension

A lightweight VS Code extension that shows estimated token count and Claude API cost for the active file, directly in the status bar. All estimation runs locally with no API calls.

## Features

- **Status bar token count**: Shows `~1,247 tokens | $0.004` for the active file, updated in real time as you type.
- **Estimate Current File**: Detailed breakdown of input/output costs across all Claude model tiers (Opus, Sonnet, Haiku).
- **Estimate CLAUDE.md Per-Turn Cost**: Finds all CLAUDE.md files in the workspace and calculates how much they add to each turn of a Claude Code session.
- **Check Project Configuration**: Audits your workspace for CLAUDE.md, .claudeignore, and .claude/settings.json. Reports missing files and suggests improvements.
- **CLAUDE.md size warning**: The status bar turns yellow when a CLAUDE.md file exceeds the configured line threshold, since large instruction files increase per-turn costs.

## Installation

This extension is not yet published to the VS Code Marketplace. To run it in development mode:

```bash
cd tools/vscode-extension
npm install
npm run compile
```

Then open VS Code, press `F5` (or Run > Start Debugging), and select "VS Code Extension Development Host". The extension will activate in the new window.

Alternatively, to install locally as a VSIX:

```bash
npm install -g @vscode/vsce
cd tools/vscode-extension
npm install
npm run compile
vsce package
code --install-extension claude-cost-estimator-0.1.0.vsix
```

## Commands

Open the command palette (`Ctrl+Shift+P` / `Cmd+Shift+P`) and search for:

| Command | Description |
|---------|-------------|
| Claude Cost: Estimate Current File | Show token count and cost breakdown for the active file |
| Claude Cost: Estimate CLAUDE.md Per-Turn Cost | Calculate per-turn and 20-turn session costs for all CLAUDE.md files |
| Claude Cost: Check Project Configuration | Audit workspace for Claude Code config files |

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `claudeCost.defaultModel` | `sonnet` | Model for cost estimation (`opus`, `sonnet`, or `haiku`) |
| `claudeCost.showInStatusBar` | `true` | Show the token count status bar item |
| `claudeCost.claudeMdWarningThreshold` | `150` | Line count above which CLAUDE.md triggers a warning |

## How Token Estimation Works

The extension uses a character-based heuristic rather than a real BPE tokenizer:

- Code files average ~4 characters per token
- Prose files average ~3.5 characters per token
- The ratio is blended based on how many syntax characters the file contains

This is fast and dependency-free, with roughly 10-15% variance compared to the actual tokenizer. For precise counts, use the `tools/token-estimator` CLI which uses tiktoken.

## Pricing Data

Costs are based on Claude API pricing as of March 2026:

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| Opus 4.6 | $5.00 | $25.00 |
| Sonnet 4.6 | $3.00 | $15.00 |
| Haiku 4.5 | $1.00 | $5.00 |

## Publishing to the Marketplace (Future)

To publish as a proper VS Code extension:

1. Create a publisher account at https://marketplace.visualstudio.com/manage
2. Add a `publisher` field to package.json
3. Add an icon (128x128 PNG) and set the `icon` field
4. Run `vsce publish`

See the [VS Code publishing docs](https://code.visualstudio.com/api/working-with-extensions/publishing-extension) for details.
