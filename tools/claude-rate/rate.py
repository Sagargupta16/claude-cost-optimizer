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

Pricing data verified 2026-06-06 against:
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

# Active models priced as of 2026-06-06. Prices are USD per 1M tokens.
MODELS: dict[str, dict[str, Any]] = {
    "opus-4-8": {
        "name": "Opus 4.8",
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
        "lifecycle": "legacy",
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
        "lifecycle": "legacy",
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

# Repeated path/filename literals -- declared once so the rater only has one
# place to update if Anthropic changes a convention.
CLAUDE_MD = "CLAUDE.md"
DOT_CLAUDE = ".claude"
SETTINGS_JSON = "settings.json"
SETTINGS_LOCAL_JSON = "settings.local.json"
MCP_JSON = ".mcp.json"
GITIGNORE = ".gitignore"
CLAUDEIGNORE = ".claudeignore"

# Lock-file names checked when auditing .claudeignore coverage.
LOCKFILE_NAMES = ("package-lock.json", "pnpm-lock.yaml", "yarn.lock")
LOCK_GLOB = "*.lock"

# Indentation prefix used in copy-pasteable fix output.
FIX_INDENT = "\n    "

# Grade thresholds expressed as (min_percent, letter) sorted descending --
# table-driven so total_to_grade is a simple linear scan and Sonar can't
# flag the chain as "always-false".
GRADE_TABLE: tuple[tuple[float, str], ...] = (
    (95, "A+"),
    (85, "A"),
    (70, "B"),
    (55, "C"),
    (40, "D"),
)


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

_PRIMARY_TIERS: tuple[tuple[int, int, str], ...] = (
    (2_000, 12, "concise"),
    (3_000, 10, "well-sized"),
    (CLAUDE_MD_HARD_LIMIT, 7, "near hard limit"),
    (6_000, 3, "OVER 4K hard limit -- content past 4K is silently truncated"),
    (8_000, 1, "way over hard limit"),
)
_TOTAL_TIERS: tuple[tuple[int, int], ...] = (
    (6_000, 8),
    (9_000, 6),
    (CLAUDE_MD_TOTAL_LIMIT, 4),
    (16_000, 2),
)


def _gather_claude_md_chars(project: Path) -> tuple[int, int, int]:
    """Return (primary_chars, total_chars, file_count) for CLAUDE.md files."""
    primary = project / CLAUDE_MD
    secondary = project / DOT_CLAUDE / CLAUDE_MD
    primary_chars = 0
    total_chars = 0
    count = 0
    for path in (primary, secondary):
        if path.is_file():
            chars = _char_count(_read_text(path) or "")
            total_chars += chars
            count += 1
            if path == primary:
                primary_chars = chars
    return primary_chars, total_chars, count


def _score_tier(value: int, tiers: tuple, default: tuple) -> tuple:
    """Pick the first tier whose threshold is >= value, else fall back."""
    for tier in tiers:
        if value <= tier[0]:
            return tier
    return default


def score_claude_md(project: Path) -> CategoryResult:
    """CLAUDE.md presence, size discipline, and total instruction budget."""
    cat = CategoryResult(name=CLAUDE_MD, score=0, max_score=20, detail="", findings=[], fixes=[])
    primary_chars, total_chars, file_count = _gather_claude_md_chars(project)

    if file_count == 0:
        cat.detail = f"{CLAUDE_MD} not found"
        cat.findings.append(f"No {CLAUDE_MD} at project root.")
        cat.fixes.append(
            f"Create {CLAUDE_MD} at the repo root with project conventions, "
            "tech stack, and 5-10 high-value rules. Keep under 4,000 characters."
        )
        return cat

    # Score primary file (max 12 points).
    primary_tier = _score_tier(primary_chars, _PRIMARY_TIERS, (0, 0, "massively bloated"))
    primary_score = primary_tier[1]
    primary_msg = primary_tier[2]

    # Score total instruction budget (max 8 points).
    total_tier = _score_tier(total_chars, _TOTAL_TIERS, (0, 0))
    total_score = total_tier[1]

    cat.score = primary_score + total_score
    cat.detail = (
        f"{primary_chars:,} chars primary ({primary_msg}); "
        f"{total_chars:,} chars total across {file_count} file(s)"
    )

    _add_claude_md_findings(cat, project, primary_chars, total_chars)
    return cat


def _add_claude_md_findings(cat: CategoryResult, project: Path, primary_chars: int, total_chars: int) -> None:
    """Attach findings/fixes to a CLAUDE.md result based on size thresholds."""
    if primary_chars > CLAUDE_MD_HARD_LIMIT:
        over = primary_chars - CLAUDE_MD_HARD_LIMIT
        cat.findings.append(
            f"{CLAUDE_MD} is {primary_chars:,} chars -- {over:,} chars over the 4K hard limit. "
            "Content beyond 4,000 chars is silently truncated."
        )
        cat.fixes.append(
            f"Trim {CLAUDE_MD} to under 4,000 characters. Move stack-specific or volatile "
            f"guidance to {DOT_CLAUDE}/{CLAUDE_MD} or referenced docs."
        )
    elif primary_chars > 3_000:
        cat.fixes.append(f"{CLAUDE_MD} is {primary_chars:,} chars (near 4K limit). Trim to under 3,000 to leave headroom.")

    if total_chars > CLAUDE_MD_TOTAL_LIMIT:
        cat.findings.append(
            f"Total instruction-file budget is {total_chars:,} chars -- over the ~12K total budget. "
            "Every byte loads on every turn."
        )
        cat.fixes.append(
            f"Audit ALL {CLAUDE_MD} files (root + {DOT_CLAUDE}/). Delete duplication, "
            "drop low-value rules, push verbose guidance into linked deep-dive docs."
        )

    secondary_path = project / DOT_CLAUDE / CLAUDE_MD
    if not secondary_path.is_file() and primary_chars > 3_000:
        cat.fixes.append(
            f"Consider splitting {CLAUDE_MD}: keep ~2K chars at root for global rules, "
            f"push stack-specific rules to {DOT_CLAUDE}/{CLAUDE_MD}."
        )


def score_claudeignore(project: Path) -> CategoryResult:
    """`.claudeignore` presence and coverage of common bloat sources."""
    cat = CategoryResult(name=CLAUDEIGNORE, score=0, max_score=15, detail="", findings=[], fixes=[])
    path = project / CLAUDEIGNORE

    if not path.is_file():
        return _claudeignore_missing(cat, project)

    entries = _parse_claudeignore_entries(path)
    missing = _find_claudeignore_gaps(project, entries)
    _apply_claudeignore_score(cat, len(entries), missing)
    return cat


# Coverage rules for _find_claudeignore_gaps. Each tuple is
# (pattern, dir_to_check_on_disk). dir_to_check_on_disk == None means
# "trigger the lock-file branch".
_COVERAGE_CHECKS: tuple[tuple[str, str | None], ...] = (
    ("node_modules/", "node_modules"),
    ("dist/", "dist"),
    ("build/", "build"),
    (".venv/", ".venv"),
    ("target/", "target"),
    ("vendor/", "vendor"),
    (LOCK_GLOB, None),
)

# Stack-specific dirs the suggester checks when no .claudeignore exists.
_DIR_SUGGESTIONS: tuple[tuple[str, str], ...] = (
    ("node_modules", "node_modules/"),
    ("dist", "dist/"),
    ("build", "build/"),
    (".venv", ".venv/"),
    ("venv", ".venv/"),
    ("target", "target/"),
    ("vendor", "vendor/"),
)
_DEFAULT_SUGGESTIONS: tuple[str, ...] = (
    ".git/", "*.log", "coverage/", ".next/", "*.min.js", "*.map",
)


def _suggest_claudeignore_patterns(project: Path) -> list[str]:
    """Build a deduped list of ignore patterns based on what's on disk."""
    suggestions: list[str] = []
    for dir_name, pattern in _DIR_SUGGESTIONS:
        if (project / dir_name).exists():
            suggestions.append(pattern)
    for lock in LOCKFILE_NAMES:
        if (project / lock).exists():
            suggestions.append(lock)
    if list(project.glob(LOCK_GLOB)) or list(project.glob("*.lockb")):
        suggestions.append(LOCK_GLOB)
    suggestions.extend(_DEFAULT_SUGGESTIONS)
    seen: set[str] = set()
    return [s for s in suggestions if not (s in seen or seen.add(s))]


def _claudeignore_missing(cat: CategoryResult, project: Path) -> CategoryResult:
    """Produce the result for a project that has no .claudeignore."""
    cat.detail = "not found"
    cat.findings.append(
        f"No {CLAUDEIGNORE} file. Claude will index node_modules, dist, lock files, "
        "and other large generated content."
    )
    deduped = _suggest_claudeignore_patterns(project)
    cat.fixes.append(
        f"Create {CLAUDEIGNORE} at repo root with these patterns:" + FIX_INDENT
        + FIX_INDENT.join(deduped)
    )
    return cat


def _parse_claudeignore_entries(path: Path) -> list[str]:
    """Read .claudeignore and return non-comment, non-blank entries."""
    raw = _read_text(path) or ""
    return [
        line.strip()
        for line in raw.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _has_lock_coverage(entries: list[str]) -> bool:
    """True if entries already cover any lock-file convention."""
    lock_set = {LOCK_GLOB, *LOCKFILE_NAMES}
    return any(e in lock_set or "lock" in e for e in entries)


def _project_has_lock(project: Path) -> bool:
    return any((project / lock).exists() for lock in LOCKFILE_NAMES)


def _find_claudeignore_gaps(project: Path, entries: list[str]) -> list[str]:
    """Return human-readable lines listing on-disk bloat not covered by entries."""
    missing: list[str] = []
    for pattern, dir_check in _COVERAGE_CHECKS:
        if dir_check is None:
            if _project_has_lock(project) and not _has_lock_coverage(entries):
                missing.append(f"{LOCKFILE_NAMES[0]}  # or {LOCK_GLOB} to cover all variants")
            continue
        if not (project / dir_check).exists():
            continue
        if any(pattern.rstrip("/") in e or e.rstrip("/") == dir_check for e in entries):
            continue
        missing.append(f"{pattern}  # {dir_check}/ exists on disk but not ignored")
    return missing


def _apply_claudeignore_score(cat: CategoryResult, count: int, missing: list[str]) -> None:
    """Map (entry count, missing) to score, detail, and remediation."""
    if count == 0:
        cat.score, cat.detail = 0, "file exists but is empty"
    elif count >= 8 and not missing:
        cat.score, cat.detail = 15, f"{count} entries, all common bloat covered"
    elif count >= 5 and not missing:
        cat.score, cat.detail = 12, f"{count} entries, common bloat covered"
    elif count >= 5:
        cat.score, cat.detail = 9, f"{count} entries, but {len(missing)} obvious gap(s)"
    else:
        cat.score, cat.detail = 5, f"only {count} entries -- minimal coverage"

    if missing:
        cat.findings.append(
            f"{CLAUDEIGNORE} exists but doesn't cover the following bloat sources "
            "actually present in your repo:"
        )
        cat.fixes.append(
            f"Add these lines to {CLAUDEIGNORE}:" + FIX_INDENT + FIX_INDENT.join(missing)
        )

    if count < 5:
        cat.fixes.append(
            "Aim for 5+ patterns. At minimum: node_modules/, dist/, build/, *.lock, "
            ".git/, coverage/, *.log, *.map"
        )

    return cat


_MODEL_KEYS: tuple[str, ...] = ("model", "defaultModel", "preferredModel")
_BUDGET_KEYS: tuple[str, ...] = (
    "budgetCap", "costLimit", "maxCost", "maxMonthlyCost", "maxCostPerSession", "budget",
)


def _settings_category_label() -> str:
    return f"{DOT_CLAUDE}/{SETTINGS_JSON}"


def _load_settings(project: Path) -> tuple[dict[str, Any] | None, Path | None]:
    """Find the first readable settings.json variant under .claude/."""
    for filename in (SETTINGS_JSON, SETTINGS_LOCAL_JSON):
        path = project / DOT_CLAUDE / filename
        data = _read_json(path)
        if data is not None:
            return data, path
    return None, None


def _settings_features(data: dict[str, Any]) -> tuple[bool, bool, bool, str | None]:
    """Return (has_model, has_budget, has_perms, model_id) for a settings dict."""
    model_id = next((data.get(k) for k in _MODEL_KEYS if data.get(k)), None)
    has_model = bool(model_id)
    has_budget = any(data.get(k) for k in _BUDGET_KEYS)
    perms = data.get("permissions") or {}
    has_perms = bool(perms.get("allow") or perms.get("deny")) if isinstance(perms, dict) else False
    return has_model, has_budget, has_perms, model_id if isinstance(model_id, str) else None


def score_settings(project: Path) -> CategoryResult:
    """`.claude/settings.json` model + budget config + permissions."""
    cat = CategoryResult(name=_settings_category_label(), score=0, max_score=15, detail="", findings=[], fixes=[])
    data, found_path = _load_settings(project)

    if data is None:
        cat.detail = f"no {SETTINGS_JSON}"
        cat.findings.append(
            f"No {DOT_CLAUDE}/{SETTINGS_JSON}. Default model and permissions are not project-pinned."
        )
        cat.fixes.append(
            f"Create {DOT_CLAUDE}/{SETTINGS_JSON} with at minimum:\n"
            '    {"model": "claude-sonnet-4-6", "permissions": {"allow": [], "deny": []}}'
        )
        return cat

    has_model, has_budget, has_perms, model_id = _settings_features(data)
    score = 0
    parts: list[str] = []

    if has_model:
        score += 6
        parts.append(f"model={model_id}")
    else:
        cat.fixes.append(
            f'Set "model" in {SETTINGS_JSON} to pin a default (e.g. "claude-sonnet-4-6"). '
            "Prevents accidental Opus usage on simple tasks."
        )

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
            "Define permissions to reduce permission-prompt friction:\n"
            '    "permissions": {"allow": ["Bash(npm test:*)", "Read(**)"], "deny": []}'
        )

    cat.score = score
    if parts and found_path is not None:
        cat.detail = f"found at {found_path.relative_to(project)}; " + ", ".join(parts)
    else:
        cat.detail = f"{SETTINGS_JSON} present but mostly empty"
    return cat


_MCP_TIERS: tuple[tuple[int, int, str], ...] = (
    # (max_count, score, detail_template) -- detail uses {n} for total.
    (3, 13, "{n} MCP server(s) -- light overhead (~{tokens:,} tokens/turn)"),
    (5, 10, "{n} MCP servers -- moderate overhead"),
    (8, 6, "{n} MCP servers -- heavy overhead (~{tokens:,} tokens/turn)"),
    (12, 3, "{n} MCP servers -- very heavy overhead"),
)


def _count_mcp_servers(project: Path) -> tuple[dict[str, int], dict[str, Any] | None]:
    """Return ({source_label: count}, settings_dict_or_None)."""
    counts: dict[str, int] = {}

    mcp_data = _read_json(project / MCP_JSON)
    if mcp_data is not None and isinstance(mcp_data.get("mcpServers"), dict):
        counts[MCP_JSON] = len(mcp_data["mcpServers"])

    settings = _read_json(project / DOT_CLAUDE / SETTINGS_JSON)
    if settings is not None:
        servers = settings.get("mcpServers", {})
        if isinstance(servers, dict) and servers:
            counts[f"{DOT_CLAUDE}/{SETTINGS_JSON}"] = len(servers)

    return counts, settings


def score_mcp_servers(project: Path) -> CategoryResult:
    """Count MCP servers across .mcp.json + settings.json. Each adds ~1.5K tokens/turn."""
    cat = CategoryResult(name="MCP servers", score=0, max_score=15, detail="", findings=[], fixes=[])
    counts, settings = _count_mcp_servers(project)
    total = sum(counts.values())

    if total == 0:
        cat.score = 15
        cat.detail = "no MCP servers configured (lowest overhead)"
        return cat

    tokens = total * TOKENS_PER_MCP_SERVER
    cat.score, cat.detail = 0, f"{total} MCP servers -- excessive overhead"
    for max_count, score_value, template in _MCP_TIERS:
        if total <= max_count:
            cat.score = score_value
            cat.detail = template.format(n=total, tokens=tokens)
            break

    if total > 5:
        cat.findings.append(
            f"{total} MCP servers configured (across {', '.join(counts.keys())}). "
            f"Each adds ~{TOKENS_PER_MCP_SERVER:,} tokens to every turn's system prompt."
        )
        cat.fixes.append(
            "Review which MCP servers you actually use every session. Disable rarely-used "
            f"ones in {MCP_JSON} or move them to .mcp.local.json (gitignored)."
        )

    if total > 0 and MCP_JSON not in counts and "mcpServers" in (settings or {}):
        cat.fixes.append(
            f"MCP servers are in {DOT_CLAUDE}/{SETTINGS_JSON} -- prefer the dedicated "
            f"{MCP_JSON} file (cleaner separation, easier to share/exclude)."
        )

    return cat


def score_hooks(project: Path) -> CategoryResult:
    """Hooks for budget tracking, cost logging, or permission policy."""
    cat = CategoryResult(name="Hooks", score=0, max_score=10, detail="", findings=[], fixes=[])

    settings = _read_json(project / DOT_CLAUDE / SETTINGS_JSON)
    hooks = settings.get("hooks") if settings else None
    hook_count = _count_hook_entries(hooks)

    if hook_count >= 3:
        cat.score = 10
        cat.detail = f"{hook_count} hook(s) configured"
    elif hook_count >= 1:
        cat.score = 6
        cat.detail = f"{hook_count} hook(s) configured"
        cat.fixes.append(
            "Consider adding cost-tracking hooks (PreToolUse for budget gates, Stop for session-cost summary)."
        )
    else:
        cat.detail = "no hooks configured"
        cat.fixes.append(
            "Add cost-tracking hooks. Example PostToolUse hook to log token use:\n"
            '    {"hooks": {"PostToolUse": [{"command": "echo \\"$CLAUDE_TOOL_NAME: '
            '$CLAUDE_TOKEN_COUNT tokens\\" >> ~/.claude-usage.log"}]}}'
        )

    return cat


def _count_hook_entries(hooks: Any) -> int:
    """Count individual hook entries in a settings.hooks dict."""
    if not isinstance(hooks, dict):
        return 0
    count = 0
    for value in hooks.values():
        if isinstance(value, list):
            count += len(value)
        elif value:
            count += 1
    return count


_DANGER_FILES: tuple[str, ...] = (
    ".env", ".env.local", ".env.production", "credentials.json", ".mcp.local.json",
)
_API_KEY_PATTERN = re.compile(
    r"(sk-[a-zA-Z0-9]{20,}|AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36})"
)


def _gitignore_lines(project: Path) -> list[str]:
    """Return non-empty .gitignore lines, or an empty list if missing."""
    path = project / GITIGNORE
    if not path.is_file():
        return []
    text = _read_text(path) or ""
    return [line.strip() for line in text.splitlines() if line.strip()]


def _is_gitignored(filename: str, gitignore_lines: list[str]) -> bool:
    """True if the gitignore lines plausibly cover `filename`."""
    target = filename.rstrip("/")
    return any(filename in line or line.rstrip("/") == target for line in gitignore_lines)


def _find_leaked_files(project: Path, gitignore_lines: list[str]) -> list[str]:
    """Sensitive files that exist on disk but aren't in .gitignore."""
    leaked: list[str] = []
    for filename in _DANGER_FILES:
        if (project / filename).is_file() and not _is_gitignored(filename, gitignore_lines):
            leaked.append(filename)
    return leaked


def _find_api_key_leaks(project: Path) -> list[str]:
    """Files in the repo that contain an obvious API key pattern."""
    suspects: list[str] = []
    targets = (
        project / CLAUDE_MD,
        project / DOT_CLAUDE / SETTINGS_JSON,
        project / MCP_JSON,
    )
    for target in targets:
        if not target.is_file():
            continue
        text = _read_text(target) or ""
        if _API_KEY_PATTERN.search(text):
            suspects.append(str(target.relative_to(project)))
    return suspects


def score_security(project: Path) -> CategoryResult:
    """Quick check for accidentally-committed secrets and missing gitignore entries."""
    cat = CategoryResult(name="Security & hygiene", score=0, max_score=10, detail="", findings=[], fixes=[])

    gitignore_lines = _gitignore_lines(project)
    has_gitignore = bool(gitignore_lines) or (project / GITIGNORE).is_file()
    leaked = _find_leaked_files(project, gitignore_lines)
    suspect_files = _find_api_key_leaks(project)

    score = 10
    if leaked:
        score -= 6
        cat.findings.append(
            f"Sensitive files exist on disk but are NOT in {GITIGNORE}: {', '.join(leaked)}. "
            "These will be committed unless explicitly ignored."
        )
        cat.fixes.append(
            f"Add to {GITIGNORE} IMMEDIATELY:" + FIX_INDENT
            + FIX_INDENT.join(leaked + [".env*", "*.key", ".mcp.local.json"])
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

    if not has_gitignore:
        score = max(0, score - 3)
        cat.findings.append(f"No {GITIGNORE} at all -- secrets and build artifacts will be tracked.")
        cat.fixes.append(f"Run `git init` properly or copy a starter {GITIGNORE} for your stack.")

    cat.score = max(0, score)
    if cat.score == cat.max_score:
        cat.detail = f"no leaked secrets, {GITIGNORE} present"
    elif leaked or suspect_files:
        cat.detail = "RISK: review findings"
    else:
        cat.detail = "minor gaps"

    return cat


def _score_cost_mode(project: Path) -> tuple[int, str | None]:
    """5 points if the cost-mode skill is installed."""
    candidates = (
        project / "skills" / "cost-mode",
        project / DOT_CLAUDE / "skills" / "cost-mode",
    )
    if any(p.exists() for p in candidates):
        return 5, "cost-mode skill installed"
    return 0, None


def _score_commands(project: Path) -> tuple[int, str | None]:
    """Up to 4 points for custom slash commands in .claude/commands/."""
    cmd_dir = project / DOT_CLAUDE / "commands"
    if not cmd_dir.is_dir():
        return 0, None
    count = len(list(cmd_dir.glob("*.md")))
    if count >= 3:
        return 4, f"{count} custom slash command(s)"
    if count >= 1:
        return 2, f"{count} custom slash command(s)"
    return 0, None


def _score_subagents(project: Path) -> tuple[int, str | None]:
    """3 points for any defined custom subagents."""
    agents_dir = project / DOT_CLAUDE / "agents"
    if agents_dir.is_dir() and any(agents_dir.iterdir()):
        return 3, "custom subagent(s) defined"
    return 0, None


def _score_plugin_metadata(project: Path) -> tuple[int, str | None]:
    """3 points for a .claude-plugin/marketplace.json file."""
    if (project / ".claude-plugin" / "marketplace.json").is_file():
        return 3, "plugin marketplace metadata"
    return 0, None


def score_optimizer_tooling(project: Path) -> CategoryResult:
    """Bonus points for already-installed cost-optimization tooling."""
    cat = CategoryResult(name="Optimizer tooling", score=0, max_score=15, detail="", findings=[], fixes=[])

    sub_scorers = (
        _score_cost_mode,
        _score_commands,
        _score_subagents,
        _score_plugin_metadata,
    )
    score = 0
    found: list[str] = []
    for sub_scorer in sub_scorers:
        sub_score, label = sub_scorer(project)
        score += sub_score
        if label is not None:
            found.append(label)

    cat.score = min(score, cat.max_score)
    cat.detail = (
        ", ".join(found) if found
        else "none of: cost-mode skill, custom commands, subagents, plugin metadata"
    )

    if not found:
        cat.fixes.append(
            "Install the cost-mode skill for ~30-60% output reduction:\n"
            "    /plugin marketplace add Sagargupta16/claude-cost-optimizer\n"
            "    /plugin install cost-mode@sagargupta16-claude-cost-optimizer"
        )
    if not (project / DOT_CLAUDE / "commands").is_dir():
        cat.fixes.append(
            f"Create {DOT_CLAUDE}/commands/ with reusable slash commands "
            "(e.g. /cost-check, /quick-fix). Saves re-explaining workflows."
        )

    return cat


# -- Grade mapping -----------------------------------------------------------

def total_to_grade(total: int, max_total: int) -> str:
    """Map (score, max) to a letter grade via GRADE_TABLE."""
    pct = (total / max_total) * 100 if max_total else 0
    for threshold, letter in GRADE_TABLE:
        if pct >= threshold:
            return letter
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

_SCORERS = (
    score_claude_md,
    score_claudeignore,
    score_settings,
    score_mcp_servers,
    score_hooks,
    score_security,
    score_optimizer_tooling,
)


def rate(project: Path) -> RateResult:
    categories = [scorer(project) for scorer in _SCORERS]
    total = sum(c.score for c in categories)
    max_total = sum(c.max_score for c in categories)
    grade = total_to_grade(total, max_total)

    _, claude_md_chars, _ = _gather_claude_md_chars(project)
    counts, _ = _count_mcp_servers(project)
    mcp_count = sum(counts.values())

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

_BAR_WIDTH = 20
_PRICING_VERIFIED_DATE = "2026-06-06"


def _ratio_color(ratio: float) -> str:
    """Pick an ANSI color matching a 0..1 score ratio."""
    if ratio >= 0.8:
        return GREEN
    if ratio >= 0.5:
        return YELLOW
    return RED


def _print_category_lines(categories: list[CategoryResult]) -> None:
    """Render the per-category bar chart + findings."""
    for cat in categories:
        ratio = cat.score / cat.max_score if cat.max_score else 0
        color = _ratio_color(ratio)
        filled = int(_BAR_WIDTH * ratio)
        bar = "#" * filled + "-" * (_BAR_WIDTH - filled)
        score_str = f"{cat.score:>2}/{cat.max_score:<2}"
        print(
            f"  {cat.name:<24} {color}[{bar}]{RESET}  {color}{score_str}{RESET}  "
            f"{DIM}{cat.detail}{RESET}"
        )
        for finding in cat.findings:
            print(f"    {YELLOW}!{RESET} {finding}")


def _print_cost_block(result: RateResult) -> None:
    """Render total/grade and the per-model cost estimate table."""
    grade_c = grade_ansi(result.grade)
    print(f"{BOLD}Total:{RESET} {result.score}/{result.max_score}  ({grade_c}{result.grade}{RESET})")
    print()
    print(
        f"{BOLD}Estimated monthly cost{RESET} "
        f"{DIM}(30 turns/session, 3 sessions/day, 22 days, 70% cache hit){RESET}"
    )
    for cost in result.cost_estimate.values():
        print(
            f"  {cost['name']:<14} {DIM}${cost['per_session']:>5.2f}/session{RESET}"
            f"  ->  {BOLD}${cost['per_month']:>7.2f}/month{RESET}"
        )
    print()
    print(f"{CYAN}Badge URL:{RESET}  {result.badge_url}")
    print(f"{CYAN}Markdown:{RESET}  {result.badge_markdown}")


def _print_fix_block(result: RateResult) -> None:
    """Render the --fix output block."""
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


def print_report(result: RateResult, show_fixes: bool = False) -> None:
    print()
    print(f"{BOLD}claude-rate{RESET} {DIM}-- Claude / AI setup audit{RESET}")
    print(f"{DIM}{'=' * 60}{RESET}")
    print(f"Project: {result.project}")
    print(f"Verified against Anthropic pricing as of: {DIM}{_PRICING_VERIFIED_DATE}{RESET}")
    print()

    _print_category_lines(result.categories)
    print()
    _print_cost_block(result)

    if show_fixes:
        _print_fix_block(result)
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
