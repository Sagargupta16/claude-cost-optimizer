# Claude Code Budget Enforcement Hooks

Hooks that track tool call usage per session, warn when approaching limits, and log session summaries for historical analysis.

## What Are Claude Code Hooks?

Claude Code hooks are shell commands that run automatically in response to specific events during a Claude Code session. They are configured in `settings.json` and execute as subprocesses -- they receive JSON on stdin with event data and can output JSON to stdout to surface messages to the user.

Claude Code has about 30 hook events ([hooks reference](https://code.claude.com/docs/en/hooks), read 2026-11-01). The ones that matter for cost tracking:

| Event | When It Fires |
|-------|---------------|
| `PreToolUse` | Before a tool call is executed |
| `PostToolUse` | After a tool call completes |
| `Stop` | When Claude finishes responding -- every turn, not once per session |
| `SubagentStop` | When a subagent finishes |
| `PreCompact` / `PostCompact` | Before and after a compaction |
| `SessionEnd` | When a session terminates (`/clear`, `/resume`, logout, exit) |

Each hook entry has a `matcher` and a list of handlers. For tool events the `matcher` is matched against the tool name -- `".*"` matches all tools; `""` matches every occurrence of events that have no tool. On macOS, Linux and WSL, Claude Code leaves the Glob and Grep tools out of the default tool set and searches with `find` and `grep` through Bash, so a matcher on `Glob|Grep` only fires on Windows or when those tools are turned back on ([tools reference](https://code.claude.com/docs/en/tools-reference), read 2026-11-01).

## What These Hooks Do

### budget-tracker.sh (PreToolUse)

Counts every tool invocation in the session. Warns when approaching a configurable limit.

- Maintains a per-session counter in a temp file
- At 80% of the limit (configurable): prints a warning with remaining count
- At 100% of the limit: prints a "limit reached" message
- Never blocks or prevents tool execution -- warnings only

### cost-logger.sh (PreToolUse)

Logs estimated token count and cost for each tool call to a daily log file. Helps you understand where tokens go and which operations are expensive.

- Estimates input/output tokens by tool type (Read, Edit, Bash, Agent, etc.)
- Reads `tool_name` and `session_id` from the JSON on stdin (Claude Code sets no per-tool environment variables)
- Logs each call with timestamp, tool name, token estimate, and cost; prices by `COST_LOGGER_MODEL`, then `ANTHROPIC_MODEL`, then Opus 5.5 (hook input carries no model)
- Warns at 50 and 100 tool calls in a session to suggest a refresh
- Never blocks -- informational only
- Review logs at `/tmp/claude-cost-log/session-YYYYMMDD-<session_id>.log`

### session-summary.sh (SessionEnd)

Runs when the session ends. Produces a summary and appends it to a persistent log file. Register it on `SessionEnd`, not `Stop`: `Stop` fires after every response, so the counter cleanup below would reset the budget tracker every turn (this repo had it on `Stop` until 1.18.0).

- Logs the session id and the budget tracker's tool call count (the SessionEnd payload carries `session_id`, `transcript_path`, `cwd` and `reason`; model, turns and duration are not in it and log as `n/a`)
- Writes a timestamped entry to `sessions.log` for historical tracking
- Cleans up the per-session counter file

### Going further: hooks that cut tokens

These three hooks count and log; they do not shrink anything Claude reads. Anthropic's [costs page](https://code.claude.com/docs/en/costs) describes the bigger lever: a hook that preprocesses output, such as a PreToolUse hook that filters test output down to the failures, can cut tens of thousands of tokens to hundreds. [rtk](https://github.com/rtk-ai/rtk) packages the same idea as a CLI proxy that compresses common dev-command output; its GitHub description claims 60-90% on those commands (its README now says "up to 90% smaller", read 2026-11-01), not measured by this repo, and its README adds that this is not the same as cutting your bill by the same amount.

## Installation

### 1. Copy the hook scripts

Clone or download this repo, then note the path to the `hooks/` directory.

### 2. Make scripts executable

```bash
chmod +x hooks/budget-tracker.sh hooks/session-summary.sh
```

### 3. Configure settings.json

Copy the hooks configuration into your Claude Code settings file. You have two options:

**Global** (all projects): `~/.claude/settings.json`

**Per-project**: `.claude/settings.json` in your project root

Edit `settings-example.json` in this directory -- replace `/path/to/claude-cost-optimizer` with the actual path -- then merge the `hooks` block into your existing settings file.

This repo's own [`.claude/settings.json`](../.claude/settings.json) wires all three hooks through `"$CLAUDE_PROJECT_DIR"/hooks/...`, so you can copy its `hooks` block into a project that keeps the scripts in its own `hooks/` folder. It validates against the `claude-code-settings.json` schema it declares. Do not use a bare relative path such as `bash hooks/cost-logger.sh`: a hook runs in the session's current directory, so it fails with "No such file or directory" as soon as Claude `cd`s into a subfolder. Claude Code sets `CLAUDE_PROJECT_DIR` to the project root for every hook ([hooks reference](https://code.claude.com/docs/en/hooks)). For a global install in `~/.claude/settings.json`, use absolute paths.

Each entry must be an object with `"type": "command"` and a `"command"` string. A bare command string in the `hooks` array is invalid and the hook silently never runs.

Example (using the provided `settings-example.json` as a reference):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "bash /home/you/claude-cost-optimizer/hooks/budget-tracker.sh"
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "bash /home/you/claude-cost-optimizer/hooks/session-summary.sh"
          }
        ]
      }
    ]
  }
}
```

### 4. Verify

Start a new Claude Code session and make a few tool calls. You should see budget warnings as you approach the limit. When you end the session, the summary will be logged.

Check the log:

```bash
cat /tmp/claude-budget/sessions.log
```

## Configuration

All configuration is through environment variables. Set them in your shell profile or in the `env` block of your Claude Code settings.

| Variable | Default | Description |
|----------|---------|-------------|
| `BUDGET_TOOL_LIMIT` | `50` | Total tool calls before the "limit reached" warning |
| `BUDGET_WARN_AT` | `80` | Percentage of the limit at which warnings begin |
| `BUDGET_LOG_DIR` | `/tmp/claude-budget` | Directory for counter files and session logs |
| `SESSION_LOG_FILE` | `$BUDGET_LOG_DIR/sessions.log` | Path to the persistent session log |

### Setting via Claude Code settings.json

```json
{
  "env": {
    "BUDGET_TOOL_LIMIT": "75",
    "BUDGET_WARN_AT": "70",
    "BUDGET_LOG_DIR": "/home/you/.claude/budget-logs"
  }
}
```

### Adjusting the Limit

The default of 50 tool calls is a reasonable starting point for cost-conscious usage. Adjust based on your workflow:

These are starting points to tune, not measurements:

| Workflow | Suggested Limit |
|----------|:--------------:|
| Quick bug fixes, simple edits | 25 |
| Moderate feature work | 60 |
| Large refactors, multi-file changes | 125 |
| Exploration and research | 200 |

## How It Works

### Data Flow

```
Claude Code event
    |
    v
stdin (JSON) --> budget-tracker.sh --> stdout ({"systemMessage": ...} warning, or empty)
                     |
                     v
              /tmp/claude-budget/session-{id}.count  (counter file)

Claude Code SessionEnd event
    |
    v
stdin (JSON) --> session-summary.sh --> stdout (discarded by Claude Code on SessionEnd)
                     |
                     v
              /tmp/claude-budget/sessions.log  (persistent log)
              /tmp/claude-budget/session-{id}.count  (cleaned up)
```

### Hook Input Format

Hooks receive a JSON payload on stdin ([hooks reference](https://code.claude.com/docs/en/hooks), read 2026-11-01). Every event carries `session_id`, `transcript_path`, `cwd` and `hook_event_name`; tool events add `tool_name`, `tool_input` and `tool_use_id`, and `effort.level` where the model has effort. A PreToolUse example:

```json
{
  "session_id": "abc123",
  "hook_event_name": "PreToolUse",
  "tool_name": "Read",
  "tool_input": {"file_path": "/path/to/file"},
  "tool_use_id": "toolu_01"
}
```

Claude Code sets no per-tool environment variables such as `HOOK_TOOL_NAME`; read the tool name from stdin. It does set `CLAUDE_PROJECT_DIR`. The payload has no model or token counts.

### Hook Exit Code Semantics

The exit code from a hook script controls whether the tool call proceeds:

| Exit Code | Meaning | Behavior |
|:---------:|---------|----------|
| **0** | Success | Tool call proceeds. Claude Code applies any JSON output fields the hook printed. |
| **2** | Blocking error | Tool call is blocked. Stderr is the reason. |
| **Any other** | Non-blocking error | Tool call proceeds, with a hook error notice. |

The budget-tracker.sh script always exits 0 (allow) because it is informational only -- it warns but never blocks tool execution.

### Hook Output Format

- **Exit 0 with JSON**: the fields apply. `systemMessage` is a warning shown to the user, which is what these scripts print. A `message` or `result` field is not a hook output field; JSON that fails validation shows as a hook error (these scripts printed those until 1.18.0, so their warnings never appeared).
- **Exit 0 with plain text or nothing**: success; the text is not shown in the transcript.
- **Exit 2**: blocks the action; stderr is the reason.
- **SessionEnd**: Claude Code discards the output fields, so a summary hook has to write to a file.

## Troubleshooting

**Hooks not running**: Verify the path in settings.json is absolute and correct. Check that the scripts are executable (`chmod +x`).

**Python not found**: The scripts use `python3` for JSON parsing. If your system uses a different name, update the scripts or create an alias.

**Permission errors on /tmp**: Set `BUDGET_LOG_DIR` to a directory you have write access to.

**Hooks blocking Claude Code**: These scripts use `set -euo pipefail` but all file operations have `|| true` fallbacks. If a hook hangs, check for filesystem issues. Claude Code has a timeout for hooks -- a stuck hook will be killed, not block indefinitely.

## Limitations

- Tool call counting is a proxy for cost, not an exact measure. A single Read of a large file costs more tokens than a Glob call, but both count as one tool call.
- The counter file is session-scoped. If Claude Code does not provide a session ID in the hook payload, all calls fall back to a shared "default" counter.
- These hooks do not have access to actual token counts or dollar amounts -- Claude Code does not expose billing data to hooks.
- The scripts handle missing payload fields gracefully, falling back to `default` and `n/a`.
