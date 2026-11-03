#!/usr/bin/env python3
"""Count the characters git prints with and without its compact flags, at a pinned commit.

Each row runs a pair of read-only, offline git commands against one fixed commit of this
repository: the full form (``git diff A B``) and the compact form (``git diff --stat A B``).
It prints the exact character count of each output as a Markdown table for
benchmarks/search-ladder.md.

What the numbers are, and are not:

- Exact characters are the primary number. Estimated tokens use this repo's convention,
  chars / 4 x 1.3 (the 4.7+ tokenizer factor in tools/claude-rate/rate.py); guide 01's
  "about 2.5 characters per token" gives about 23% more tokens for the same text.
- Claude Code keeps a valid Bash result inline up to about 30,000 characters. A longer one
  reaches Claude as a file path plus a preview of up to 2,000 characters, and Claude reads or
  searches the file when it needs more; a failing command gets about 10,000 characters inline
  (tools reference, https://code.claude.com/docs/en/tools-reference, read 2026-11-03). For a
  full output over 30,000 characters the script therefore computes no saving: what that row
  costs depends on what Claude reads next.
- One repository, one commit, deterministic output. It is not a session measurement.

git output is pinned with ``-c`` overrides (no colour, no pager, no signatures or decorations,
myers diff, 7-character abbreviations, medium log format) and COLUMNS=80, so a user's own
git config does not change the counts.
"""

from __future__ import annotations

import argparse
import math
import os
import subprocess
import sys
from pathlib import Path

PINNED_SHA = "8e337f0"
INLINE_CAP = 30_000
PREVIEW_CHARS = 2_000
FAILURE_CAP = 10_000

GIT_PINS = [
    "-c", "color.ui=never",
    "-c", "core.pager=cat",
    "-c", "core.abbrev=7",
    "-c", "core.quotePath=true",
    "-c", "log.showSignature=false",
    "-c", "log.decorate=no",
    "-c", "log.abbrevCommit=false",
    "-c", "log.mailmap=false",
    "-c", "log.date=default",
    "-c", "format.pretty=medium",
    "-c", "diff.algorithm=myers",
    "-c", "diff.context=3",
    "-c", "diff.interHunkContext=0",
    "-c", "diff.renames=true",
    "-c", "diff.noprefix=false",
    "-c", "diff.mnemonicPrefix=false",
    "-c", "diff.relative=false",
]  # fmt: skip

DIFF_FLAGS = ["--no-ext-diff", "--no-textconv"]

# (label, full args, compact args); "{sha}" is replaced by the pinned commit.
PAIRS: list[tuple[str, list[str], list[str]]] = [
    (
        "`git diff {sha}~1 {sha}` vs `--stat`",
        ["diff", *DIFF_FLAGS, "{sha}~1", "{sha}"],
        ["diff", *DIFF_FLAGS, "--stat", "{sha}~1", "{sha}"],
    ),
    (
        "`git log -20 {sha}` vs `--oneline`",
        ["log", "-20", "{sha}"],
        ["log", "--oneline", "-20", "{sha}"],
    ),
    (
        "`git show {sha}` vs `--stat`",
        ["show", *DIFF_FLAGS, "{sha}"],
        ["show", *DIFF_FLAGS, "--stat", "{sha}"],
    ),
]

# Rows this repository cannot run offline at a pinned commit, listed so the table says so.
UNMEASURED: list[tuple[str, str]] = [
    (
        "`git status` vs `git status --short`",
        "output depends on the working tree, not a commit",
    ),
    ("`gh pr view` vs `gh pr view --json <fields>`", "needs network and GitHub auth"),
    ("`gh run view --log` vs `--log-failed`", "needs network and GitHub auth"),
    ("`docker ps` vs `docker ps --format`", "needs a Docker daemon"),
    ("`kubectl get` vs `-o name` / custom columns", "needs a cluster"),
    ("`aws ...` vs `--query ... --output text`", "needs AWS credentials and resources"),
    ("`pytest` vs `pytest -q --tb=short`", "this repo's Python tests use unittest"),
    ("`jest` vs `jest --silent`", "this repo's site tests use vitest"),
]


def est_tokens(chars: int) -> int:
    """Estimate tokens with this repo's convention: chars / 4 x 1.3, rounded up."""
    return math.ceil(chars / 4 * 1.3)


def run_git(repo: Path, args: list[str]) -> str:
    """Run one read-only git command with the output pins and return its stdout as text."""
    env = {**os.environ, "COLUMNS": "80", "GIT_PAGER": "cat", "LC_ALL": "C"}
    result = subprocess.run(
        ["git", "-C", str(repo), *GIT_PINS, *args],
        capture_output=True,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {message}")
    return result.stdout.decode("utf-8", errors="replace")


def resolve_commit(repo: Path, sha: str) -> str:
    """Return the full hash of ``sha``, or raise if this clone does not have it."""
    return run_git(repo, ["rev-parse", "--verify", f"{sha}^{{commit}}"]).strip()


def note_for(full: int, compact: int) -> str:
    """Explain what the full output costs given Claude Code's inline cap."""
    if full > INLINE_CAP:
        return (
            f"full output is over the {INLINE_CAP:,}-char inline cap: Claude gets a file path"
            f" plus a {PREVIEW_CHARS:,}-char preview, and the cost depends on what it reads"
            " next, so no saving is computed"
        )
    saved = full - compact
    return f"compact form is {saved:,} chars ({saved / full:.1%}) shorter; both under the cap"


def measure(repo: Path, sha: str) -> list[str]:
    """Run every pair and return the Markdown table lines."""
    lines = [
        "| Command pair | Full chars | Compact chars | Full est. tokens | Compact est. tokens | Note |",
        "|---|--:|--:|--:|--:|---|",
    ]
    for label, full_args, compact_args in PAIRS:
        full = len(run_git(repo, [a.replace("{sha}", sha) for a in full_args]))
        compact = len(run_git(repo, [a.replace("{sha}", sha) for a in compact_args]))
        lines.append(
            f"| {label.replace('{sha}', sha)} | {full:,} | {compact:,} | {est_tokens(full):,}"
            f" | {est_tokens(compact):,} | {note_for(full, compact)} |"
        )
    for label, reason in UNMEASURED:
        lines.append(f"| {label} | not measured | not measured | - | - | {reason} |")
    return lines


def parse_args() -> argparse.Namespace:
    """Parse the command line."""
    parser = argparse.ArgumentParser(
        description="Count characters of git output with and without compact flags at a pinned commit."
    )
    parser.add_argument(
        "--sha",
        default=PINNED_SHA,
        help=f"commit to measure (default {PINNED_SHA}, the commit benchmarks/search-ladder.md uses)",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="repository root (default: this script's repository)",
    )
    return parser.parse_args()


def main() -> int:
    """Print the measurement table, or a clear error when git or the commit is missing."""
    args = parse_args()
    try:
        full_sha = resolve_commit(args.repo, args.sha)
        version = run_git(args.repo, ["--version"]).strip()
        table = measure(args.repo, args.sha)
    except FileNotFoundError:
        print("error: git is not on PATH", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(
            f"error: {exc} (a shallow clone may lack commit {args.sha})",
            file=sys.stderr,
        )
        return 1
    print(f"Commit {full_sha}, {version}, COLUMNS=80.")
    print(
        f"est. tokens = chars / 4 x 1.3; inline cap {INLINE_CAP:,} chars (failing commands {FAILURE_CAP:,})."
    )
    print()
    print("\n".join(table))
    return 0


if __name__ == "__main__":
    sys.exit(main())
