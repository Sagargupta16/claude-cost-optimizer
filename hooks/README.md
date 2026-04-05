# Claude Code Budget Enforcement Hooks

Hooks that track tool call usage per session, warn when approaching limits, and log session summaries for historical analysis.

## What Are Claude Code Hooks?

Claude Code hooks are shell commands that run automatically in response to specific events during a Claude Code session. They are configured in `settings.json` and execute as subprocesses -- they receive JSON on stdin with event data and can output JSON to stdout to surface messages to the user.

Supported hook events:

| Event | When It Fires |
|-------|---------------|
| `PreToolUse` | Before a tool call is executed |
| `PostToolUse` | After a tool call completes |
| `Notification` | When Claude Code generates a notification |
| `Stop` | When a session ends (the model stops responding) |
| `SubagentStop` | When a subagent finishes its task |

Each hook entry has a `matcher` (regex matched against the tool name) and a list of shell commands to run. The `matcher` field is a regex string -- `".*"` matches all tools, `""` matches the event itself (used for Stop/Notification).

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
- Logs each call with timestamp, tool name, token estimate, and cost
- Warns at 50 and 100 tool calls to suggest session refresh
- Never blocks -- informational only
- Review logs at `/tmp/claude-cost-log/session-YYYYMMDD.log`

### session-summary.sh (Stop)

Runs when the session ends. Produces a summary and appends it to a persistent log file.

- Extracts session metadata (model, turns, tool calls, duration) from the stop event
- Reads the budget tracker's counter file for accurate tool call counts
- Writes a timestamped entry to `sessions.log` for historical tracking
- Cleans up the per-session counter file

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

Example (using the provided `settings-example.json` as a reference):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": ".*",
        "hooks": [
          "bash /home/you/claude-cost-optimizer/hooks/budget-tracker.sh"
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          "bash /home/you/claude-cost-optimizer/hooks/session-summary.sh"
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

| Workflow | Suggested Limit |
|----------|:--------------:|
| Quick bug fixes, simple edits | 20-30 |
| Moderate feature work | 50-75 |
| Large refactors, multi-file changes | 100-150 |
| Exploration and research | 150+ |

## How It Works

### Data Flow

```
Claude Code event
    |
    v
stdin (JSON) --> budget-tracker.sh --> stdout (JSON warning or empty)
                     |
                     v
              /tmp/claude-budget/session-{id}.count  (counter file)

Claude Code Stop event
    |
    v
stdin (JSON) --> session-summary.sh --> stdout (JSON summary message)
                     |
                     v
              /tmp/claude-budget/sessions.log  (persistent log)
              /tmp/claude-budget/session-{id}.count  (cleaned up)
```

### Hook Input Format

Based on community research into Claude Code's observed behavior, hooks receive both a JSON payload on stdin and environment variables.

**JSON payload on stdin** (PreToolUse/PostToolUse):

```json
{
  "hook_event_name": "PreToolUse",
  "tool_name": "Read",
  "tool_input": {"file_path": "/path/to/file"},
  "tool_input_json": "{\"file_path\": \"/path/to/file\"}",
  "tool_output": "...",
  "tool_result_is_error": false
}
```

Note: `tool_output` and `tool_result_is_error` are only present in PostToolUse events.

**Environment variables** set by Claude Code for each hook invocation:

| Variable | Description | Availability |
|----------|-------------|--------------|
| `HOOK_EVENT` | Event name (`"PreToolUse"`, `"PostToolUse"`) | All hook events |
| `HOOK_TOOL_NAME` | The tool being called (e.g., `"Read"`, `"Bash"`, `"Edit"`) | PreToolUse, PostToolUse |
| `HOOK_TOOL_INPUT` | Tool input as a string | PreToolUse, PostToolUse |
| `HOOK_TOOL_IS_ERROR` | `"0"` or `"1"` | PostToolUse only |
| `HOOK_TOOL_OUTPUT` | The tool's output | PostToolUse only |

Using environment variables (e.g., `$HOOK_TOOL_NAME`) is simpler and more reliable than parsing the JSON payload for common fields like tool name.

### Hook Exit Code Semantics

The exit code from a hook script controls whether the tool call proceeds:

| Exit Code | Meaning | Behavior |
|:---------:|---------|----------|
| **0** | Allow | Tool call proceeds. Anything printed to stdout is captured as feedback to Claude. |
| **2** | Deny | Tool call is blocked. Stdout is used as the denial message shown to Claude. |
| **Any other** | Warn | Tool call proceeds, but a warning is logged. |

The budget-tracker.sh script always exits 0 (allow) because it is informational only -- it warns but never blocks tool execution.

### Hook Output Format

Hooks can print text to stdout. The behavior depends on the exit code:

- **Exit 0**: stdout is captured as feedback to Claude (can be plain text or JSON with a `message` field)
- **Exit 2**: stdout is used as the denial reason shown to Claude
- **Empty stdout**: the hook ran silently with no feedback

## Troubleshooting

**Hooks not running**: Verify the path in settings.json is absolute and correct. Check that the scripts are executable (`chmod +x`).

**Python not found**: The scripts use `python3` for JSON parsing. If your system uses a different name, update the scripts or create an alias.

**Permission errors on /tmp**: Set `BUDGET_LOG_DIR` to a directory you have write access to.

**Hooks blocking Claude Code**: These scripts use `set -euo pipefail` but all file operations have `|| true` fallbacks. If a hook hangs, check for filesystem issues. Claude Code has a timeout for hooks -- a stuck hook will be killed, not block indefinitely.

## Limitations

- Tool call counting is a proxy for cost, not an exact measure. A single Read of a large file costs more tokens than a Glob call, but both count as one tool call.
- The counter file is session-scoped. If Claude Code does not provide a session ID in the hook payload, all calls fall back to a shared "default" counter.
- These hooks do not have access to actual token counts or dollar amounts -- Claude Code does not expose billing data to hooks.
- The Stop event payload schema may vary between Claude Code versions. The scripts handle missing fields gracefully.
