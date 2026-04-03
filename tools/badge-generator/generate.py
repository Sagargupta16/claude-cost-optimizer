#!/usr/bin/env python3
"""
Claude Cost Efficiency Badge Generator

Analyzes a project's Claude Code configuration for cost efficiency
and generates a shields.io badge with a letter grade.

Checks:
  - CLAUDE.md: exists, line count (concise = cheaper context)
  - .claudeignore: exists, number of entries (fewer indexed files)
  - .claude/settings.json: model config, budget cap
  - MCP servers: count (fewer = less overhead per turn)

Usage:
    python generate.py /path/to/project
    python generate.py . --json
"""

from __future__ import annotations

import argparse
import json
import os
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

def score_claude_md(project: Path) -> dict:
    """Score CLAUDE.md based on existence and line count."""
    path = project / "CLAUDE.md"
    if not path.is_file():
        return {"score": 0, "detail": "CLAUDE.md not found", "lines": None}

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    count = len(lines)

    if count <= 80:
        score = 25
    elif count <= 100:
        score = 20
    elif count <= 150:
        score = 15
    elif count <= 200:
        score = 10
    elif count <= 300:
        score = 5
    else:
        score = 0

    return {"score": score, "detail": f"{count} lines", "lines": count}


def score_claudeignore(project: Path) -> dict:
    """Score .claudeignore based on existence and entry count."""
    path = project / ".claudeignore"
    if not path.is_file():
        return {"score": 0, "detail": ".claudeignore not found", "entries": None}

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    entries = [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]
    count = len(entries)

    if count >= 5:
        score = 25
    elif count > 0:
        score = 15
    else:
        score = 0

    return {"score": score, "detail": f"{count} entries", "entries": count}


def score_settings(project: Path) -> dict:
    """Score .claude/settings.json for model and budget cap config."""
    path = project / ".claude" / "settings.json"
    if not path.is_file():
        return {
            "score": 0,
            "detail": "settings.json not found",
            "has_model": False,
            "has_budget": False,
        }

    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (json.JSONDecodeError, OSError):
        return {
            "score": 0,
            "detail": "settings.json is invalid JSON",
            "has_model": False,
            "has_budget": False,
        }

    has_model = bool(data.get("model") or data.get("defaultModel"))
    has_budget = bool(
        data.get("budgetCap")
        or data.get("costLimit")
        or data.get("maxCostPerSession")
        or data.get("budget")
    )

    if has_model and has_budget:
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
    if has_budget:
        parts.append("budget cap set")
    if not parts:
        parts.append("no model or budget config")

    return {
        "score": score,
        "detail": ", ".join(parts),
        "has_model": has_model,
        "has_budget": has_budget,
    }


def score_mcp(project: Path) -> dict:
    """Score MCP server count from settings.json."""
    path = project / ".claude" / "settings.json"
    if not path.is_file():
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
    claudeignore = score_claudeignore(project)
    settings = score_settings(project)
    mcp = score_mcp(project)

    total = claude_md["score"] + claudeignore["score"] + settings["score"] + mcp["score"]
    grade = total_to_grade(total)

    return {
        "project": str(project.resolve()),
        "score": total,
        "grade": grade,
        "badge_url": badge_url(grade),
        "badge_markdown": f"![Claude Cost Grade]({badge_url(grade)})",
        "breakdown": {
            "claude_md": claude_md,
            "claudeignore": claudeignore,
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
        (".claudeignore", "claudeignore"),
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
        print(f"  {label:<16} {color}{s:>2}/25{RESET}  {DIM}{entry['detail']}{RESET}")

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

    result = audit(project)

    if args.json_output:
        print(json.dumps(result, indent=2))
    else:
        print_report(result)


if __name__ == "__main__":
    main()
