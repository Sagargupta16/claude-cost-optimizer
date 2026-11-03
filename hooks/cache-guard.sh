#!/usr/bin/env bash
# cache-guard.sh - Show what a model switch or a stale resume costs in prompt
# cache re-writes, before the request that pays it.
#
# Hook types (register both; see hooks/settings-example.json):
#   PreModelSwitch                       (Claude Code v2.1.251 or later)
#   SessionStart with matcher "resume|fork"
#
# Claude Code pipes JSON to stdin (https://code.claude.com/docs/en/hooks, read
# 2026-11-03). The fields used here:
#
#   PreModelSwitch: from_model, to_model, context_tokens, prompt_cache_warm,
#                   cache_ttl ("5m" or "1h"), estimated_cache_write_usd, pricing
#                   ("catalog", "configured" or "default"), transcript_path
#   SessionStart:   source ("resume" or "fork"), model, context_tokens,
#                   seconds_since_last_response, prompt_cache_likely_expired,
#                   estimated_cache_write_usd
#
# A model switch: Claude Code's own estimate of writing the prompt to the new
# model's cache, against staying (a cache read while the cache is warm, a re-write
# once it is cold). For a cheaper target it adds how many requests like your last
# 10 the switch takes to pay back, from the transcript, assuming the same tokens on
# both models; for a dearer target only the added cost per request.
# A resume or fork whose cache has likely expired, with at least
# CACHE_GUARD_MIN_TOKENS of context: the re-write cost, and /rename, then /clear or
# a fresh session if the old context is not needed.
#
# Output: one JSON object with "systemMessage", or nothing; always exit 0. Never a
# permissionDecision: "allow" would skip Claude Code's own confirmation while the
# cache is warm, and "ask" would repeat it. claude-rate abandons its own work after
# 3 seconds and prints nothing. Do not give the PreModelSwitch entry a short
# "timeout": a PreModelSwitch hook that reaches its timeout blocks the switch
# (default 30 seconds).
#
# Configuration (environment variables):
#   CACHE_GUARD_MIN_TOKENS - resume warnings start at this context size (default 50000,
#                            a starting point to tune, not a measurement)
#   CLAUDE_RATE_PY         - full path to rate.py. Default: ../tools/claude-rate/rate.py
#                            next to this script, then claude-rate (0.4.0 or later) on PATH.
#                            When neither is found the hook prints nothing.

set -uo pipefail

case "${BASH_SOURCE[0]}" in
    */* | *\\*) HOOK_DIR="${BASH_SOURCE[0]%[/\\]*}" ;;
    *) HOOK_DIR="." ;;
esac
RATE_PY="${CLAUDE_RATE_PY:-$HOOK_DIR/../tools/claude-rate/rate.py}"

# Not exec: whatever runs (or fails to start), this script exits 0, so the switch
# or the resume goes ahead unchanged when nothing is printed.
if [[ -f "$RATE_PY" ]]; then
    if command -v python3 >/dev/null 2>&1; then
        python3 "$RATE_PY" --hook cache-guard 2>/dev/null
    elif command -v python >/dev/null 2>&1; then
        python "$RATE_PY" --hook cache-guard 2>/dev/null
    fi
elif command -v claude-rate >/dev/null 2>&1; then
    claude-rate --hook cache-guard 2>/dev/null
fi
exit 0
