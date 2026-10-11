# /optimize -- Claude Code Cost Optimization Command

A custom Claude Code slash command that audits your project's configuration and generates a cost-efficiency report with a letter grade and actionable recommendations.

## What It Does

When you run `/optimize` in Claude Code, it inspects your project for cost-related configuration and produces a structured report:

1. **CLAUDE.md audit** -- checks existence, line count against Anthropic's 200-line guidance, and structure
2. **File-read exclusions audit** -- counts `Read(...)` rules in `permissions.deny` and checks coverage of common expensive paths. A `.claudeignore` is not a Claude Code feature (Claude Code never reads it), so the command flags one and converts its patterns to `Read(...)` rules
3. **settings.json audit** -- checks model configuration and cost-related flags
4. **MCP server audit** -- counts connected servers, checks whether tool search is on (the default), and flags servers that duplicate a CLI
5. **Conversation pattern check** -- looks for custom commands and large files

The output includes an estimated per-session cost, a letter grade (A+ through F), and ranked recommendations with expected savings percentages, or "no published figure" where no measurement exists.

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
Date:    2026-09-28

CONFIGURATION AUDIT
-------------------
CLAUDE.md:          EXISTS (243 lines)
Read deny rules:    0 in permissions.deny; .claudeignore found (not read by Claude Code)
settings.json:      EXISTS (model: opus)
MCP servers:        4 connected (tool search: ON)
Custom commands:    2 defined

COST ESTIMATE
-------------
Model:              Opus 5.5 ($4/$20 per 1M)
Est. input/turn:    ~5930 tokens (MCP not counted: no per-server figure)
Est. output/turn:   ~500 tokens
Est. session cost:  ~$0.48 (40 turns)
Est. monthly cost:  ~$52.35 (assuming 5 sessions/day, 22 workdays)

GRADE: D (50/100)

ISSUES FOUND
------------
1. CLAUDE.md is 243 lines -- over Anthropic's 200-line guidance; longer files consume more context and reduce adherence
2. No Read deny rules in permissions.deny -- Claude may read node_modules, lock files, and build artifacts
3. .claudeignore found (6 rules) -- Claude Code does not read it
4. Opus set as default with no task-based model switching
5. 4 MCP servers connected; 2 duplicate installed CLIs (gh, aws)

RECOMMENDATIONS (ranked by impact)
-----------------------------------
1. [HIGH] Use Sonnet 5.5 as default for most tasks (assumed 80% of sessions), reserve Opus 5.5 for complex work -- saves ~40% per session
2. [HIGH] Move the 6 .claudeignore patterns into permissions.deny as Read(...) rules -- no published figure
3. [MED]  Trim CLAUDE.md under 200 lines (move workflow-specific sections into skills or path-scoped .claude/rules/) -- saves ~1.4% per session, plus better adherence
4. [MED]  Disable the gh and aws MCP servers with /mcp and use the CLIs -- no published figure; run /context to see what they use

ESTIMATED SAVINGS IF ALL APPLIED: ~41% reduction (~$0.48/session -> ~$0.28/session)
```

The example math: input is 3,500 base + 243 lines x 10 = ~5,930 tokens/turn. The estimate bills that stable prefix the way Claude Code caches it: turn 1 writes it at $5/1M (1.25x input), and the other 39 turns read it at $0.20/1M, so $0.030 + $0.046 = $0.076 of input, plus 20,000 output tokens ($0.40 at $20/1M), for ~$0.48 per session. Sonnet 5.5 is half of Opus 5.5 at every rate, so moving 80% of sessions there saves 0.8 x 50% = 40%. Trimming CLAUDE.md to 190 lines cuts the prefix to 5,400 tokens, saving $0.007 (1.4%). Both together give 0.2 x $0.469 + 0.8 x $0.235 = ~$0.28. Conversation history is not modeled, so real sessions, whose history grows every turn, cost more; check them with `/usage`.

## Customizing the Grading Thresholds

The grade is calculated by starting at 100 points and subtracting penalties for each issue found. You can adjust the scoring to match your priorities by editing the "Scoring" section in `optimize.md`.

### Default Penalty Table

| Finding | Default Penalty | Customization Notes |
|---------|:--------------:|---------------------|
| No CLAUDE.md | -20 | Lower if your project is simple enough to not need one |
| CLAUDE.md over 200 lines | -10 | Matches Anthropic's 200-line guidance; adjust for larger projects |
| CLAUDE.md over 300 lines | -20 | Replaces the 200-line penalty |
| No `Read(...)` deny rules | -20 | Lower for small projects with few ignorable files. A `.claudeignore` does not count |
| Weak Read deny rule coverage | -10 | Adjust based on your tech stack |
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
- **Tokens per CLAUDE.md line**: ~10 (measured on this repo's root CLAUDE.md and 14 CLAUDE.md templates: 20,161 cl100k tokens over 2,048 lines, 9.8 per line; the Claude 4.7+ tokenizer gives about 30% more)
- **Caching**: the system prompt and CLAUDE.md prefix is written once at the 5-minute cache-write rate (1.25x input) and read at the model's cache-read rate on the other 39 turns, as Claude Code caches it; below the model's minimum cacheable prompt it bills at full input. Conversation history is not modeled
- **MCP servers**: not counted. Tool search is on by default, so only tool names and server instructions enter context, and no per-server figure is published. Run `/context` to see the real number
- **Base system prompt**: ~3,500 tokens/turn, the repo's modelling assumption rather than a published figure; Claude Code's real system prompt plus its built-in tool definitions is larger, and `/context` shows the actual number
- **Average output per turn**: ~500 tokens
- **Default model**: Opus 5.5 at $4/$20 per 1M input/output tokens when no model is set

Adjust these if your usage patterns differ. For example, if your sessions average 20 turns, roughly halve the session cost estimate (the turn-1 cache write does not shrink).

## Relationship to Other Tools

This command complements the other tools in this repo:

- **[Token Estimator](../token-estimator/)** -- estimates token counts for specific files
- **[Usage Analyzer](../usage-analyzer/)** -- analyzes historical session data for cost patterns
- **[/cost-check command](../../templates/commands/cost-check.md)** -- lightweight in-session cost check (run during a session)
- **/optimize** (this command) -- comprehensive project-level configuration audit (run at the start of a project)
