#!/usr/bin/env python3
"""
Claude Cost Efficiency Badge Generator

Analyzes a project's Claude Code configuration for cost efficiency
and generates a shields.io badge with a letter grade.

Checks:
  - CLAUDE.md: primary file line count plus estimated tokens across
    CLAUDE.md and .claude/CLAUDE.md
  - File-read exclusions: Read(...) rules in permissions.deny, plus lock-file
    coverage
  - .claude/settings.json: model config, real cost controls
  - MCP servers: count (fewer = less overhead per turn)

CLAUDE.md and File-read exclusions use the same rubric as
tools/claude-rate/rate.py (20 and 15 points there), rescaled to this tool's
25-point categories.

Usage:
    python generate.py /path/to/project
    python generate.py . --json
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import urllib.parse
from pathlib import Path


# -- ANSI colors (disabled when NO_COLOR is set or output is not a TTY) ------


def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if not hasattr(sys.stdout, "isatty"):
        return False
    return sys.stdout.isatty()


_COLOR = _supports_color()

BOLD = "\033[1m" if _COLOR else ""
DIM = "\033[2m" if _COLOR else ""
RESET = "\033[0m" if _COLOR else ""
GREEN = "\033[32m" if _COLOR else ""
YELLOW = "\033[33m" if _COLOR else ""
RED = "\033[31m" if _COLOR else ""
CYAN = "\033[36m" if _COLOR else ""
WHITE = "\033[97m" if _COLOR else ""


# -- Scoring helpers ----------------------------------------------------------

SETTINGS_JSON = ".claude/settings.json"


def _resolve_inside(project: Path, name: str) -> Path | None:
    """Resolve project/name and ensure it stays inside the project root."""
    candidate = (project / name).resolve()
    if not candidate.is_relative_to(project):
        return None
    return candidate


def _read_inside(project: Path, name: str) -> str | None:
    """Text of project/name, or None if it is missing or outside the project."""
    path = _resolve_inside(project, name)
    if path is None or not path.is_file():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def _scale_to_25(points: int, rubric_max: int) -> int:
    """Rescale a shared-rubric score to a 25-point category, rounding half up."""
    return (points * 50 + rubric_max) // (rubric_max * 2)


# Shared rubric (same tiers as tools/claude-rate/rate.py). Primary line count:
# <=100 -> 12, <=200 -> 10, <=300 -> 6, <=500 -> 3, else 1. Estimated tokens
# across both files: <=2,000 -> 8, <=4,000 -> 6, <=8,000 -> 4, <=16,000 -> 2, else 0.
CLAUDE_MD_LINE_TIERS = ((100, 12), (200, 10), (300, 6), (500, 3))
CLAUDE_MD_TOKEN_TIERS = ((2_000, 8), (4_000, 6), (8_000, 4), (16_000, 2))
CLAUDE_MD_RUBRIC_MAX = 20


def score_claude_md(project: Path) -> dict:
    """Score CLAUDE.md on primary line count and estimated tokens across files."""
    texts = [
        text
        for text in (
            _read_inside(project, "CLAUDE.md"),
            _read_inside(project, ".claude/CLAUDE.md"),
        )
        if text is not None
    ]
    if not texts:
        return {
            "score": 0,
            "detail": "CLAUDE.md not found",
            "lines": None,
            "tokens": None,
            "rubric_score": 0,
            "rubric_max": CLAUDE_MD_RUBRIC_MAX,
            "findings": [],
        }

    # Primary is the root CLAUDE.md, or .claude/CLAUDE.md when the root has none.
    lines = len(texts[0].splitlines())
    tokens = math.ceil(sum(len(text) for text in texts) / 4)
    points = next((p for limit, p in CLAUDE_MD_LINE_TIERS if lines <= limit), 1)
    points += next((p for limit, p in CLAUDE_MD_TOKEN_TIERS if tokens <= limit), 0)

    findings: list[str] = []
    if lines > 200:
        findings.append(
            f"{lines} lines -- over Anthropic's 200-line guidance for CLAUDE.md. "
            "Longer files consume more context and reduce adherence. Move "
            "workflow-specific instructions into skills or path-scoped .claude/rules/ "
            "so they load on demand."
        )

    return {
        "score": _scale_to_25(points, CLAUDE_MD_RUBRIC_MAX),
        "detail": f"{lines} lines, ~{tokens:,} tokens across {len(texts)} file(s)",
        "lines": lines,
        "tokens": tokens,
        "rubric_score": points,
        "rubric_max": CLAUDE_MD_RUBRIC_MAX,
        "findings": findings,
    }


# Shared rubric: Read(...) rules in permissions.deny, >=10 -> 13, >=5 -> 10,
# >=1 -> 6, 0 -> 0; +2 when every lock file at the root is covered; cap 15.
READ_RULE = re.compile(r"Read\(.+\)")
READ_RULE_TIERS = ((10, 13), (5, 10), (1, 6))
LOCK_FILES = (
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "poetry.lock",
    "Cargo.lock",
    "uv.lock",
)
FILE_READ_RUBRIC_MAX = 15
# Claude Code does not read this file; it is detected only to say so.
IGNORE_FILE = ".claudeignore"
IGNORE_FILE_FINDING = (
    "`.claudeignore` is not read by Claude Code -- it appears nowhere in Claude "
    "Code's documentation. Move its patterns into permissions.deny as Read(...) rules."
)


def _load_settings(project: Path) -> dict | None:
    """First of .claude/settings.json, .claude/settings.local.json that is a JSON object."""
    for name in (SETTINGS_JSON, ".claude/settings.local.json"):
        text = _read_inside(project, name)
        if text is None:
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    return None


def score_file_read_exclusions(project: Path) -> dict:
    """Score Read(...) rules in permissions.deny, plus lock-file coverage."""
    perms = (_load_settings(project) or {}).get("permissions")
    deny = perms.get("deny") if isinstance(perms, dict) else None
    rules = [
        r
        for r in (deny if isinstance(deny, list) else [])
        if isinstance(r, str) and READ_RULE.fullmatch(r)
    ]
    count = len(rules)
    locks = [name for name in LOCK_FILES if (project / name).is_file()]
    uncovered = [
        lock
        for lock in locks
        if not any(lock in r or "*.lock" in r or "*lock*" in r for r in rules)
    ]

    points = next((p for minimum, p in READ_RULE_TIERS if count >= minimum), 0)
    if count >= 1 and not uncovered:
        points = min(points + 2, FILE_READ_RUBRIC_MAX)

    if count == 0:
        detail = "no Read deny rules in permissions.deny"
    elif not locks:
        detail = f"{count} Read deny rule(s); no lock files at root"
    elif uncovered:
        detail = (
            f"{count} Read deny rule(s); lock files not covered: {', '.join(uncovered)}"
        )
    else:
        detail = f"{count} Read deny rule(s); lock files covered"

    ignore_file = _resolve_inside(project, IGNORE_FILE)
    findings = [IGNORE_FILE_FINDING] if ignore_file and ignore_file.is_file() else []

    return {
        "score": _scale_to_25(points, FILE_READ_RUBRIC_MAX),
        "detail": detail,
        "rules": count,
        "lock_files_uncovered": uncovered,
        "rubric_score": points,
        "rubric_max": FILE_READ_RUBRIC_MAX,
        "findings": findings,
    }


def has_cost_controls(data: dict) -> bool:
    """Whether settings.json configures a real spend-bounding setting.

    One of four implementations that must agree: `_cost_control_signals` in
    tools/claude-rate/rate.py, `has_cost_controls` in
    tools/actions/claude-cost-audit/audit.py, and `computeCostControls` in
    site/src/utils/repoAnalyzer.ts are the others. All four used to test for
    budgetCap / costLimit / maxCost / maxMonthlyCost / maxCostPerSession /
    budget, with a different subset in each file, so they already disagreed
    with each other. None of those six is in the Claude Code
    settings schema (checked 2026-09-06 against
    https://www.schemastore.org/claude-code-settings.json, 142 top-level
    properties, no spend cap among them), so the check rewarded a key the
    product ignores.

    Value-aware on purpose: "fastMode": true doubles the bill and
    "effortLevel": "max" raises it, so presence of the key is not enough.
    """
    effort = data.get("effortLevel")
    if isinstance(effort, str) and effort.strip().lower() in ("low", "medium"):
        return True
    if data.get("fastMode") is False:
        return True
    if data.get("alwaysThinkingEnabled") is False:
        return True
    models = data.get("availableModels")
    if (
        data.get("enforceAvailableModels") is True
        and isinstance(models, list)
        and models
    ):
        return True
    if data.get("autoCompactEnabled") is True:
        return True
    return False


def score_settings(project: Path) -> dict:
    """Score .claude/settings.json for model pin and real cost controls."""
    path = _resolve_inside(project, SETTINGS_JSON)
    if path is None or not path.is_file():
        return {
            "score": 0,
            "detail": "settings.json not found",
            "has_model": False,
            "has_cost_controls": False,
        }

    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (json.JSONDecodeError, OSError):
        return {
            "score": 0,
            "detail": "settings.json is invalid JSON",
            "has_model": False,
            "has_cost_controls": False,
        }

    has_model = bool(data.get("model") or data.get("defaultModel"))
    has_controls = has_cost_controls(data)

    if has_model and has_controls:
        score = 25
    elif has_model:
        score = 15
    elif data:
        score = 5
    else:
        score = 0

    parts: list[str] = []
    if has_model:
        parts.append("model configured")
    if has_controls:
        parts.append("cost controls set")
    if not parts:
        parts.append("no model pin or cost controls")

    return {
        "score": score,
        "detail": ", ".join(parts),
        "has_model": has_model,
        "has_cost_controls": has_controls,
    }


def score_mcp(project: Path) -> dict:
    """Score MCP server count from settings.json."""
    path = _resolve_inside(project, SETTINGS_JSON)
    if path is None or not path.is_file():
        # No settings file means no MCP servers -- that's efficient
        return {"score": 25, "detail": "0 MCP servers (no settings file)", "count": 0}

    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (json.JSONDecodeError, OSError):
        return {"score": 25, "detail": "0 MCP servers (invalid settings)", "count": 0}

    servers = data.get("mcpServers", {})
    count = len(servers) if isinstance(servers, dict) else 0

    if count <= 3:
        score = 25
    elif count <= 5:
        score = 20
    elif count <= 8:
        score = 15
    elif count <= 12:
        score = 10
    else:
        score = 0

    return {"score": score, "detail": f"{count} MCP servers", "count": count}


# -- Grade mapping ------------------------------------------------------------


def total_to_grade(total: int) -> str:
    """Map a 0-100 score to a letter grade."""
    if total >= 95:
        return "A+"
    if total >= 85:
        return "A"
    if total >= 70:
        return "B"
    if total >= 55:
        return "C"
    if total >= 40:
        return "D"
    return "F"


def grade_color(grade: str) -> str:
    """shields.io color for a grade."""
    colors = {
        "A+": "brightgreen",
        "A": "green",
        "B": "yellowgreen",
        "C": "yellow",
        "D": "orange",
        "F": "red",
    }
    return colors.get(grade, "lightgrey")


def grade_ansi_color(grade: str) -> str:
    """ANSI color for terminal display."""
    if grade in ("A+", "A"):
        return GREEN
    if grade == "B":
        return YELLOW
    return RED


# -- Badge URL ----------------------------------------------------------------


def badge_url(grade: str) -> str:
    """Generate a shields.io badge URL."""
    label = "Claude_Cost_Grade"
    color = grade_color(grade)
    encoded_grade = urllib.parse.quote(grade, safe="")
    return f"https://img.shields.io/badge/{label}-{encoded_grade}-{color}"


# -- Main logic ---------------------------------------------------------------


def audit(project: Path) -> dict:
    """Run the full audit and return structured results."""
    claude_md = score_claude_md(project)
    file_read = score_file_read_exclusions(project)
    settings = score_settings(project)
    mcp = score_mcp(project)

    total = claude_md["score"] + file_read["score"] + settings["score"] + mcp["score"]
    grade = total_to_grade(total)

    return {
        "project": str(project.resolve()),
        "score": total,
        "grade": grade,
        "badge_url": badge_url(grade),
        "badge_markdown": f"![Claude Cost Grade]({badge_url(grade)})",
        "breakdown": {
            "claude_md": claude_md,
            "file_read_exclusions": file_read,
            "settings": settings,
            "mcp_servers": mcp,
        },
    }


def print_report(result: dict) -> None:
    """Print a human-readable terminal report."""
    grade = result["grade"]
    gc = grade_ansi_color(grade)

    print()
    print(f"{BOLD}Claude Cost Efficiency Audit{RESET}")
    print(f"{DIM}{'=' * 40}{RESET}")
    print(f"Project: {result['project']}")
    print()

    breakdown = result["breakdown"]
    categories = [
        ("CLAUDE.md", "claude_md"),
        ("File-read exclusions", "file_read_exclusions"),
        ("Settings", "settings"),
        ("MCP Servers", "mcp_servers"),
    ]

    for label, key in categories:
        entry = breakdown[key]
        s = entry["score"]
        if s >= 20:
            color = GREEN
        elif s >= 10:
            color = YELLOW
        else:
            color = RED
        print(f"  {label:<22} {color}{s:>2}/25{RESET}  {DIM}{entry['detail']}{RESET}")
        for finding in entry.get("findings", []):
            print(f"    {YELLOW}!{RESET} {finding}")

    print()
    print(f"{BOLD}Total: {result['score']}/100{RESET}")
    print(f"{BOLD}Grade: {gc}{grade}{RESET}")
    print()
    print(f"{CYAN}Badge URL:{RESET}")
    print(f"  {result['badge_url']}")
    print()
    print(f"{CYAN}Markdown:{RESET}")
    print(f"  {result['badge_markdown']}")
    print()


# -- CLI entry point ----------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit a project's Claude Code configuration for cost efficiency "
        "and generate a shields.io badge.",
    )
    parser.add_argument(
        "path",
        help="Path to the project directory to audit",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output results as JSON instead of a terminal report",
    )

    args = parser.parse_args()

    project = Path(args.path)
    if not project.is_dir():
        print(f"Error: '{args.path}' is not a directory", file=sys.stderr)
        sys.exit(1)
    project = project.resolve()

    result = audit(project)

    if args.json_output:
        print(json.dumps(result, indent=2))
    else:
        print_report(result)


if __name__ == "__main__":
    main()
