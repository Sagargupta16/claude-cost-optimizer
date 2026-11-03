#!/usr/bin/env bash
# session-summary.sh - Summarize a Claude Code session on SessionEnd
#
# Hook type: SessionEnd (not Stop: Stop fires every time Claude finishes a
#            response, so the counter cleanup below would reset the budget
#            tracker after every turn; https://code.claude.com/docs/en/hooks)
# Purpose: When a session ends, read session_id, transcript_path and reason from
#          stdin, price the session from its transcript with claude-rate
#          (tools/claude-rate/rate.py --transcript: list-price estimate, subagent
#          transcripts included), and append a summary to a persistent log file.
#          Claude Code discards SessionEnd output, so the log file is where the
#          summary goes.
#
# The SessionEnd payload carries no model, turn count or duration; those come
# from the transcript. When budget-tracker.sh has been pricing the session, this
# reuses its state file and reads only the bytes added since. A long session
# priced from scratch can take seconds, and SessionEnd hooks share a 1.5-second
# budget by default: give this hook "timeout": 10 (hooks/settings-example.json
# does) so the summary is not cut off.
#
# Configuration (environment variables):
#   BUDGET_LOG_DIR     - directory for log files
#                        (default: /tmp/claude-budget; %TEMP%\claude-budget on Windows)
#   SESSION_LOG_FILE   - full path to the log file (default: $BUDGET_LOG_DIR/sessions.log)
#   CLAUDE_RATE_PY     - full path to rate.py. Default: ../tools/claude-rate/rate.py next
#                        to this script, then an installed claude-rate (0.4.0 or later).
#                        Without it the summary logs the tool call count only.

set -uo pipefail

case "${BASH_SOURCE[0]}" in
    */* | *\\*) HOOK_DIR="${BASH_SOURCE[0]%[/\\]*}" ;;
    *) HOOK_DIR="." ;;
esac

read -r -d '' SUMMARY_PY <<'PY' || true
import sys

sys.path[:] = [p for p in sys.path if p not in ("", ".")]  # never import from the project folder

import datetime
import json
import os
import re
import tempfile
import time
from pathlib import Path


def native(path):
    """A Git Bash path such as /c/Users/you as a Windows Python reads it (C:/Users/you)."""
    match = re.match(r"^/([a-zA-Z])(/.*)?$", path)
    return f"{match[1]}:{match[2] or '/'}" if os.name == "nt" and match else path


def log_dir():
    configured = os.environ.get("BUDGET_LOG_DIR")
    if configured:
        return Path(native(configured))
    return Path(tempfile.gettempdir() if os.name == "nt" else "/tmp") / "claude-budget"


def safe(text):
    return re.sub(r"[^A-Za-z0-9._-]", "_", str(text))[:120] or "default"


def load_report(hook_dir):
    """claude-rate's transcript_report, or None when it is not found."""
    import importlib.util

    explicit = os.environ.get("CLAUDE_RATE_PY")
    path = Path(native(explicit)) if explicit else Path(hook_dir) / ".." / "tools" / "claude-rate" / "rate.py"
    if path.is_file():
        spec = importlib.util.spec_from_file_location("claude_rate_hook", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules["claude_rate_hook"] = module  # dataclasses look their module up here
        spec.loader.exec_module(module)
        return getattr(module, "transcript_report", None)
    if explicit:
        return None
    try:
        import claude_rate  # the wheel installs rate.py under this name
    except ImportError:
        return None
    return getattr(claude_rate, "transcript_report", None)


def price(payload, directory, hook_dir):
    transcript = payload.get("transcript_path")
    if not isinstance(transcript, str) or not transcript:
        return None
    report = load_report(hook_dir)
    if report is None:
        import shutil
        import subprocess

        binary = shutil.which("claude-rate")
        if not binary:
            return None
        done = subprocess.run([binary, "--transcript", transcript, "--state", str(directory / "spend-state.json")],
                              capture_output=True, text=True, timeout=20)
        return json.loads(done.stdout)
    return report(Path(transcript), directory / "spend-state.json")


def span(first, last):
    try:
        start = datetime.datetime.fromisoformat(first.replace("Z", "+00:00"))
        end = datetime.datetime.fromisoformat(last.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return "n/a"
    minutes = int((end - start).total_seconds() // 60)
    return f"{minutes // 60}h{minutes % 60:02d}m (first to last request)"


def summary(payload, directory, sid, hook_dir):
    try:
        calls = (directory / f"session-{sid}.count").read_text().strip() or "n/a"
    except OSError:
        calls = "n/a"
    lines = [
        f"Session: {sid}",
        f"  Timestamp : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"  Reason    : {payload.get('reason') or 'n/a'}",
    ]
    try:
        report = price(payload, directory, hook_dir)
    except Exception:  # pricing is best effort; the log line still gets written
        report = None
    if report and "error" not in report:
        models = ", ".join(f"{name} ${dollars:,.2f}" for name, dollars in report.get("by_model", {}).items()) or "n/a"
        unpriced = f" ({report['unpriced']:,} on models without a price row)" if report.get("unpriced") else ""
        lines += [
            f"  Models    : {models}",
            f"  Requests  : {report.get('requests', 0):,}{unpriced}",
            f"  Prompts   : {report.get('prompts', 0):,}",
            f"  Spend     : ${report.get('dollars', 0):,.2f} (list-price estimate, subagents included; "
            "on a Pro, Max or Ultra plan it is API-equivalent value, not your bill)",
            f"  Span      : {span(report.get('first'), report.get('last'))}",
        ]
    else:
        lines.append("  Spend     : n/a (claude-rate not found; set CLAUDE_RATE_PY to tools/claude-rate/rate.py)")
    lines.append(f"  Tool calls: {calls}")
    return "\n".join(lines)


def clean(directory, sid):
    """Remove this session's counter, spend cache and markers, and markers older than three days."""
    stale = time.time() - 3 * 86_400
    targets = [directory / f"session-{sid}.count", directory / f"session-{sid}.spend.json"]
    for marker in directory.glob("mark-*"):
        try:
            if marker.name.startswith((f"mark-session-{sid}-", f"mark-turn-{sid}-", f"mark-nopricer-{sid}")) \
                    or marker.stat().st_mtime < stale:
                targets.append(marker)
        except OSError:
            pass
    for target in targets:
        try:
            target.unlink()
        except OSError:
            pass


def main():
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace") or "{}")
    except ValueError:
        payload = {}
    payload = payload if isinstance(payload, dict) else {}
    directory = log_dir()
    directory.mkdir(parents=True, exist_ok=True)
    sid = safe(payload.get("session_id") or "default")
    text = summary(payload, directory, sid, sys.argv[1] if len(sys.argv) > 1 else ".")
    log = Path(native(os.environ["SESSION_LOG_FILE"])) if os.environ.get("SESSION_LOG_FILE") else directory / "sessions.log"
    try:
        with log.open("a", encoding="utf-8") as handle:
            handle.write(f"---\n{text}\n")
    except OSError:
        pass
    clean(directory, sid)
    # Claude Code discards SessionEnd output; this only shows when you run the script by hand.
    print(json.dumps({"systemMessage": text}))


try:
    main()
except Exception:  # a summary hook never breaks the session
    pass
PY

if command -v python3 >/dev/null 2>&1; then
    python3 -c "$SUMMARY_PY" "$HOOK_DIR" 2>/dev/null
elif command -v python >/dev/null 2>&1; then
    python -c "$SUMMARY_PY" "$HOOK_DIR" 2>/dev/null
fi
exit 0
