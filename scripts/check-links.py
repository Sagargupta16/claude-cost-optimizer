#!/usr/bin/env python3
"""Validate every relative markdown link and heading anchor in the repo.

All four broken internal links found in the v1.12.0 audit were this exact
shape, and none of them needed the network to detect:

  * case-studies/README.md linked `/CONTRIBUTING.md` and
    `/.github/ISSUE_TEMPLATE/case-study.md`. A leading slash resolves against
    the domain on GitHub, not the repo, so both 404 for every visitor.
  * guides/06 linked `../README.md#off-peak-2x-usage-promotional-events`, an
    anchor that no longer exists anywhere in the README.
  * README linked `#pricing-reference-verified-2026-09-05` while the heading it
    targeted still carried the previous verification date, so the slug the
    heading actually produced did not match the link and the anchor was dead.

Deliberately offline. External URLs are skipped: they rot for reasons outside
this repo's control, which makes them a flaky CI gate rather than a useful one.

Exit 0 when clean, 1 with a per-link report otherwise.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# [text](target) -- skips image embeds only when they are inline `!` prefixed.
LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
# Trailing hashes and whitespace are stripped in code rather than in the pattern:
# a lazy group followed by optional trailing hashes backtracks super-linearly.
ATX_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")

# Any absolute URI (scheme-prefixed) plus hashbang routes. This checker is offline
# by design, so anything with a scheme is out of scope regardless of which one.
EXTERNAL_TARGET = re.compile(r"^(?:[A-Za-z][A-Za-z0-9+.-]*:|#!)")
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


def github_anchor(heading: str) -> str:
    """Reproduce GitHub's heading-to-anchor slug.

    GitHub lowercases, drops every character that is not a word character,
    whitespace, or a hyphen, then replaces each remaining whitespace character
    with a hyphen. Crucially it does not collapse runs, so "Legacy & Retired
    Models" becomes "legacy--retired-models" with a double hyphen -- the `&` is
    deleted and both surrounding spaces still become hyphens. Collapsing the run
    is what makes a naive slugifier report false positives on `&` and `+`.
    """
    text = re.sub(r"`([^`]*)`", r"\1", heading)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = text.replace("*", "")
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"\s", "-", text)


def anchors_in(path: Path) -> set[str]:
    """Every anchor a markdown file exposes: headings plus explicit HTML ids."""
    found: set[str] = set()
    text = path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        match = ATX_HEADING.match(line)
        if match:
            title = match.group(2).rstrip().rstrip("#").rstrip()
            found.add(github_anchor(title))
    for raw_id in re.findall(r"<a\s+(?:name|id)=[\"']([^\"']+)[\"']", text):
        found.add(raw_id.lower())
    for raw_id in re.findall(r"\sid=[\"']([^\"']+)[\"']", text):
        found.add(raw_id.lower())
    return found


def markdown_files(root: Path) -> list[Path]:
    # is_file() matters: templates/CLAUDE.md is a directory, not a file.
    return [
        p
        for p in sorted(root.rglob("*.md"))
        if p.is_file() and not EXCLUDED_DIR_PARTS & set(p.relative_to(root).parts)
    ]


def check_link(root: Path, source: Path, target: str) -> str | None:
    """Return a problem description, or None when the link resolves."""
    if EXTERNAL_TARGET.match(target):
        return None

    if target.startswith("/"):
        return (
            f"root-relative link {target!r} -- on GitHub this resolves against "
            f"the domain, not the repo. Use a path relative to this file."
        )

    path_part, _, fragment = target.partition("#")

    if not path_part:
        resolved = source
    else:
        resolved = (source.parent / path_part).resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            # The repo-root CLAUDE.md is required to link the workspace files that
            # sit above the repo root, so those are legitimately outside. Scoped to
            # that one path: any other CLAUDE.md in the tree gets checked normally.
            if source == root / "CLAUDE.md":
                return None
            return f"target escapes the repo: {target!r}"
        if not resolved.exists():
            return f"target does not exist: {target!r}"

    if fragment and resolved.suffix == ".md" and resolved.is_file():
        available = anchors_in(resolved)
        if fragment.lower() not in available:
            return f"anchor not found: {target!r} (no heading yields #{fragment})"

    return None


def check_file(root: Path, path: Path) -> tuple[int, list[str]]:
    """Return (internal link count, problem descriptions) for one markdown file."""
    rel = path.relative_to(root).as_posix()
    problems: list[str] = []
    link_count = 0

    text = path.read_text(encoding="utf-8", errors="replace")
    for lineno, line in enumerate(text.splitlines(), start=1):
        for match in LINK_PATTERN.finditer(line):
            target = match.group(1)
            if EXTERNAL_TARGET.match(target):
                continue
            link_count += 1
            problem = check_link(root, path, target)
            if problem:
                problems.append(f"{rel}:{lineno}: {problem}")

    return link_count, problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="repo root to check")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    problems: list[str] = []
    files = markdown_files(root)
    link_count = 0

    for path in files:
        found, file_problems = check_file(root, path)
        link_count += found
        problems.extend(file_problems)

    print(f"check-links: scanned {len(files)} files, {link_count} internal link(s)")

    if problems:
        print(f"\n{len(problems)} broken internal link(s):\n")
        for problem in problems:
            print(f"  {problem}")
        return 1

    print("check-links: OK -- every internal link and anchor resolves")
    return 0


if __name__ == "__main__":
    sys.exit(main())
