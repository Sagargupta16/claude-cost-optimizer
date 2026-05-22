#!/usr/bin/env sh
# claude-rate -- one-shot installer/runner.
#
# Downloads rate.py from GitHub and runs it against the directory you choose.
# Pass --install to keep the script around at ~/.local/bin/claude-rate
# instead of running it once.
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/Sagargupta16/claude-cost-optimizer/main/tools/claude-rate/install.sh | sh
#   curl -sSL https://raw.githubusercontent.com/Sagargupta16/claude-cost-optimizer/main/tools/claude-rate/install.sh | sh -s -- --install
#   curl -sSL https://raw.githubusercontent.com/Sagargupta16/claude-cost-optimizer/main/tools/claude-rate/install.sh | sh -s -- /path/to/project --fix

set -eu

SCRIPT_URL="https://raw.githubusercontent.com/Sagargupta16/claude-cost-optimizer/main/tools/claude-rate/rate.py"

# Locate Python 3.
if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1 && python -c 'import sys; sys.exit(0 if sys.version_info[0] >= 3 else 1)' 2>/dev/null; then
    PY=python
else
    echo "claude-rate: Python 3 not found on PATH." >&2
    echo "  Install Python 3.10+ from https://www.python.org/downloads/" >&2
    exit 127
fi

# Locate a downloader.
if command -v curl >/dev/null 2>&1; then
    DOWNLOAD="curl -fsSL"
elif command -v wget >/dev/null 2>&1; then
    DOWNLOAD="wget -qO-"
else
    echo "claude-rate: neither curl nor wget found." >&2
    exit 127
fi

# Persistent install vs one-shot.
if [ "${1:-}" = "--install" ]; then
    shift
    DEST="${HOME}/.local/bin"
    mkdir -p "$DEST"
    TARGET="$DEST/claude-rate"
    echo "claude-rate: installing to $TARGET"
    $DOWNLOAD "$SCRIPT_URL" > "$TARGET"
    chmod +x "$TARGET"
    case ":$PATH:" in
        *":$DEST:"*) ;;
        *)
            echo
            echo "Note: $DEST is not on your PATH. Add this to your shell profile:"
            echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
            ;;
    esac
    echo "Done. Run: claude-rate ."
    exit 0
fi

# One-shot mode: download to a temp file and run with all args forwarded.
TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT INT TERM
$DOWNLOAD "$SCRIPT_URL" > "$TMP"
exec "$PY" "$TMP" "$@"
