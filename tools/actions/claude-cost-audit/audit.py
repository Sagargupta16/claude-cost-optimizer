#!/usr/bin/env python3
"""
Claude Cost Audit -- CI-optimized version

Same analysis as badge-generator/generate.py but designed for GitHub Actions:
  - Always outputs JSON to stdout
  - Sets GITHUB_OUTPUT variables (grade, score, badge_url)
  - Exit code 0 on success, 1 on error

Usage (in a composite action step):
    python audit.py /path/to/project
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
from pathlib import Path


# -- Scoring ------------------------------------------------------------------

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


def set_github_output(key: str, value: str) -> None:
    """Append a key=value pair to GITHUB_OUTPUT if running in Actions."""
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(f"{key}={value}\n")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: audit.py <project-path>", file=sys.stderr)
        sys.exit(1)

    project = Path(sys.argv[1])
    if not project.is_dir():
        print(f"Error: '{sys.argv[1]}' is not a directory", file=sys.stderr)
        sys.exit(1)

    result = audit(project)

    # Always output JSON
    print(json.dumps(result, indent=2))

    # Set GitHub Actions outputs
    set_github_output("grade", result["grade"])
    set_github_output("score", str(result["score"]))
    set_github_output("badge_url", result["badge_url"])


if __name__ == "__main__":
    main()
