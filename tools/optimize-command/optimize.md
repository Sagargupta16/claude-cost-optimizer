Analyze this project's Claude Code cost efficiency and provide an optimization report.

Do not ask clarifying questions. Run every step below, collect the data, and produce the final report.

## Steps

### 1. Check CLAUDE.md

Read `CLAUDE.md` in the project root. If it exists:
- Count the total number of lines.
- Flag if it exceeds 150 lines (the recommended ceiling for cost efficiency).
- Check whether it contains large code blocks, verbose examples, or sections that could be collapsed or moved to separate files.
- Note whether it uses a concise, structured format (headings, bullet points, tables) vs. prose paragraphs.

If it does not exist, record that as a finding -- projects without CLAUDE.md cause Claude to spend extra tokens exploring the codebase on every session.

### 2. Check .claudeignore

Check whether `.claudeignore` exists in the project root. If it exists:
- Read its contents and count the number of rules.
- Assess coverage: does it exclude common high-token directories and files? Check for these specifically:
  - `node_modules/`, `dist/`, `build/`, `.next/`, `__pycache__/`, `.venv/`, `venv/`
  - Lock files: `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `poetry.lock`, `Pipfile.lock`
  - Generated files: `*.min.js`, `*.min.css`, `*.map`, `*.bundle.js`
  - Large data: `*.csv`, `*.parquet`, `*.sqlite`, `*.db`
  - Media: `*.png`, `*.jpg`, `*.gif`, `*.mp4`, `*.ico`
- List any obvious gaps (common expensive directories or files that are not excluded).

If it does not exist, record that as a significant finding.

### 3. Check .claude/settings.json

Check whether `.claude/settings.json` exists. If it exists:
- Read it and note:
  - Which model is configured as default (if any).
  - Whether any permission allowlists or denylists are set.
  - Whether `--max-turns` or any cost-related flags are configured.
- Flag if Opus is the default for a project where Sonnet or Haiku would suffice for most tasks.

If it does not exist, note that the project is using global defaults.

### 4. Check MCP Servers

Run `claude mcp list` in the project root using Bash. If the command is not available or fails, check `.claude/settings.json` and `~/.claude/settings.json` for `mcpServers` configuration instead.

- Count the number of MCP servers connected.
- Each server adds roughly 500-2000 tokens of tool schema to every turn.
- Flag if more than 3 servers are connected (high overhead).
- Flag any servers that appear unused or redundant.

### 5. Check Conversation Patterns

Look for signs of common cost pitfalls:
- Check if there are custom commands in `.claude/commands/` that could reduce repetitive prompting.
- Check if the project has large files (>500 lines) that Claude is likely to read in full when targeted reads would suffice.
- Count the total number of files in the project (excluding ignored directories) to estimate codebase complexity.

## Scoring

Calculate a letter grade based on these criteria. Start at 100 points and subtract:

| Finding | Penalty |
|---------|---------|
| No CLAUDE.md | -20 |
| CLAUDE.md over 150 lines | -10 |
| CLAUDE.md over 300 lines | -20 (replaces the -10) |
| No .claudeignore | -20 |
| .claudeignore exists but missing 3+ common exclusions | -10 |
| No .claude/settings.json (using global defaults only) | -5 |
| Default model is Opus with no task-based switching configured | -10 |
| 4+ MCP servers connected | -10 |
| 6+ MCP servers connected | -15 (replaces the -10) |
| No custom commands defined | -5 |

Grade scale:
- 90-100: A+ (Highly optimized)
- 80-89: A (Well optimized)
- 70-79: B (Good, room for improvement)
- 60-69: C (Average, notable savings available)
- 50-59: D (Below average, significant waste)
- Below 50: F (Unoptimized, immediate action needed)

## Cost Estimate

Estimate the per-session cost using these assumptions:
- Average session: 40 turns
- CLAUDE.md is loaded every turn (line count x ~1.5 tokens per line x 40 turns)
- Each MCP server adds ~1000 tokens per turn
- Base system prompt: ~2000 tokens per turn
- Average output per turn: ~500 tokens
- Use the pricing for the configured model (default to Opus 4.7 at $5/$25 per 1M input/output tokens if no model is set)

Show the math briefly, then give the final estimate.

## Report Format

Present findings in exactly this format:

```
CLAUDE CODE COST OPTIMIZATION REPORT
=====================================
Project: {project name from directory or CLAUDE.md}
Date:    {today's date}

CONFIGURATION AUDIT
-------------------
CLAUDE.md:          {EXISTS / MISSING} ({n} lines)
.claudeignore:      {EXISTS / MISSING} ({n} rules)
settings.json:      {EXISTS / MISSING} (model: {model or "default"})
MCP servers:        {n} connected (~{n} extra tokens/turn)
Custom commands:    {n} defined

COST ESTIMATE
-------------
Model:              {model}
Est. input/turn:    ~{n} tokens
Est. output/turn:   ~{n} tokens
Est. session cost:  ~${n.nn} (40 turns)
Est. monthly cost:  ~${n.nn} (assuming 5 sessions/day, 22 workdays)

GRADE: {letter grade} ({score}/100)

ISSUES FOUND
------------
1. {issue description}
2. {issue description}
...

RECOMMENDATIONS (ranked by impact)
-----------------------------------
1. [{HIGH/MED/LOW}] {recommendation} -- saves ~{n}% per session
2. [{HIGH/MED/LOW}] {recommendation} -- saves ~{n}% per session
...

ESTIMATED SAVINGS IF ALL APPLIED: ~{n}% reduction (~${n.nn}/session -> ~${n.nn}/session)
```

Keep the report factual and specific. Do not pad with generic advice. Every recommendation must reference a concrete finding from the audit above.
