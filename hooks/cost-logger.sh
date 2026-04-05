#!/bin/bash
# cost-logger.sh -- Logs estimated cost per tool call.
# Use with PreToolUse hook to build cost awareness.
#
# Hook config (add to settings.json):
#   "hooks": {
#     "PreToolUse": [{
#       "matcher": ".*",
#       "hooks": ["bash hooks/cost-logger.sh"]
#     }]
#   }
#
# Exit codes: 0 = allow (never blocks)

TOOL="${HOOK_TOOL_NAME:-unknown}"
LOG_DIR="${TMPDIR:-/tmp}/claude-cost-log"
mkdir -p "$LOG_DIR"
SESSION_LOG="$LOG_DIR/session-$(date +%Y%m%d).log"

# Estimate tokens by tool type (rough averages)
case "$TOOL" in
  Read|Glob|Grep)
    EST_INPUT=2000
    EST_OUTPUT=100
    ;;
  Edit|Write)
    EST_INPUT=3000
    EST_OUTPUT=1500
    ;;
  Bash)
    EST_INPUT=2000
    EST_OUTPUT=500
    ;;
  Agent)
    EST_INPUT=5000
    EST_OUTPUT=2000
    ;;
  *)
    EST_INPUT=1000
    EST_OUTPUT=500
    ;;
esac

# Log the estimate (Opus pricing as worst-case: $5/$25 per 1M)
COST=$(echo "scale=4; ($EST_INPUT * 5 + $EST_OUTPUT * 25) / 1000000" | bc 2>/dev/null || echo "0.01")
echo "$(date +%H:%M:%S) $TOOL input:~${EST_INPUT} output:~${EST_OUTPUT} ~\$${COST}" >> "$SESSION_LOG"

# Count total calls this session
COUNT=$(wc -l < "$SESSION_LOG" 2>/dev/null || echo 0)

# Warn at thresholds (informational only, never blocks)
if [ "$COUNT" -eq 50 ]; then
  echo '{"result": "50 tool calls this session. Consider starting fresh if switching tasks."}'
elif [ "$COUNT" -eq 100 ]; then
  echo '{"result": "100 tool calls. Session history is expensive. Run /compact or start a new session."}'
fi

exit 0
