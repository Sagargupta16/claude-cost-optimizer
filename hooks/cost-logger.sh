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

# Per-model rates in dollars per 1M tokens (verified 2026-09-29).
# Defaults to the "opus" alias (Opus 5.5) when no model is set; unrecognized
# model strings fall through to the legacy Opus rate.
MODEL="${HOOK_MODEL_ID:-${ANTHROPIC_MODEL:-opus}}"
case "$MODEL" in
  *haiku*)
    RATE_INPUT=1
    RATE_OUTPUT=5
    ;;
  *sonnet-4-6*|*sonnet-4.6*|*sonnet-4-5*|*sonnet-4.5*)
    # Legacy Sonnet 4.6 / 4.5 keep $3/$15.
    RATE_INPUT=3
    RATE_OUTPUT=15
    ;;
  *sonnet*)
    # Sonnet 5.5 and Sonnet 5 are both $2/$10 (Sonnet 5's rate is permanent).
    RATE_INPUT=2
    RATE_OUTPUT=10
    ;;
  *fable*|*mythos*)
    RATE_INPUT=10
    RATE_OUTPUT=50
    ;;
  opus|opus\[*\]|*opus-5-5*|*opus-5.5*|*opus5.5*|*opus5-5*)
    # Opus 5.5 is $4/$20, 20% below Opus 5. Must match before the generic Opus
    # branch below, because "opus-5" is a substring of "opus-5-5".
    RATE_INPUT=4
    RATE_OUTPUT=20
    ;;
  *)
    # Legacy Opus 5 / 4.8 / 4.7 / 4.6 / 4.5, and unrecognized models: $5/$25.
    RATE_INPUT=5
    RATE_OUTPUT=25
    ;;
esac

# Log the estimate. Opus 5.5 runs adaptive thinking always on (Opus 5 turns it
# on by default) and bills reasoning tokens as output, so real output cost can
# exceed this estimate.
COST=$(echo "scale=4; ($EST_INPUT * $RATE_INPUT + $EST_OUTPUT * $RATE_OUTPUT) / 1000000" | bc 2>/dev/null || echo "0.01")
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
