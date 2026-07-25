# Usage Analyzer

Analyze your Claude Code session data to identify cost hotspots, track spending, and get actionable recommendations for reducing costs.

## Installation

No external dependencies required. Uses only the Python standard library.

Python 3.10+ recommended.

## Usage

### Basic: Analyze a session directory

```bash
python tools/usage-analyzer/analyze.py ~/.claude/projects/
```

Output:

```
  Claude Code Usage Report
  ========================================================

  Overview
  --------------------------------------------------------
  Sessions analyzed:  12
  Total turns:        487
  Total tokens:       2,341,890
    Input tokens:     2,105,230
    Output tokens:    236,660
  Estimated cost:     $9.86
  Avg tokens/turn:    4,809

  Top 5 Sessions (by cost)
  --------------------------------------------------------
  #    Session                     Tokens   Turns       Cost
  .... ........................ .......... ....... ..........
  1    refactor-auth-module        482,100      87     $2.17
  2    new-dashboard-feature       391,420      63     $1.64
  3    debug-api-timeout           287,300      52     $1.19
  4    update-dependencies         198,700      41     $0.83
  5    fix-css-layout              156,200      38     $0.62

  Cost Hotspots
  --------------------------------------------------------
  ! Session 'refactor-auth-module' averages 5,541 tokens/turn.
    Consider trimming context or using .claudeignore.
  ! Opus is used for 312/487 (64%) of turns. Switch routine
    tasks to Sonnet or Haiku for major savings.

  Recommendations
  --------------------------------------------------------
  1. Input tokens dominate your usage (90%). Focus on reducing
     context size: trim CLAUDE.md, use .claudeignore, avoid
     reading large files.
  2. Estimated total spend: $9.86. Review the most expensive
     sessions above for quick wins.
```

### Show more sessions

```bash
python tools/usage-analyzer/analyze.py ~/.claude/projects/ --top 10
```

### Sort by different criteria

```bash
python tools/usage-analyzer/analyze.py ~/.claude/projects/ --sort tokens
python tools/usage-analyzer/analyze.py ~/.claude/projects/ --sort turns
python tools/usage-analyzer/analyze.py ~/.claude/projects/ --sort cost
```

### JSON output

```bash
python tools/usage-analyzer/analyze.py ~/.claude/projects/ --json
```

Useful for piping into other tools or dashboards.

## Flags Reference

| Flag | Description | Default | Example |
|------|-------------|---------|---------|
| `directory` | Path to directory containing session files | (required) | `~/.claude/projects/` |
| `--top N` | Number of top sessions to display | `5` | `--top 10` |
| `--sort FIELD` | Sort sessions by: `cost`, `tokens`, or `turns` | `cost` | `--sort tokens` |
| `--json` | Output results as JSON | off | `--json` |

## Models and Pricing

Cost estimates use current Claude API pricing (as of 2026-07-25, after the Opus 5 GA on 2026-07-24). The analyzer reads the `model` field out of your session records and matches it against these keys:

| Model | Detected from | Input (per 1M) | Output (per 1M) | Cache Hit (per 1M) |
|-------|---------------|:--------------:|:---------------:|:------------------:|
| Fable 5 (`fable`) | `fable`, `mythos` | $10.00 | $50.00 | $1.00 |
| Opus 5 (`opus`) | `opus-5`, or any other `opus` | $5.00 | $25.00 | $0.50 |
| Opus 4.8 (`opus-4.8`, legacy) | `opus-4-8`, `opus-4.8` | $5.00 | $25.00 | $0.50 |
| Opus 4.7 (`opus-4.7`, legacy) | `opus-4-7`, `opus-4.7` | $5.00 | $25.00 | $0.50 |
| Opus 4.6 (`opus-4.6`, legacy) | `opus-4-6`, `opus-4.6` | $5.00 | $25.00 | $0.50 |
| Sonnet 5 (`sonnet`) | `sonnet` | $3.00 | $15.00 | $0.30 |
| Haiku 4.5 (`haiku`) | `haiku` | $1.00 | $5.00 | $0.10 |

Notes:

- `opus` is Opus 5, the current Opus-tier flagship. Opus 4.8 is now a legacy model (same posted rate, retirement no sooner than 2027-05-28) and is still the server-side fallback target for Opus 5 cyber-classifier refusals.
- Mythos 5 is Glasswing-only and prices identically to Fable 5, so it maps to the `fable` key. (Mythos Preview retired 2026-06-30.)
- Sonnet 5 also has an introductory rate of $2/$10 through 2026-08-31. The table uses the standard rate so estimates stay valid past that date.
- Sessions whose records carry no recognizable model name fall back to Sonnet pricing, which keeps unknown-model estimates conservative rather than inflated.

> **Opus 5 note.** Opus 5 costs the same per token as Opus 4.8, but adaptive thinking is ON by default and reasoning tokens bill as output at the normal $25/1M rate. That means an identical workload bills higher on Opus 5 than it did on Opus 4.8 until you lower `output_config.effort` (it defaults to `high`). The analyzer reports what you actually spent, so your Opus 5 output totals may look larger than expected for the same amount of work.

## Supported File Formats

The analyzer scans for `.json` and `.jsonl` files and attempts to parse them as Claude Code session data. It recognizes several formats:

- **JSONL message logs**: One JSON object per line, each representing a message or event with `usage`, `role`, and `content` fields.
- **JSON session summaries**: A single JSON object with aggregate `usage` or `token_usage` fields.
- **JSON message arrays**: A JSON array of message objects.

Files that don't match any recognized format are silently skipped.

## What the Report Tells You

### Overview
Total tokens, cost, and average tokens per turn across all sessions.

### Top Sessions
The most expensive sessions ranked by your chosen sort criteria. Look here for the biggest cost-saving opportunities.

### Cost Hotspots
Specific patterns that are driving up costs:
- **High per-turn token usage**: Sessions where each turn processes a large context.
- **Heavy file reads**: Too many file read operations inflating input tokens.
- **Expensive model overuse**: Using Fable 5 or Opus where Sonnet or Haiku would suffice.
- **Opus 5 default thinking**: Opus 5 turns detected, where reasoning tokens bill as output because thinking is on by default.
- **Long sessions**: Conversations that accumulate excessive context over many turns.

### Recommendations
Actionable suggestions based on your usage patterns, linking back to strategies from the Claude Cost Optimizer guides.

## Tips

- Run the analyzer weekly to track spending trends.
- After optimizing your setup (trimming CLAUDE.md, adding .claudeignore), re-analyze to measure the impact.
- Use `--json` output to build your own cost tracking dashboards.
- Focus on the top 2-3 most expensive sessions for the highest ROI.
