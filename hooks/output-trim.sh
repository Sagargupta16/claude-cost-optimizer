#!/usr/bin/env bash
# output-trim.sh -- Opt-in PostToolUse hook: shorten noisy output of green
# build, install and test runs before Claude reads it.
#
# Thin shim for output_trim.py (stdlib only, Python 3.10+). Read that file's
# header for the rules, the scope and the environment variables.
#
# Hook config (add to settings.json):
#   "hooks": {
#     "PostToolUse": [{
#       "matcher": "Bash",
#       "hooks": [{ "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR\"/hooks/output-trim.sh" }]
#     }]
#   }
#
# PostToolUse only fires for a Bash command that exited 0. A failed run goes to
# PostToolUseFailure, which cannot rewrite output, so failures are never touched.
# Needs Claude Code 2.1.121 or later.
#
# Kill switch: CLAUDE_TRIM_OFF=1
#
# Exit codes: always 0. It prints nothing (the output is left alone) unless it
# has a shorter copy to hand back, and it fails open on any error.

[ "${CLAUDE_TRIM_OFF:-}" = "1" ] && exit 0

# Run the script from its own folder so the path survives MSYS/Git Bash path
# conversion on Windows.
cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null || exit 0

# Pick the first interpreter that is really Python 3.10 or newer (the Windows
# Store python3 stub exits non-zero and is skipped).
for PY in python3 python py; do
  if command -v "$PY" >/dev/null 2>&1 \
    && "$PY" -c 'import sys; sys.exit(sys.version_info < (3, 10))' >/dev/null 2>&1; then
    exec "$PY" output_trim.py
  fi
done

exit 0
