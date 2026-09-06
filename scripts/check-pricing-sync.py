#!/usr/bin/env python3
"""Guard the repo against the three pricing-drift failures that shipped in v1.12.0.

This repo's product is being a trustworthy pricing reference, so drift between
files is the core product risk. A hand-followed sync checklist lives at the end
of docs/pricing-data.md and it has already failed twice: v1.12.0 re-verified
every rate on 2026-09-05 but left 16 provenance stamps reading 2026-07-25, and
moved Opus 4.1 to the retired list in 2 files while 8 others still called it
"retiring soon".

Three checks, each mapped to a defect that actually shipped:

  1. verified-date consistency -- every "verified <date>" / "pricing as of
     <date>" stamp must equal the canonical date in tools/claude-rate/rate.py.
  2. stale retirement tense -- no file may say a model "retires" on a date that
     has already passed.
  3. relative dates -- no "N days out" style countdowns, which are correct only
     on the day they are written.

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


def check_file(path: Path, rel: str, expected: str, today: dt.date) -> list[str]:
    """Return one problem string per defect found in this file."""
    problems: list[str] = []
    text = path.read_text(encoding="utf-8", errors="replace")

    for lineno, line in enumerate(text.splitlines(), start=1):
        for pattern in STAMP_PATTERNS:
            for match in pattern.finditer(line):
                found = match.group(1)
                if found != expected:
                    problems.append(
                        f"{rel}:{lineno}: verified date {found} does not match the "
                        f"canonical {expected} (from {CANONICAL_SOURCE})"
                    )

        for match in RETIRE_PATTERN.finditer(line):
            when = parse_date(match.group(1))
            if when <= today:
                problems.append(
                    f'{rel}:{lineno}: says a model "retires" on {when}, which has '
                    f"already passed -- use past tense and move it to the retired list"
                )

        for match in RELATIVE_DATE_PATTERN.finditer(line):
            problems.append(
                f"{rel}:{lineno}: relative date {match.group(0).strip()!r} -- "
                f"state an absolute date instead, it cannot stay correct"
            )

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
