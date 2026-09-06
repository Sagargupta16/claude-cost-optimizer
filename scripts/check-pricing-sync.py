#!/usr/bin/env python3
"""Guard the repo against the four pricing-drift failures that shipped in v1.12.0.

This repo's product is being a trustworthy pricing reference, so drift between
files is the core product risk. A hand-followed sync checklist lives at the end
of docs/pricing-data.md and it has already failed twice: v1.12.0 re-verified
every rate on 2026-09-05 but left 16 provenance stamps reading 2026-07-25, and
moved Opus 4.1 to the retired list in 2 files while 4 others still called it
"retiring soon".

Both counts are measured, not estimated, and the basis matters because a bare
count here would be the same defect this script exists to catch. Against
3e3a975 (the v1.12.0 tree), the two stamp patterns below match 16 occurrences
of 2026-07-25. For Opus 4.1, counting files whose Opus 4.1 line uses
"retired" versus "retires"/"retiring" and excluding CHANGELOG.md, which
narrates both states by design, gives 2 and 4.

Four checks, each mapped to a defect that actually shipped:

  1. verified-date consistency -- every "verified <date>" / "pricing as of
     <date>" stamp must equal the canonical date in tools/claude-rate/rate.py.
  2. stale retirement tense -- no file may say a model "retires" on a date that
     has already passed.
  3. relative dates -- no "N days out" style countdowns, which are correct only
     on the day they are written.
  4. doc freshness dates -- an "Updated <date>" / "As of <date>" banner must not
     be older than the canonical verified date. Check 1 alone missed five of
     these, because they are not phrased as pricing stamps.

What this does NOT do: check 1 enforces *agreement* with rate.py, not
correctness. Bump _PRICING_VERIFIED_DATE only after re-reading Anthropic's
pricing pages; a clean run means the tree is internally consistent with whatever
date that constant holds, nothing more.

Exit 0 when clean, 1 with a per-file report otherwise. Run from the repo root.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

# The one place the verified date is defined. Everything else must agree with it.
CANONICAL_SOURCE = Path("tools/claude-rate/rate.py")
CANONICAL_PATTERN = re.compile(r'_PRICING_VERIFIED_DATE\s*=\s*"(\d{4}-\d{2}-\d{2})"')

SCANNED_SUFFIXES = {".md", ".py", ".ts", ".tsx", ".json"}

# Paths that legitimately carry many historical dates.
EXCLUDED_NAMES = {"CHANGELOG.md"}
EXCLUDED_DIR_PARTS = {
    "node_modules",
    "dist",
    "out",
    "build",
    "__pycache__",
    ".git",
    ".ruff_cache",
    ".venv",
}

# Check 1. A provenance stamp is a date introduced by "verified" or by
# "pricing as of". "pricing. As of <date>, X is GA on Bedrock" is a claim about
# availability rather than a pricing stamp, so the second pattern deliberately
# refuses a sentence break between "pricing" and "as of".
STAMP_PATTERNS = (
    re.compile(
        r"verified[:\s]+(?:against[^\n]{0,80}?)?(\d{4}-\d{2}-\d{2})", re.IGNORECASE
    ),
    re.compile(r"pricing ?\(?as of:?\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE),
    CANONICAL_PATTERN,
)

# Check 2. Future-tense retirement wording plus a date. Past tense ("retired
# 2026-08-05") is correct and must not be flagged, so only "retires"/"retiring"
# match. The date may be ISO or "August 5, 2026" prose.
_MONTH_NAMES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
_MONTH_NUMBERS = {name.lower(): n for n, name in enumerate(_MONTH_NAMES, start=1)}
RETIRE_PATTERN = re.compile(
    r"retir(?:es|ing)\b[^.\n|]{0,40}?"
    r"(\d{4}-\d{2}-\d{2}|(?:" + "|".join(_MONTH_NAMES) + r") \d{1,2}, \d{4})",
    re.IGNORECASE,
)

# Check 3. Countdowns that are wrong the day after they are written.
RELATIVE_DATE_PATTERN = re.compile(
    r"\b(?:about|roughly|approximately|just|only)?\s*\d+\s+(?:days?|weeks?|months?)"
    r"\s+(?:out|away|from now)\b",
    re.IGNORECASE,
)

# Check 4. Doc-freshness banners of the "Updated <date>" and "As of <date>" shape.
# Check 1 deliberately refuses a sentence break between "pricing" and "as of",
# which is what let five of these survive a release that re-verified everything.
# The date must follow the phrase immediately, so a historical clause such as
# "As of Opus 5's GA on <date>" is left alone.
FRESHNESS_PATTERN = re.compile(
    r"\b(?:updated|as of|at the time of writing)\b[:\s]*\(?(\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)


def parse_date(raw: str) -> dt.date:
    """Parse either 2026-08-05 or 'August 5, 2026' into a calendar date."""
    try:
        return dt.date.fromisoformat(raw)
    except ValueError:
        month, day, year = raw.replace(",", "").split()
        return dt.date(int(year), _MONTH_NUMBERS[month.lower()], int(day))


def canonical_date(root: Path) -> str:
    source = root / CANONICAL_SOURCE
    match = CANONICAL_PATTERN.search(source.read_text(encoding="utf-8"))
    if not match:
        sys.exit(f"error: no _PRICING_VERIFIED_DATE found in {CANONICAL_SOURCE}")
    return match.group(1)


def scanned_files(root: Path) -> list[Path]:
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in SCANNED_SUFFIXES:
            continue
        if path.name in EXCLUDED_NAMES:
            continue
        if EXCLUDED_DIR_PARTS & set(path.relative_to(root).parts):
            continue
        files.append(path)
    return files


def _stamp_problems(line: str, expected: str) -> list[str]:
    problems: list[str] = []
    for pattern in STAMP_PATTERNS:
        for match in pattern.finditer(line):
            found = match.group(1)
            if found != expected:
                problems.append(
                    f"verified date {found} does not match the canonical "
                    f"{expected} (from {CANONICAL_SOURCE})"
                )
    return problems


def _retirement_problems(line: str, today: dt.date) -> list[str]:
    problems: list[str] = []
    for match in RETIRE_PATTERN.finditer(line):
        when = parse_date(match.group(1))
        if when <= today:
            problems.append(
                f'says a model "retires" on {when}, which has already passed '
                f"-- use past tense and move it to the retired list"
            )
    return problems


def _countdown_problems(line: str) -> list[str]:
    return [
        f"relative date {match.group(0).strip()!r} -- state an absolute date "
        f"instead, it cannot stay correct"
        for match in RELATIVE_DATE_PATTERN.finditer(line)
    ]


def _freshness_problems(line: str, expected: str) -> list[str]:
    problems: list[str] = []
    for match in FRESHNESS_PATTERN.finditer(line):
        found = match.group(1)
        if found < expected:
            problems.append(
                f"doc freshness date {found} is older than the canonical verified "
                f"date {expected} -- re-check the claim and restate it, or drop it"
            )
    return problems


def check_file(path: Path, rel: str, expected: str, today: dt.date) -> list[str]:
    """Return one problem string per defect found in this file."""
    problems: list[str] = []
    text = path.read_text(encoding="utf-8", errors="replace")

    for lineno, line in enumerate(text.splitlines(), start=1):
        found = (
            _stamp_problems(line, expected)
            + _retirement_problems(line, today)
            + _countdown_problems(line)
            + _freshness_problems(line, expected)
        )
        problems.extend(f"{rel}:{lineno}: {problem}" for problem in found)

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root", nargs="?", default=".", help="repo root to check (default: .)"
    )
    parser.add_argument(
        "--today",
        default=None,
        help="override today's date (YYYY-MM-DD) for testing the retirement check",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    today = (
        dt.date.fromisoformat(args.today)
        if args.today
        else dt.datetime.now(tz=dt.timezone.utc).date()
    )
    expected = canonical_date(root)

    problems: list[str] = []
    files = scanned_files(root)
    for path in files:
        rel = path.relative_to(root).as_posix()
        problems.extend(check_file(path, rel, expected, today))

    print(f"check-pricing-sync: canonical verified date is {expected}")
    print(f"check-pricing-sync: scanned {len(files)} files")

    if problems:
        print(f"\n{len(problems)} problem(s) found:\n")
        for problem in problems:
            print(f"  {problem}")
        print(
            "\nFix the files above, or update _PRICING_VERIFIED_DATE in "
            f"{CANONICAL_SOURCE} if the whole repo was re-verified."
        )
        return 1

    print("check-pricing-sync: OK -- all stamps agree and no stale retirement wording")
    return 0


if __name__ == "__main__":
    sys.exit(main())
