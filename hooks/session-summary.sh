#!/usr/bin/env bash
# session-summary.sh - Summarize a Claude Code session on Stop
#
# Hook type: Stop
# Purpose: When a session ends, read the session data from stdin,
#          print a brief summary, and append it to a persistent log
#          file for historical tracking.
#
# Configuration (environment variables):
#   BUDGET_LOG_DIR     - directory for log files (default: /tmp/claude-budget)
#   SESSION_LOG_FILE   - full path to the log file (default: $BUDGET_LOG_DIR/sessions.log)

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
LOG_DIR="${BUDGET_LOG_DIR:-/tmp/claude-budget}"
LOG_FILE="${SESSION_LOG_FILE:-${LOG_DIR}/sessions.log}"

# ---------------------------------------------------------------------------
# Read stdin (JSON payload from Claude Code)
# ---------------------------------------------------------------------------
INPUT="$(cat)"

# ---------------------------------------------------------------------------
# Extract session data using Python (no jq dependency).
# Gracefully handle missing fields -- every value has a fallback.
# ---------------------------------------------------------------------------
SUMMARY="$(printf '%s' "$INPUT" | python3 -c "
import sys, json, datetime

try:
    data = json.load(sys.stdin)
except Exception:
    data = {}

session_id = data.get('session_id', '') or data.get('session', {}).get('id', 'unknown')

# Tool call count -- check the budget tracker's counter file if available
tool_calls = data.get('tool_calls', data.get('num_tool_calls', ''))
if not tool_calls:
    # Try reading from the budget tracker counter file
    import os
    log_dir = os.environ.get('BUDGET_LOG_DIR', '/tmp/claude-budget')
    counter_path = os.path.join(log_dir, f'session-{session_id}.count')
    try:
        with open(counter_path) as f:
            tool_calls = f.read().strip()
    except Exception:
        tool_calls = 'n/a'

# Total turns
turns = data.get('num_turns', data.get('turns', 'n/a'))

# Model used
model = data.get('model', 'n/a')

# Duration -- some stop events include start/end timestamps
duration = 'n/a'
if 'duration_ms' in data:
    ms = int(data['duration_ms'])
    minutes = ms // 60000
    seconds = (ms % 60000) // 1000
    duration = f'{minutes}m {seconds}s'
elif 'duration_seconds' in data:
    s = int(data['duration_seconds'])
    duration = f'{s // 60}m {s % 60}s'

timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

summary = (
    f'Session: {session_id}\\n'
    f'  Timestamp : {timestamp}\\n'
    f'  Model     : {model}\\n'
    f'  Turns     : {turns}\\n'
    f'  Tool calls: {tool_calls}\\n'
    f'  Duration  : {duration}'
)
print(summary)
" 2>/dev/null || echo "Session summary: parse error (non-blocking)")"

# ---------------------------------------------------------------------------
# Ensure log directory exists
# ---------------------------------------------------------------------------
mkdir -p "$LOG_DIR" 2>/dev/null || true

# ---------------------------------------------------------------------------
# Append to persistent log file
# ---------------------------------------------------------------------------
{
    echo "---"
    echo "$SUMMARY"
} >> "$LOG_FILE" 2>/dev/null || true

# ---------------------------------------------------------------------------
# Output summary as a message for the user to see in the terminal
# ---------------------------------------------------------------------------
# Escape newlines for JSON output
JSON_MSG="$(printf '%s' "$SUMMARY" | python3 -c "
import sys, json
text = sys.stdin.read()
print(json.dumps(text))
" 2>/dev/null || echo '"Session complete."')"

printf '{"message":%s}\n' "$JSON_MSG"

# ---------------------------------------------------------------------------
# Clean up the budget tracker counter file for this session (optional)
# ---------------------------------------------------------------------------
SESSION_ID="$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    sid = data.get('session_id', '') or data.get('session', {}).get('id', '')
    print(sid if sid else 'default')
except Exception:
    print('default')
" 2>/dev/null || echo "default")"

COUNTER_FILE="${LOG_DIR}/session-${SESSION_ID}.count"
rm -f "$COUNTER_FILE" 2>/dev/null || true
