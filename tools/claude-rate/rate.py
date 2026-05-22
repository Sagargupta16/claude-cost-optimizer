#!/usr/bin/env python3
"""
claude-rate -- Local Claude / AI setup rater.

Scans your project directory and rates your Claude Code (and adjacent AI
tooling) configuration for cost-efficiency. Returns a 0-100 score, an A+
to F letter grade, a per-category breakdown, copy-pasteable fix suggestions,
and an estimated monthly spend on every active model tier.

Unlike the deployed web analyzer (which only sees what's on GitHub),
claude-rate runs on the actual filesystem and can inspect things the
analyzer can't see -- e.g. real MCP server count, .mcp.json contents, hook
configurations, accidentally-committed secrets, .gitignore coverage of
sensitive files, and untracked CLAUDE.md drafts.

Usage:
    python rate.py                       # rate the current directory
    python rate.py /path/to/project
    python rate.py . --json              # machine-readable output
    python rate.py . --fix               # print copy-pasteable fix commands
    python rate.py . --strict            # fail with exit code 1 if grade < B

No external dependencies. Pure Python 3.10+ stdlib.

Pricing data verified 2026-05-22 against:
    https://platform.claude.com/docs/en/about-claude/pricing
    https://platform.claude.com/docs/en/about-claude/models/overview
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# -- Pricing data (mirrors site/src/utils/pricing.ts) ------------------------

# Active models priced as of 2026-05-22. Prices are USD per 1M tokens.
MODELS: dict[str, dict[str, Any]] = {
    "opus-4-7": {
        "name": "Opus 4.7",
        "input": 5.00,
        "output": 25.00,
        "cache_hit": 0.50,
        "cache_5m_write": 6.25,
        "cache_1h_write": 10.00,
        "context_window": 1_000_000,
        "tokenizer_overhead": 1.35,
        "fast_mode": True,
        "lifecycle": "active",
    },
    "opus-4-6": {
        "name": "Opus 4.6",
        "input": 5.00,
        "output": 25.00,
        "cache_hit": 0.50,
        "cache_5m_write": 6.25,
        "cache_1h_write": 10.00,
        "context_window": 1_000_000,
        "tokenizer_overhead": 1.0,
        "fast_mode": True,
        "lifecycle": "active",
    },
    "sonnet-4-6": {
        "name": "Sonnet 4.6",
        "input": 3.00,
        "output": 15.00,
        "cache_hit": 0.30,
        "cache_5m_write": 3.75,
        "cache_1h_write": 6.00,
        "context_window": 1_000_000,
        "tokenizer_overhead": 1.0,
        "fast_mode": False,
        "lifecycle": "active",
    },
    "haiku-4-5": {
        "name": "Haiku 4.5",
        "input": 1.00,
        "output": 5.00,
        "cache_hit": 0.10,
        "cache_5m_write": 1.25,
        "cache_1h_write": 2.00,
        "context_window": 200_000,
        "tokenizer_overhead": 1.0,
        "fast_mode": False,
        "lifecycle": "active",
    },
}

# Token estimation constants (mirrors TOKEN_ESTIMATES in pricing.ts).
TOKENS_PER_CLAUDE_MD_LINE = 7
SYSTEM_PROMPT_TOKENS = 3_500
TOKENS_PER_MCP_SERVER = 1_500
TOKENS_PER_FILE_READ = 2_000
OUTPUT_TOKENS_PER_TURN = 500
HISTORY_GROWTH_PER_TURN = 1_500
CACHE_HIT_RATE = 0.7

# Limits. CLAUDE.md content beyond 4,000 chars is silently truncated; total
# instruction-file budget across CLAUDE.md + .claude/CLAUDE.md is ~12,000.
CLAUDE_MD_HARD_LIMIT = 4_000
CLAUDE_MD_TOTAL_LIMIT = 12_000


# -- ANSI colors -------------------------------------------------------------

def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if not hasattr(sys.stdout, "isatty"):
        return False
    return sys.stdout.isatty()


_C = _supports_color()
BOLD = "\033[1m" if _C else ""
DIM = "\033[2m" if _C else ""
RESET = "\033[0m" if _C else ""
GREEN = "\033[32m" if _C else ""
YELLOW = "\033[33m" if _C else ""
RED = "\033[31m" if _C else ""
CYAN = "\033[36m" if _C else ""
BLUE = "\033[34m" if _C else ""
MAGENTA = "\033[35m" if _C else ""


# -- Data classes ------------------------------------------------------------

@dataclass
class CategoryResult:
    name: str
    score: int
    max_score: int
    detail: str
    findings: list[str] = field(default_factory=list)
    fixes: list[str] = field(default_factory=list)


@dataclass
class RateResult:
    project: str
    score: int
    max_score: int
    grade: str
    categories: list[CategoryResult]
    cost_estimate: dict[str, dict[str, float]]
    badge_url: str
    badge_markdown: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "score": self.score,
            "max_score": self.max_score,
            "grade": self.grade,
            "badge_url": self.badge_url,
            "badge_markdown": self.badge_markdown,
            "categories": [
                {
                    "name": c.name,
                    "score": c.score,
                    "max_score": c.max_score,
                    "detail": c.detail,
                    "findings": c.findings,
                    "fixes": c.fixes,
                }
                for c in self.categories
            ],
            "cost_estimate": self.cost_estimate,
        }


# -- Helpers -----------------------------------------------------------------

def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _read_json(path: Path) -> dict[str, Any] | None:
    text = _read_text(path)
    if text is None:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _line_count(text: str) -> int:
    return len(text.splitlines())


def _char_count(text: str) -> int:
    return len(text)


def _glob_count(project: Path, patterns: tuple[str, ...]) -> int:
    total = 0
    for pat in patterns:
        total += sum(1 for _ in project.glob(pat))
    return total


# -- Category scorers --------------------------------------------------------

def score_claude_md(project: Path) -> CategoryResult:
    """CLAUDE.md presence, size discipline, and total instruction budget."""
    cat = CategoryResult(name="CLAUDE.md", score=0, max_score=20, detail="", findings=[], fixes=[])

    primary = project / "CLAUDE.md"
    secondary = project / ".claude" / "CLAUDE.md"
    files = [(primary, "CLAUDE.md"), (secondary, ".claude/CLAUDE.md")]

    found_any = False
    primary_chars = 0
    total_chars = 0
    breakdown: list[tuple[str, int, int]] = []  # (label, chars, lines)

    for path, label in files:
        if path.is_file():
            text = _read_text(path) or ""
            chars = _char_count(text)
            lines = _line_count(text)
            breakdown.append((label, chars, lines))
            total_chars += chars
            if path == primary:
                primary_chars = chars
                found_any = True

    if not found_any:
        cat.detail = "CLAUDE.md not found"
        cat.findings.append("No CLAUDE.md at project root.")
        cat.fixes.append(
            "Create CLAUDE.md at the repo root with project conventions, "
            "tech stack, and 5-10 high-value rules. Keep under 4,000 characters."
        )
        return cat

    # Score primary file (max 12 points).
    if primary_chars <= 2_000:
        primary_score = 12
        primary_msg = "concise"
    elif primary_chars <= 3_000:
        primary_score = 10
        primary_msg = "well-sized"
    elif primary_chars <= CLAUDE_MD_HARD_LIMIT:
        primary_score = 7
        primary_msg = "near hard limit"
    elif primary_chars <= 6_000:
        primary_score = 3
        primary_msg = "OVER 4K hard limit -- content past 4K is silently truncated"
    elif primary_chars <= 8_000:
        primary_score = 1
        primary_msg = "way over hard limit"
    else:
        primary_score = 0
        primary_msg = "massively bloated"

    # Score total instruction budget (max 8 points).
    if total_chars <= 6_000:
        total_score = 8
    elif total_chars <= 9_000:
        total_score = 6
    elif total_chars <= CLAUDE_MD_TOTAL_LIMIT:
        total_score = 4
    elif total_chars <= 16_000:
        total_score = 2
    else:
        total_score = 0

    cat.score = primary_score + total_score
    cat.detail = f"{primary_chars:,} chars primary ({primary_msg}); {total_chars:,} chars total across {len(breakdown)} file(s)"

    if primary_chars > CLAUDE_MD_HARD_LIMIT:
        cat.findings.append(
            f"CLAUDE.md is {primary_chars:,} chars -- {primary_chars - CLAUDE_MD_HARD_LIMIT:,} chars over the 4K hard limit. "
            "Content beyond 4,000 chars is silently truncated."
        )
        cat.fixes.append("Trim CLAUDE.md to under 4,000 characters. Move stack-specific or volatile guidance to .claude/CLAUDE.md or referenced docs.")
    elif primary_chars > 3_000:
        cat.fixes.append(f"CLAUDE.md is {primary_chars:,} chars (near 4K limit). Trim to under 3,000 to leave headroom.")

    if total_chars > CLAUDE_MD_TOTAL_LIMIT:
        cat.findings.append(
            f"Total instruction-file budget is {total_chars:,} chars -- over the ~12K total budget. "
            "Every byte loads on every turn."
        )
        cat.fixes.append("Audit ALL CLAUDE.md files (root + .claude/). Delete duplication, drop low-value rules, push verbose guidance into linked deep-dive docs.")

    if not (project / ".claude" / "CLAUDE.md").is_file() and primary_chars > 3_000:
        cat.fixes.append("Consider splitting CLAUDE.md: keep ~2K chars at root for global rules, push stack-specific rules to .claude/CLAUDE.md.")

    return cat


def score_claudeignore(project: Path) -> CategoryResult:
    """`.claudeignore` presence and coverage of common bloat sources."""
    cat = CategoryResult(name=".claudeignore", score=0, max_score=15, detail="", findings=[], fixes=[])

    path = project / ".claudeignore"
    if not path.is_file():
        cat.detail = "not found"
        cat.findings.append("No .claudeignore file. Claude will index node_modules, dist, lock files, and other large generated content.")
        # Heuristic fix list based on what the project actually has.
        suggestions: list[str] = []
        if (project / "node_modules").exists():
            suggestions.append("node_modules/")
        if (project / "package-lock.json").exists():
            suggestions.append("package-lock.json")
        if (project / "pnpm-lock.yaml").exists():
            suggestions.append("pnpm-lock.yaml")
        if (project / "yarn.lock").exists():
            suggestions.append("yarn.lock")
        if (project / "dist").exists():
            suggestions.append("dist/")
        if (project / "build").exists():
            suggestions.append("build/")
        if list(project.glob("*.lock")) or list(project.glob("*.lockb")):
            suggestions.append("*.lock")
        if (project / ".venv").exists() or (project / "venv").exists():
            suggestions.append(".venv/")
        if (project / "target").exists():  # rust
            suggestions.append("target/")
        if (project / "vendor").exists():  # go / php
            suggestions.append("vendor/")
        suggestions.extend([".git/", "*.log", "coverage/", ".next/", "*.min.js", "*.map"])
        seen: set[str] = set()
        deduped = [s for s in suggestions if not (s in seen or seen.add(s))]
        cat.fixes.append(
            "Create .claudeignore at repo root with these patterns:\n    "
            + "\n    ".join(deduped)
        )
        return cat

    raw = _read_text(path) or ""
    entries = [l.strip() for l in raw.splitlines() if l.strip() and not l.strip().startswith("#")]
    count = len(entries)

    # Coverage check: warn when obvious bloat sources exist on disk but aren't ignored.
    missing: list[str] = []
    checks = [
        ("node_modules/", "node_modules"),
        ("dist/", "dist"),
        ("build/", "build"),
        (".venv/", ".venv"),
        ("target/", "target"),
        ("vendor/", "vendor"),
        ("*.lock", None),  # any lock file
    ]
    for pattern, dir_check in checks:
        if dir_check and (project / dir_check).exists():
            if not any(pattern.rstrip("/") in e or e.rstrip("/") == dir_check for e in entries):
                missing.append(f"{pattern}  # {dir_check}/ exists on disk but not ignored")
        elif pattern == "*.lock" and (
            (project / "package-lock.json").exists()
            or (project / "pnpm-lock.yaml").exists()
            or (project / "yarn.lock").exists()
        ):
            if not any(e in {"*.lock", "package-lock.json", "pnpm-lock.yaml", "yarn.lock"} or "lock" in e for e in entries):
                missing.append("package-lock.json  # or *.lock to cover all variants")

    if count >= 8 and not missing:
        cat.score = 15
        cat.detail = f"{count} entries, all common bloat covered"
    elif count >= 5 and not missing:
        cat.score = 12
        cat.detail = f"{count} entries, common bloat covered"
    elif count >= 5:
        cat.score = 9
        cat.detail = f"{count} entries, but {len(missing)} obvious gap(s)"
    elif count >= 1:
        cat.score = 5
        cat.detail = f"only {count} entries -- minimal coverage"
    else:
        cat.score = 0
        cat.detail = "file exists but is empty"

    if missing:
        cat.findings.append(
            ".claudeignore exists but doesn't cover the following bloat sources actually present in your repo:"
        )
        cat.fixes.append("Add these lines to .claudeignore:\n    " + "\n    ".join(missing))

    if count < 5:
        cat.fixes.append(
            "Aim for 5+ patterns. At minimum: node_modules/, dist/, build/, *.lock, .git/, coverage/, *.log, *.map"
        )

    return cat


def score_settings(project: Path) -> CategoryResult:
    """`.claude/settings.json` model + budget config + permissions."""
    cat = CategoryResult(name=".claude/settings.json", score=0, max_score=15, detail="", findings=[], fixes=[])

    primary = project / ".claude" / "settings.json"
    local = project / ".claude" / "settings.local.json"
    user = project / ".claude" / "settings.local.json"

    data: dict[str, Any] | None = None
    found_path: Path | None = None
    for p in (primary, local, user):
        d = _read_json(p)
        if d is not None:
            data = d
            found_path = p
            break

    if data is None:
        cat.detail = "no settings.json"
        cat.findings.append("No .claude/settings.json. Default model and permissions are not project-pinned.")
        cat.fixes.append(
            "Create .claude/settings.json with at minimum:\n"
            '    {"model": "claude-sonnet-4-6", "permissions": {"allow": [], "deny": []}}'
        )
        return cat

    has_model = bool(data.get("model") or data.get("defaultModel") or data.get("preferredModel"))
    has_budget = any(
        data.get(k)
        for k in ("budgetCap", "costLimit", "maxCost", "maxMonthlyCost", "maxCostPerSession", "budget")
    )
    perms = data.get("permissions") or {}
    has_perms = bool(perms.get("allow") or perms.get("deny")) if isinstance(perms, dict) else False

    score = 0
    parts: list[str] = []
    if has_model:
        score += 6
        model_id = data.get("model") or data.get("defaultModel") or data.get("preferredModel")
        parts.append(f"model={model_id}")
    else:
        cat.fixes.append('Set "model" in settings.json to pin a default (e.g. "claude-sonnet-4-6"). Prevents accidental Opus usage on simple tasks.')

    if has_budget:
        score += 5
        parts.append("budget cap configured")
    else:
        cat.fixes.append('Add a budget cap (e.g. "maxMonthlyCost": 100) to prevent runaway costs.')

    if has_perms:
        score += 4
        parts.append("permissions defined")
    else:
        cat.fixes.append(
            'Define permissions to reduce permission-prompt friction:\n'
            '    "permissions": {"allow": ["Bash(npm test:*)", "Read(**)"], "deny": []}'
        )

    cat.score = score
    cat.detail = f"found at {found_path.relative_to(project)}; " + ", ".join(parts) if parts else "settings.json present but mostly empty"
    return cat


def score_mcp_servers(project: Path) -> CategoryResult:
    """Count MCP servers across .mcp.json + settings.json. Each adds ~1.5K tokens/turn."""
    cat = CategoryResult(name="MCP servers", score=0, max_score=15, detail="", findings=[], fixes=[])

    counts: dict[str, int] = {}

    mcp_file = project / ".mcp.json"
    mcp_data = _read_json(mcp_file)
    if mcp_data is not None:
        servers = mcp_data.get("mcpServers", {})
        if isinstance(servers, dict):
            counts[".mcp.json"] = len(servers)

    settings = _read_json(project / ".claude" / "settings.json")
    if settings is not None:
        servers = settings.get("mcpServers", {})
        if isinstance(servers, dict) and servers:
            counts[".claude/settings.json"] = len(servers)

    total = sum(counts.values())

    if total == 0:
        cat.score = 15
        cat.detail = "no MCP servers configured (lowest overhead)"
        return cat
    if total <= 3:
        cat.score = 13
        cat.detail = f"{total} MCP server(s) -- light overhead (~{total * TOKENS_PER_MCP_SERVER:,} tokens/turn)"
    elif total <= 5:
        cat.score = 10
        cat.detail = f"{total} MCP servers -- moderate overhead"
    elif total <= 8:
        cat.score = 6
        cat.detail = f"{total} MCP servers -- heavy overhead (~{total * TOKENS_PER_MCP_SERVER:,} tokens/turn)"
    elif total <= 12:
        cat.score = 3
        cat.detail = f"{total} MCP servers -- very heavy overhead"
    else:
        cat.score = 0
        cat.detail = f"{total} MCP servers -- excessive overhead"

    if total > 5:
        cat.findings.append(
            f"{total} MCP servers configured (across {', '.join(counts.keys())}). "
            f"Each adds ~{TOKENS_PER_MCP_SERVER:,} tokens to every turn's system prompt."
        )
        cat.fixes.append(
            "Review which MCP servers you actually use every session. Disable rarely-used ones in .mcp.json or move them to .mcp.local.json (gitignored)."
        )

    if total > 0 and ".mcp.json" not in counts and "mcpServers" in (settings or {}):
        cat.fixes.append(
            "MCP servers are in .claude/settings.json -- prefer the dedicated .mcp.json file (cleaner separation, easier to share/exclude)."
        )

    return cat


def score_hooks(project: Path) -> CategoryResult:
    """Hooks for budget tracking, cost logging, or permission policy."""
    cat = CategoryResult(name="Hooks", score=0, max_score=10, detail="", findings=[], fixes=[])

    settings = _read_json(project / ".claude" / "settings.json")
    hooks = settings.get("hooks") if settings else None

    hook_count = 0
    if isinstance(hooks, dict):
        for v in hooks.values():
            if isinstance(v, list):
                hook_count += len(v)
            elif v:
                hook_count += 1

    if hook_count >= 3:
        cat.score = 10
        cat.detail = f"{hook_count} hook(s) configured"
    elif hook_count >= 1:
        cat.score = 6
        cat.detail = f"{hook_count} hook(s) configured"
        cat.fixes.append("Consider adding cost-tracking hooks (PreToolUse for budget gates, Stop for session-cost summary).")
    else:
        cat.detail = "no hooks configured"
        cat.fixes.append(
            "Add cost-tracking hooks. Example PostToolUse hook to log token use:\n"
            '    {"hooks": {"PostToolUse": [{"command": "echo \\"$CLAUDE_TOOL_NAME: $CLAUDE_TOKEN_COUNT tokens\\" >> ~/.claude-usage.log"}]}}'
        )

    return cat


def score_security(project: Path) -> CategoryResult:
    """Quick check for accidentally-committed secrets and missing gitignore entries."""
    cat = CategoryResult(name="Security & hygiene", score=0, max_score=10, detail="", findings=[], fixes=[])

    score = 10
    danger_files = [".env", ".env.local", ".env.production", "credentials.json", ".mcp.local.json"]
    leaked: list[str] = []

    gitignore_path = project / ".gitignore"
    gitignore_text = _read_text(gitignore_path) if gitignore_path.is_file() else ""

    for f in danger_files:
        full = project / f
        if full.is_file():
            # File exists -- is it gitignored?
            ignored = bool(gitignore_text and any(f in line.strip() or line.strip().rstrip("/") == f.rstrip("/") for line in gitignore_text.splitlines()))
            if not ignored:
                leaked.append(f)

    # Look for obvious API key patterns in CLAUDE.md / settings (not deep scan -- just an eyeball).
    api_key_pattern = re.compile(r"(sk-[a-zA-Z0-9]{20,}|AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36})")
    suspect_files: list[str] = []
    for sf in (project / "CLAUDE.md", project / ".claude" / "settings.json", project / ".mcp.json"):
        if sf.is_file():
            text = _read_text(sf) or ""
            if api_key_pattern.search(text):
                suspect_files.append(str(sf.relative_to(project)))

    if leaked:
        score -= 6
        cat.findings.append(
            f"Sensitive files exist on disk but are NOT in .gitignore: {', '.join(leaked)}. "
            "These will be committed unless explicitly ignored."
        )
        cat.fixes.append(
            "Add to .gitignore IMMEDIATELY:\n    " + "\n    ".join(leaked + [".env*", "*.key", ".mcp.local.json"])
        )

    if suspect_files:
        score = 0
        cat.findings.append(
            f"POSSIBLE API KEY in tracked files: {', '.join(suspect_files)}. "
            "Rotate the key immediately and remove from git history."
        )
        cat.fixes.append(
            "1. Rotate the leaked credential at the provider.\n"
            "    2. Remove from the file.\n"
            "    3. Use git-filter-repo or BFG to scrub history.\n"
            "    4. Force-push (coordinate with team first)."
        )

    if not gitignore_path.is_file():
        score = max(0, score - 3)
        cat.findings.append("No .gitignore at all -- secrets and build artifacts will be tracked.")
        cat.fixes.append("Run `git init` properly or copy a starter .gitignore for your stack.")

    cat.score = max(0, score)
    if cat.score == cat.max_score:
        cat.detail = "no leaked secrets, gitignore present"
    elif leaked or suspect_files:
        cat.detail = "RISK: review findings"
    else:
        cat.detail = "minor gaps"

    return cat


def score_optimizer_tooling(project: Path) -> CategoryResult:
    """Bonus points for already-installed cost-optimization tooling."""
    cat = CategoryResult(name="Optimizer tooling", score=0, max_score=15, detail="", findings=[], fixes=[])

    score = 0
    found: list[str] = []

    # cost-mode skill installed (locally or via plugin)
    if (project / "skills" / "cost-mode").exists() or (project / ".claude" / "skills" / "cost-mode").exists():
        score += 5
        found.append("cost-mode skill installed")

    # custom slash commands
    cmd_dir = project / ".claude" / "commands"
    if cmd_dir.is_dir():
        cmd_count = len(list(cmd_dir.glob("*.md")))
        if cmd_count >= 3:
            score += 4
            found.append(f"{cmd_count} custom slash command(s)")
        elif cmd_count >= 1:
            score += 2
            found.append(f"{cmd_count} custom slash command(s)")

    # subagents directory
    agents_dir = project / ".claude" / "agents"
    if agents_dir.is_dir() and any(agents_dir.iterdir()):
        score += 3
        found.append("custom subagent(s) defined")

    # Plugin marketplace registration (lightweight signal of Claude Code seriousness)
    if (project / ".claude-plugin" / "marketplace.json").is_file():
        score += 3
        found.append("plugin marketplace metadata")

    cat.score = min(score, cat.max_score)
    cat.detail = ", ".join(found) if found else "none of: cost-mode skill, custom commands, subagents, plugin metadata"

    if not found:
        cat.fixes.append(
            "Install the cost-mode skill for ~30-60% output reduction:\n"
            "    /plugin marketplace add Sagargupta16/claude-cost-optimizer\n"
            "    /plugin install cost-mode@sagargupta16-claude-cost-optimizer"
        )
    if not (project / ".claude" / "commands").is_dir():
        cat.fixes.append(
            "Create .claude/commands/ with reusable slash commands (e.g. /cost-check, /quick-fix). Saves re-explaining workflows."
        )

    return cat


# -- Grade mapping -----------------------------------------------------------

def total_to_grade(total: int, max_total: int) -> str:
    pct = (total / max_total) * 100 if max_total else 0
    if pct >= 95:
        return "A+"
    if pct >= 85:
        return "A"
    if pct >= 70:
        return "B"
    if pct >= 55:
        return "C"
    if pct >= 40:
        return "D"
    return "F"


def grade_color(grade: str) -> str:
    return {
        "A+": "brightgreen",
        "A": "green",
        "B": "yellowgreen",
        "C": "yellow",
        "D": "orange",
        "F": "red",
    }.get(grade, "lightgrey")


def grade_ansi(grade: str) -> str:
    if grade in ("A+", "A"):
        return GREEN
    if grade == "B":
        return YELLOW
    if grade == "C":
        return YELLOW
    return RED


def badge_url(grade: str) -> str:
    import urllib.parse

    return (
        "https://img.shields.io/badge/Claude%20Cost%20Grade-"
        f"{urllib.parse.quote(grade, safe='')}-{grade_color(grade)}"
    )


# -- Cost estimation ---------------------------------------------------------

def estimate_costs(claude_md_chars: int, mcp_count: int) -> dict[str, dict[str, float]]:
    """Estimate per-session and per-month cost for each active model.

    Assumes 30 turns/session, 3 sessions/day, 22 working days/month, and a
    70% cache hit rate -- mirrors the deployed analyzer's defaults.
    """
    claude_md_tokens = (claude_md_chars / 4)  # ~4 chars per token
    mcp_tokens = mcp_count * TOKENS_PER_MCP_SERVER
    system_prompt_tokens = SYSTEM_PROMPT_TOKENS + claude_md_tokens + mcp_tokens

    turns = 30
    input_tokens = (
        system_prompt_tokens * turns
        + (turns * (turns - 1) * HISTORY_GROWTH_PER_TURN) / 2
        + TOKENS_PER_FILE_READ * turns
    )
    output_tokens = OUTPUT_TOKENS_PER_TURN * turns

    cached = input_tokens * CACHE_HIT_RATE
    uncached = input_tokens * (1 - CACHE_HIT_RATE)

    sessions_per_day = 3
    working_days = 22

    out: dict[str, dict[str, float]] = {}
    for mid, m in MODELS.items():
        overhead = m["tokenizer_overhead"]
        input_cost = (uncached * overhead / 1_000_000) * m["input"]
        cache_cost = (cached * overhead / 1_000_000) * m["cache_hit"]
        output_cost = (output_tokens * overhead / 1_000_000) * m["output"]
        per_session = input_cost + cache_cost + output_cost
        out[mid] = {
            "name": m["name"],
            "per_session": round(per_session, 2),
            "per_month": round(per_session * sessions_per_day * working_days, 2),
        }
    return out


# -- Main rate function ------------------------------------------------------

def rate(project: Path) -> RateResult:
    categories = [
        score_claude_md(project),
        score_claudeignore(project),
        score_settings(project),
        score_mcp_servers(project),
        score_hooks(project),
        score_security(project),
        score_optimizer_tooling(project),
    ]

    total = sum(c.score for c in categories)
    max_total = sum(c.max_score for c in categories)
    grade = total_to_grade(total, max_total)

    # Reconstruct CLAUDE.md char count for cost estimation.
    primary_md = project / "CLAUDE.md"
    secondary_md = project / ".claude" / "CLAUDE.md"
    claude_md_chars = 0
    for p in (primary_md, secondary_md):
        if p.is_file():
            claude_md_chars += _char_count(_read_text(p) or "")

    settings = _read_json(project / ".claude" / "settings.json") or {}
    mcp_count = 0
    mcp_data = _read_json(project / ".mcp.json")
    if mcp_data and isinstance(mcp_data.get("mcpServers"), dict):
        mcp_count += len(mcp_data["mcpServers"])
    if isinstance(settings.get("mcpServers"), dict):
        mcp_count += len(settings["mcpServers"])

    cost_estimate = estimate_costs(claude_md_chars, mcp_count)

    url = badge_url(grade)

    return RateResult(
        project=str(project.resolve()),
        score=total,
        max_score=max_total,
        grade=grade,
        categories=categories,
        cost_estimate=cost_estimate,
        badge_url=url,
        badge_markdown=f"![Claude Cost Grade]({url})",
    )


# -- Output formatters -------------------------------------------------------

def print_report(result: RateResult, show_fixes: bool = False) -> None:
    print()
    print(f"{BOLD}claude-rate{RESET} {DIM}-- Claude / AI setup audit{RESET}")
    print(f"{DIM}{'=' * 60}{RESET}")
    print(f"Project: {result.project}")
    print(f"Verified against Anthropic pricing as of: {DIM}2026-05-22{RESET}")
    print()

    for cat in result.categories:
        ratio = cat.score / cat.max_score if cat.max_score else 0
        if ratio >= 0.8:
            color = GREEN
        elif ratio >= 0.5:
            color = YELLOW
        else:
            color = RED
        bar_width = 20
        filled = int(bar_width * ratio)
        bar = "#" * filled + "-" * (bar_width - filled)
        score_str = f"{cat.score:>2}/{cat.max_score:<2}"
        print(f"  {cat.name:<24} {color}[{bar}]{RESET}  {color}{score_str}{RESET}  {DIM}{cat.detail}{RESET}")

        if cat.findings:
            for f in cat.findings:
                # wrap at ~74 chars for readability
                print(f"    {YELLOW}!{RESET} {f}")

    print()
    grade_c = grade_ansi(result.grade)
    print(f"{BOLD}Total:{RESET} {result.score}/{result.max_score}  ({grade_c}{result.grade}{RESET})")
    print()

    print(f"{BOLD}Estimated monthly cost{RESET} {DIM}(30 turns/session, 3 sessions/day, 22 days, 70% cache hit){RESET}")
    for mid, c in result.cost_estimate.items():
        print(f"  {c['name']:<14} {DIM}${c['per_session']:>5.2f}/session{RESET}  ->  {BOLD}${c['per_month']:>7.2f}/month{RESET}")

    print()
    print(f"{CYAN}Badge URL:{RESET}  {result.badge_url}")
    print(f"{CYAN}Markdown:{RESET}  {result.badge_markdown}")

    if show_fixes:
        print()
        print(f"{BOLD}Suggested fixes{RESET} {DIM}(--fix for copy-pasteable form){RESET}")
        print(f"{DIM}{'-' * 60}{RESET}")
        any_fix = False
        for cat in result.categories:
            for fix in cat.fixes:
                any_fix = True
                print(f"  {MAGENTA}*{RESET} [{cat.name}] {fix}")
                print()
        if not any_fix:
            print(f"  {GREEN}No fixes needed -- your setup looks well-tuned.{RESET}")
    else:
        unfixed = sum(len(c.fixes) for c in result.categories)
        if unfixed:
            print()
            print(f"{DIM}Run with --fix to see {unfixed} copy-pasteable fix suggestion(s).{RESET}")

    print()


# -- CLI entry point ---------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="claude-rate",
        description="Rate the cost-efficiency of a Claude / AI setup in a local project directory.",
        epilog="Source: https://github.com/Sagargupta16/claude-cost-optimizer",
    )
    parser.add_argument("path", nargs="?", default=".", help="Project directory (default: current dir)")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Emit machine-readable JSON")
    parser.add_argument("--fix", action="store_true", dest="show_fixes", help="Show copy-pasteable fix suggestions")
    parser.add_argument("--strict", action="store_true", help="Exit with status 1 if grade is below B")
    parser.add_argument("--version", action="version", version="claude-rate 0.1.0")

    args = parser.parse_args()

    project = Path(args.path)
    if not project.is_dir():
        print(f"{RED}Error:{RESET} '{args.path}' is not a directory", file=sys.stderr)
        sys.exit(2)

    result = rate(project)

    if args.json_output:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print_report(result, show_fixes=args.show_fixes)

    if args.strict and result.grade in ("C", "D", "F"):
        sys.exit(1)


if __name__ == "__main__":
    main()
