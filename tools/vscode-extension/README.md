# Claude Cost Estimator - VS Code Extension

A lightweight VS Code extension that shows estimated token count and Claude API cost for the active file, directly in the status bar. All estimation runs locally with no API calls.

## Features

- **Status bar token count**: Shows `~1,247 tokens | $0.004` for the active file, updated in real time as you type.
- **Estimate Current File**: Detailed breakdown of input/output costs across all Claude model tiers (Fable 5.1, Opus 5.5, legacy Fable/Opus/Sonnet snapshots, Sonnet 5, Haiku 4.5).
- **Estimate CLAUDE.md Per-Turn Cost**: Finds all CLAUDE.md files in the workspace and calculates how much they add to each turn of a Claude Code session. Warns when the file is too small to be cacheable on the selected model.
- **Check Project Configuration**: Audits your workspace for CLAUDE.md and .claude/settings.json, including file-read exclusions (`Read(...)` rules under `permissions.deny`). Reports missing files and suggests improvements. A `.claudeignore` file is not read by Claude Code -- it appears nowhere in Claude Code's documentation -- so move its patterns into `permissions.deny`.
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
| `claudeCost.defaultModel` | `sonnet` | Model for cost estimation: `fable` (Fable 5.1), `fable-5`, `opus` (Opus 5.5), `opus-5`, `opus-4.8`, `opus-4.7`, `opus-4.6`, `sonnet` (Sonnet 5), `sonnet-4.6`, or `haiku` |
| `claudeCost.showInStatusBar` | `true` | Show the token count status bar item |
| `claudeCost.claudeMdWarningThreshold` | `150` | Line count above which CLAUDE.md triggers a warning |

## How Token Estimation Works

The extension uses a character-based heuristic rather than a real BPE tokenizer:

- Code files average ~4 characters per token
- Prose files average ~3.5 characters per token
- The ratio is blended based on how many syntax characters the file contains

This is fast and dependency-free, with roughly 10-15% variance compared to the actual tokenizer. For precise counts, use the `tools/token-estimator` CLI which uses tiktoken.

## Pricing Data

Costs are based on Claude API pricing as of 2026-09-28:

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Min cacheable prompt |
|-------|:---------------------:|:----------------------:|:--------------------:|
| Fable 5.1 (alias: `fable`) | $10.00 | $50.00 | 512 |
| Fable 5 (alias: `fable-5`) | $10.00 | $50.00 | 512 |
| Opus 5.5 (alias: `opus`) | $4.00 | $20.00 | 512 |
| Opus 5, legacy (alias: `opus-5`) | $5.00 | $25.00 | 512 |
| Opus 4.8, legacy (alias: `opus-4.8`) | $5.00 | $25.00 | 1,024 |
| Opus 4.7, legacy (alias: `opus-4.7`) | $5.00 | $25.00 | 2,048 |
| Opus 4.6, legacy (alias: `opus-4.6`) | $5.00 | $25.00 | 4,096 |
| Sonnet 5 (alias: `sonnet`) | $2.00 | $10.00 | 1,024 |
| Haiku 4.5 (alias: `haiku`) | $1.00 | $5.00 | 4,096 |

The `opus` alias points at Opus 5.5 (released 2026-09-22), Anthropic's recommended default, at $4/$20 -- 20% below Opus 5. Opus 5, 4.8, 4.7, and 4.6 stay in the table as legacy snapshots at $5/$25 so you can price an older pinned model, not because you should pick one.

Cache reads have three multipliers: 0.1x base input by default, 0.025x on Fable 5.1, and 0.05x on Opus 5.5 ($0.20/MTok).

Sonnet 5 is $2/$10 permanently -- the launch rate was labelled introductory through 2026-08-31, but Anthropic made it standard and cancelled the increase to $3/$15.

**Minimum cacheable prompt.** A `cache_control` block on a prefix shorter than the listed floor is silently ignored: no error, no `cache_creation_input_tokens`, and full input price on every turn. "Estimate CLAUDE.md Per-Turn Cost" adds a note when your CLAUDE.md falls below the floor for the selected model. Watch this on Haiku 4.5 especially -- its 4,096-token floor is 8x Opus 5.5's, so a CLAUDE.md that caches fine on Opus quietly pays full price on Haiku.

> **Opus 5.5 note.** Opus 5.5 runs adaptive thinking always on and reasoning tokens bill as output. The per-turn output figure here assumes a flat 500 tokens, which is a floor rather than an average. Thinking cannot be disabled on Opus 5.5 (`thinking: {type: "disabled"}` returns a 400), so lower `output_config.effort` for routine turns -- it defaults to `medium`. On legacy Opus 5, setting `thinking` to disabled is legal only at effort `high` or below.

## Publishing to the Marketplace (Future)

To publish as a proper VS Code extension:

1. Create a publisher account at https://marketplace.visualstudio.com/manage
2. Add a `publisher` field to package.json
3. Add an icon (128x128 PNG) and set the `icon` field
4. Run `vsce publish`

See the [VS Code publishing docs](https://code.visualstudio.com/api/working-with-extensions/publishing-extension) for details.
