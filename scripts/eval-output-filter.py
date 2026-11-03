#!/usr/bin/env python3
"""eval-output-filter.py -- measure hooks/output_trim.py on captured runner output.

For every fixture in benchmarks/filter-fixtures/ (output captured from this
repo's own test and install runs) this builds the PostToolUse payload the hook
would receive, runs the hook's real decision path (command gate, size gate,
trim, never-worse guard) and prints what changed:

  bytes and lines before and after, as measured
  estimated tokens before and after, a labelled estimate (see TOKEN NOTE)
  needed_dropped: strings listed in labels.json under "needed" that the trimmed
                  output no longer contains (each is checked to exist in the raw
                  fixture, after ANSI codes are removed)
  growth: bytes added when the trimmed output is larger than the raw output

Controls in labels.json run a fixture under a command the hook must not touch
(cat, a pipeline, git diff); one that gets trimmed is a failure.

Only runs that exit 0 are measured: PostToolUse never fires for a failed run,
so there are no failing fixtures.

  python scripts/eval-output-filter.py            print the table
  python scripts/eval-output-filter.py --strict   exit 1 on any dropped needed
                                                  string, any growth, or any
                                                  control that was trimmed
  python scripts/eval-output-filter.py --dir DIR  use another fixture folder
                                                  (needs its own labels.json)

Exit codes: 0 ok, 1 strict failure, 2 bad fixtures or labels.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "benchmarks" / "filter-fixtures"
HOOK = ROOT / "hooks" / "output_trim.py"
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")

# TOKEN NOTE: tokens are an estimate, not a count: characters / 4, times 1.3 for
# the 4.7+ tokenizer (repo CLAUDE.md "Pricing Data"). Real counts depend on the text.
TOKEN_NOTE = "est. tokens = round(characters / 4 * 1.3): a rule-of-thumb estimate (1.3 = 4.7+ tokenizer factor), not a token count"


def est_tokens(chars: int) -> int:
    return round(chars / 4 * 1.3)


def load_hook() -> ModuleType:
    spec = importlib.util.spec_from_file_location("output_trim", HOOK)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {HOOK}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def payload_for(name: str, command: str, text: str, stream: str) -> dict:
    response = {"stdout": text, "stderr": "", "interrupted": False, "isImage": False}
    if stream == "stderr":
        response["stdout"], response["stderr"] = "", text
    return {
        "hook_event_name": "PostToolUse",
        "session_id": "eval-output-filter",
        "tool_use_id": f"toolu_{re.sub(r'[^A-Za-z0-9]', '_', name)}",
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "tool_response": response,
    }


def run_hook(
    hook: ModuleType, name: str, command: str, text: str, stream: str
) -> tuple[dict | None, str]:
    return hook.process(payload_for(name, command, text, stream))


def row_for(hook: ModuleType, name: str, spec: dict, text: str) -> dict:
    stream = spec.get("stream", "stdout")
    plain = ANSI_RE.sub("", text)
    needed = spec.get("needed", [])
    missing = [item for item in needed if item not in plain]
    if missing:
        raise ValueError(f"{name}: needed text not in the raw fixture: {missing}")
    updated, reason = run_hook(hook, name, spec["command"], text, stream)
    after_text = text if updated is None else updated["stdout"] + updated["stderr"]
    joined = (
        after_text if updated is None else updated["stdout"] + "\n" + updated["stderr"]
    )
    before_bytes, after_bytes = len(text.encode()), len(after_text.encode())
    return {
        "name": name,
        "action": "trimmed" if updated is not None else f"pass ({reason})",
        "trimmed": updated is not None,
        "bytes_before": before_bytes,
        "bytes_after": after_bytes,
        "lines_before": len(text.splitlines()),
        "lines_after": len(after_text.splitlines()),
        "tokens_before": est_tokens(len(text)),
        "tokens_after": est_tokens(len(after_text)),
        "needed": len(needed),
        "needed_dropped": [item for item in needed if item not in joined],
        "growth": max(0, after_bytes - before_bytes),
    }


def control_failures(
    hook: ModuleType, controls: list[dict], directory: Path
) -> tuple[list[str], list[str]]:
    lines, failures = [], []
    for control in controls:
        text = (directory / control["fixture"]).read_bytes().decode("utf-8")
        updated, reason = run_hook(
            hook,
            control["fixture"],
            control["command"],
            text,
            control.get("stream", "stdout"),
        )
        verdict = "trimmed" if updated is not None else f"pass ({reason})"
        lines.append(f"  {verdict:<34} {control['command']}")
        if updated is not None:
            failures.append(f"control was trimmed: {control['command']}")
    return lines, failures


def print_table(rows: list[dict]) -> None:
    head = [
        "fixture",
        "action",
        "bytes in",
        "bytes out",
        "lines in",
        "lines out",
        "tok in",
        "tok out",
        "needed",
        "dropped",
        "growth",
    ]
    body = [
        [r["name"], r["action"], r["bytes_before"], r["bytes_after"], r["lines_before"], r["lines_after"],
         r["tokens_before"], r["tokens_after"], r["needed"], len(r["needed_dropped"]), r["growth"]]
        for r in rows
    ]  # fmt: skip
    totals = [
        "TOTAL", f"{sum(r['trimmed'] for r in rows)} of {len(rows)} trimmed",
        *(sum(r[k] for r in rows) for k in ("bytes_before", "bytes_after", "lines_before", "lines_after", "tokens_before", "tokens_after", "needed")),
        sum(len(r["needed_dropped"]) for r in rows), sum(r["growth"] for r in rows),
    ]  # fmt: skip
    table = [head, *body, totals]
    widths = [max(len(str(line[i])) for line in table) for i in range(len(head))]
    for number, line in enumerate(table):
        cells = [
            str(c).ljust(widths[i]) if i < 2 else str(c).rjust(widths[i])
            for i, c in enumerate(line)
        ]
        print("  ".join(cells).rstrip())
        if number in (0, len(table) - 2):
            print("  ".join("-" * w for w in widths))


def evaluate(directory: Path) -> tuple[list[dict], list[str], list[str]]:
    labels = json.loads((directory / "labels.json").read_text(encoding="utf-8"))
    hook = load_hook()
    rows = []
    for name, spec in labels["fixtures"].items():
        rows.append(
            row_for(hook, name, spec, (directory / name).read_bytes().decode("utf-8"))
        )
    control_lines, control_bad = control_failures(
        hook, labels.get("controls", []), directory
    )
    return rows, control_lines, control_bad


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure the output-trim hook on captured runner output."
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 on a dropped needed string, growth, or a trimmed control",
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=FIXTURES,
        help="fixture folder with labels.json (default: benchmarks/filter-fixtures)",
    )
    args = parser.parse_args()

    for var in ("CLAUDE_TRIM_OFF", "CLAUDE_TRIM_MIN_CHARS"):
        os.environ.pop(
            var, None
        )  # measure the defaults, whatever the caller's shell sets
    with tempfile.TemporaryDirectory() as scratch:
        tempfile.tempdir = (
            scratch  # the hook's full-output files land here and are removed
        )
        try:
            rows, control_lines, control_bad = evaluate(args.dir)
        except (OSError, ValueError, KeyError) as error:
            print(f"error: {error}", file=sys.stderr)
            return 2

    print_table(rows)
    print()
    print("controls (the hook must leave these alone):")
    print("\n".join(control_lines) or "  none")
    print()
    print(TOKEN_NOTE)
    print(
        "bytes and lines are measured; only runs that exit 0 reach this hook, so there are no failing fixtures"
    )

    failures = list(control_bad)
    for row in rows:
        if row["needed_dropped"]:
            failures.append(
                f"{row['name']}: needed text dropped: {row['needed_dropped']}"
            )
        if row["growth"]:
            failures.append(f"{row['name']}: output grew by {row['growth']} bytes")
    for failure in failures:
        print(f"FAIL {failure}")
    if args.strict and failures:
        return 1
    if args.strict:
        print("strict: ok (no needed text dropped, no growth, every control untouched)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
