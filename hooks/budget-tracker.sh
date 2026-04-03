#!/usr/bin/env bash
# budget-tracker.sh - Track tool call count per Claude Code session
#
# Hook type: PreToolUse or PostToolUse
# Purpose: Counts cumulative tool invocations in a session and warns
#          when approaching a configurable threshold.
#
# Claude Code pipes JSON to stdin on each hook invocation. The JSON
# payload has the following structure (based on observed behavior):
#
#   {
#     "hook_event_name": "PreToolUse",
#     "tool_name": "Read",
#     "tool_input": {"file_path": "/path/to/file"},
#     "tool_input_json": "{\"file_path\": \"/path/to/file\"}",
#     "tool_output": "...",            (PostToolUse only)
#     "tool_result_is_error": false     (PostToolUse only)
#   }
#
# Claude Code also sets these environment variables for hooks:
#   HOOK_EVENT      - "PreToolUse" or "PostToolUse"
#   HOOK_TOOL_NAME  - the tool name (e.g., "Read", "Bash", "Edit")
#   HOOK_TOOL_INPUT - tool input as a string
#   HOOK_TOOL_IS_ERROR - "0" or "1" (PostToolUse only)
#   HOOK_TOOL_OUTPUT   - tool output (PostToolUse only)
#
# Exit code semantics for hooks:
#   0 - Allow the tool call (stdout is captured as feedback to Claude)
#   2 - Deny the tool call (stdout is used as the denial message)
#   Any other - Warn (tool continues, but a warning is logged)
#
# This script always exits 0 (allow) -- it only provides informational
# warnings, never blocks tool execution.
#
# Configuration (environment variables):
#   BUDGET_TOOL_LIMIT  - warn after this many tool calls (default: 50)
#   BUDGET_WARN_AT     - start warning at this percentage (default: 80)
#   BUDGET_LOG_DIR     - directory for counter files (default: /tmp/claude-budget)

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TOOL_LIMIT="${BUDGET_TOOL_LIMIT:-50}"
WARN_PERCENT="${BUDGET_WARN_AT:-80}"
LOG_DIR="${BUDGET_LOG_DIR:-/tmp/claude-budget}"

# ---------------------------------------------------------------------------
# Read stdin (JSON payload from Claude Code)
# ---------------------------------------------------------------------------
INPUT="$(cat)"

# Try to extract a session identifier from the hook payload.
# Claude Code sends session_id in the event data. Fall back to a default
# if parsing fails -- never block Claude Code on a parse error.
SESSION_ID="$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    # session_id may be at the top level or nested under session
    sid = data.get('session_id', '') or data.get('session', {}).get('id', '')
    print(sid if sid else 'default')
except Exception:
    print('default')
" 2>/dev/null || echo "default")"

# Grab the tool name from the HOOK_TOOL_NAME environment variable.
# This is simpler and more reliable than parsing JSON. Fall back to
# JSON parsing if the env var is not set (older Claude Code versions).
if [ -n "${HOOK_TOOL_NAME:-}" ]; then
    TOOL_NAME="$HOOK_TOOL_NAME"
else
    TOOL_NAME="$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_name', 'unknown'))
except Exception:
    print('unknown')
" 2>/dev/null || echo "unknown")"
fi

# ---------------------------------------------------------------------------
# Ensure log directory exists
# ---------------------------------------------------------------------------
mkdir -p "$LOG_DIR" 2>/dev/null || true

COUNTER_FILE="${LOG_DIR}/session-${SESSION_ID}.count"

# ---------------------------------------------------------------------------
# Increment counter (atomic-ish for single-threaded hook execution)
# ---------------------------------------------------------------------------
if [ -f "$COUNTER_FILE" ]; then
    CURRENT="$(cat "$COUNTER_FILE" 2>/dev/null || echo "0")"
else
    CURRENT=0
fi

# Validate that CURRENT is a number
case "$CURRENT" in
    ''|*[!0-9]*) CURRENT=0 ;;
esac

NEXT=$((CURRENT + 1))
printf '%d' "$NEXT" > "$COUNTER_FILE" 2>/dev/null || true

# ---------------------------------------------------------------------------
# Check threshold and warn if needed
# ---------------------------------------------------------------------------
WARN_AT=$(( TOOL_LIMIT * WARN_PERCENT / 100 ))

if [ "$NEXT" -ge "$TOOL_LIMIT" ]; then
    # Over the limit -- output a warning message via JSON stdout.
    # Claude Code hooks can return JSON with a "message" field to surface
    # information to the user.
    printf '{"message":"[Budget] Tool call %d of %d -- limit reached. Consider starting a new session or raising BUDGET_TOOL_LIMIT."}\n' \
        "$NEXT" "$TOOL_LIMIT"
elif [ "$NEXT" -ge "$WARN_AT" ]; then
    REMAINING=$((TOOL_LIMIT - NEXT))
    printf '{"message":"[Budget] Tool call %d of %d -- %d remaining before limit."}\n' \
        "$NEXT" "$TOOL_LIMIT" "$REMAINING"
fi

# If we're under the warning threshold, output nothing. Claude Code
# treats empty stdout as "no action needed."
#
# Exit 0 = allow the tool call. We never deny (exit 2) -- this hook
# is informational only. See exit code semantics at the top of this file.
