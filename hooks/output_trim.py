#!/usr/bin/env python3
"""output_trim.py -- opt-in PostToolUse hook that shortens noisy runner output.

Claude Code runs this after a Bash call that exited 0 and sends one JSON
payload on stdin. When the command is a build, install or test runner and its
output is long, the hook prints hookSpecificOutput.updatedToolOutput so Claude
reads a shorter copy: the first and last lines, every error/warn/fail line with
two lines of context, ANSI codes and redraws stripped, repeated lines folded
to a count. The full output goes to a .txt file named in the footer.

Everything else passes through untouched, and the hook prints nothing:
a read-like command (cat, grep, git diff ...), a command whose first real
program is not a known runner, a pipeline, output under CLAUDE_TRIM_MIN_CHARS,
a trim that is not at least 20% shorter, any error inside this script.

Scope: PostToolUse only sees runs that exited 0 (builds, installs, passing
suites). A failed run goes to PostToolUseFailure, which cannot rewrite output,
so this hook never sees one. The tool has already run and OpenTelemetry records
the original output; only what Claude reads changes.

Needs Claude Code 2.1.121 or later (changelog: PostToolUse hooks can replace
tool output for all tools through updatedToolOutput; read 2026-11-03).

Environment:
  CLAUDE_TRIM_OFF=1         kill switch
  CLAUDE_TRIM_MIN_CHARS=N   leave output shorter than N characters alone (default 2000)

Per-session stats (appended, no command text):
  ${TMPDIR:-/tmp}/claude-trim/<session>/stats.tsv
  columns: time, runner, chars before, chars after, lines before, lines kept
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
import tempfile
import time
from pathlib import Path

DEFAULT_MIN_CHARS = 2000
HEAD_LINES = 30
TAIL_LINES = 40
CONTEXT_LINES = 2
MAX_SIGNAL_HITS = 40
FOLD_IDENTICAL = 3
FOLD_SIMILAR = 4
MIN_SAVING = 0.20

ANSI_RE = re.compile(
    r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\)?|[@-Z\\-_])"
)
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
DIGITS_RE = re.compile(r"\d+")
SIGNAL_RE = re.compile(
    r"\b(?:err|error|errors|fail|failed|failure|failures|fatal|panic|exception|"
    r"traceback|warn|warning|warnings|deprecated|deprecation|assert\w*)\b",
    re.IGNORECASE,
)
# Result lines a runner prints once at its end. A chain of runners puts all but
# the last of these in the middle of the output, where head and tail miss them.
SUMMARY_RE = re.compile(
    r"\b\d+ (?:passed|passing|failed|skipped|deselected)\b"  # pytest, vitest, jest, mocha
    r"|^Ran \d+ tests? in\b|^OK\b"  # unittest
    r"|^(?:ℹ|#) [a-z_]+ [\d.]+$"  # node:test spec and TAP
    r"|^(?:Done in|added \d+ packages|Successfully installed|BUILD SUCCESS|test result:)"
)

# -- Which commands count as a runner -----------------------------------------

SEGMENT_RE = re.compile(r"&&|\|\||;|\n")
ENV_ASSIGN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
SCRIPT_RE = re.compile(r"(?:test|build|compile|typecheck|check)(?:[:\-].*)?")

TRIVIAL = frozenset(
    {
        "cd",
        "pushd",
        "popd",
        "export",
        "set",
        "unset",
        "source",
        ".",
        "true",
        ":",
        "echo",
    }
)
READ_LIKE = frozenset(
    {
        "cat", "head", "tail", "sed", "awk", "grep", "egrep", "fgrep", "rg", "ag", "ls", "dir",
        "find", "fd", "less", "more", "bat", "type", "tree", "wc", "cut", "jq", "sort",
    }
)  # fmt: skip
GIT_READ = frozenset(
    {"diff", "show", "log", "blame", "grep", "status", "ls-files", "cat-file"}
)

DIRECT_RUNNERS = frozenset(
    {
        "pytest",
        "py.test",
        "vitest",
        "jest",
        "mocha",
        "tsc",
        "mvn",
        "mvnw",
        "gradle",
        "gradlew",
    }
)
PYTHONS = frozenset({"python", "python3", "py"})
PACKAGE_MANAGERS = frozenset({"npm", "pnpm", "yarn", "bun"})
PACKAGE_SUBCOMMANDS = frozenset({"test", "t", "install", "i", "ci", "add", "build"})
SUBCOMMANDS = {
    "go": frozenset({"test", "build", "vet"}),
    "cargo": frozenset({"test", "build", "check", "clippy", "nextest"}),
    "dotnet": frozenset({"test", "build", "restore"}),
    "uv": frozenset({"sync"}),
    "pip": frozenset({"install"}),
    "pip3": frozenset({"install"}),
}
VALUE_OPTIONS = frozenset(
    {
        "--dir", "-C", "--cwd", "--prefix", "--filter", "-F", "--workspace", "-w", "--directory",
        "--project", "--with", "--python", "-p", "--extra", "--group", "--manifest-path", "--package",
    }
)  # fmt: skip


def _base(token: str) -> str:
    name = token.replace("\\", "/").rsplit("/", 1)[-1].lower()
    return re.sub(r"\.(?:exe|cmd|bat|ps1)$", "", name)


def _skip_options(tokens: list[str]) -> list[str]:
    """Drop leading env assignments and options (with their values) from tokens."""
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if ENV_ASSIGN_RE.match(token):
            i += 1
        elif token.startswith("-"):
            i += 2 if token in VALUE_OPTIONS else 1
        else:
            break
    return tokens[i:]


def _positionals(args: list[str]) -> list[str]:
    """Positional words before a bare `--`, skipping options and +toolchain."""
    found: list[str] = []
    skip = False
    for arg in args:
        if skip:
            skip = False
        elif arg == "--":
            break
        elif arg.startswith("-"):
            skip = arg in VALUE_OPTIONS
        elif not arg.startswith("+"):
            found.append(arg)
    return found


def _unwrap(tokens: list[str]) -> list[str]:
    """Step through time, env, npx, uv run, pnpm exec ... to the real program."""
    while tokens:
        name, rest = _base(tokens[0]), tokens[1:]
        if name in {"time", "command", "nohup", "exec", "env", "npx", "bunx", "pnpx"}:
            tokens = _skip_options(rest)
            continue
        after = _skip_options(rest)
        if name in {"uv", "poetry", "pipenv"} and after[:1] == ["run"]:
            tokens = _skip_options(after[1:])
        elif name in {"pnpm", "yarn", "bun"} and after[:1] in (
            ["exec"],
            ["dlx"],
            ["x"],
        ):
            tokens = _skip_options(after[1:])
        else:
            break
    return tokens


def _match_python(args: list[str]) -> str | None:
    if "-m" not in args:
        return None
    at = args.index("-m")
    module = args[at + 1 : at + 2]
    if module in (["pytest"], ["unittest"]):
        return f"python -m {module[0]}"
    if module == ["pip"] and _positionals(args[at + 2 :])[:1] == ["install"]:
        return "python -m pip install"
    return None


def _match_runner(tokens: list[str]) -> str | None:
    if not tokens:
        return None
    name, args = _base(tokens[0]), tokens[1:]
    if name in DIRECT_RUNNERS:
        return name
    if name in PYTHONS:
        return _match_python(args)
    if name == "node":
        return "node --test" if "--test" in args else None
    words = _positionals(args)
    sub = words[0] if words else ""
    if name in PACKAGE_MANAGERS:
        if sub in PACKAGE_SUBCOMMANDS:
            return f"{name} {sub}"
        if (
            sub in ("run", "run-script")
            and len(words) > 1
            and SCRIPT_RE.fullmatch(words[1])
        ):
            return f"{name} run {words[1]}"
        return None
    if name == "uv" and sub == "pip" and words[1:2] == ["install"]:
        return "uv pip install"
    return f"{name} {sub}" if sub in SUBCOMMANDS.get(name, ()) else None


def _is_read_like(tokens: list[str]) -> bool:
    name = _base(tokens[0])
    if name == "git":
        return (
            bool(_positionals(tokens[1:])[:1])
            and _positionals(tokens[1:])[0] in GIT_READ
        )
    return name in READ_LIKE


def runner_of(command: str) -> str | None:
    """Runner name when the first real command is a runner and nothing is read-like."""
    if "|" in command.replace("||", ";"):
        return None  # a pipeline: the caller already shaped the output
    runner: str | None = None
    for segment in SEGMENT_RE.split(command):
        try:
            tokens = shlex.split(segment, posix=True)
        except ValueError:
            return None
        while tokens and ENV_ASSIGN_RE.match(tokens[0]):
            tokens = tokens[1:]
        if not tokens or _base(tokens[0]) in TRIVIAL:
            continue
        tokens = _unwrap(tokens)
        if not tokens or _is_read_like(tokens):
            return None
        if runner is None:
            runner = _match_runner(tokens)
            if runner is None:
                return None
    return runner


# -- Trimming -------------------------------------------------------------------


def clean_lines(text: str) -> list[str]:
    """Strip ANSI codes and control characters, keep only the last redraw of a line."""
    text = CONTROL_RE.sub("", ANSI_RE.sub("", text.replace("\r\n", "\n")))
    lines = []
    for raw in text.split("\n"):
        parts = [part for part in raw.split("\r") if part.strip()]
        lines.append((parts[-1] if parts else "").rstrip())
    if lines and not lines[-1]:
        lines.pop()
    return lines


def _fold_run(run: list[str]) -> tuple[list[str], int]:
    count = len(run)
    if not run[0].strip():
        return run[:1], count - 1
    if all(line == run[0] for line in run):
        if count >= FOLD_IDENTICAL:
            return [
                run[0],
                f"[trim: previous line repeated {count - 1} more times]",
            ], count - 1
        return run, 0
    if count >= FOLD_SIMILAR and not any(SIGNAL_RE.search(line) for line in run):
        return [
            run[0],
            f"[trim: {count - 2} similar lines folded, only digits differ]",
            run[-1],
        ], count - 2
    return run, 0


def fold_runs(lines: list[str]) -> tuple[list[str], int]:
    """Fold runs of identical or digit-only-different lines; return (lines, dropped)."""
    out: list[str] = []
    dropped = 0
    i = 0
    while i < len(lines):
        key = DIGITS_RE.sub("#", lines[i])
        j = i + 1
        while j < len(lines) and DIGITS_RE.sub("#", lines[j]) == key:
            j += 1
        folded, gone = _fold_run(lines[i:j])
        out.extend(folded)
        dropped += gone
        i = j
    return out, dropped


def select_lines(lines: list[str]) -> tuple[list[str], int]:
    """Keep head, tail and signal lines with context; return (lines, omitted)."""
    n = len(lines)
    if n <= HEAD_LINES + TAIL_LINES:
        return lines, 0
    keep = set(range(HEAD_LINES)) | set(range(n - TAIL_LINES, n))
    hits = [i for i in range(HEAD_LINES, n - TAIL_LINES) if SIGNAL_RE.search(lines[i])]
    for i in hits[:MAX_SIGNAL_HITS]:
        keep.update(range(max(0, i - CONTEXT_LINES), min(n, i + CONTEXT_LINES + 1)))
    summaries = [i for i in range(HEAD_LINES, n - TAIL_LINES) if SUMMARY_RE.search(lines[i])]
    keep.update(summaries[:MAX_SIGNAL_HITS])
    out: list[str] = []
    omitted = 0
    i = 0
    while i < n:
        if i in keep:
            out.append(lines[i])
            i += 1
            continue
        j = i
        while j < n and j not in keep:
            j += 1
        flagged = sum(1 for k in range(i, j) if SIGNAL_RE.search(lines[k]))
        note = f", {flagged} of them matched error/warn/fail" if flagged else ""
        out.append(f"[trim: {j - i} lines omitted{note}]")
        omitted += j - i
        i = j
    return out, omitted


def trim_stream(text: str) -> tuple[str, int, int]:
    """Return (trimmed text, lines before, lines kept)."""
    lines = clean_lines(text)
    folded, dropped = fold_runs(lines)
    kept, omitted = select_lines(folded)
    return "\n".join(kept), len(lines), len(lines) - dropped - omitted


# -- The hook ---------------------------------------------------------------------


def _safe(value: object, default: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]", "_", str(value or ""))[:80].strip(".")
    return cleaned or default


def _spill_path(payload: dict) -> Path:
    folder = (
        Path(tempfile.gettempdir())
        / "claude-trim"
        / _safe(payload.get("session_id"), "default")
    )
    return (
        folder
        / f"{_safe(payload.get('tool_use_id'), str(int(time.time() * 1000)))}.txt"
    )


def _write_spill(path: Path, out: str, err: str) -> bool:
    body = f"{out}\n--- stderr ---\n{err}" if err else out
    try:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(
            fd, "w", encoding="utf-8", errors="replace", newline=""
        ) as handle:
            handle.write(body)
    except OSError:
        return False
    return True


def _log_stats(
    folder: Path, runner: str, before: int, after: int, lines: int, kept: int
) -> None:
    row = f"{time.strftime('%H:%M:%S')}\t{runner}\t{before}\t{after}\t{lines}\t{kept}\n"
    try:
        with open(folder / "stats.tsv", "a", encoding="utf-8") as handle:
            handle.write(row)
    except OSError:
        pass


def _min_chars() -> int:
    try:
        return int(os.environ.get("CLAUDE_TRIM_MIN_CHARS", DEFAULT_MIN_CHARS))
    except ValueError:
        return DEFAULT_MIN_CHARS


def _trim_response(
    payload: dict, response: dict, runner: str, out: str, err: str
) -> tuple[dict | None, str]:
    before = len(out) + len(err)
    new_out, out_lines, out_kept = trim_stream(out)
    new_err, err_lines, err_kept = trim_stream(err)
    path = _spill_path(payload)
    footer = (
        f"[trim: showing {out_kept + err_kept} of {out_lines + err_lines} lines; "
        f"full output ({before} chars) is in {path.as_posix()}]"
    )
    if new_err:
        new_err = f"{new_err}\n{footer}"
    else:
        new_out = f"{new_out}\n{footer}" if new_out else footer
    after = len(new_out) + len(new_err)
    if after > before * (1 - MIN_SAVING):
        return None, "saving-under-20-percent"
    if not _write_spill(path, out, err):
        return None, "no-spill-file"
    _log_stats(
        path.parent, runner, before, after, out_lines + err_lines, out_kept + err_kept
    )
    updated = dict(response)
    updated["stdout"] = new_out
    updated["stderr"] = new_err
    return updated, "trimmed"


def process(payload: dict) -> tuple[dict | None, str]:
    """Return (updated tool_response or None to pass through, reason)."""
    if os.environ.get("CLAUDE_TRIM_OFF") == "1":
        return None, "kill-switch"
    if payload.get("tool_name") != "Bash" or payload.get("hook_event_name") not in (
        None,
        "PostToolUse",
    ):
        return None, "not-a-bash-post-tool-use"
    tool_input = payload.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    runner = runner_of(command) if isinstance(command, str) else None
    if runner is None:
        return None, "not-a-runner"
    response = payload.get("tool_response")
    if (
        not isinstance(response, dict)
        or response.get("interrupted")
        or response.get("isImage")
    ):
        return None, "unusable-response"
    if response.get("backgroundTaskId"):
        return None, "background-task"
    out, err = response.get("stdout"), response.get("stderr") or ""
    if not isinstance(out, str) or not isinstance(err, str):
        return None, "unusable-response"
    if len(out) + len(err) < _min_chars():
        return None, "below-min-chars"
    return _trim_response(payload, response, runner, out, err)


def main() -> int:
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace"))
        updated, _reason = process(payload) if isinstance(payload, dict) else (None, "")
        if updated is not None:
            sys.stdout.write(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "PostToolUse",
                            "updatedToolOutput": updated,
                        }
                    }
                )
            )
    except Exception:  # fail open: a hook bug must never change or block a tool result
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
