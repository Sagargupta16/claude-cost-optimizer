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
- **Expensive model overuse**: Using Opus where Sonnet or Haiku would suffice.
- **Long sessions**: Conversations that accumulate excessive context over many turns.

### Recommendations
Actionable suggestions based on your usage patterns, linking back to strategies from the Claude Cost Optimizer guides.

## Tips

- Run the analyzer weekly to track spending trends.
- After optimizing your setup (trimming CLAUDE.md, adding .claudeignore), re-analyze to measure the impact.
- Use `--json` output to build your own cost tracking dashboards.
- Focus on the top 2-3 most expensive sessions for the highest ROI.
