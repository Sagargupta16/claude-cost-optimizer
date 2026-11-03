#!/usr/bin/env bash
# budget-tracker.sh - Count tool calls per Claude Code session and, when you set
# a dollar cap, price the session from its transcript before each tool call.
#
# Hook type: PreToolUse (matcher ".*"). On PostToolUse it still warns, but
#            PostToolUse cannot ask or deny.
#
# Claude Code pipes JSON to stdin on each hook invocation
# (https://code.claude.com/docs/en/hooks, read 2026-11-03). The fields used here:
#
#   {
#     "session_id": "abc123",
#     "transcript_path": "/home/you/.claude/projects/.../abc123.jsonl",
#     "prompt_id": "550e8400-e29b-41d4-a716-446655440000",
#     "permission_mode": "default",
#     "hook_event_name": "PreToolUse",
#     "tool_name": "Read"
#   }
#
# The payload carries no token counts or dollars, and Claude Code sets no
# per-tool environment variables. With a cap set, this script has claude-rate
# (tools/claude-rate/rate.py, --transcript) price the session at list price from
# its transcript: the main transcript plus its subagent transcripts, each message
# once. That is an estimate. The transcript is written asynchronously, so it can
# trail by a request or two, and on a Pro, Max or Ultra plan it is API-equivalent
# value, not the bill.
#
# Output: always exit 0, and at most one JSON object on stdout. Warnings go in
# "systemMessage" (shown to the user). At a cap, on PreToolUse, it also returns
# hookSpecificOutput.permissionDecision "ask" (or "deny", see BUDGET_HARD_DENY).
# In claude -p runs Claude Code treats an unanswerable "ask" as a deny, and in
# dontAsk mode this script sends "deny" itself. SubagentHandback calls (a
# subagent delivering its report) are never asked or denied, only warned.
#
# Dollar ladder per cap (each step fires once, through O_EXCL marker files, the
# same create-only-if-absent rule as bash noclobber): 70% suggests one model tier
# down at the next task boundary, 80% warns, 90% suggests /compact or a Haiku
# subagent, 100% asks, and it asks again at every +25% (125%, 150%, ...) so one
# approval does not end the cap. The percentages are starting points, not
# measurements. With BUDGET_HARD_DENY=1 every tool call is denied from 120%,
# matching the hard limit in guides/05-team-budgeting.md.
#
# Configuration (environment variables):
#   BUDGET_TOOL_LIMIT        - warn after this many tool calls (default: 50)
#   BUDGET_WARN_AT           - start tool-call warnings at this percentage (default: 80)
#   BUDGET_LOG_DIR           - counter, marker and state files
#                              (default: /tmp/claude-budget; %TEMP%\claude-budget on Windows)
#   BUDGET_SESSION_USD_WARN  - one warning when session spend passes this many dollars
#   BUDGET_SESSION_USD       - session cap in dollars (subagents included)
#   BUDGET_DAY_USD           - cap on today's spend across every session this tracker
#                              priced (local calendar day; resumed history counts once)
#   BUDGET_TURN_USD          - cap on the current prompt's spend (subagents included)
#   BUDGET_HARD_DENY         - 1 = deny every tool call once a cap is 120% spent
#   CLAUDE_RATE_PY           - full path to rate.py. Default: ../tools/claude-rate/rate.py
#                              next to this script, then an installed claude-rate
#                              (0.4.0 or later). A cap with no claude-rate found warns
#                              once per session and counts tool calls only.
#
# Cost per call: one python process. claude-rate runs only when the session's
# transcripts changed size since the last call; it reads only the bytes added
# since then (state in $BUDGET_LOG_DIR/spend-state.json).

set -uo pipefail

# Directory of this script, passed to Python as an argument (Git Bash converts
# /c/... arguments to C:/... for a Windows Python; it does not convert env vars).
case "${BASH_SOURCE[0]}" in
    */* | *\\*) HOOK_DIR="${BASH_SOURCE[0]%[/\\]*}" ;;
    *) HOOK_DIR="." ;;
esac

read -r -d '' BUDGET_PY <<'PY' || true
import sys

sys.path[:] = [p for p in sys.path if p not in ("", ".")]  # never import from the project folder

import json
import os
import re
import tempfile
from pathlib import Path

STEPS = ((90, " /compact, or hand searches to a Haiku subagent, to slow the climb."), (80, ""),
         (70, " At the next task boundary, one model tier down (Opus to Sonnet, Sonnet to Haiku) slows the climb."))
SCOPES = (("session", "BUDGET_SESSION_USD", "Session spend"),
          ("day", "BUDGET_DAY_USD", "Today's spend (all sessions)"),
          ("turn", "BUDGET_TURN_USD", "This prompt's spend"))
NOTE = ("List-price estimate from the transcript; it can trail by a request or two, and on a Pro, "
        "Max or Ultra plan it is API-equivalent value, not your bill.")
NEVER_GATE = {"SubagentHandback"}


def native(path):
    """A Git Bash path such as /c/Users/you as a Windows Python reads it (C:/Users/you)."""
    match = re.match(r"^/([a-zA-Z])(/.*)?$", path)
    return f"{match[1]}:{match[2] or '/'}" if os.name == "nt" and match else path


def money_env(name):
    try:
        value = float(os.environ.get(name) or "nan")
    except ValueError:
        return None
    return value if 0 < value < float("inf") else None


def int_env(name, default):
    try:
        return int(os.environ.get(name) or default)
    except ValueError:
        return default


def log_dir():
    configured = os.environ.get("BUDGET_LOG_DIR")
    if configured:
        return Path(native(configured))
    return Path(tempfile.gettempdir() if os.name == "nt" else "/tmp") / "claude-budget"


def safe(text):
    return re.sub(r"[^A-Za-z0-9._-]", "_", str(text))[:120] or "default"


def mark(directory, name):
    """Create a marker once: True only for the one caller that created it."""
    try:
        os.close(os.open(directory / f"mark-{name}", os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        return True
    except OSError:
        return False


def count_call(directory, sid):
    path = directory / f"session-{sid}.count"
    try:
        current = int(path.read_text().strip() or 0)
    except (OSError, ValueError):
        current = 0
    try:
        path.write_text(str(current + 1))
    except OSError:
        pass
    return current + 1


def tool_message(calls):
    limit = int_env("BUDGET_TOOL_LIMIT", 50)
    if calls >= limit:
        return f"[Budget] Tool call {calls} of {limit} -- limit reached. Consider starting a new session or raising BUDGET_TOOL_LIMIT."
    if calls >= limit * int_env("BUDGET_WARN_AT", 80) // 100:
        return f"[Budget] Tool call {calls} of {limit} -- {limit - calls} remaining before limit."
    return None


def import_report(path):
    import importlib.util

    spec = importlib.util.spec_from_file_location("claude_rate_hook", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["claude_rate_hook"] = module  # dataclasses look their module up here
    spec.loader.exec_module(module)
    return getattr(module, "transcript_report", None)


def load_pricer(hook_dir):
    """A function (transcript, state file) -> report dict, or None when claude-rate is not found."""
    explicit = os.environ.get("CLAUDE_RATE_PY")
    path = Path(native(explicit)) if explicit else Path(hook_dir) / ".." / "tools" / "claude-rate" / "rate.py"
    if path.is_file():
        report = import_report(path)
        return (lambda t, s: report(Path(t), s)) if report else None
    if explicit:
        return None
    try:
        import claude_rate  # the wheel installs rate.py under this name

        if hasattr(claude_rate, "transcript_report"):
            return lambda t, s: claude_rate.transcript_report(Path(t), s)
    except ImportError:
        pass
    import shutil
    import subprocess

    binary = shutil.which("claude-rate")
    if not binary:
        return None

    def run(transcript, state):
        done = subprocess.run([binary, "--transcript", transcript, "--state", str(state)],
                              capture_output=True, text=True, timeout=20)
        return json.loads(done.stdout)

    return run


def signature(transcript):
    """Total size of the session's transcripts, to skip pricing when nothing was written."""
    path = Path(transcript)
    parts = path.parts
    if "subagents" in parts[1:]:
        cut = len(parts) - 1 - parts[::-1].index("subagents")
        session_dir = Path(*parts[:cut])
        path = session_dir.parent / f"{session_dir.name}.jsonl"
    side = path.parent / path.stem / "subagents"
    total = 0
    for item in [path, *(side.rglob("*.jsonl") if side.is_dir() else [])]:
        try:
            total += item.stat().st_size
        except OSError:
            pass
    return total


def priced(directory, sid, transcript, hook_dir):
    """The session's spend report, re-priced only when its transcripts changed size; None without claude-rate."""
    cache = directory / f"session-{sid}.spend.json"
    size = signature(transcript)
    try:
        held = json.loads(cache.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        held = {}
    if isinstance(held, dict) and held.get("signature") == size and isinstance(held.get("report"), dict):
        return held["report"]
    pricer = load_pricer(hook_dir)
    if pricer is None:
        return None
    report = pricer(transcript, directory / "spend-state.json")
    if report.get("state") in ("saved", "none"):
        tmp = cache.with_name(f"{cache.name}.{os.getpid()}.tmp")
        try:
            tmp.write_text(json.dumps({"signature": size, "report": report}), encoding="utf-8")
            os.replace(tmp, cache)
        except OSError:
            pass
    return report


def usd(value):
    return f"${value:,.2f}" if value >= 0.995 else f"${value:.3f}"


def ladder(directory, base, label, spent, cap, hard):
    """(message, None) for a warning step, (core text, (decision, follow-up)) at the cap, or (None, None).

    Warning steps fire once; the ask fires again at every +25% of the cap.
    """
    pct = spent / cap * 100
    figures = f"{label} ~{usd(spent)} of {usd(cap)} ({pct:.0f}%)"
    if hard and pct >= 120:
        core = f"[Budget] {figures} is past 120% of the cap and BUDGET_HARD_DENY=1 is set"
        return core, ("deny", "so tool calls are denied; raise the cap or start a new session")
    if pct >= 100:
        for threshold, _ in STEPS:
            mark(directory, f"{base}-{threshold}")
        step = 100 + 25 * int((pct - 100) // 25)
        if not mark(directory, f"{base}-ask{step}"):
            return None, None
        then = "tool calls are denied from 120% (BUDGET_HARD_DENY=1)" if hard else f"the next check is at {step + 25}%"
        return f"[Budget] {figures}: at or over the cap", ("ask", then)
    for threshold, hint in STEPS:
        if pct >= threshold:
            fired = mark(directory, f"{base}-{threshold}")
            for lower, _ in STEPS:
                if lower < threshold:
                    mark(directory, f"{base}-{lower}")
            return (f"[Budget] {figures}.{hint}" if fired else None), None
    return None, None


def money(payload, directory, sid, hook_dir):
    """(notice, dollar messages, (decision, reason) pairs) for the caps that are set."""
    caps = {scope: money_env(name) for scope, name, _ in SCOPES}
    warn_line = money_env("BUDGET_SESSION_USD_WARN")
    transcript = payload.get("transcript_path")
    if not (any(caps.values()) or warn_line) or not isinstance(transcript, str) or not transcript:
        return None, [], []
    report = priced(directory, sid, transcript, hook_dir)
    if report is None:
        notice = ("[Budget] A dollar cap is set but claude-rate was not found, so only tool calls are counted. "
                  "Set CLAUDE_RATE_PY to the full path of tools/claude-rate/rate.py, or install claude-rate "
                  "0.4.0 or later.")
        return (notice if mark(directory, f"nopricer-{sid}") else None), [], []
    turn = report.get("turn") or {}
    prompt = payload.get("prompt_id")
    spent = {
        "session": report.get("dollars") or 0.0,
        "day": (report.get("day") or {}).get("dollars") or 0.0,
        "turn": (turn.get("dollars") or 0.0) if prompt and turn.get("prompt_id") == prompt else 0.0,
    }
    keys = {"session": sid, "day": (report.get("day") or {}).get("date", ""), "turn": f"{sid}-{prompt}"}
    hard = os.environ.get("BUDGET_HARD_DENY") == "1"
    messages, decisions = [], []
    for scope, _, label in SCOPES:
        if caps[scope]:
            message, decision = ladder(directory, f"{scope}-{safe(keys[scope])}", label, spent[scope], caps[scope], hard)
            if decision:
                decisions.append((message, decision))
            elif message:
                messages.append(message)
    if warn_line and spent["session"] >= warn_line and mark(directory, f"session-{sid}-warnline"):
        messages.append(f"[Budget] Session spend ~{usd(spent['session'])} passed your {usd(warn_line)} warning line.")
    return None, messages, decisions


def gate_texts(decisions, dont_ask):
    """The decision for this call and the text for each cap at its limit."""
    deny = dont_ask or any(kind == "deny" for _, (kind, _) in decisions)
    texts = []
    for core, (kind, then) in decisions:
        if kind == "deny":
            texts.append(f"{core}, {then}.")
        elif deny:
            texts.append(f"{core}; nobody can answer a prompt in dontAsk mode, so this call is denied.")
        else:
            texts.append(f"{core}. Allow this call to keep going; {then}.")
    return ("deny" if deny else "ask"), texts


def main():
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace") or "{}")
    except ValueError:
        payload = {}
    payload = payload if isinstance(payload, dict) else {}
    directory = log_dir()
    directory.mkdir(parents=True, exist_ok=True)
    sid = safe(payload.get("session_id") or "default")
    hook_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    calls = tool_message(count_call(directory, sid))
    try:
        notice, messages, decisions = money(payload, directory, sid, hook_dir)
    except Exception:  # pricing failed: keep the tool-call warning, never block
        notice, messages, decisions = None, [], []
    out = {}
    gate = payload.get("hook_event_name") == "PreToolUse" and payload.get("tool_name") not in NEVER_GATE
    if decisions and gate:
        decision, texts = gate_texts(decisions, payload.get("permission_mode") == "dontAsk")
        out["hookSpecificOutput"] = {"hookEventName": "PreToolUse", "permissionDecision": decision,
                                     "permissionDecisionReason": " ".join(texts) + f" {NOTE}"}
        if decision == "deny":
            messages.extend(texts)  # a deny reason goes to Claude, so tell the user too
    else:
        messages.extend(f"{core}." for core, _ in decisions)  # this call cannot be gated: warn only
    shown = [text for text in (calls, notice) if text] + ([" ".join(messages) + f" {NOTE}"] if messages else [])
    if shown:
        out["systemMessage"] = " ".join(shown)
    if out:
        print(json.dumps(out))


try:
    main()
except Exception:  # a budget hook never breaks the session: fail open, print nothing
    pass
PY

# Not exec: whatever Python does (or a python3 that is only the Windows Store
# stub), this script exits 0, so the tool call is never held up.
# The first interpreter that really is Python 3.10 or newer: the Windows Store
# python3 stub exits non-zero, so it is skipped instead of silently running nothing.
for PY in python3 python py; do
    if command -v "$PY" >/dev/null 2>&1 && "$PY" -c 'import sys; sys.exit(sys.version_info < (3, 10))' >/dev/null 2>&1; then
        "$PY" -c "$BUDGET_PY" "$HOOK_DIR" 2>/dev/null
        break
    fi
done
exit 0
