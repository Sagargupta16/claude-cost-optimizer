# /optimize -- Claude Code Cost Optimization Command

A custom Claude Code slash command that audits your project's configuration and generates a cost-efficiency report with a letter grade and actionable recommendations.

## What It Does

When you run `/optimize` in Claude Code, it inspects your project for cost-related configuration and produces a structured report:

1. **CLAUDE.md audit** -- checks existence, line count, and structure
2. **.claudeignore audit** -- checks existence and coverage of common expensive paths
3. **settings.json audit** -- checks model configuration and cost-related flags
4. **MCP server count** -- estimates per-turn token overhead from connected servers
5. **Conversation pattern check** -- looks for custom commands and large files

The output includes an estimated per-session cost, a letter grade (A+ through F), and ranked recommendations with expected savings percentages.

## Installation

Copy the command file to your project's `.claude/commands/` directory:

```bash
# From your project root
mkdir -p .claude/commands
cp path/to/optimize.md .claude/commands/optimize.md
```

Or copy it directly from this repo:

```bash
mkdir -p .claude/commands
curl -o .claude/commands/optimize.md \
  https://raw.githubusercontent.com/Sagargupta16/claude-cost-optimizer/main/tools/optimize-command/optimize.md
```

Once installed, type `/optimize` in any Claude Code session within that project.

### Global Installation

To make the command available in all projects, place it in your user-level commands directory:

```bash
mkdir -p ~/.claude/commands
cp path/to/optimize.md ~/.claude/commands/optimize.md
```

## Example Output

```
CLAUDE CODE COST OPTIMIZATION REPORT
=====================================
Project: my-web-app
Date:    2026-04-03

CONFIGURATION AUDIT
-------------------
CLAUDE.md:          EXISTS (187 lines)
.claudeignore:      MISSING
settings.json:      EXISTS (model: opus-4-6)
MCP servers:        4 connected (~4000 extra tokens/turn)
Custom commands:    0 defined

COST ESTIMATE
-------------
Model:              opus-4-6
Est. input/turn:    ~6280 tokens
Est. output/turn:   ~500 tokens
Est. session cost:  ~$1.75 (40 turns)
Est. monthly cost:  ~$192.50 (assuming 5 sessions/day, 22 workdays)

GRADE: D (55/100)

ISSUES FOUND
------------
1. CLAUDE.md exceeds 150-line limit (187 lines) -- adds ~2200 unnecessary tokens/turn
2. No .claudeignore -- Claude may read node_modules, lock files, and build artifacts
3. Opus set as default with no task-based model switching
4. 4 MCP servers add ~4000 tokens per turn
5. No custom commands defined for repetitive workflows

RECOMMENDATIONS (ranked by impact)
-----------------------------------
1. [HIGH] Add .claudeignore excluding node_modules, dist, lock files -- saves ~15% per session
2. [HIGH] Trim CLAUDE.md to under 150 lines (move verbose sections to linked files) -- saves ~10%
3. [HIGH] Use Sonnet or Haiku as default model, reserve Opus for complex tasks -- saves ~20-40%
4. [MED]  Remove unused MCP servers (audit which are actually needed) -- saves ~5%
5. [LOW]  Add custom commands for frequent workflows to reduce prompting tokens -- saves ~3%

ESTIMATED SAVINGS IF ALL APPLIED: ~45% reduction (~$1.75/session -> ~$0.96/session)
```

## Customizing the Grading Thresholds

The grade is calculated by starting at 100 points and subtracting penalties for each issue found. You can adjust the scoring to match your priorities by editing the "Scoring" section in `optimize.md`.

### Default Penalty Table

| Finding | Default Penalty | Customization Notes |
|---------|:--------------:|---------------------|
| No CLAUDE.md | -20 | Lower if your project is simple enough to not need one |
| CLAUDE.md over 150 lines | -10 | Adjust the line threshold for larger projects |
| CLAUDE.md over 300 lines | -20 | Replaces the 150-line penalty |
| No .claudeignore | -20 | Lower for small projects with few ignorable files |
| Weak .claudeignore coverage | -10 | Adjust based on your tech stack |
| No settings.json | -5 | Increase if team standardization matters |
| Opus as default without switching | -10 | Remove if your work requires Opus consistently |
| 4+ MCP servers | -10 | Raise or lower based on your server overhead |
| 6+ MCP servers | -15 | Replaces the 4+ penalty |
| No custom commands | -5 | Increase if your team has many repetitive workflows |

### Grade Scale

| Score | Grade | Meaning |
|:-----:|:-----:|---------|
| 90-100 | A+ | Highly optimized -- minimal waste |
| 80-89 | A | Well optimized -- minor improvements possible |
| 70-79 | B | Good -- some clear improvements available |
| 60-69 | C | Average -- notable savings on the table |
| 50-59 | D | Below average -- significant waste |
| <50 | F | Unoptimized -- immediate action recommended |

To change the grade boundaries, edit the "Grade scale" list in the Scoring section of `optimize.md`.

### Cost Estimation Assumptions

The per-session cost estimate uses these defaults (editable in the "Cost Estimate" section):

- **Turns per session**: 40
- **Tokens per CLAUDE.md line**: ~1.5
- **Tokens per MCP server per turn**: ~1000
- **Base system prompt**: ~2000 tokens/turn
- **Average output per turn**: ~500 tokens

Adjust these if your usage patterns differ. For example, if your sessions average 20 turns, halve the session cost estimate.

## Relationship to Other Tools

This command complements the other tools in this repo:

- **[Token Estimator](../token-estimator/)** -- estimates token counts for specific files
- **[Usage Analyzer](../usage-analyzer/)** -- analyzes historical session data for cost patterns
- **[/cost-check command](../../templates/commands/cost-check.md)** -- lightweight in-session cost check (run during a session)
- **/optimize** (this command) -- comprehensive project-level configuration audit (run at the start of a project)
