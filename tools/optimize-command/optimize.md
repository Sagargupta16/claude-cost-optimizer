Analyze this project's Claude Code cost efficiency and provide an optimization report.

Do not ask clarifying questions. Run every step below, collect the data, and produce the final report.

## Steps

### 1. Check CLAUDE.md

Read `CLAUDE.md` in the project root. If it exists:
- Count the total number of lines.
- Flag if it exceeds 200 lines. Anthropic's guidance: "target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence." There is no character limit (the only size cap: Claude Code skips a file over 4 MiB); the whole file loads at launch and costs tokens every session. `@path` imports do not help here: imported files load at launch alongside the CLAUDE.md that references them.
- Check whether it contains large code blocks, verbose examples, or workflow-specific sections (PR reviews, DB migrations) that could move into skills, path-scoped `.claude/rules/` files (with `paths:` frontmatter) or a subdirectory CLAUDE.md so they load on demand.
- Note whether it uses a concise, structured format (headings, bullet points, tables) vs. prose paragraphs.

If it does not exist, record that as a finding -- projects without CLAUDE.md cause Claude to spend extra tokens exploring the codebase on every session.

### 2. Check file-read exclusions (Read deny rules)

Claude Code keeps its file tools out of paths through `Read(...)` rules in `permissions.deny`. It does not read a `.claudeignore` file: that name appears nowhere in Claude Code's documentation.

Read `permissions.deny` in `.claude/settings.json` (fall back to `.claude/settings.local.json`) and count the entries of the form `Read(...)`. If there are any:
- Assess coverage: do they exclude common high-token directories and files? Check for these specifically:
  - `node_modules/`, `dist/`, `build/`, `.next/`, `__pycache__/`, `.venv/`, `venv/`
  - Lock files: `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `poetry.lock`, `Pipfile.lock`
  - Generated files: `*.min.js`, `*.min.css`, `*.map`, `*.bundle.js`
  - Large data: `*.csv`, `*.parquet`, `*.sqlite`, `*.db`
  - Media: `*.png`, `*.jpg`, `*.gif`, `*.mp4`, `*.ico`
- List any obvious gaps (common expensive directories or files that are not excluded).

Rules use gitignore syntax: `Read(./dist/**)` is relative to the project, and a bare name such as `Read(.env)` matches at any depth.

If there are no `Read(...)` rules, record that as a significant finding and include this starter block in the recommendation (do not edit settings files during the audit):

```json
{
  "permissions": {
    "deny": [
      "Read(./node_modules/**)",
      "Read(./dist/**)",
      "Read(./build/**)",
      "Read(./coverage/**)",
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(*.min.js)",
      "Read(./package-lock.json)"
    ]
  }
}
```

If a `.claudeignore` exists in the project root, record that it is not read by Claude Code, and include its patterns converted to `Read(...)` rules in the recommendation: a line `dir/` becomes `Read(./dir/**)`; a line containing `/` elsewhere becomes `Read(./line)` (strip a leading `/`); a bare name or glob with no `/` becomes `Read(line)`. Skip blank lines, `#` comments and `!` negations.

No published measurement exists for what Read deny rules save. Do not put a percentage on this recommendation; say the effect depends on how often Claude would otherwise open those files.

### 3. Check .claude/settings.json

Check whether `.claude/settings.json` exists. If it exists:
- Read it and note:
  - Which model is configured as default (if any).
  - Whether any permission allowlists or denylists are set (Read deny rules are scored in step 2).
  - Whether any cost-related settings are configured, such as `env.CLAUDE_CODE_MAX_TURNS` (the settings form of `--max-turns`), `promptCacheTtl`, or per-model effort in `modelSettings`.
- Flag if Opus is the default for a project where Sonnet or Haiku would suffice for most tasks. Opus 5.5 is $4/$20 per 1M input/output tokens; Sonnet 5 ($2/$10) is 2x cheaper and Haiku 4.5 ($1/$5) is 4x cheaper.

If it does not exist, note that the project is using global defaults.

### 4. Check MCP Servers

Run `claude mcp list` in the project root using Bash. If the command is not available or fails, read the `mcpServers` object in `.mcp.json` at the project root (project scope) and in `~/.claude.json` (user scope, plus per-project entries under `projects`). MCP servers are not configured in `settings.json`.

- Count the number of MCP servers connected.
- Check whether tool search is on. It is on by default: only tool names and server instructions enter context until Claude uses a specific tool. It is off when `ENABLE_TOOL_SEARCH=false` or `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1` is set, or `ANTHROPIC_BASE_URL` points at a non-first-party host without `ENABLE_TOOL_SEARCH=true` (check the `env` blocks of both settings files and the shell environment); then full tool schemas load up front on every request.
- No per-server token figure is published. Do not estimate one; tell the user to run `/context` to see what MCP tools actually consume.
- Flag if more than 3 servers are connected (each adds its tool names and server instructions even with tool search on).
- Flag any servers that appear unused or redundant (disable them with `/mcp`), and any server that duplicates an installed CLI such as `gh`, `aws`, `gcloud` or `sentry-cli`. Anthropic recommends the CLI when available because it adds no per-tool listing.

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
| CLAUDE.md over 200 lines | -10 |
| CLAUDE.md over 300 lines | -20 (replaces the -10) |
| No `Read(...)` rules in `permissions.deny` (a `.claudeignore` does not count) | -20 |
| Read deny rules exist but miss 3+ common exclusions | -10 |
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
- MCP servers: leave them out of the per-turn number (no per-server figure is published) and say so; if tool search is off, note that the estimate is low because full tool schemas load up front
- Base system prompt: ~2000 tokens per turn
- Average output per turn: ~500 tokens
- Use the pricing for the configured model (default to Opus 5.5 at $4/$20 per 1M input/output tokens if no model is set). Rates per 1M input/output: Opus 5.5 $4/$20, Sonnet 5 $2/$10, Haiku 4.5 $1/$5, Fable 5.1 $10/$50; legacy Opus 5 and Opus 4.x $5/$25, legacy Sonnet 4.6 and 4.5 $3/$15

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
Read deny rules:    {n} in permissions.deny{; .claudeignore found (not read by Claude Code)}
settings.json:      {EXISTS / MISSING} (model: {model or "default"})
MCP servers:        {n} connected (tool search: {ON / OFF})
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

Keep the report factual and specific. Do not pad with generic advice. Every recommendation must reference a concrete finding from the audit above. Where no measurement exists (Read deny rules, MCP servers), write "no published figure" in place of the percentage and leave it out of the total.
