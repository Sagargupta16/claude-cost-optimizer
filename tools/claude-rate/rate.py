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

Pricing data verified 2026-11-10 against:
    https://platform.claude.com/docs/en/about-claude/pricing
    https://platform.claude.com/docs/en/models/overview
    https://platform.claude.com/docs/en/models/haiku-5-5/overview
    https://platform.claude.com/docs/en/models/sonnet-5-5/overview
    https://platform.claude.com/docs/en/models/opus-5-5/overview
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# -- Pricing data (mirrors site/src/utils/pricing.ts) ------------------------

# Models priced as of 2026-11-10. Prices are USD per 1M tokens.
# `fast_mode` marks the models that honor `speed: "fast"` (a flat 2x of the
# model's own base on both input and output). Since Fable 5.2's release on
# 2026-11-09 that is Fable 5.2 (and Mythos 5.2), Opus 5.5, Opus 5 and Opus 4.8:
# Opus 4.7 errors on `speed: "fast"`, and Opus 4.6 silently downgrades to
# standard speed at standard rates. The old 6x tier no longer exists. Opus 4.8
# Fast Mode is deprecated and removed on 2026-11-30 (Anthropic release notes,
# 2026-10-30).
# `cache_hit` has three multipliers: 0.1x input on most models, 0.05x on
# Opus 5.5 ($0.20/MTok) and Sonnet 5.5 ($0.10/MTok since 2026-10-07), and 0.025x
# on Fable 5.2 / Mythos 5.2 ($0.20/MTok) and Fable 5.1 / Mythos 5.1 ($0.25/MTok)
# -- read the field, never recompute it as input * 0.1.
# `long_prompt` (Haiku 5.5 only) is a second price tier: a request whose prompt,
# cache reads and writes included, is over `threshold` tokens pays those rates on
# the whole request.
MODELS: dict[str, dict[str, Any]] = {
    # $8/$40 -- 20% below Fable 5.1 on every rate, and 2x Opus 5.5 (Fable 5.1 was 2.5x).
    "fable-5-2": {
        "name": "Fable 5.2",
        "input": 8.00,
        "output": 40.00,
        "cache_hit": 0.20,
        "cache_5m_write": 10.00,
        "cache_1h_write": 16.00,
        "context_window": 1_000_000,
        "tokenizer_overhead": 1.3,
        "fast_mode": True,
        "lifecycle": "active",
    },
    "fable-5-1": {
        "name": "Fable 5.1",
        "input": 10.00,
        "output": 50.00,
        "cache_hit": 0.25,
        "cache_5m_write": 12.50,
        "cache_1h_write": 20.00,
        "context_window": 1_000_000,
        "tokenizer_overhead": 1.3,
        "fast_mode": False,
        "lifecycle": "legacy",
    },
    "fable-5": {
        "name": "Fable 5",
        "input": 10.00,
        "output": 50.00,
        "cache_hit": 1.00,
        "cache_5m_write": 12.50,
        "cache_1h_write": 20.00,
        "context_window": 1_000_000,
        "tokenizer_overhead": 1.3,
        "fast_mode": False,
        "lifecycle": "legacy",
    },
    # $4/$20 -- 20% below Opus 5 (Opus 4.5 made the earlier cut, $15/$75 to $5/$25).
    "opus-5-5": {
        "name": "Opus 5.5",
        "input": 4.00,
        "output": 20.00,
        "cache_hit": 0.20,
        "cache_5m_write": 5.00,
        "cache_1h_write": 8.00,
        "context_window": 1_000_000,
        "tokenizer_overhead": 1.3,
        "fast_mode": True,
        "lifecycle": "active",
    },
    "opus-5": {
        "name": "Opus 5",
        "input": 5.00,
        "output": 25.00,
        "cache_hit": 0.50,
        "cache_5m_write": 6.25,
        "cache_1h_write": 10.00,
        "context_window": 1_000_000,
        "tokenizer_overhead": 1.3,
        "fast_mode": True,
        "lifecycle": "legacy",
    },
    "opus-4-8": {
        "name": "Opus 4.8",
        "input": 5.00,
        "output": 25.00,
        "cache_hit": 0.50,
        "cache_5m_write": 6.25,
        "cache_1h_write": 10.00,
        "context_window": 1_000_000,
        "tokenizer_overhead": 1.3,
        "fast_mode": True,
        "lifecycle": "legacy",
    },
    "opus-4-7": {
        "name": "Opus 4.7",
        "input": 5.00,
        "output": 25.00,
        "cache_hit": 0.50,
        "cache_5m_write": 6.25,
        "cache_1h_write": 10.00,
        "context_window": 1_000_000,
        "tokenizer_overhead": 1.3,
        "fast_mode": False,
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
        "fast_mode": False,
        "lifecycle": "legacy",
    },
    # Retired on the Claude API 2026-08-05; Bedrock and Google Cloud (Google managed)
    # still serve it. Rates: the pricing page, read 2026-11-03. Opus 4 bills the same,
    # so `opus-4` is a _PRICE_ALIASES entry, not a second row. Keep a retired row for
    # as long as any platform still serves the model.
    "opus-4-1": {
        "name": "Opus 4.1",
        "input": 15.00,
        "output": 75.00,
        "cache_hit": 1.50,
        "cache_5m_write": 18.75,
        "cache_1h_write": 30.00,
        "context_window": 200_000,
        "tokenizer_overhead": 1.0,
        "fast_mode": False,
        "lifecycle": "legacy",
    },
    # Same $2/$10 and tokenizer as Sonnet 5; the cache floor drops to 512 tokens,
    # and the cache read was cut to $0.10 (0.05x) on 2026-10-07.
    "sonnet-5-5": {
        "name": "Sonnet 5.5",
        "input": 2.00,
        "output": 10.00,
        "cache_hit": 0.10,
        "cache_5m_write": 2.50,
        "cache_1h_write": 4.00,
        "context_window": 1_000_000,
        "tokenizer_overhead": 1.3,
        "fast_mode": False,
        "lifecycle": "active",
    },
    # $2/$10 became the permanent standard price on 2026-09-01; the scheduled
    # increase to $3/$15 was cancelled.
    "sonnet-5": {
        "name": "Sonnet 5",
        "input": 2.00,
        "output": 10.00,
        "cache_hit": 0.20,
        "cache_5m_write": 2.50,
        "cache_1h_write": 4.00,
        "context_window": 1_000_000,
        "tokenizer_overhead": 1.3,
        "fast_mode": False,
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
        "lifecycle": "legacy",
    },
    # Tiered: $0.10/$0.50 up to 100,000 prompt tokens, $0.50/$2.50 above.
    "haiku-5-5": {
        "name": "Haiku 5.5",
        "input": 0.10,
        "output": 0.50,
        "cache_hit": 0.01,
        "cache_5m_write": 0.125,
        "cache_1h_write": 0.20,
        "context_window": 1_000_000,
        "tokenizer_overhead": 1.3,
        "fast_mode": False,
        "lifecycle": "active",
        "long_prompt": {
            "threshold": 100_000,
            "input": 0.50,
            "output": 2.50,
            "cache_hit": 0.05,
            "cache_5m_write": 0.625,
            "cache_1h_write": 1.00,
        },
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
        "lifecycle": "legacy",
    },
}

# Token estimation constants (mirrors TOKEN_ESTIMATES in pricing.ts).
TOKENS_PER_CLAUDE_MD_LINE = 10
SYSTEM_PROMPT_TOKENS = 3_500
# Worst case: full schemas with MCP tool search off. With tool search on (the
# default) a server adds only its tool names and instructions, so this overstates.
TOKENS_PER_MCP_SERVER = 1_500
TOKENS_PER_FILE_READ = 2_000
OUTPUT_TOKENS_PER_TURN = 500
HISTORY_GROWTH_PER_TURN = 1_500

# CLAUDE.md loads in full at launch; there is no character cap. Anthropic's
# guidance is to "target under 200 lines per CLAUDE.md file. Longer files
# consume more context and reduce adherence." So size is scored on the primary
# file's line count plus estimated tokens (chars / 4) across both files.
CLAUDE_MD_LINE_GUIDANCE = 200

# Repeated path/filename literals -- declared once so the rater only has one
# place to update if Anthropic changes a convention.
CLAUDE_MD = "CLAUDE.md"
DOT_CLAUDE = ".claude"
SETTINGS_JSON = "settings.json"
SETTINGS_LOCAL_JSON = "settings.local.json"
MCP_JSON = ".mcp.json"
GITIGNORE = ".gitignore"
# Claude Code does not read this file. It is detected only so the rater can
# say so and convert its patterns into Read deny rules.
IGNORE_FILE = ".claudeignore"
IGNORE_FILE_FINDING = (
    "`.claudeignore` is not read by Claude Code -- its permissions docs say the "
    "file has no effect. Move its patterns into permissions.deny as Read(...) rules."
)

# Lock files at the project root that the Read deny rules should cover.
LOCKFILE_NAMES = (
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "poetry.lock",
    "Cargo.lock",
    "uv.lock",
)
LOCK_GLOB = "*.lock"
LOCK_WILDCARD = "*lock*"

# A permissions.deny entry that keeps Claude's file tools out of a path.
READ_RULE = re.compile(r"Read\(.+\)")

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


def _read_text(root: Path, relative: str | Path) -> str | None:
    """Read a file under `root`, rejecting any path that escapes the project."""
    base = root.resolve()
    candidate = (base / relative).resolve()
    if not candidate.is_relative_to(base):
        return None
    try:
        return candidate.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _read_json(root: Path, relative: str | Path) -> dict[str, Any] | None:
    text = _read_text(root, relative)
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

# Primary file line count -> (max_lines, points, label). Over 500 lines scores 1.
_PRIMARY_TIERS: tuple[tuple[int, int, str], ...] = (
    (100, 12, "concise"),
    (CLAUDE_MD_LINE_GUIDANCE, 10, "within the 200-line guidance"),
    (300, 6, "over the 200-line guidance"),
    (500, 3, "well over the 200-line guidance"),
)
# Estimated tokens across both files -> (max_tokens, points). Over 16,000 scores 0.
_TOTAL_TIERS: tuple[tuple[int, int], ...] = (
    (2_000, 8),
    (4_000, 6),
    (8_000, 4),
    (16_000, 2),
)


def _gather_claude_md(project: Path) -> tuple[int, int, int]:
    """Return (primary_lines, total_chars, file_count) for CLAUDE.md files.

    Primary is the root CLAUDE.md, or .claude/CLAUDE.md when the root has none.
    """
    texts = [
        _read_text(project, relative) or ""
        for relative in (Path(CLAUDE_MD), Path(DOT_CLAUDE) / CLAUDE_MD)
        if (project / relative).is_file()
    ]
    primary_lines = _line_count(texts[0]) if texts else 0
    return primary_lines, sum(_char_count(t) for t in texts), len(texts)


def _score_tier(value: int, tiers: tuple, default: tuple) -> tuple:
    """Pick the first tier whose threshold is >= value, else fall back."""
    for tier in tiers:
        if value <= tier[0]:
            return tier
    return default


def score_claude_md(project: Path) -> CategoryResult:
    """CLAUDE.md presence, primary line count, and estimated tokens across files."""
    cat = CategoryResult(
        name=CLAUDE_MD, score=0, max_score=20, detail="", findings=[], fixes=[]
    )
    primary_lines, total_chars, file_count = _gather_claude_md(project)

    if file_count == 0:
        cat.detail = f"{CLAUDE_MD} not found"
        cat.findings.append(f"No {CLAUDE_MD} at project root.")
        cat.fixes.append(
            f"Create {CLAUDE_MD} at the repo root with project conventions, "
            "tech stack, and 5-10 high-value rules. Keep it under 200 lines "
            "(Anthropic's guidance)."
        )
        return cat

    total_tokens = math.ceil(total_chars / 4)

    # Primary file line count (max 12 points).
    primary_tier = _score_tier(
        primary_lines, _PRIMARY_TIERS, (0, 1, "far over the 200-line guidance")
    )
    primary_score = primary_tier[1]
    primary_msg = primary_tier[2]

    # Estimated tokens across both files (max 8 points).
    total_tier = _score_tier(total_tokens, _TOTAL_TIERS, (0, 0))
    total_score = total_tier[1]

    cat.score = primary_score + total_score
    cat.detail = (
        f"{primary_lines:,} lines primary ({primary_msg}); "
        f"~{total_tokens:,} tokens total across {file_count} file(s)"
    )

    _add_claude_md_findings(cat, primary_lines, total_tokens)
    _add_dead_load_findings(cat, project)
    return cat


def _add_claude_md_findings(
    cat: CategoryResult, primary_lines: int, total_tokens: int
) -> None:
    """Attach findings/fixes to a CLAUDE.md result based on size thresholds."""
    if primary_lines > CLAUDE_MD_LINE_GUIDANCE:
        cat.findings.append(
            f"{primary_lines} lines -- over Anthropic's 200-line guidance for CLAUDE.md. "
            "Longer files consume more context and reduce adherence. Move "
            "workflow-specific instructions into skills or path-scoped .claude/rules/ "
            "so they load on demand."
        )
        cat.fixes.append(
            f"Trim {CLAUDE_MD} to under 200 lines. Move workflow-specific instructions "
            "(PR reviews, DB migrations) into skills, and directory-specific rules into "
            f"{DOT_CLAUDE}/rules/ with `paths:` frontmatter."
        )

    if total_tokens > _TOTAL_TIERS[0][0]:
        cat.fixes.append(
            f"Your {CLAUDE_MD} files total ~{total_tokens:,} tokens and load in full at "
            "the start of every session. Delete duplication and drop low-value rules; "
            "2,000 tokens or fewer scores full marks."
        )


# -- Always-loaded instructions: stale paths, repeated lines, size gate --
#
# Findings only; none of this changes the score. At launch Claude Code loads
# CLAUDE.md, .claude/CLAUDE.md, CLAUDE.local.md, every .claude/rules/ file
# without `paths` frontmatter, and the files they @import, up to four hops
# (code.claude.com/docs/en/memory, read 2026-11-03). CLAUDE.md files in parent
# directories load too; they sit outside the project and are not read here.

CLAUDE_LOCAL_MD = "CLAUDE.local.md"
_INSTRUCTION_FILES = (CLAUDE_MD, f"{DOT_CLAUDE}/{CLAUDE_MD}")
_IMPORT_HOPS = 4
_FENCE = re.compile(r"\s*(```|~~~)")
_MD_LINK = re.compile(r"\[[^\]\n]*\]\(([^)\s]+)[^)]*\)")
_CODE_SPAN = re.compile(r"`[^`\n]+`")
_IMPORT_REF = re.compile(r"(?<!\w)@([^\s`]+)")
_URL_SCHEME = re.compile(r"[A-Za-z][\w+.-]*:")
_FILE_EXT = re.compile(r"\.\w{1,6}$")
_LIST_MARKER = re.compile(r"^(?:[-*+]|\d+[.)])\s+")
_DUP_MIN_CHARS = 25
_NEAR_DUP_RATIO = 0.9
_LISTED_REFS = 5


def _project_rule_files(project: Path) -> list[str]:
    """Project .claude/rules/ files without `paths` frontmatter (they load every session)."""
    rules = project / DOT_CLAUDE / "rules"
    if not rules.is_dir():
        return []
    names = [rule.relative_to(project).as_posix() for rule in sorted(rules.rglob("*.md"))]
    return [n for n in names if "paths" not in _frontmatter(_read_text(project, n) or "")]


def _instruction_files(project: Path) -> list[str]:
    """Always-loaded project instruction files that exist, widest scope first."""
    names = [*_INSTRUCTION_FILES, *_project_rule_files(project), CLAUDE_LOCAL_MD]
    return [name for name in names if (project / name).is_file()]


def _prose_lines(text: str) -> list[tuple[int, str]]:
    """(1-based line number, line) outside frontmatter and fenced code blocks."""
    lines = text.splitlines()
    start = 0
    if lines and lines[0].strip() == "---":
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        start = 0 if end is None else end + 1
    out: list[tuple[int, str]] = []
    fenced = False
    for number, line in enumerate(lines[start:], start + 1):
        if _FENCE.match(line):
            fenced = not fenced
        elif not fenced:
            out.append((number, line))
    return out


def _clean_ref(token: str) -> str:
    return token.rstrip(".,;:!?)").split("#", 1)[0]


def _skippable_ref(ref: str) -> bool:
    """URLs, home or absolute paths, globs, placeholders and variables are not checked."""
    return (
        not ref
        or _URL_SCHEME.match(ref) is not None
        or ref.startswith(("/", "~", "$", "-", "\\"))
        or any(ch in ref for ch in "*?[]{}<>$% \t")
    )


def _missing_target(project: Path, base: Path, ref: str) -> bool:
    """True when `ref`, resolved from `base`, stays inside the project and does not exist."""
    target = (base / ref).resolve()
    return target.is_relative_to(project.resolve()) and not target.exists()


def _backtick_ref_missing(project: Path, ref: str) -> bool:
    """A backticked path counts only when it has a `/` and its first folder exists."""
    head = ref.split("/", 1)[0]
    return "/" in ref and bool(head) and (project / head).is_dir() and _missing_target(project, project, ref)


def _import_ref_missing(project: Path, base: Path, ref: str) -> bool:
    """A dead @import: a path whose first folder exists, or a file name with an extension."""
    if "/" in ref:
        if not (base / ref.split("/", 1)[0]).is_dir():
            return False
    elif not _FILE_EXT.search(ref):
        return False
    return _missing_target(project, base, ref)


def _line_refs(line: str) -> tuple[list[str], list[str], list[str]]:
    """(link targets, backticked tokens, @imports) on a line; a link's label is not a reference."""
    import urllib.parse

    links = [urllib.parse.unquote(t) for t in _MD_LINK.findall(line)]
    rest = _MD_LINK.sub(" ", line)
    spans = [span[1:-1].strip() for span in _CODE_SPAN.findall(rest)]
    imports = _IMPORT_REF.findall(_CODE_SPAN.sub(" ", rest))
    return [_clean_ref(t) for t in links], [_clean_ref(t) for t in spans], [_clean_ref(t) for t in imports]


def _stale_refs(project: Path, name: str) -> list[str]:
    """`file:line ref` for each path reference in one instruction file that points at nothing."""
    base = (project / name).parent
    stale: list[str] = []
    for number, line in _prose_lines(_read_text(project, name) or ""):
        links, spans, imports = _line_refs(line)
        found = [r for r in links if not _skippable_ref(r) and _missing_target(project, base, r)]
        found += [r for r in spans if not _skippable_ref(r) and _backtick_ref_missing(project, r)]
        found += [f"@{r}" for r in imports if not _skippable_ref(r) and _import_ref_missing(project, base, r)]
        stale.extend(f"{name}:{number} {ref}" for ref in found)
    return stale


def _normalized_line(line: str) -> str | None:
    """A line as the duplicate check compares it, or None for headings, tables and short lines.

    Mirrored by normalizedLine in site/src/utils/repoAnalyzer.ts: change both together.
    """
    text = line.strip()
    if text.startswith(("#", "|", "<!--")):
        return None
    text = _LIST_MARKER.sub("", text, count=1)
    for mark in ("**", "__", "`"):
        text = text.replace(mark, "")
    text = re.sub(r"\s+", " ", text).strip().lower().rstrip(".:;,!")
    return text if len(text) >= _DUP_MIN_CHARS else None


def _near_duplicate(norm: str, earlier: list[tuple[str, str]]) -> str | None:
    """Location of an earlier line at least 90% similar to `norm` (same first two words)."""
    import difflib

    for text, where in earlier[:200]:
        matcher = difflib.SequenceMatcher(None, text, norm)
        if matcher.quick_ratio() >= _NEAR_DUP_RATIO and matcher.ratio() >= _NEAR_DUP_RATIO:
            return f"{where} (near)"
    return None


def _repeated_lines(project: Path, names: list[str]) -> tuple[list[str], int]:
    """(`later:line repeats first:line` entries, chars of the repeated lines) across files."""
    first: dict[str, str] = {}
    by_words: dict[str, list[tuple[str, str]]] = {}
    repeats: list[str] = []
    chars = 0
    for name in names:
        for number, line in _prose_lines(_read_text(project, name) or ""):
            norm = _normalized_line(line)
            if norm is None:
                continue
            words = " ".join(norm.split()[:2])
            match = first.get(norm) or _near_duplicate(norm, by_words.get(words, []))
            if match:
                repeats.append(f"{name}:{number} repeats {match}")
                chars += len(line.strip())
                continue
            first[norm] = f"{name}:{number}"
            by_words.setdefault(words, []).append((norm, first[norm]))
    return repeats, chars


def _listed(items: list[str]) -> str:
    shown = "; ".join(items[:_LISTED_REFS])
    more = len(items) - _LISTED_REFS
    return f"{shown}; and {more} more" if more > 0 else shown


def _add_dead_load_findings(cat: CategoryResult, project: Path) -> None:
    """Stale path references and repeated lines in the always-loaded instruction files."""
    names = _instruction_files(project)
    checked = (*_INSTRUCTION_FILES, CLAUDE_LOCAL_MD)
    stale = [ref for name in names if name in checked for ref in _stale_refs(project, name)]
    if stale:
        cat.findings.append(
            f"{len(stale)} path reference(s) in CLAUDE.md files point at nothing: {_listed(stale)}. "
            "Claude may try to open them and get an error."
        )
        cat.fixes.append("Point each stale reference at a file that exists, or remove it: " + _listed(stale))
    repeats, chars = _repeated_lines(project, names)
    if repeats:
        cat.findings.append(
            f"{len(repeats)} line(s) repeat an earlier line in the always-loaded instruction files "
            f"(~{math.ceil(chars / 4):,} tokens in every session): {_listed(repeats)}."
        )
        cat.fixes.append(
            "Keep one copy of each repeated line, in the file named after 'repeats' (it loads at "
            "least as widely). A copy kept on purpose in a narrower scope can stay."
        )


def _import_refs(line: str) -> list[str]:
    return [_clean_ref(t) for t in _IMPORT_REF.findall(_CODE_SPAN.sub(" ", _MD_LINK.sub(" ", line)))]


def _imports_of(project: Path, name: str) -> list[str]:
    """Files inside the project that one instruction file @imports and that exist."""
    root, base = project.resolve(), (project / name).parent
    found: list[str] = []
    for _, line in _prose_lines(_read_text(project, name) or ""):
        for ref in (r for r in _import_refs(line) if not _skippable_ref(r)):
            target = (base / ref).resolve()
            if target.is_relative_to(root) and target.is_file():
                found.append(target.relative_to(root).as_posix())
    return found


def _followed_imports(project: Path, names: list[str]) -> list[str]:
    """@imports of the instruction files, followed up to four hops, each counted once."""
    seen = set(names)
    frontier = list(names)
    found: list[str] = []
    for _ in range(_IMPORT_HOPS):
        nxt: list[str] = []
        for ref in (r for name in frontier for r in _imports_of(project, name)):
            if ref not in seen:
                seen.add(ref)
                nxt.append(ref)
        found.extend(nxt)
        frontier = nxt
    return found


def always_loaded_files(project: Path, include_user: bool = False) -> list[tuple[str, int]]:
    """(name, chars) of the instruction files Claude Code loads at launch, for --max-context-tokens."""
    names = _instruction_files(project)
    files = [(n, len(_read_text(project, n) or "")) for n in names + _followed_imports(project, names)]
    if include_user:
        files += [(f"user {name}", chars) for name, chars in _always_loaded_instructions(_claude_dir())]
    return files


def _over_context_budget(project: Path, limit: int, include_user: bool) -> bool:
    """Print a reason and return True when the always-loaded estimate is over `limit` tokens."""
    files = always_loaded_files(project, include_user)
    tokens = math.ceil(sum(chars for _, chars in files) / 4)
    if tokens <= limit:
        return False
    biggest = sorted(files, key=lambda f: f[1], reverse=True)[:3]
    listed = ", ".join(f"{name} ~{math.ceil(chars / 4):,}" for name, chars in biggest)
    print(
        f"claude-rate: always-loaded instructions are ~{tokens:,} tokens, over "
        f"--max-context-tokens {limit:,}. Largest: {listed}.",
        file=sys.stderr,
    )
    return True


_READ_RULE_TIERS: tuple[tuple[int, int], ...] = (
    # (min_rule_count, points)
    (10, 13),
    (5, 10),
    (1, 6),
)

# The Read deny block --fix suggests is built from what the project has. A Read
# deny rule also blocks Edit and Write on the same path
# (code.claude.com/docs/en/permissions, read 2026-11-03), so a folder below is
# named only when it exists within two levels of the root, git reports it
# ignored, and no tracked file sits under it. A single-segment deny pattern such
# as Read(dist/**) matches that folder name at any depth, which also covers
# nested copies in a monorepo. The .env rules and root lock files are always kept.
_ENV_DENY: tuple[str, ...] = ("Read(./.env)", "Read(./.env.*)")
_GENERATED_DIRS: tuple[str, ...] = (
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".next",
    ".turbo",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "htmlcov",
    "target",
    "vendor",
    ".dart_tool",
    ".terraform",
    ".gradle",
)
# Generated-file globs, suggested only when git tracks a file that matches one.
_GENERATED_GLOBS: tuple[str, ...] = ("*.min.js", "*.min.css", "*.map", "*.pb.go", "*_pb2.py", "*.g.dart")
_DIR_SCAN_DEPTH = 2
_DENY_NOTES = (
    "A Read deny rule also blocks Edit and Write on the same path (code.claude.com/docs/en/permissions, "
    "read 2026-11-03), so a build or dependency folder is listed only when it exists, git ignores it and "
    "it holds no tracked file. The Grep tool skips gitignored files, but it is in the default tool set "
    "only on Windows; Glob and the find and grep that Claude runs through Bash make no such promise, and "
    "a committed generated file is never skipped (code.claude.com/docs/en/tools-reference, read 2026-11-03)."
)


def _read_deny_rules(settings: dict[str, Any] | None) -> list[str]:
    """Entries of permissions.deny that are Read(...) rules."""
    perms = (settings or {}).get("permissions")
    deny = perms.get("deny") if isinstance(perms, dict) else None
    if not isinstance(deny, list):
        return []
    return [r for r in deny if isinstance(r, str) and READ_RULE.fullmatch(r)]


def _lock_covered(lock: str, rules: list[str]) -> bool:
    return any(lock in r or LOCK_GLOB in r or LOCK_WILDCARD in r for r in rules)


def _ignore_file_as_read_rules(project: Path) -> list[str]:
    """Convert each ignore-file pattern to a Read deny rule.

    `dir/` -> Read(./dir/**); a pattern containing `/` elsewhere -> Read(./pattern)
    with any leading `/` stripped; a bare name or glob -> Read(pattern), which
    matches at any depth. Blank lines, comments and `!` negations are skipped.
    """
    rules: list[str] = []
    for line in (_read_text(project, IGNORE_FILE) or "").splitlines():
        s = line.strip()
        if not s or s.startswith(("#", "!")):
            continue
        if s.endswith("/"):
            rules.append(f"Read(./{s[:-1].removeprefix('/')}/**)")
        elif "/" in s:
            rules.append(f"Read(./{s.removeprefix('/')})")
        else:
            rules.append(f"Read({s})")
    return rules


def _json_block(data: dict[str, Any]) -> str:
    """A copy-pasteable JSON block, indented for fix output."""
    text = json.dumps(data, indent=2)
    return FIX_INDENT + FIX_INDENT.join(text.splitlines())


def _deny_block(rules: list[str] | tuple[str, ...]) -> str:
    """A copy-pasteable permissions.deny JSON block, indented for fix output."""
    return _json_block({"permissions": {"deny": list(rules)}})


def _subdirs(folder: Path) -> list[Path]:
    try:
        return [Path(e.path) for e in os.scandir(folder) if e.is_dir(follow_symlinks=False)]
    except OSError:
        return []


def _find_generated_dirs(project: Path) -> list[str]:
    """Relative paths of _GENERATED_DIRS folders with at most two folders between them and the root."""
    found: list[str] = []
    frontier = [project]
    for _ in range(_DIR_SCAN_DEPTH + 1):
        nxt: list[Path] = []
        for entry in (e for folder in frontier for e in _subdirs(folder)):
            if entry.name in _GENERATED_DIRS:
                found.append(entry.relative_to(project).as_posix())
            elif entry.name != ".git":
                nxt.append(entry)
        frontier = nxt
    return found


def _git(project: Path, *args: str, stdin: str = "") -> str | None:
    """stdout of a read-only git command run in `project`, or None when git cannot answer."""
    import subprocess

    try:
        run = subprocess.run(
            ["git", "-C", str(project), *args],
            input=stdin,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    # check-ignore exits 1 when nothing is ignored; anything else is a failure.
    return run.stdout if run.returncode in (0, 1) else None


def _in_git_repo(project: Path) -> bool:
    return any((folder / ".git").exists() for folder in (project, *project.parents))


def _ignore_line_forms(path: str) -> set[str]:
    """The .gitignore lines that name the folder at `path` exactly."""
    name = path.rsplit("/", 1)[-1]
    forms = {name, f"{name}/", f"**/{name}", f"**/{name}/"}
    if "/" not in path:
        forms |= {f"/{name}", f"/{name}/"}
    return forms


def _ignored_untracked(project: Path, paths: list[str]) -> list[str]:
    """The folders git ignores that hold no tracked file.

    When git cannot answer inside a repository, nothing is suggested (it cannot
    confirm the folder holds no committed file). Outside any repository nothing is
    tracked, so a folder counts when the root .gitignore names it exactly.
    """
    if not paths:
        return []
    ignored = _git(project, "check-ignore", "--stdin", "-z", stdin="\0".join(paths))
    tracked = _git(project, "ls-files", "-z", "--", *paths)
    if ignored is None or tracked is None:
        if _in_git_repo(project):
            return []
        lines = set(_gitignore_lines(project))
        return [p for p in paths if _ignore_line_forms(p) & lines]
    tracked_files = [t for t in tracked.split("\0") if t]
    return [p for p in ignored.split("\0") if p and not any(t.startswith(f"{p}/") for t in tracked_files)]


def _glob_match(pattern: str, name: str) -> bool:
    """Shell-style match with * and ? only; the site analyzer uses the same rule."""
    regex = re.escape(pattern).replace(r"\*", ".*").replace(r"\?", ".")
    return re.fullmatch(regex, name) is not None


def _tracked_globs(project: Path) -> list[str]:
    """_GENERATED_GLOBS that match at least one file git tracks."""
    out = _git(project, "ls-files", "-z", "--", *_GENERATED_GLOBS) or ""
    names = [path.rsplit("/", 1)[-1] for path in out.split("\0") if path]
    return [glob for glob in _GENERATED_GLOBS if any(_glob_match(glob, n) for n in names)]


def _detected_read_deny(project: Path) -> list[str]:
    """Read deny rules that fit this project: .env, the gated generated paths, root lock files."""
    folders = _ignored_untracked(project, _find_generated_dirs(project))
    names = sorted({p.rsplit("/", 1)[-1] for p in folders}, key=_GENERATED_DIRS.index)
    locks = [lock for lock in LOCKFILE_NAMES if (project / lock).is_file()]
    return [
        *_ENV_DENY,
        *(f"Read({name}/**)" for name in names),
        *(f"Read({glob})" for glob in _tracked_globs(project)),
        *(f"Read(./{lock})" for lock in locks),
    ]


def _rule_segments(rule: str) -> list[str]:
    """Path segments of a Read(...) rule, without the ./, / and ** parts."""
    inner = rule[rule.find("(") + 1 : rule.rfind(")")]
    return [seg for seg in inner.split("/") if seg not in ("", ".", "**")]


def _deny_covered(candidate: str, rules: list[str]) -> bool:
    """A suggested rule is already there when an existing rule names or globs its first segment.

    Lock files use the scoring rule (_lock_covered). Mirrored by denyCovered in
    site/src/utils/repoAnalyzer.ts.
    """
    key = _rule_segments(candidate)[0]
    if key in LOCKFILE_NAMES:
        return _lock_covered(key, rules)
    return any(_glob_match(seg, key) for rule in rules for seg in _rule_segments(rule))


def _file_read_detail(count: int, locks: list[str], uncovered: list[str]) -> str:
    if count == 0:
        return "no Read deny rules in permissions.deny"
    if not locks:
        lock_note = "no lock files at root"
    elif uncovered:
        lock_note = "lock files not covered: " + ", ".join(uncovered)
    else:
        lock_note = "lock files covered"
    return f"{count} Read deny rule(s); {lock_note}"


def score_file_read_exclusions(project: Path) -> CategoryResult:
    """Read(...) rules in permissions.deny, plus lock-file coverage."""
    cat = CategoryResult(
        name="File-read exclusions",
        score=0,
        max_score=15,
        detail="",
        findings=[],
        fixes=[],
    )
    settings, _ = _load_settings(project)
    rules = _read_deny_rules(settings)
    count = len(rules)
    locks = [lock for lock in LOCKFILE_NAMES if (project / lock).is_file()]
    uncovered = [lock for lock in locks if not _lock_covered(lock, rules)]
    detected = _detected_read_deny(project)

    score = next((pts for minimum, pts in _READ_RULE_TIERS if count >= minimum), 0)
    if count >= 1 and not uncovered:
        score += 2
    cat.score = min(score, cat.max_score)
    cat.detail = _file_read_detail(count, locks, uncovered)

    if (project / IGNORE_FILE).is_file():
        cat.findings.append(IGNORE_FILE_FINDING)
        cat.fixes.append(
            f"Merge its patterns into permissions.deny in {DOT_CLAUDE}/{SETTINGS_JSON}, "
            f"then delete {IGNORE_FILE}:"
            + _deny_block(_ignore_file_as_read_rules(project))
        )
    elif count == 0:
        cat.fixes.append(
            "Keep Claude's file tools out of dependency, build and generated paths with "
            f"Read deny rules in {DOT_CLAUDE}/{SETTINGS_JSON}. No published measurement "
            "exists for what they save; the effect depends on how often Claude would "
            f"otherwise open those files. {_DENY_NOTES} Detected for this project:"
            + _deny_block(detected)
        )

    # Lock files are part of the detected list, so an uncovered one prints once, here.
    missing = [rule for rule in detected if not _deny_covered(rule, rules)] if count >= 1 else []
    if missing:
        cat.fixes.append(
            "Add these Read deny rules detected for this project (a folder is listed only when git "
            "ignores it and it holds no tracked file, since a Read deny also blocks Edit and Write):"
            + FIX_INDENT
            + FIX_INDENT.join(f'"{rule}"' for rule in missing)
        )

    return cat


_MODEL_KEYS: tuple[str, ...] = ("model", "defaultModel", "preferredModel")

# This sub-score used to award 5 of this category's 15 points for any of
# budgetCap / costLimit / maxCost / maxMonthlyCost / maxCostPerSession / budget.
# All six were checked against https://www.schemastore.org/claude-code-settings.json
# on 2026-09-06: none of them appears among the schema's 142 top-level
# properties. Claude Code has no monthly spend cap setting at all, so a third of
# the category was going to keys the product silently ignores, and the fix text
# told users to add one.
#
# The points now go to settings Claude Code really reads that bound spend. Each
# entry is value-aware on purpose: the key being present is not enough, because
# "fastMode": true doubles the bill and a high "effortLevel" raises it.
# "alwaysThinkingEnabled": false is not counted: it has no effect on Opus 5.5,
# Sonnet 5.5, Haiku 5.5 or the Fable models, which always think
# (code.claude.com/docs/en/settings-reference, read 2026-11-01).
#
# Since 2026-11-03 three more count, each only at a value that bounds spend
# (settings, env-vars and model-config references, read 2026-11-03): an
# auto-compact window under the 1,000,000 default (top-level autoCompactWindow,
# a modelSettings entry, or CLAUDE_CODE_AUTO_COMPACT_WINDOW in env), an env
# MAX_MCP_OUTPUT_TOKENS under its 25,000 default, and CLAUDE_CODE_SUBAGENT_MODEL
# on haiku or sonnet only with CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1 (alone it is a
# default that a subagent's own model field or a model Claude passes overrides),
# and only when it differs from the main model's family. bashOutputMaxChars is not
# counted: the settings reference documents it as a way to raise the Bash limit.
# These rules are mirrored in tools/badge-generator/generate.py,
# tools/actions/claude-cost-audit/audit.py and site/src/utils/repoAnalyzer.ts.
_WINDOW_RANGE = (100_000, 1_000_000)
_MCP_OUTPUT_DEFAULT = 25_000
_TOKEN_COUNT = re.compile(r"\s*([0-9]+)\s*([kKmM]?)\s*")
_TOKEN_SCALE = {"": 1, "k": 1_000, "m": 1_000_000}
# On these providers the `haiku` alias is Haiku 4.5, not Haiku 5.5
# (code.claude.com/docs/en/model-config, read 2026-11-03).
_PROVIDER_FLAGS: tuple[str, ...] = (
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_FOUNDRY",
    "CLAUDE_CODE_USE_ANTHROPIC_AWS",
    "CLAUDE_CODE_USE_MANTLE",
)
_MODEL_FAMILIES: tuple[str, ...] = ("haiku", "sonnet", "opus", "fable", "mythos")


def _env_block(data: dict[str, Any]) -> dict[str, Any]:
    env = data.get("env")
    return env if isinstance(env, dict) else {}


def _model_settings(data: dict[str, Any]) -> dict[str, Any]:
    per_model = data.get("modelSettings")
    return per_model if isinstance(per_model, dict) else {}


def _setting_tokens(value: Any) -> int | None:
    """A token count from a settings key, which takes a JSON number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return int(value)


def _env_tokens(value: Any, suffixes: bool = True) -> int | None:
    """A token count from an env value: 200000 or "200000", plus "200k" or "1M" when `suffixes`."""
    if not isinstance(value, str):
        return _setting_tokens(value)
    match = _TOKEN_COUNT.fullmatch(value)
    if match is None or (match[2] and not suffixes):
        return None
    return int(match[1]) * _TOKEN_SCALE[match[2].lower()]


def _model_family(model: Any) -> str | None:
    text = model.lower() if isinstance(model, str) else ""
    return next((family for family in _MODEL_FAMILIES if family in text), None)


def _window_signals(data: dict[str, Any]) -> list[str]:
    """Auto-compact windows below the 1M default: top-level, per model, or the env variable."""
    low, high = _WINDOW_RANGE
    found = [("autoCompactWindow", _setting_tokens(data.get("autoCompactWindow")))]
    found += [
        (f"{model} autoCompactWindow", _setting_tokens(conf.get("autoCompactWindow")))
        for model, conf in _model_settings(data).items()
        if isinstance(conf, dict)
    ]
    env_window = _env_tokens(_env_block(data).get("CLAUDE_CODE_AUTO_COMPACT_WINDOW"))
    found.append(("CLAUDE_CODE_AUTO_COMPACT_WINDOW", env_window))
    return [f"{name}={value}" for name, value in found if value is not None and low <= value < high]


def _env_cost_signals(data: dict[str, Any]) -> list[str]:
    """env settings that bound spend: a lower MCP output cap, a forced cheaper subagent model."""
    env = _env_block(data)
    signals: list[str] = []
    mcp_cap = _env_tokens(env.get("MAX_MCP_OUTPUT_TOKENS"), suffixes=False)
    if mcp_cap is not None and 0 < mcp_cap < _MCP_OUTPUT_DEFAULT:
        signals.append(f"MAX_MCP_OUTPUT_TOKENS={mcp_cap}")
    sub = env.get("CLAUDE_CODE_SUBAGENT_MODEL")
    forced = str(env.get("CLAUDE_CODE_SUBAGENT_MODEL_FORCE", "")).strip() == "1"
    family = _model_family(sub)
    if forced and family in ("haiku", "sonnet") and family != _model_family(data.get("model")):
        signals.append(f"CLAUDE_CODE_SUBAGENT_MODEL={sub} (forced)")
    return signals


def _cost_control_signals(data: dict[str, Any]) -> list[str]:
    """Real settings whose configured value reduces or bounds spend."""
    signals: list[str] = []

    # Reasoning tokens bill at the output rate. Claude Code's default effort is
    # "medium" on Opus 5.5, Sonnet 5.5 and Haiku 5.5 and "high" on most other
    # models, so pinning low or medium is the largest lever after model choice.
    effort = data.get("effortLevel")
    if isinstance(effort, str) and effort.strip().lower() in ("low", "medium"):
        signals.append(f'effortLevel="{effort}"')

    # A cap holds on every provider; "max" sets no cap.
    cap = data.get("maxEffortLevel")
    if isinstance(cap, str) and cap.strip().lower() in ("low", "medium", "high", "xhigh"):
        signals.append(f'maxEffortLevel="{cap}"')

    # Fast Mode is a flat 2x on input and output. Declining it explicitly, or
    # making it a per-session opt-in, is a real saving.
    if data.get("fastMode") is False:
        signals.append("fastMode=false")
    if data.get("fastModePerSessionOptIn") is True:
        signals.append("fastModePerSessionOptIn=true")

    # The closest real analogue of a spend cap: an enforced allowlist can keep
    # Opus- and Fable-tier models out of a project entirely.
    models = data.get("availableModels")
    if (
        data.get("enforceAvailableModels") is True
        and isinstance(models, list)
        and models
    ):
        signals.append(f"enforceAvailableModels over {len(models)} model(s)")

    # Bounds context growth, which is what actually drives per-turn input cost.
    if data.get("autoCompactEnabled") is True:
        signals.append("autoCompactEnabled=true")

    signals.extend(_window_signals(data))
    signals.extend(_env_cost_signals(data))
    return signals


def _flag_on(value: Any) -> bool:
    return str(value).strip().lower() not in ("", "0", "false", "none")


def _on_haiku_5_5(data: dict[str, Any]) -> bool:
    """The pinned model is Haiku 5.5: its full id, or the `haiku` alias with no provider flag set."""
    model = data.get("model")
    name = model.strip().lower() if isinstance(model, str) else ""
    env = _env_block(data)
    on_provider = any(_flag_on(env.get(flag, "")) for flag in _PROVIDER_FLAGS)
    return "haiku-5-5" in name or (name == "haiku" and not on_provider)


def _haiku_window_set(data: dict[str, Any]) -> bool:
    """A window under 1M applies to Haiku 5.5: the env variable, its own entry, or the top-level key."""
    per_model = {m: c for m, c in _model_settings(data).items() if "haiku" in m.lower()}
    view = {"autoCompactWindow": data.get("autoCompactWindow"), "env": _env_block(data), "modelSettings": per_model}
    return bool(_window_signals(view))


def _add_settings_findings(cat: CategoryResult, data: dict[str, Any]) -> None:
    """A dead env key and the Haiku 5.5 price line; neither changes the score."""
    if "CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION" in _env_block(data):
        cat.findings.append(
            "env CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION does nothing: it was removed in v2.1.224 and is "
            "now a no-op (code.claude.com/docs/en/env-vars, read 2026-11-03). "
            "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS limits how many subagents run at once."
        )
    if _on_haiku_5_5(data) and not _haiku_window_set(data):
        base = MODELS["haiku-5-5"]
        tier = base["long_prompt"]
        cat.findings.append(
            "model is Haiku 5.5 with no auto-compact window. It auto-compacts at about 967K tokens by "
            "default (code.claude.com/docs/en/model-config, read 2026-11-03), but a request whose prompt "
            f"is over {tier['threshold']:,} tokens pays ${tier['input']:.2f}/${tier['output']:.2f} per 1M "
            f"on the whole request instead of ${base['input']:.2f}/${base['output']:.2f}, "
            f"{tier['input'] / base['input']:.0f}x."
        )
        cat.fixes.append(
            'Compact Haiku 5.5 sessions sooner: run /autocompact 100k in one, or add "modelSettings": '
            '{"claude-haiku-5-5": {"autoCompactWindow": 100000}}. The docs do not say how far below a '
            "100K window compaction starts, so this does not keep every request under the price line."
        )


def _settings_category_label() -> str:
    return f"{DOT_CLAUDE}/{SETTINGS_JSON}"


def _load_settings(project: Path) -> tuple[dict[str, Any] | None, Path | None]:
    """Find the first readable settings.json variant under .claude/."""
    for filename in (SETTINGS_JSON, SETTINGS_LOCAL_JSON):
        relative = Path(DOT_CLAUDE) / filename
        data = _read_json(project, relative)
        if data is not None:
            return data, project / relative
    return None, None


def _settings_features(
    data: dict[str, Any],
) -> tuple[bool, list[str], bool, str | None]:
    """Return (has_model, cost_control_signals, has_perms, model_id)."""
    model_id = next((data.get(k) for k in _MODEL_KEYS if data.get(k)), None)
    has_model = bool(model_id)
    cost_signals = _cost_control_signals(data)
    perms = data.get("permissions") or {}
    has_perms = (
        bool(perms.get("allow") or perms.get("deny"))
        if isinstance(perms, dict)
        else False
    )
    return (
        has_model,
        cost_signals,
        has_perms,
        model_id if isinstance(model_id, str) else None,
    )


def score_settings(project: Path) -> CategoryResult:
    """`.claude/settings.json` model pin + real cost controls + permissions."""
    cat = CategoryResult(
        name=_settings_category_label(),
        score=0,
        max_score=15,
        detail="",
        findings=[],
        fixes=[],
    )
    data, found_path = _load_settings(project)

    if data is None:
        cat.detail = f"no {SETTINGS_JSON}"
        cat.findings.append(
            f"No {DOT_CLAUDE}/{SETTINGS_JSON}. Default model and permissions are not project-pinned."
        )
        cat.fixes.append(
            f"Create {DOT_CLAUDE}/{SETTINGS_JSON} with at minimum:\n"
            '    {"model": "claude-sonnet-5-5", "permissions": {"allow": [], "deny": []}}\n'
            "    Reach for claude-opus-5-5 only on complex agentic work -- its adaptive "
            "thinking is always on (it cannot be disabled) and reasoning tokens bill as "
            "output at $20/1M, so effort is the only lever; it defaults to medium."
        )
        return cat

    has_model, cost_signals, has_perms, model_id = _settings_features(data)
    _add_settings_findings(cat, data)
    score = 0
    parts: list[str] = []

    if has_model:
        score += 6
        parts.append(f"model={model_id}")
    else:
        cat.fixes.append(
            f'Set "model" in {SETTINGS_JSON} to pin a default (e.g. "claude-sonnet-5-5"). '
            "Prevents accidental Opus usage on simple tasks -- and on Opus 5.5 that matters "
            "more, since adaptive thinking is always on and every reasoning token "
            "bills at the $20/1M output rate."
        )

    if cost_signals:
        score += 5
        parts.append("cost controls: " + ", ".join(cost_signals))
    else:
        cat.fixes.append(
            "No cost controls in settings.json. Claude Code has no monthly spend "
            "cap setting -- keys like maxMonthlyCost or budgetCap are not in the "
            "settings schema and are silently ignored, so adding one buys nothing. "
            "Use settings it actually reads:\n"
            '    "effortLevel": "medium"          reasoning tokens bill as output\n'
            '    "maxEffortLevel": "high"         caps effort on every provider\n'
            '    "fastMode": false                declines the flat 2x Fast Mode '
            "multiplier\n"
            '    "fastModePerSessionOptIn": true  a saved /fast no longer carries over\n'
            '    "autoCompactEnabled": true       bounds the context growth that '
            "drives input cost\n"
            '    "autoCompactWindow": 200000      compacts sooner than the ~967K default '
            "on 1M-context models\n"
            '    "enforceAvailableModels": true with "availableModels": '
            '["claude-sonnet-5-5"]  keeps Opus- and Fable-tier models out entirely\n'
            '    "env": {"MAX_MCP_OUTPUT_TOKENS": "10000"}  caps each MCP tool result '
            "(default 25,000 tokens)\n"
            '    "env": {"CLAUDE_CODE_SUBAGENT_MODEL": "haiku", '
            '"CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "1"}  runs every subagent on one model\n'
            "    For an actual spend ceiling you need a PreToolUse hook, not a "
            "setting -- see hooks/budget-tracker.sh in this repo."
        )

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
    (3, 13, "{n} MCP server(s) -- light overhead"),
    (5, 10, "{n} MCP servers -- moderate overhead"),
    (8, 6, "{n} MCP servers -- heavy overhead"),
    (12, 3, "{n} MCP servers -- very heavy overhead"),
)


def _count_mcp_servers(project: Path) -> tuple[dict[str, int], dict[str, Any] | None]:
    """Return ({source_label: count}, settings_dict_or_None)."""
    counts: dict[str, int] = {}

    mcp_data = _read_json(project, MCP_JSON)
    if mcp_data is not None and isinstance(mcp_data.get("mcpServers"), dict):
        counts[MCP_JSON] = len(mcp_data["mcpServers"])

    settings = _read_json(project, Path(DOT_CLAUDE) / SETTINGS_JSON)
    if settings is not None:
        servers = settings.get("mcpServers", {})
        if isinstance(servers, dict) and servers:
            counts[f"{DOT_CLAUDE}/{SETTINGS_JSON}"] = len(servers)

    return counts, settings


def score_mcp_servers(project: Path) -> CategoryResult:
    """Count MCP servers across .mcp.json + settings.json."""
    cat = CategoryResult(
        name="MCP servers", score=0, max_score=15, detail="", findings=[], fixes=[]
    )
    counts, settings = _count_mcp_servers(project)
    total = sum(counts.values())

    if total == 0:
        cat.score = 15
        cat.detail = "no MCP servers configured (lowest overhead)"
        return cat

    cat.score, cat.detail = 0, f"{total} MCP servers -- excessive overhead"
    for max_count, score_value, template in _MCP_TIERS:
        if total <= max_count:
            cat.score = score_value
            cat.detail = template.format(n=total)
            break

    if total > 5:
        cat.findings.append(
            f"{total} MCP servers configured (across {', '.join(counts.keys())}). "
            "With tool search on (the default), each adds its tool names and server "
            "instructions to context; full tool schemas load up front only when tool "
            "search is off (ENABLE_TOOL_SEARCH=false, CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1, "
            "a HIPAA configuration, or a provider or gateway that rejects it)."
        )
        cat.fixes.append(
            "Review which MCP servers you actually use every session. Disable unused "
            f"ones with /mcp or in {MCP_JSON}, and move personal ones to local scope "
            "(claude mcp add --scope local, stored in ~/.claude.json) so they load only "
            "for you. "
            "Prefer CLI tools (gh, aws, gcloud, sentry-cli) where they exist -- they add "
            "no per-tool listing."
        )

    if total > 0 and MCP_JSON not in counts and "mcpServers" in (settings or {}):
        cat.fixes.append(
            f"MCP servers are in {DOT_CLAUDE}/{SETTINGS_JSON} -- prefer the dedicated "
            f"{MCP_JSON} file (cleaner separation, easier to share/exclude)."
        )

    return cat


# The hooks block the no-hooks fix suggests: the shape of hooks/settings-example.json.
_HOOK_EXAMPLE: dict[str, Any] = {
    "hooks": {
        "PreToolUse": [
            {
                "matcher": ".*",
                "hooks": [{"type": "command", "command": 'bash "$CLAUDE_PROJECT_DIR"/hooks/budget-tracker.sh'}],
            }
        ],
        "SessionEnd": [
            {
                "matcher": "",
                "hooks": [{"type": "command", "command": 'bash "$CLAUDE_PROJECT_DIR"/hooks/session-summary.sh'}],
            }
        ],
    }
}


def score_hooks(project: Path) -> CategoryResult:
    """Hooks for budget tracking, cost logging, or permission policy."""
    cat = CategoryResult(
        name="Hooks", score=0, max_score=10, detail="", findings=[], fixes=[]
    )

    settings = _read_json(project, Path(DOT_CLAUDE) / SETTINGS_JSON)
    hooks = settings.get("hooks") if settings else None
    hook_count = _count_hook_entries(hooks)

    if hook_count >= 3:
        cat.score = 10
        cat.detail = f"{hook_count} hook(s) configured"
    elif hook_count >= 1:
        cat.score = 6
        cat.detail = f"{hook_count} hook(s) configured"
        cat.fixes.append(
            "Consider adding cost-tracking hooks (PreToolUse for budget gates, SessionEnd for a "
            "session-cost summary; Stop fires after every turn)."
        )
    else:
        cat.detail = "no hooks configured"
        cat.fixes.append(
            "Add cost-tracking hooks. Copy budget-tracker.sh and session-summary.sh from the hooks/ "
            "folder of github.com/Sagargupta16/claude-cost-optimizer into your project's hooks/ folder "
            f"first, then add this to {DOT_CLAUDE}/{SETTINGS_JSON}:" + _json_block(_HOOK_EXAMPLE)
        )

    _add_hook_hygiene(cat, project)
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


# -- Hook hygiene: findings only, the Hooks score still counts entries --
#
# From code.claude.com/docs/en/hooks, read 2026-11-03: each handler is an object
# with a "type" inside a matcher group's "hooks" array; the same handler in more
# than one settings file runs once; matching hooks run in parallel; a command
# hook without `args` is shell form, which runs in PowerShell on Windows when Git
# Bash is not installed, and there a failing PreToolUse or PermissionRequest hook
# with onFailure unset blocks the tool call. Findings name the settings file,
# event, index and script path, never the command text, which can carry a token.
# Project settings only: ~/.claude/settings.json hooks belong to --user.

_HOOK_SCRIPT = re.compile(r"[^\s]+\.(?:sh|bash|py|js|mjs|cjs|ts|ps1|rb|pl)", re.IGNORECASE)
_PROJECT_DIR_VAR = re.compile(r"(?:\$\{CLAUDE_PROJECT_DIR\}|\$CLAUDE_PROJECT_DIR|\$env:CLAUDE_PROJECT_DIR)(?=/|$)")
_HOME_VAR = re.compile(r"(?:\$\{HOME\}|\$HOME|\$env:USERPROFILE|~)(?=/|$)")
_HEADLESS_RUN = re.compile(r"(?<![\w-])claude(?:\.exe)?(?![\w-])[^\n|;&]*?\s(?:-p|--print)\b")
_BLOCKING_HOOK_EVENTS = ("PreToolUse", "PermissionRequest")
_ALL_SOURCES = (None, "", "*", ".*")
_HOOK_INTERPRETERS = ("bash", "python3", "jq", "node")
_SCRIPT_READ_LIMIT = 256_000
_HookHandler = tuple[str, str, Any, dict[str, Any]]


def _hook_groups(project: Path) -> list[tuple[str, str, int, Any]]:
    """(settings file, event, group index, matcher group) across the project settings files."""
    groups: list[tuple[str, str, int, Any]] = []
    for filename in (SETTINGS_JSON, SETTINGS_LOCAL_JSON):
        data = _read_json(project, Path(DOT_CLAUDE) / filename)
        hooks = data.get("hooks") if data else None
        for event, entries in hooks.items() if isinstance(hooks, dict) else []:
            listed = entries if isinstance(entries, list) else [entries]
            groups.extend((filename, event, i, group) for i, group in enumerate(listed))
    return groups


def _hook_handlers(project: Path) -> tuple[list[_HookHandler], list[str]]:
    """(where, event, matcher, handler) for each distinct handler, and where malformed ones sit."""
    handlers: list[_HookHandler] = []
    malformed: list[str] = []
    seen: set[str] = set()
    for filename, event, index, group in _hook_groups(project):
        where = f"{filename} {event}[{index}]"
        inner = group.get("hooks") if isinstance(group, dict) else None
        if not isinstance(inner, list):
            malformed.append(where)
            continue
        for h, handler in enumerate(inner):
            if not isinstance(handler, dict) or not handler.get("type"):
                malformed.append(f"{where}.hooks[{h}]")
                continue
            key = json.dumps([event, group.get("matcher"), handler], sort_keys=True)
            if key not in seen:
                seen.add(key)
                handlers.append((f"{where}.hooks[{h}]", event, group.get("matcher"), handler))
    return handlers, malformed


def _shell_words(command: str) -> list[str]:
    """Split a shell command into words: quotes group and are dropped; | ; & < > ( ) separate.

    Mirrored by shellWords in site/src/utils/repoAnalyzer.ts.
    """
    words: list[str] = []
    word, quote = "", ""
    for ch in command.replace("\\", "/"):
        if quote and ch == quote:
            quote = ""
        elif quote or (ch not in "\"'" and not ch.isspace() and ch not in "|;&<>()"):
            word += ch
        elif ch in "\"'":
            quote = ch
        elif word:
            words.append(word)
            word = ""
    return [*words, word] if word else words


def _hook_words(handler: dict[str, Any]) -> list[str]:
    """The command's words: exec form is command plus args, shell form is split like a shell."""
    command = handler.get("command")
    if not isinstance(command, str):
        return []
    args = handler.get("args")
    if isinstance(args, list):
        return [part.replace("\\", "/") for part in (command, *map(str, args))]
    return _shell_words(command)


def _hook_script(words: list[str]) -> str | None:
    return next((w for w in words if _HOOK_SCRIPT.fullmatch(w) and not w.startswith("-") and "://" not in w), None)


def _script_location(project: Path, word: str) -> tuple[Path | None, bool]:
    """(path, is_relative) for a hook script word; path is None when a variable or shell path hides it."""
    for pattern, base in ((_PROJECT_DIR_VAR, project), (_HOME_VAR, Path.home())):
        if pattern.match(word):
            return base / pattern.sub("", word, count=1).lstrip("/"), False
    if "$" in word or "%" in word:
        return None, False
    drive = re.match(r"/([A-Za-z])/", word)
    if sys.platform == "win32" and word.startswith("/"):
        # Git Bash spells C:\x as /c/x; other absolute shell paths cannot be checked here.
        return (Path(f"{drive[1]}:/{word[3:]}"), False) if drive else (None, False)
    if word.startswith("/") or re.match(r"[A-Za-z]:/", word):
        return Path(word), False
    return project / word, True


def _hook_text(handler: dict[str, Any], script: Path | None) -> str:
    """The command plus args, and the named script's non-comment lines when it is small enough to read."""
    args = handler.get("args")
    text = " ".join([str(handler.get("command", "")), *(map(str, args) if isinstance(args, list) else [])])
    try:
        if script is not None and script.is_file() and script.stat().st_size <= _SCRIPT_READ_LIMIT:
            lines = script.read_text(encoding="utf-8", errors="replace").splitlines()
            text += "\n" + "\n".join(line for line in lines if not line.lstrip().startswith(("#", "//")))
    except OSError:
        pass
    return text


def _git_bash_found() -> bool:
    """Whether Git for Windows' bash.exe sits where it installs it, or next to git on PATH."""
    import shutil

    git = shutil.which("git")
    roots = [Path(git).resolve().parent.parent] if git else []
    roots += [Path(os.environ[v]) / "Git" for v in ("ProgramFiles", "ProgramW6432") if os.environ.get(v)]
    if os.environ.get("LOCALAPPDATA"):
        roots.append(Path(os.environ["LOCALAPPDATA"]) / "Programs" / "Git")
    return any((root / "bin" / "bash.exe").is_file() for root in roots)


def _powershell_hooks_here(project: Path) -> bool:
    """Windows with no Git Bash found and no CLAUDE_CODE_GIT_BASH_PATH: shell-form hooks run in PowerShell."""
    if sys.platform != "win32":
        return False
    settings, _ = _load_settings(project)
    configured = os.environ.get("CLAUDE_CODE_GIT_BASH_PATH") or _env_block(settings or {}).get("CLAUDE_CODE_GIT_BASH_PATH")
    return not configured and not _git_bash_found()


def _matches_bash(matcher: Any) -> bool:
    return matcher in _ALL_SOURCES or (isinstance(matcher, str) and re.search(r"\bBash\b", matcher) is not None)


def _handler_kinds(project: Path, event: str, handler: dict[str, Any], powershell: bool) -> tuple[Path | None, list[str]]:
    """(script path, problem kinds) for one command handler."""
    import shutil

    words = _hook_words(handler)
    script = _hook_script(words)
    path, relative = _script_location(project, script) if script else (None, False)
    text = _hook_text(handler, path)
    names = {w.rsplit("/", 1)[-1].removesuffix(".exe") for w in words}
    kinds = [
        kind
        for kind, hit in (
            ("missing", path is not None and not path.is_file()),
            ("relative", relative),
            ("headless", _HEADLESS_RUN.search(text) is not None),
            ("updated_input", event == "PreToolUse" and "updatedInput" in text),
            (
                "powershell",
                powershell and event in _BLOCKING_HOOK_EVENTS and "args" not in handler
                and "onFailure" not in handler and handler.get("shell") != "powershell",
            ),
        )
        if hit
    ]
    kinds += [f"interpreter:{n}" for n in _HOOK_INTERPRETERS if n in names and shutil.which(n) is None]
    return path, kinds


def _display_path(project: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _hook_problems(project: Path) -> dict[str, list[str]]:
    """Locations per problem kind across the project's hook handlers."""
    handlers, malformed = _hook_handlers(project)
    problems: dict[str, list[str]] = {"malformed": malformed} if malformed else {}
    powershell = _powershell_hooks_here(project)
    for where, event, matcher, handler in handlers:
        if event == "SessionStart" and matcher in _ALL_SOURCES:
            problems.setdefault("session_start", []).append(where)
        if handler.get("type") != "command":
            continue
        path, kinds = _handler_kinds(project, event, handler, powershell)
        label = f"{where} ({_display_path(project, path)})" if path else where
        for kind in kinds:
            if kind != "updated_input" or _matches_bash(matcher):
                problems.setdefault(kind, []).append(label)
    return problems


# (finding, fix or None for an info note) per problem kind; {n} is the count, {where} the list.
_HOOK_MESSAGES: dict[str, tuple[str, str | None]] = {
    "malformed": (
        '{n} hook handler(s) never run: {where}. Each handler must be an object with a "type" (such as '
        '"command") inside a matcher group\'s "hooks" array; a bare command string or a handler without '
        "a type does not run (hooks reference, read 2026-11-03).",
        'Rewrite each as {{"matcher": "...", "hooks": [{{"type": "command", "command": "..."}}]}}.',
    ),
    "missing": (
        "{n} hook handler(s) point at a script that does not exist: {where}. A mistyped path means the "
        "hook never runs (hooks reference, read 2026-11-03).",
        "Fix each script path, or remove the hook.",
    ),
    "relative": (
        "{n} hook handler(s) use a relative script path: {where}. A hook runs in the session's current "
        "directory, so it fails once Claude cds into a subfolder.",
        'Start the path with "$CLAUDE_PROJECT_DIR"/ in a shell-form command, or ${{CLAUDE_PROJECT_DIR}}/ '
        "in args.",
    ),
    "headless": (
        "{n} hook handler(s) run claude -p (or --print): {where}. Each run is its own Claude Code session "
        "on your plan limits or API credits, started every time the hook fires.",
        "Keep claude -p in hooks on events that fire rarely, such as SessionEnd; Stop fires after every "
        "turn and PostToolUse after every tool call.",
    ),
    "powershell": (
        "{n} PreToolUse or PermissionRequest hook handler(s) would run in PowerShell here, because Git Bash "
        "was not found: {where}. On Windows without Git Bash a shell-form hook of these events that fails "
        "with onFailure unset blocks the tool call (hooks reference, read 2026-11-03).",
        "Install Git for Windows, or set CLAUDE_CODE_GIT_BASH_PATH to its bash.exe. For a hook that "
        'should never gate the call, add "onFailure": "continue" (Claude Code v2.1.295 or later).',
    ),
    "session_start": (
        "Note: SessionStart hook {where} has no matcher, so it also runs on resume, clear, compact and "
        "fork. That is intended if it re-injects context after compacting; Claude's first response "
        "waits for SessionStart hooks to finish (hooks reference, read 2026-11-03).",
        None,
    ),
    "updated_input": (
        "Note: {n} PreToolUse hook handlers that match Bash return updatedInput: {where}. Matching hooks "
        "run in parallel, and the hooks reference (read 2026-11-03) does not say which updatedInput wins.",
        None,
    ),
}


def _add_hook_hygiene(cat: CategoryResult, project: Path) -> None:
    """Hook handlers that never run, break after a cd, start paid sessions, or can block on Windows."""
    for kind, where in _hook_problems(project).items():
        if kind == "updated_input" and len(where) < 2:
            continue
        if kind.startswith("interpreter:"):
            name = kind.split(":", 1)[1]
            cat.findings.append(f"Note: hook handler(s) {_listed(where)} run {name}, which is not on PATH here.")
            continue
        finding, fix = _HOOK_MESSAGES[kind]
        cat.findings.append(finding.format(n=len(where), where=_listed(where)))
        if fix is not None:
            cat.fixes.append(fix.format())


_DANGER_FILES: tuple[str, ...] = (
    ".env",
    ".env.local",
    ".env.production",
    "credentials.json",
    ".mcp.local.json",
)
_API_KEY_PATTERN = re.compile(
    r"(sk-[a-zA-Z0-9]{20,}|AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36})"
)


def _gitignore_lines(project: Path) -> list[str]:
    """Return non-empty .gitignore lines, or an empty list if missing."""
    path = project / GITIGNORE
    if not path.is_file():
        return []
    text = _read_text(project, GITIGNORE) or ""
    return [line.strip() for line in text.splitlines() if line.strip()]


def _is_gitignored(filename: str, gitignore_lines: list[str]) -> bool:
    """True if the gitignore lines plausibly cover `filename`."""
    target = filename.rstrip("/")
    return any(
        filename in line or line.rstrip("/") == target for line in gitignore_lines
    )


def _find_leaked_files(project: Path, gitignore_lines: list[str]) -> list[str]:
    """Sensitive files that exist on disk but aren't in .gitignore."""
    leaked: list[str] = []
    for filename in _DANGER_FILES:
        if (project / filename).is_file() and not _is_gitignored(
            filename, gitignore_lines
        ):
            leaked.append(filename)
    return leaked


def _find_api_key_leaks(project: Path) -> list[str]:
    """Files in the repo that contain an obvious API key pattern."""
    suspects: list[str] = []
    targets = (
        Path(CLAUDE_MD),
        Path(DOT_CLAUDE) / SETTINGS_JSON,
        Path(MCP_JSON),
    )
    for relative in targets:
        target = project / relative
        if not target.is_file():
            continue
        text = _read_text(project, relative) or ""
        if _API_KEY_PATTERN.search(text):
            suspects.append(str(target.relative_to(project)))
    return suspects


def score_security(project: Path) -> CategoryResult:
    """Quick check for accidentally-committed secrets and missing gitignore entries."""
    cat = CategoryResult(
        name="Security & hygiene",
        score=0,
        max_score=10,
        detail="",
        findings=[],
        fixes=[],
    )

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
            f"Add to {GITIGNORE} IMMEDIATELY:"
            + FIX_INDENT
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
        cat.findings.append(
            f"No {GITIGNORE} at all -- secrets and build artifacts will be tracked."
        )
        cat.fixes.append(
            f"Run `git init` properly or copy a starter {GITIGNORE} for your stack."
        )

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
    if _subagents(project / DOT_CLAUDE / "agents"):
        return 3, "custom subagent(s) defined"
    return 0, None


def _score_plugin_metadata(project: Path) -> tuple[int, str | None]:
    """3 points for a .claude-plugin/marketplace.json file."""
    if (project / ".claude-plugin" / "marketplace.json").is_file():
        return 3, "plugin marketplace metadata"
    return 0, None


def score_optimizer_tooling(project: Path) -> CategoryResult:
    """Bonus points for already-installed cost-optimization tooling."""
    cat = CategoryResult(
        name="Optimizer tooling",
        score=0,
        max_score=15,
        detail="",
        findings=[],
        fixes=[],
    )

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
        ", ".join(found)
        if found
        else "none of: cost-mode skill, custom commands, subagents, plugin metadata"
    )
    cat.findings.extend(_subagent_findings(project / DOT_CLAUDE / "agents", _project_env(project)))

    if not found:
        cat.fixes.append(
            "Install the cost-mode skill for shorter responses and model-routing hints:\n"
            "    /plugin marketplace add Sagargupta16/claude-cost-optimizer\n"
            "    /plugin install cost-mode@claude-cost-optimizer"
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


def _rates_for_prompt(model: dict[str, Any], prompt_tokens: float) -> dict[str, Any]:
    """The input, output and cache-read rates a request of `prompt_tokens` pays.

    Haiku 5.5 is priced by prompt length: a prompt over its threshold pays the
    long-prompt rates on the whole request. Every other model has one rate.
    """
    tier = model.get("long_prompt")
    if tier and prompt_tokens > tier["threshold"]:
        return tier
    return model


def estimate_costs(claude_md_chars: int, mcp_count: int) -> dict[str, dict[str, float]]:
    """Estimate per-session and per-month cost for each active model.

    Assumes 30 turns/session, 3 sessions/day, 22 working days/month -- the
    deployed analyzer's defaults -- and bills each turn the way Claude Code
    caches a conversation: the previous request is a cache read and only the
    new exchange is a 5-minute cache write (code.claude.com/docs/en/prompt-caching).
    """
    claude_md_tokens = claude_md_chars / 4  # ~4 chars per token
    mcp_tokens = mcp_count * TOKENS_PER_MCP_SERVER
    system_prompt_tokens = SYSTEM_PROMPT_TOKENS + claude_md_tokens + mcp_tokens

    turns = 30
    sessions_per_day = 3
    working_days = 22

    out: dict[str, dict[str, float]] = {}
    for mid, m in MODELS.items():
        overhead = m["tokenizer_overhead"]
        # Per turn, because a tiered model prices each request by its own prompt
        # length. The first turn writes the whole prompt to the cache.
        per_session = 0.0
        previous = 0.0
        for turn in range(turns):
            prompt = (
                system_prompt_tokens + turn * HISTORY_GROWTH_PER_TURN + TOKENS_PER_FILE_READ
            ) * overhead
            rates = _rates_for_prompt(m, prompt)
            per_session += (
                previous * rates["cache_hit"]
                + (prompt - previous) * rates["cache_5m_write"]
                + OUTPUT_TOKENS_PER_TURN * overhead * rates["output"]
            ) / 1_000_000
            previous = prompt
        out[mid] = {
            "name": m["name"],
            "per_session": round(per_session, 2),
            "per_month": round(per_session * sessions_per_day * working_days, 2),
        }
    return out


# -- Your whole setup (--user) and real usage (--usage) -----------------------
#
# Everything here reads local files only and sends nothing anywhere. From
# ~/.claude.json and settings it reads counts and setting names, never values
# (they can hold credentials); from transcripts it reads token counts, model
# names, timestamps, session ids and the record fields in _RECORD_META_KEYS, plus
# the text of Claude Code's own API error messages, and from each subagent's
# agent-<id>.meta.json only its agentType; never message content. --tools is the
# exception: it also reads tool names, inputs and result text, locally, and prints
# aggregates only.

# Skill listing: each skill's description plus when_to_use sits in context on
# every turn, capped at 1,536 characters (code.claude.com/docs/en/skills).
_SKILL_LISTING_CAP = 1_536
_USAGE_DAYS_DEFAULT = 30
# Same model prices under another snapshot name: these rows reuse that pricing.
_PRICE_ALIASES = {
    "mythos-5-2": "fable-5-2",
    "mythos-5-1": "fable-5-1",
    "mythos-5": "fable-5",
    "opus-4-5": "opus-4-6",
    "opus-4": "opus-4-1",
    "sonnet-4-5": "sonnet-4-6",
    "sonnet-4": "sonnet-4-6",
}


@dataclass
class ScopeResult:
    """A graded scope (your user-level setup, or your measured usage)."""

    name: str
    score: int
    max_score: int
    grade: str
    categories: list[CategoryResult]
    facts: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "score": self.score,
            "max_score": self.max_score,
            "grade": self.grade,
            "categories": [c.__dict__ for c in self.categories],
            "facts": self.facts,
        }


def _scope(name: str, categories: list[CategoryResult], facts: dict[str, Any]) -> ScopeResult:
    total = sum(c.score for c in categories)
    max_total = sum(c.max_score for c in categories)
    return ScopeResult(name, total, max_total, total_to_grade(total, max_total), categories, facts)


def _claude_dir() -> Path:
    """Claude Code's config directory: $CLAUDE_CONFIG_DIR, else ~/.claude."""
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(env).expanduser() if env else Path.home() / ".claude"


def _json_file(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    except OSError:
        return ""


_FRONTMATTER_KEY = re.compile(r"[A-Za-z_][\w-]*")


def _frontmatter(text: str) -> dict[str, str]:
    """Top-level keys of a leading YAML frontmatter block; block scalars are joined."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    out: dict[str, str] = {}
    key = None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        name, colon, rest = line.partition(":")
        if colon and _FRONTMATTER_KEY.fullmatch(name):
            key, value = name, rest.strip()
            out[key] = "" if value in (">", ">-", "|", "|-") else value.strip("'\"")
        elif key and line[:1] in (" ", "\t", "-"):
            out[key] = f"{out[key]} {line.strip()}".strip()
    return out


def _tier_points(value: float, tiers: tuple[tuple[float, int], ...], floor: int) -> int:
    """Points for the first (limit, points) tier that `value` is at or under."""
    return next((points for limit, points in tiers if value <= limit), floor)


# -- Subagent files (project, user and plugin agents directories) -------------
#
# From each agent file this reads frontmatter keys only: name, model, tools,
# disallowedTools and the length of description; never the body. For the provider
# check it reads whether the CLAUDE_CODE_USE_* flags are on and whether
# ANTHROPIC_DEFAULT_HAIKU_MODEL and CLAUDE_CODE_SUBAGENT_MODEL are set, no other
# env value.

# Providers on which the `haiku` alias is Haiku 4.5, not Haiku 5.5 (guides/07-mcp-agent-costs.md).
_HAIKU_ALIAS_PROVIDERS = {
    "CLAUDE_CODE_USE_BEDROCK": "Bedrock",
    "CLAUDE_CODE_USE_VERTEX": "Google Cloud",
    "CLAUDE_CODE_USE_FOUNDRY": "Foundry",
    "CLAUDE_CODE_USE_ANTHROPIC_AWS": "Claude Platform on AWS",
}
_TRUE_FLAGS = ("1", "true", "yes", "on")
_SUBAGENT_NAMES_SHOWN = 4
# Claude Code warns at startup once the descriptions of all non-built-in subagents
# together pass this many tokens (code.claude.com/docs/en/sub-agents, read 2026-11-03).
_SUBAGENT_DESCRIPTION_LIMIT = 15_000


def _subagents(agents_dir: Path) -> list[tuple[str, dict[str, str]]]:
    """(path under agents_dir, frontmatter) of each subagent file there.

    Claude Code scans the directory recursively and skips a file without a `name`.
    """
    files = sorted(agents_dir.rglob("*.md")) if agents_dir.is_dir() else []
    parsed = [(f.relative_to(agents_dir).as_posix(), _frontmatter(_text_file(f))) for f in files]
    return [(label, meta) for label, meta in parsed if meta.get("name")]


def _merged_env(*sources: dict[str, Any]) -> dict[str, str]:
    """The process environment with the `env` block of each settings dict laid over it."""
    env = dict(os.environ)
    for data in sources:
        block = data.get("env")
        if isinstance(block, dict):
            env.update({str(key): str(value) for key, value in block.items()})
    return env


def _project_env(project: Path) -> dict[str, str]:
    names = (SETTINGS_JSON, SETTINGS_LOCAL_JSON)
    return _merged_env(*[_read_json(project, Path(DOT_CLAUDE) / name) or {} for name in names])


def _haiku_alias_provider(env: dict[str, str]) -> str | None:
    """The provider on which `haiku` resolves to Haiku 4.5 and nothing pins it, else None."""
    if env.get("ANTHROPIC_DEFAULT_HAIKU_MODEL"):
        return None
    on = (name for flag, name in _HAIKU_ALIAS_PROVIDERS.items() if env.get(flag, "").strip().lower() in _TRUE_FLAGS)
    return next(on, None)


def _legacy_successor(model: str) -> str | None:
    """`<id> $in/$out -> <current> $in/$out` when `model` is a legacy full model id, else None."""
    key = _model_key(model)
    old = MODELS.get(key) if key else None
    new = MODELS.get(_SUCCESSORS.get(key.split("-")[0], "")) if key else None
    if not old or not new or old.get("lifecycle") != "legacy":
        return None
    return f"{model} ${old['input']:g}/${old['output']:g} -> {new['name']} ${new['input']:g}/${new['output']:g}"


def _group_subagents(agents_dir: Path) -> dict[str, list[str]]:
    """Subagent files under `agents_dir` grouped by the cost finding they earn."""
    groups: dict[str, list[str]] = {}
    for label, meta in _subagents(agents_dir):
        model = meta.get("model", "").split("#")[0].strip()
        if not model:
            groups.setdefault("no-model", []).append(label)
        elif model.lower() == "haiku":
            groups.setdefault("haiku", []).append(label)
        elif successor := _legacy_successor(model):
            groups.setdefault("legacy", []).append(f"{label} ({successor})")
        if "tools" not in meta and "disallowedTools" not in meta:
            groups.setdefault("open-tools", []).append(label)
    return groups


def _name_list(labels: list[str]) -> str:
    extra = len(labels) - _SUBAGENT_NAMES_SHOWN
    shown = ", ".join(labels[:_SUBAGENT_NAMES_SHOWN])
    return f"{shown}, +{extra} more" if extra > 0 else shown


def _subagent_findings(agents_dir: Path, env: dict[str, str]) -> list[str]:
    """Cost findings for the subagents under `agents_dir`, one line per kind of problem.

    A subagent with no `model` runs on CLAUDE_CODE_SUBAGENT_MODEL if that is set, else
    on the main conversation's model; `model: inherit` says the same on purpose, so it
    is not flagged (code.claude.com/docs/en/sub-agents, "Choose a model").
    """
    groups = _group_subagents(agents_dir)
    findings = []
    if "no-model" in groups and not env.get("CLAUDE_CODE_SUBAGENT_MODEL"):
        findings.append(
            f"{len(groups['no-model'])} subagent(s) name no `model` and run on the main conversation's model: "
            f"{_name_list(groups['no-model'])}. Add `model: haiku` to read-only search roles and a named model to the rest."
        )
    provider = _haiku_alias_provider(env)
    if "haiku" in groups and provider:
        old, new = MODELS["haiku-4-5"], MODELS["haiku-5-5"]
        findings.append(
            f"{len(groups['haiku'])} subagent(s) use `model: haiku`: {_name_list(groups['haiku'])}. On {provider} "
            f"that alias is Haiku 4.5 (${old['input']:g}/${old['output']:g} per 1M), not Haiku 5.5 "
            f"(${new['input']:g}/${new['output']:g} up to 100K prompt tokens); set ANTHROPIC_DEFAULT_HAIKU_MODEL to a Haiku 5.5 id."
        )
    if "legacy" in groups:
        findings.append(
            f"{len(groups['legacy'])} subagent(s) pin a legacy model: {_name_list(groups['legacy'])}. "
            "Unless an eval needs the old one, pin the current model of that family."
        )
    if "open-tools" in groups:
        findings.append(
            f"info: {len(groups['open-tools'])} subagent(s) set neither `tools` nor `disallowedTools`, so each inherits "
            f"every tool available to subagents: {_name_list(groups['open-tools'])}."
        )
    return findings


def _always_loaded_instructions(claude_dir: Path) -> list[tuple[str, int]]:
    """(name, chars) of user-scope files Claude Code loads at launch in every project.

    ~/.claude/CLAUDE.md, plus every ~/.claude/rules/ file without `paths`
    frontmatter (code.claude.com/docs/en/memory).
    """
    files = []
    claude_md = claude_dir / CLAUDE_MD
    if claude_md.is_file():
        files.append((CLAUDE_MD, len(_text_file(claude_md))))
    rules = claude_dir / "rules"
    for rule in sorted(rules.rglob("*.md")) if rules.is_dir() else []:
        text = _text_file(rule)
        if "paths" not in _frontmatter(text):
            files.append((f"rules/{rule.relative_to(rules).as_posix()}", len(text)))
    return files


_INSTRUCTION_TIERS = ((2_000, 25), (4_000, 20), (8_000, 14), (16_000, 8))


def score_user_instructions(claude_dir: Path) -> CategoryResult:
    files = _always_loaded_instructions(claude_dir)
    tokens = math.ceil(sum(chars for _, chars in files) / 4)
    cat = CategoryResult("Global instructions", 0, 25, "", [], [])
    cat.score = _tier_points(tokens, _INSTRUCTION_TIERS, 3)
    cat.detail = f"~{tokens:,} tokens in {len(files)} always-loaded file(s)"
    if tokens > _INSTRUCTION_TIERS[0][0]:
        biggest = sorted(files, key=lambda f: f[1], reverse=True)[:3]
        listed = ", ".join(f"{name} ~{math.ceil(chars / 4):,}" for name, chars in biggest)
        cat.findings.append(
            f"~{tokens:,} tokens load at the start of every session in every project. Largest: {listed}."
        )
        cat.fixes.append(
            "Move project- or task-specific rules into that project's CLAUDE.md, a skill, or a "
            "rules file with `paths:` frontmatter so it loads only for matching files."
        )
    return cat


def _skill_listing(skill_md: Path, overrides: dict[str, Any], max_desc: int) -> tuple[str, int, int]:
    """(name, listing characters, name characters) one skill adds to the listing.

    `overrides` is the merged skillOverrides setting: "off" and "user-invocable-only"
    hide the skill, "name-only" lists just its name. `disable-model-invocation: true`
    also takes its description out of context.
    """
    meta = _frontmatter(_text_file(skill_md))
    name = meta.get("name", skill_md.parent.name)
    mode = overrides.get(name)
    if meta.get("disable-model-invocation", "").lower() == "true" or mode in _HIDDEN_OVERRIDES:
        return name, 0, 0
    if mode == "name-only":
        return name, len(name), len(name)
    listing = " ".join(part for part in (meta.get("description", ""), meta.get("when_to_use", "")) if part)
    return name, min(len(listing), max_desc) + len(name), len(name)


def _skill_listing_chars(skill_md: Path) -> int:
    return _skill_listing(skill_md, {}, _SKILL_LISTING_CAP)[1]


def _enabled_plugin_dirs(claude_dir: Path, settings: dict[str, Any]) -> list[Path]:
    """Install directories of the plugins enabled in user settings."""
    enabled = {k for k, v in (settings.get("enabledPlugins") or {}).items() if v is True}
    installed = _json_file(claude_dir / "plugins" / "installed_plugins.json").get("plugins") or {}
    dirs = []
    for key, entries in installed.items():
        records = entries if isinstance(entries, list) else [entries]
        paths = [Path(r["installPath"]) for r in records if isinstance(r, dict) and r.get("installPath")]
        dirs.extend(p for p in paths[:1] if key in enabled and p.is_dir())
    return dirs


# The whole listing is capped at skillListingBudgetFraction of the context window
# (default 0.01). Over the cap, Claude Code keeps every skill's name and drops the
# descriptions of the least-used skills (code.claude.com/docs/en/settings-reference,
# read 2026-11-03). A token is estimated as 4 characters.
_LISTING_BUDGET_FRACTION = 0.01
# skillOverrides values that take a skill out of the listing; "name-only" keeps its name.
_HIDDEN_OVERRIDES = ("off", "user-invocable-only")
# The window assumed when settings pin no model this tool prices: the current Opus flagship.
_DEFAULT_WINDOW_MODEL = "opus-5-5"
_LISTING_TIERS = ((1_000, 20), (2_500, 16), (5_000, 11), (10_000, 6))


def _scoped_setting(sources: list[dict[str, Any]], key: str) -> Any:
    """`key` from the last settings dict that sets it (project settings come after user settings)."""
    return next((data[key] for data in reversed(sources) if key in data), None)


def _number_setting(sources: list[dict[str, Any]], key: str, default: float, high: float | None = None) -> float:
    value = _scoped_setting(sources, key)
    valid = isinstance(value, (int, float)) and not isinstance(value, bool) and 0 < value
    return value if valid and (high is None or value <= high) else default


def _skill_overrides(sources: list[dict[str, Any]]) -> dict[str, Any]:
    """skillOverrides merged across user and project settings, the later scope winning per skill."""
    merged: dict[str, Any] = {}
    for data in sources:
        block = data.get("skillOverrides")
        if isinstance(block, dict):
            merged.update(block)
    return merged


def _listing_window(sources: list[dict[str, Any]]) -> tuple[int, str]:
    """(context window, how it was chosen) for the listing cap: the pinned model, else the default."""
    pinned = _scoped_setting(sources, "model")
    name = re.sub(r"\[\w+\]$", "", pinned).strip() if isinstance(pinned, str) else ""
    key = _model_key(name) or _SUCCESSORS.get(name)
    if key in MODELS:
        return MODELS[key]["context_window"], f"{MODELS[key]['name']}, the pinned model"
    default = MODELS[_DEFAULT_WINDOW_MODEL]
    reason = f"`{name}` is not a model this tool prices" if name else "no model pinned"
    return default["context_window"], f"{default['name']} assumed, {reason}"


@dataclass(slots=True)
class _SkillListing:
    """The skill listing as Claude Code builds it, and the cap it must fit.

    `entries` holds (name, characters, name characters) per skill; a hidden skill
    has 0 of both. `cap_chars` is fraction x window x 4.
    """

    entries: list[tuple[str, int, int]]
    plugins: int
    cap_chars: int
    fraction: float
    window: int
    basis: str

    @property
    def full_chars(self) -> int:
        return sum(chars for _, chars, _ in self.entries)

    @property
    def over_cap(self) -> bool:
        return self.full_chars > self.cap_chars

    @property
    def sent_chars(self) -> int:
        """Names always stay; descriptions fill what is left under the cap."""
        names = sum(name_chars for _, _, name_chars in self.entries)
        return max(min(self.full_chars, self.cap_chars), names)


def _project_settings(project: Path | None) -> list[dict[str, Any]]:
    if project is None:
        return []
    return [_json_file(project / DOT_CLAUDE / name) for name in (SETTINGS_JSON, SETTINGS_LOCAL_JSON)]


def _skill_listing_state(claude_dir: Path, settings: dict[str, Any], project: Path | None = None) -> _SkillListing:
    """The user-level skill listing under user and project settings (cap, overrides, pinned model)."""
    sources = [settings, *_project_settings(project)]
    window, basis = _listing_window(sources)
    fraction = _number_setting(sources, "skillListingBudgetFraction", _LISTING_BUDGET_FRACTION, 1)
    max_desc = int(_number_setting(sources, "skillListingMaxDescChars", _SKILL_LISTING_CAP))
    overrides = _skill_overrides(sources)
    roots = [claude_dir] + _enabled_plugin_dirs(claude_dir, settings)
    skills = [md for root in roots for md in (root / "skills").glob("*/SKILL.md")]
    entries = [_skill_listing(md, overrides, max_desc) for md in skills]
    return _SkillListing(entries, len(roots) - 1, round(window * fraction * 4), fraction, window, basis)


def score_user_skills(
    claude_dir: Path,
    settings: dict[str, Any],
    project: Path | None = None,
    listing: _SkillListing | None = None,
) -> CategoryResult:
    listing = listing or _skill_listing_state(claude_dir, settings, project)
    tokens = math.ceil(listing.sent_chars / 4)
    cap = listing.cap_chars // 4
    cat = CategoryResult("Skill listing", 0, 20, "", [], [])
    cat.score = _tier_points(tokens, _LISTING_TIERS, 2)
    cat.detail = (
        f"{len(listing.entries)} skill(s) in ~/.claude/skills and {listing.plugins} enabled plugin(s), "
        f"~{tokens:,} listing tokens; cap ~{cap:,} tokens = {listing.fraction * 100:g}% of "
        f"{listing.window:,} ({listing.basis})"
    )
    if tokens > _LISTING_TIERS[0][0]:
        cat.findings.append(
            f"Skill descriptions add ~{tokens:,} tokens to context on every turn, used or not."
        )
        cat.fixes.append(
            "Run /skill-doctor in a session: it lists what each skill costs and how often it is "
            "used. Disable plugins you do not use, and set `disable-model-invocation: true` on "
            "skills you only ever call by name -- their descriptions then leave the listing. "
            "`skillOverrides` can also set a skill to `name-only` (its name stays listed) or `off`."
        )
    if listing.over_cap:
        cat.findings.append(
            f"Skill descriptions total ~{math.ceil(listing.full_chars / 4):,} tokens, over the ~{cap:,}-token "
            "listing cap, so Claude Code drops the descriptions of the least-used skills and keeps every name. "
            "Removing one skill mostly restores another skill's description; the listing stays near the cap."
        )
        cat.fixes.append(
            "To shrink the listing itself, lower `skillListingBudgetFraction` or set skills to `name-only` "
            "or `off` in `skillOverrides`; raising the fraction keeps more descriptions at the cost of "
            "context on every turn."
        )
    return cat


def _user_mcp_counts(project: Path) -> dict[str, int]:
    """User-scope servers, plus local-scope servers stored for this project, in ~/.claude.json."""
    data = _json_file(Path.home() / ".claude.json")
    key = project.resolve().as_posix().lower()
    projects = {k.lower(): v for k, v in (data.get("projects") or {}).items() if isinstance(v, dict)}
    return {
        "user": len(data.get("mcpServers") or {}),
        "local (this project)": len((projects.get(key) or {}).get("mcpServers") or {}),
    }


def score_user_mcp(project: Path, settings: dict[str, Any]) -> CategoryResult:
    counts = _user_mcp_counts(project)
    total = sum(counts.values())
    cat = CategoryResult("MCP servers (user)", 0, 20, "", [], [])
    cat.score = _tier_points(total, ((3, 20), (5, 15), (8, 9)), 4)
    cat.detail = ", ".join(f"{n} {scope}" for scope, n in counts.items())
    env = settings.get("env") if isinstance(settings.get("env"), dict) else {}
    if str(env.get("ENABLE_TOOL_SEARCH", "")).lower() == "false":
        cat.findings.append(
            "ENABLE_TOOL_SEARCH=false in user settings: every MCP tool schema loads up front on every request."
        )
    if total > 3:
        cat.fixes.append(
            "These load in every project. Run /mcp to disable servers you are not using, and move "
            "project-specific ones to that project's .mcp.json. Prefer an installed CLI (gh, aws, "
            "gcloud) where one exists -- it adds no per-tool listing."
        )
    return cat


def _user_cost_signals(settings: dict[str, Any]) -> list[str]:
    """Cost controls in user settings that Opus 5.5 and later models honor.

    A top-level effortLevel in ~/.claude/settings.json is ignored by Opus 5.5 and
    models released after it; /effort saves a per-model level under modelSettings
    (code.claude.com/docs/en/settings-reference).
    """
    signals = [s for s in _cost_control_signals(settings) if not s.startswith("effortLevel")]
    per_model = settings.get("modelSettings") if isinstance(settings.get("modelSettings"), dict) else {}
    for model, conf in per_model.items():
        effort = conf.get("effortLevel") if isinstance(conf, dict) else None
        if isinstance(effort, str) and effort.lower() in ("low", "medium"):
            signals.append(f"{model} effortLevel={effort}")
    return signals


def score_user_settings(settings: dict[str, Any]) -> CategoryResult:
    has_model, _, _, model_id = _settings_features(settings) if settings else (False, [], False, None)
    signals = _user_cost_signals(settings) if settings else []
    cat = CategoryResult("Settings (user)", 0, 20, "", [], [])
    cat.score = (8 if has_model else 0) + (12 if signals else 0)
    cat.detail = f"model={model_id or 'not pinned'}; cost controls: {', '.join(signals) or 'none'}"
    if settings.get("fastMode") is True:
        cat.findings.append("fastMode=true: Fast Mode bills 2x the model's base rate on every request.")
    if isinstance(settings.get("effortLevel"), str):
        cat.findings.append(
            "Top-level effortLevel in user settings does not apply to Opus 5.5 or later models. "
            "Run /effort in a session to save a per-model level under modelSettings."
        )
    if not signals:
        cat.fixes.append(
            "Set a cost control Claude Code reads: /effort low or medium per model (saved under "
            'modelSettings), "maxEffortLevel", "fastMode": false, "fastModePerSessionOptIn": true, '
            '"availableModels" with "enforceAvailableModels", an auto-compact window under 1000000 '
            '(/autocompact), or in "env" MAX_MCP_OUTPUT_TOKENS under 25000 or CLAUDE_CODE_SUBAGENT_MODEL '
            "with CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1."
        )
    return cat


def score_user_read_denies(settings: dict[str, Any]) -> CategoryResult:
    count = len(_read_deny_rules(settings))
    cat = CategoryResult("Read deny rules (user)", 0, 15, "", [], [])
    cat.score = _tier_points(-count, ((-5, 15), (-1, 9)), 0)
    cat.detail = f"{count} Read(...) rule(s) in user permissions.deny"
    if count == 0:
        cat.fixes.append(
            "Add rules that apply in every project to ~/.claude/settings.json: "
            '"permissions": {"deny": ["Read(.env)", "Read(.env.*)", "Read(node_modules/**)", '
            '"Read(dist/**)"]} -- a single-segment deny pattern matches at any depth. A Read deny '
            "also blocks Edit and Write on that path, so leave out build folders you commit."
        )
    return cat


def _subagent_dirs(claude_dir: Path, settings: dict[str, Any], project: Path) -> list[Path]:
    """Agents directories whose descriptions load in this project: user, project and enabled plugins."""
    plugins = [plugin / "agents" for plugin in _enabled_plugin_dirs(claude_dir, settings)]
    dirs = [claude_dir / "agents", project / DOT_CLAUDE / "agents", *plugins]
    return list(dict.fromkeys(d.resolve() for d in dirs))


def _subagent_description_tokens(agent_dirs: list[Path]) -> list[tuple[str, int]]:
    """(name, description tokens) of every subagent under the given agents directories."""
    return [
        (meta["name"], math.ceil(len(meta.get("description", "")) / 4))
        for agents_dir in agent_dirs
        for _, meta in _subagents(agents_dir)
    ]


def _subagent_description_findings(items: list[tuple[str, int]]) -> list[str]:
    total = sum(tokens for _, tokens in items)
    if total <= _SUBAGENT_DESCRIPTION_LIMIT:
        return []
    biggest = ", ".join(f"{name} ~{tokens:,}" for name, tokens in sorted(items, key=lambda i: i[1], reverse=True)[:3])
    return [
        f"Subagent descriptions total ~{total:,} tokens, over the {_SUBAGENT_DESCRIPTION_LIMIT:,}-token level at "
        f"which Claude Code warns at startup (built-in agents excluded). Largest: {biggest}. Trim `description` "
        "and move detail into the agent's system prompt, which loads only when that agent runs."
    ]


def _startup_facts(
    files: list[tuple[str, int]], listing: _SkillListing, subagents: list[tuple[str, int]]
) -> dict[str, Any]:
    """Estimated tokens that load at the start of every session from user-level files.

    Instruction files pay in full; skill and subagent descriptions are listing
    entries. The skill part is what fits under the cap. Characters / 4 undercounts on
    the 4.7+ tokenizer, which makes about 30% more tokens for the same text (pricing
    page, read 2026-11-03).
    """
    items = (
        [(name, math.ceil(chars / 4), "always-on, pays in full") for name, chars in files]
        + [(name, math.ceil(chars / 4), "listing entry") for name, chars, _ in listing.entries if chars]
        + [(name, tokens, "listing entry") for name, tokens in subagents]
    )
    total = (
        sum(math.ceil(chars / 4) for _, chars in files)
        + math.ceil(listing.sent_chars / 4)
        + sum(tokens for _, tokens in subagents)
    )
    top = sorted(items, key=lambda item: item[1], reverse=True)[:5]
    share = total / listing.window
    largest = ", ".join(f"{name} ~{tokens:,} ({load})" for name, tokens, load in top)
    return {
        "tokens": total,
        "window": listing.window,
        "window_basis": listing.basis,
        "share_of_window": round(share, 3),
        "top": [{"name": name, "tokens": tokens, "load": load} for name, tokens, load in top],
        "line": (
            f"Startup tokens (estimate, chars/4): ~{total:,} of a {listing.window:,}-token window "
            f"({listing.basis}), {share:.1%}. Largest: {largest}. The 4.7+ tokenizer makes about 30% "
            "more tokens for the same text."
        ),
    }


def rate_user(project: Path) -> ScopeResult:
    """Grade the user-level setup that loads in every project."""
    claude_dir = _claude_dir()
    settings = _json_file(claude_dir / SETTINGS_JSON)
    listing = _skill_listing_state(claude_dir, settings, project)
    subagents = _subagent_description_tokens(_subagent_dirs(claude_dir, settings, project))
    skills = score_user_skills(claude_dir, settings, project, listing)
    skills.detail += f"; {len(subagents)} subagent(s), ~{sum(tokens for _, tokens in subagents):,} description tokens"
    skills.findings.extend(_subagent_description_findings(subagents))
    user_settings = score_user_settings(settings)
    user_settings.findings.extend(_subagent_findings(claude_dir / "agents", _merged_env(settings)))
    categories = [
        score_user_instructions(claude_dir),
        skills,
        score_user_mcp(project, settings),
        user_settings,
        score_user_read_denies(settings),
    ]
    facts = {
        "config_dir": str(claude_dir),
        "startup": _startup_facts(_always_loaded_instructions(claude_dir), listing, subagents),
    }
    return _scope("Your Claude Code setup (user scope)", categories, facts)


# -- Real usage from local transcripts --


# A transcript model id: an optional Bedrock ARN, region and provider prefix, then
# claude-<family>-<version> or the older claude-<version>-<family>, then an optional
# date, Bedrock -v1:0 and [1m] suffix. It is matched whole, never as a substring.
_ID_PREFIX = r"(?:arn:\S+?/)?(?:(?:[a-z]{2,6}\.)?anthropic[./])?"
_ID_VERSION = r"\d+(?:-\d{1,2})?"
_ID_SUFFIX = r"(?:-\d{8}|-latest|@\d{8}|@latest)?(?:-v\d+(?::\d+)?)?(?:\[\w+\])?"
_MODEL_ID_FORMS = (
    re.compile(rf"{_ID_PREFIX}claude-(?P<family>[a-z]+)-(?P<version>{_ID_VERSION}){_ID_SUFFIX}"),
    re.compile(rf"{_ID_PREFIX}claude-(?P<version>{_ID_VERSION})-(?P<family>[a-z]+){_ID_SUFFIX}"),
)


def _model_key(model_id: str) -> str | None:
    """MODELS key for a transcript model id, or None unless a priced model has exactly that family and version.

    The id is parsed whole and looked up exactly. A substring or prefix match priced
    a point release the table lacks (claude-opus-5-6) at the older model's rate; it
    now stays unpriced and is counted as such.
    """
    for form in _MODEL_ID_FORMS:
        parsed = form.fullmatch(model_id)
        if parsed:
            key = f"{parsed['family']}-{parsed['version']}"
            key = _PRICE_ALIASES.get(key, key)
            return key if key in MODELS else None
    return None


def _request_cost(model: dict[str, Any], usage: dict[str, Any]) -> tuple[float, int]:
    """(list-price dollars, prompt tokens) for one API request's usage block."""
    fresh = usage.get("input_tokens") or 0
    cache_read = usage.get("cache_read_input_tokens") or 0
    writes = usage.get("cache_creation_input_tokens") or 0
    split = usage.get("cache_creation") if isinstance(usage.get("cache_creation"), dict) else {}
    write_1h = split.get("ephemeral_1h_input_tokens") or 0
    write_5m = writes - write_1h
    prompt = fresh + cache_read + writes
    rates = _rates_for_prompt(model, prompt)
    dollars = (
        fresh * rates["input"]
        + cache_read * rates["cache_hit"]
        + write_5m * rates["cache_5m_write"]
        + write_1h * rates["cache_1h_write"]
        + (usage.get("output_tokens") or 0) * rates["output"]
    ) / 1_000_000
    if usage.get("speed") == "fast" and model.get("fast_mode"):
        dollars *= 2
    return dollars, prompt


@dataclass(slots=True)
class _UsageRecord:
    """One billed API request from a transcript, with the fields the usage reports group by.

    `meta` holds the record's own scalar fields named in _RECORD_META_KEYS (cwd,
    gitBranch, version, entrypoint, effort, agentId, requestId and the
    attribution* tags) when present, plus `diagnostics` from the message when
    Claude Code wrote one. `sidechain` is True for subagent requests.
    """

    message_id: str
    model: str
    usage: dict[str, Any]
    timestamp: str
    session_id: str
    path: Path
    sidechain: bool
    meta: dict[str, Any]


@dataclass(slots=True)
class _TranscriptEvent:
    """A transcript record that bills nothing but explains spend.

    kind is "compact_boundary" (meta: trigger, preTokens, postTokens, durationMs),
    "api_error" (a retried request; meta: level, retryAttempt, maxRetries,
    retryInMs, isNetworkDown, rateLimits) or "error_message" (the error Claude
    Code showed; meta: error, such as "rate_limit", and the first 300
    characters of its text).
    """

    kind: str
    timestamp: str
    session_id: str
    path: Path
    sidechain: bool
    meta: dict[str, Any]


_RECORD_META_KEYS = (
    "cwd", "gitBranch", "version", "entrypoint", "effort", "agentId", "requestId",
    "attributionSkill", "attributionMcpServer", "attributionMcpTool", "attributionPlugin", "attributionAgent",
)
_USAGE_KEYS = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens", "output_tokens", "speed")
_COMPACT_KEYS = ("trigger", "preTokens", "postTokens", "durationMs")
_RETRY_KEYS = ("level", "retryAttempt", "maxRetries", "retryInMs")
_EVENT_MARKERS = ('"compact_boundary"', '"api_error"', '"isApiErrorMessage":true')


@dataclass
class _UsageTotals:
    files: int = 0
    requests: int = 0
    unpriced: int = 0
    fresh: int = 0
    cache_read: int = 0
    cache_write: int = 0
    output: int = 0
    output_dollars: float = 0.0
    fast_requests: int = 0
    history_start: str = ""
    prompts: list[int] = field(default_factory=list)
    by_model: dict[str, dict[str, float]] = field(default_factory=dict)
    sessions: set[str] = field(default_factory=set)
    records: list[_UsageRecord] = field(default_factory=list)
    events: list[_TranscriptEvent] = field(default_factory=list)
    unpriced_models: dict[str, int] = field(default_factory=dict)
    # Fix lines from the cache-break report (rate_usage fills it), read by _score_cache.
    cache_fixes: list[str] = field(default_factory=list)

    def add(self, record: _UsageRecord) -> None:
        usage = record.usage
        self.requests += 1
        self.records.append(record)
        self.sessions.add(record.session_id)
        self.fresh += usage.get("input_tokens") or 0
        self.cache_read += usage.get("cache_read_input_tokens") or 0
        self.cache_write += usage.get("cache_creation_input_tokens") or 0
        self.output += usage.get("output_tokens") or 0
        self.fast_requests += usage.get("speed") == "fast"
        key = _model_key(record.model)
        if key is None:
            self.unpriced += 1
            self.unpriced_models[record.model] = self.unpriced_models.get(record.model, 0) + 1
            return
        dollars, prompt = _request_cost(MODELS[key], usage)
        self.prompts.append(prompt)
        # Fast Mode doubles output as well, so output_share divides like with like.
        self.output_dollars += _class_dollars(MODELS[key], usage)["output"]
        row = self.by_model.setdefault(MODELS[key]["name"], {"requests": 0, "dollars": 0.0, "key": key})
        row["requests"] += 1
        row["dollars"] += dollars


def _slim_usage(usage: dict[str, Any]) -> dict[str, Any]:
    """The usage fields the cost math reads, so a 30-day scan stays small in memory."""
    slim = {key: usage[key] for key in _USAGE_KEYS if usage.get(key)}
    split = usage.get("cache_creation")
    if isinstance(split, dict) and split.get("ephemeral_1h_input_tokens"):
        slim["cache_creation"] = {"ephemeral_1h_input_tokens": split["ephemeral_1h_input_tokens"]}
    return slim


def _event_meta(record: dict[str, Any]) -> dict[str, Any]:
    """The few scalar fields of a compaction or retry record that the reports read."""
    if record.get("subtype") == "compact_boundary":
        compact = record.get("compactMetadata")
        return {k: compact[k] for k in _COMPACT_KEYS if k in compact} if isinstance(compact, dict) else {}
    meta = {k: record[k] for k in _RETRY_KEYS if k in record}
    error = record.get("error") if isinstance(record.get("error"), dict) else {}
    meta.update({k: error[k] for k in ("isNetworkDown", "rateLimits") if error.get(k) is not None})
    return meta


def _error_text(message: dict[str, Any]) -> str:
    content = message.get("content")
    blocks = content if isinstance(content, list) else []
    return " ".join(b.get("text", "") for b in blocks if isinstance(b, dict))[:300]


def _transcript_entry(line: str, path: Path) -> _UsageRecord | _TranscriptEvent | None:
    """The billed request or the event on one transcript line, else None.

    Only lines that can hold one are parsed: assistant records with usage, and
    the compaction, retry and error records named in _EVENT_MARKERS.
    """
    billed = '"usage"' in line and '"assistant"' in line
    if not billed and not any(marker in line for marker in _EVENT_MARKERS):
        return None
    try:
        record = json.loads(line)
    except ValueError:
        return None
    if not isinstance(record, dict):
        return None
    common = (record.get("timestamp") or "", record.get("sessionId") or path.stem, path, bool(record.get("isSidechain")))
    if record.get("type") == "system" and record.get("subtype") in ("compact_boundary", "api_error"):
        return _TranscriptEvent(record["subtype"], *common, _event_meta(record))
    message = record.get("message") if record.get("type") == "assistant" else None
    if not isinstance(message, dict):
        return None
    if record.get("isApiErrorMessage"):
        return _TranscriptEvent("error_message", *common, {"error": record.get("error"), "text": _error_text(message)})
    model = message.get("model") or ""
    if not isinstance(message.get("usage"), dict) or not message.get("id") or model.startswith("<"):
        return None
    meta = {k: sys.intern(v) if isinstance(v, str) else v for k in _RECORD_META_KEYS if (v := record.get(k)) not in (None, "")}
    if isinstance(message.get("diagnostics"), dict):
        meta["diagnostics"] = message["diagnostics"]
    return _UsageRecord(message["id"], sys.intern(model), _slim_usage(message["usage"]), *common, meta)


def _keep_latest(best: dict[str, _UsageRecord], record: _UsageRecord) -> None:
    """Keep one record per message id: the one with the most output tokens.

    A response is streamed as one record per content block, all with the same
    message id. Their usage blocks are snapshots taken as the response grows, so
    the first one can undercount output; the largest is the final count.
    """
    held = best.get(record.message_id)
    if held is None:
        best[record.message_id] = record
        return
    new_out, held_out = record.usage.get("output_tokens") or 0, held.usage.get("output_tokens") or 0
    if new_out > held_out or (new_out == held_out and record.timestamp < held.timestamp):
        best[record.message_id] = record


def collect_usage(days: int) -> _UsageTotals:
    """Sum the last `days` days of Claude Code transcripts under <config dir>/projects.

    Records are windowed by their own timestamp: a file modified today can hold
    records from weeks ago. File mtime is only a pre-filter (a file last written
    before the window holds nothing inside it). Each message id is counted once,
    across main and subagent files, at its final usage snapshot (_keep_latest).
    `records` and `events` keep every request and event in the window, oldest
    first, for the reports built on top.
    """
    totals = _UsageTotals()
    root = _claude_dir() / "projects"
    floor = time.time() - days * 86_400
    cutoff = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(floor))
    best: dict[str, _UsageRecord] = {}
    older_files = False
    for path in sorted(root.rglob("*.jsonl")) if root.is_dir() else []:
        if path.stat().st_mtime < floor:
            older_files = True
            continue
        with path.open(encoding="utf-8", errors="replace") as handle:
            for entry in filter(None, (_transcript_entry(line, path) for line in handle)):
                if entry.timestamp and (not totals.history_start or entry.timestamp < totals.history_start):
                    totals.history_start = entry.timestamp
                if isinstance(entry, _UsageRecord):
                    _keep_latest(best, entry)
                elif entry.timestamp >= cutoff:
                    totals.events.append(entry)
    for record in sorted(best.values(), key=lambda r: r.timestamp):
        if not record.timestamp or record.timestamp >= cutoff:
            totals.add(record)
    totals.events.sort(key=lambda e: e.timestamp)
    totals.files = len({record.path for record in totals.records})
    if older_files or totals.history_start[:19] <= cutoff:
        # Transcripts older than the window are on disk, so the window is fully covered.
        totals.history_start = ""
    return totals


def _percentile(values: list[int], share: float) -> int:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(share * len(ordered)))] if ordered else 0


_CACHE_TIERS = ((0.5, 5), (0.7, 15), (0.8, 30), (0.9, 40))
_CONTEXT_TIERS = ((50_000, 30), (100_000, 24), (200_000, 16), (400_000, 8))


def _score_cache(totals: _UsageTotals) -> CategoryResult:
    prompt_tokens = totals.fresh + totals.cache_read + totals.cache_write
    hit = totals.cache_read / prompt_tokens if prompt_tokens else 0.0
    cat = CategoryResult("Cache hit rate", 0, 50, "", [], [])
    cat.score = next((points for floor, points in reversed(_CACHE_TIERS) if hit >= floor), 0)
    cat.score = 50 if hit >= 0.95 else cat.score
    cat.detail = f"{hit:.1%} of prompt tokens were cache reads"
    if hit < 0.9:
        cat.fixes.append(
            "Cache misses re-bill your whole prefix. Keep one session per task, /clear between "
            "unrelated tasks instead of switching models mid-task, compact before a long break "
            "rather than after it, and leave MCP tool search on so server changes keep the cache."
        )
    cat.fixes.extend(totals.cache_fixes)
    return cat


def _score_context(totals: _UsageTotals) -> CategoryResult:
    median = _percentile(totals.prompts, 0.5)
    p90 = _percentile(totals.prompts, 0.9)
    over_100k = sum(p > 100_000 for p in totals.prompts)
    cat = CategoryResult("Context size", 0, 30, "", [], [])
    cat.score = _tier_points(median, _CONTEXT_TIERS, 2)
    share = over_100k / len(totals.prompts) if totals.prompts else 0.0
    cat.detail = f"median prompt {median:,} tokens, p90 {p90:,}; {share:.0%} of requests over 100K"
    if median > 100_000:
        cat.fixes.append(
            "Every turn resends the whole conversation. /clear between tasks, /compact once a task "
            "is done, and delegate searches to subagents so their reads stay out of your main context."
        )
    return cat


def _usage_facts(totals: _UsageTotals, days: int) -> dict[str, Any]:
    spend = sum(row["dollars"] for row in totals.by_model.values())
    models = sorted(totals.by_model.items(), key=lambda kv: kv[1]["dollars"], reverse=True)
    return {
        "days": days,
        "sessions": len(totals.sessions),
        "transcript_files": totals.files,
        "history_start": totals.history_start[:10] or None,
        "requests": totals.requests,
        "unpriced_requests": totals.unpriced,
        "unpriced": [
            {"model": model_id, "requests": count}
            for model_id, count in sorted(totals.unpriced_models.items(), key=lambda kv: kv[1], reverse=True)
        ],
        "list_price_dollars": round(spend, 2),
        "output_share": round(totals.output_dollars / spend, 3) if spend else 0,
        "fast_mode_requests": totals.fast_requests,
        "by_model": [
            {"model": name, "key": row["key"], "requests": int(row["requests"]),
             "dollars": round(row["dollars"], 2), "share": round(row["dollars"] / spend, 3) if spend else 0}
            for name, row in models
        ],
    }


# Current model for each legacy family, for the migration suggestion.
_SUCCESSORS = {"opus": "opus-5-5", "sonnet": "sonnet-5-5", "haiku": "haiku-5-5", "fable": "fable-5-2"}


def _legacy_fixes(facts: dict[str, Any]) -> list[str]:
    """Suggest the current model for each legacy model carrying 10% or more of list-price spend."""
    fixes = []
    for row in facts["by_model"]:
        old = MODELS[row["key"]]
        new_key = _SUCCESSORS.get(row["key"].split("-")[0])
        if old.get("lifecycle") != "legacy" or row["share"] < 0.1 or not new_key:
            continue
        new = MODELS[new_key]
        fixes.append(
            f"{row['share']:.0%} of list-price spend ({row['requests']:,} requests) ran on legacy {old['name']} "
            f"(${old['input']:g}/${old['output']:g} per 1M). {new['name']} is ${new['input']:g}/${new['output']:g}; "
            "pin it in the subagent, skill or workflow that names the old model, or check what the "
            "`opus`/`sonnet`/`haiku` alias resolves to on your provider."
        )
    return fixes


def _routing_fix(facts: dict[str, Any]) -> str | None:
    """A routing suggestion when one premium model carries most of the list-price spend."""
    top = facts["by_model"][0] if facts["by_model"] else None
    model = MODELS.get(top["key"]) if top else None
    if not model or top["share"] < 0.8 or model["input"] < MODELS["sonnet-5-5"]["input"] * 2:
        return None
    haiku = MODELS["haiku-5-5"]
    return (
        f"{top['share']:.0%} of list-price spend is on {top['model']} (${model['input']:g}/${model['output']:g} "
        f"per 1M). Route search, summaries and other simple subagent work to Haiku 5.5 "
        f"(${haiku['input']:g}/${haiku['output']:g} while the prompt stays under 100K tokens, "
        f"{model['input'] / haiku['input']:g}x cheaper per token) with `model: haiku` in the subagent."
    )


def _score_models(facts: dict[str, Any], fast_requests: int) -> CategoryResult:
    """Share of list-price spend on current models, plus migration and routing advice."""
    legacy = sum(row["share"] for row in facts["by_model"] if MODELS[row["key"]].get("lifecycle") == "legacy")
    cat = CategoryResult("Model mix", round(20 * (1 - legacy)), 20, "", [], [])
    cat.detail = f"{legacy:.0%} of list-price spend on legacy models"
    routing = _routing_fix(facts)
    if routing:
        cat.fixes.append(routing)
    cat.fixes.extend(_legacy_fixes(facts))
    if fast_requests:
        cat.findings.append(f"{fast_requests:,} request(s) ran in Fast Mode, billed at 2x the model's base rate.")
    return cat


def rate_usage(days: int, options: argparse.Namespace | None = None) -> ScopeResult:
    """Grade measured usage from local transcripts: cache efficiency, context size, model mix.

    `options` is the parsed command line, for the report flags; None means defaults.
    Each report below adds its own keys to `facts`; the grade reads only the three
    categories.
    """
    totals = collect_usage(days)
    facts = _usage_facts(totals, days)
    name = f"Your measured usage (last {days} days)"
    if not totals.prompts:
        # Nothing to measure: report that rather than grading an empty sample.
        return ScopeResult(name, 0, 0, "n/a", [], facts)
    # [A1] usage facts
    facts.update(_usage_reports(totals, days, options))
    totals.cache_fixes = _cache_break_fixes(facts)

    # [A2] usage facts
    _a2_add_facts(facts, totals, days, options)

    # [A3] usage facts
    if getattr(options, "tools", False):
        facts["tool_output"] = collect_tool_output(days)

    categories = [_score_cache(totals), _score_context(totals), _score_models(facts, totals.fast_requests)]
    return _scope(name, categories, facts)


# -- Usage reports: cache breaks, spend by class and session, limit hits [A1] ---
#
# One pass over collect_usage's records and compaction events, oldest first; the
# transcripts are not read again. Privacy: besides the record fields collect_usage
# keeps, these reports read `agentType` from each subagent's sibling .meta.json and
# match a few phrases in Claude Code's own rate_limit / billing_error messages to
# name the limit. They print counts, token totals and dollars, never message content.

# A request is a cache break when the cache held at least _BREAK_MIN_PREFIX tokens
# after the previous request in its chain (that request's cache read + cache write),
# this request read back under _BREAK_READ_SHARE of it, and it re-wrote at least
# _BREAK_MIN_REBUILT tokens. A chain is one transcript file (each subagent file is
# its own), or one agent's sidechain inside a main file.
_BREAK_MIN_PREFIX = 4_096
_BREAK_READ_SHARE = 0.5
_BREAK_MIN_REBUILT = 2_000
_TTL_5M_SECONDS = 300
_TTL_1H_SECONDS = 3_600
_IDLE_LONG_SECONDS = 4 * 3_600
_IDLE_SHORT = "idle 5-60 min"
_DAYS_PER_MONTH = 30
# 1h-TTL what-if verdict: "not yet" while |net| is under this share of the extra
# write cost; no recommendation while more than this share of a scope's writes are 1h.
_TTL_NOT_YET_SHARE = 0.10
_TTL_ALREADY_1H_SHARE = 0.5
# A cause's fix is "do" at or above this share of list spend, "not yet" at or above the second.
_FIX_DO_SHARE = 0.05
_FIX_NOT_YET_SHARE = 0.01
_TOP_SESSIONS = 5
_TOP_AGENT_TYPES = 5
_TOP_BREAK_ROWS = 3
_TOP_BREAK_SESSIONS = 3
# An effort change keeps the cache on these models, except on Bedrock, Google Cloud's
# Agent Platform, a Claude apps gateway or a HIPAA setup (guides/08-prompt-caching.md).
# Transcripts do not name the provider; an id with a provider marker counts as one.
_EFFORT_KEEPS_CACHE = ("opus-5-5", "sonnet-5-5", "haiku-5-5", "fable-5-2", "fable-5-1")
_PROVIDER_ID_MARKERS = ("anthropic.", "@", "arn:")
_LIMIT_ERRORS = ("rate_limit", "billing_error")
# Wording of Claude Code's limit messages (code.claude.com/docs/en/costs, read 2026-11-03).
_LIMIT_KINDS = (
    ("session", re.compile(r"session limit", re.IGNORECASE)),
    ("weekly", re.compile(r"weekly limit", re.IGNORECASE)),
    ("model-specific", re.compile(r"\b(?:opus|sonnet|haiku|fable|mythos) limit", re.IGNORECASE)),
    ("spend limit", re.compile(r"spend limit|shared budget", re.IGNORECASE)),
)
# Token class -> the MODELS rate field that bills it.
_CLASS_RATES = {
    "input": "input",
    "cache_read": "cache_hit",
    "cache_5m_write": "cache_5m_write",
    "cache_1h_write": "cache_1h_write",
    "output": "output",
}
_CLASS_LABELS = {
    "input": "fresh input",
    "cache_read": "cache read",
    "cache_5m_write": "5m write",
    "cache_1h_write": "1h write",
    "output": "output",
}
_WRITE_CLASSES = ("cache_5m_write", "cache_1h_write")
_FIXES_BY_CAUSE = {
    "idle": "Run /compact before a break, or start a fresh session after one, so the next turn rebuilds a short prefix.",
    "model switch": "Send side work to a subagent with `model: haiku` instead of switching the session with /model.",
    "fast mode toggle": "Pick fast or standard speed at session start; the two keep separate caches.",
}
_VERDICT_RULES = {
    "do": f"do ({_FIX_DO_SHARE:.0%} of list spend or more)",
    "not yet": f"not yet ({_FIX_NOT_YET_SHARE:.0%} to {_FIX_DO_SHARE:.0%} of list spend)",
}


def _class_tokens(usage: dict[str, Any]) -> dict[str, int]:
    """Tokens per billing class in one request's usage block."""
    writes = usage.get("cache_creation_input_tokens") or 0
    split = usage.get("cache_creation") if isinstance(usage.get("cache_creation"), dict) else {}
    write_1h = split.get("ephemeral_1h_input_tokens") or 0
    return {
        "input": usage.get("input_tokens") or 0,
        "cache_read": usage.get("cache_read_input_tokens") or 0,
        "cache_5m_write": writes - write_1h,
        "cache_1h_write": write_1h,
        "output": usage.get("output_tokens") or 0,
    }


# (model name, long-prompt tier, Fast Mode factor) -> per-token rates, built once per combination.
_CLASS_RATE_CACHE: dict[tuple[str, bool, int], dict[str, float]] = {}


def _class_rates(model: dict[str, Any], tokens: dict[str, int], fast: bool) -> dict[str, float]:
    """Dollars per token of each class: the request's own Haiku 5.5 tier, and 2x in Fast Mode.

    The returned dict is shared between requests; read it, never change it.
    """
    prompt = tokens["input"] + tokens["cache_read"] + tokens["cache_5m_write"] + tokens["cache_1h_write"]
    rates = _rates_for_prompt(model, prompt)
    factor = 2 if fast and model.get("fast_mode") else 1
    key = (model["name"], rates is not model, factor)
    if key not in _CLASS_RATE_CACHE:
        _CLASS_RATE_CACHE[key] = {cls: rates[name] * factor / 1_000_000 for cls, name in _CLASS_RATES.items()}
    return _CLASS_RATE_CACHE[key]


def _class_dollars(model: dict[str, Any], usage: dict[str, Any]) -> dict[str, float]:
    """List-price dollars per token class for one request; they sum to _request_cost's total."""
    tokens = _class_tokens(usage)
    rates = _class_rates(model, tokens, usage.get("speed") == "fast")
    return {cls: count * rates[cls] for cls, count in tokens.items()}


def _share(part: float, whole: float) -> float:
    return round(part / whole, 4) if whole else 0.0


def _usd(dollars: float) -> str:
    return f"-${-dollars:,.2f}" if dollars < 0 else f"${dollars:,.2f}"


def _epoch(timestamp: str) -> float | None:
    """Seconds since the epoch for a transcript timestamp; None when missing or malformed."""
    from datetime import datetime

    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp() if timestamp else None
    except ValueError:
        return None


def _iso_week(timestamp: str) -> str:
    """ISO week of a transcript timestamp, like 2026-W45."""
    from datetime import datetime

    try:
        year, week, _ = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).isocalendar()
    except ValueError:
        return "unknown"
    return f"{year}-W{week:02d}"


@dataclass(slots=True)
class _Place:
    """Where a transcript file sits: the session it bills to, its project folder, its agent type."""

    session: str
    project: str
    subagent_file: bool
    agent_type: str | None


def _agent_type(path: Path) -> str | None:
    """`agentType` from a subagent transcript's sibling agent-<id>.meta.json."""
    try:
        with path.with_suffix(".meta.json").open("rb") as handle:
            meta = json.loads(handle.read())
    except (OSError, ValueError):
        return None
    value = meta.get("agentType") if isinstance(meta, dict) else None
    return value if isinstance(value, str) and value else None


def _place(path: Path, root: Path) -> _Place:
    """Session, project folder and agent type of one transcript file.

    Main files are <project>/<session>.jsonl. A subagent file
    (<project>/<session>/subagents/[workflows/<id>/]agent-<id>.jsonl) bills to the
    session folder before `subagents`, and its type is in the sibling .meta.json.
    """
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        parts = (path.parent.name, path.name)
    subagent = "subagents" in parts[1:-1]
    session = parts[parts.index("subagents", 1) - 1] if subagent else path.stem
    project = parts[0] if len(parts) > 1 else path.parent.name
    return _Place(session, project, subagent, _agent_type(path) if subagent else None)


@dataclass(slots=True)
class _PricedRequest:
    """One request priced by token class, with what the A1 reports group it by."""

    record: _UsageRecord
    key: str
    model: dict[str, Any]
    tokens: dict[str, int]
    rates: dict[str, float]
    dollars: float
    write_dollars: float
    prompt: int
    writes: int
    fast: bool
    scope: str
    place: _Place


def _price(
    record: _UsageRecord, keys: dict[str, str | None], places: dict[Path, _Place], root: Path
) -> _PricedRequest | None:
    """Price one record by token class; None when its model has no price row."""
    if record.model not in keys:
        keys[record.model] = _model_key(record.model)
    key = keys[record.model]
    if key is None:
        return None
    if record.path not in places:
        places[record.path] = _place(record.path, root)
    place = places[record.path]
    model = MODELS[key]
    tokens = _class_tokens(record.usage)
    fast = record.usage.get("speed") == "fast"
    rates = _class_rates(model, tokens, fast)
    writes = tokens["cache_5m_write"] + tokens["cache_1h_write"]
    scope = "subagents" if record.sidechain or place.subagent_file else "main"
    write_dollars = tokens["cache_5m_write"] * rates["cache_5m_write"] + tokens["cache_1h_write"] * rates["cache_1h_write"]
    dollars = (
        tokens["input"] * rates["input"] + tokens["cache_read"] * rates["cache_read"]
        + write_dollars + tokens["output"] * rates["output"]
    )
    prompt = tokens["input"] + tokens["cache_read"] + writes
    return _PricedRequest(record, key, model, tokens, rates, dollars, write_dollars, prompt, writes, fast, scope, place)


def _tally(table: dict[str, dict[str, Any]], key: str, req: _PricedRequest) -> None:
    """Add one request to a dollars / requests / cache-hit / model-mix row."""
    row = table.setdefault(key, {"dollars": 0.0, "requests": 0, "read": 0, "prompt": 0, "models": {}})
    row["dollars"] += req.dollars
    row["requests"] += 1
    row["read"] += req.tokens["cache_read"]
    row["prompt"] += req.prompt
    name = req.model["name"]
    row["models"][name] = row["models"].get(name, 0.0) + req.dollars


@dataclass
class _SpendReport:
    """Where the money went: token class, caching net, main vs subagents by type, sessions."""

    total: float = 0.0
    by_class: dict[str, float] = field(default_factory=lambda: dict.fromkeys(_CLASS_RATES, 0.0))
    caching: dict[str, list[float]] = field(default_factory=dict)
    scopes: dict[str, dict[str, Any]] = field(default_factory=dict)
    types: dict[str, dict[str, Any]] = field(default_factory=dict)
    sessions: dict[str, dict[str, Any]] = field(default_factory=dict)
    subagent_files: dict[Path, bool] = field(default_factory=dict)
    # For the cost-mode break-even: per-token rates summed over main-thread requests.
    skill_reads: float = 0.0
    skill_writes: float = 0.0
    main_output: float = 0.0
    main_sessions: set[str] = field(default_factory=set)

    def add(self, req: _PricedRequest) -> None:
        self.total += req.dollars
        for cls, count in req.tokens.items():
            self.by_class[cls] += count * req.rates[cls]
        self._caching(req)
        _tally(self.scopes, req.scope, req)
        self._session(req)
        if req.scope == "main":
            self._cost_mode(req)
            return
        _tally(self.types, req.place.agent_type or "unknown", req)
        if req.place.subagent_file:
            self.subagent_files[req.record.path] = req.place.agent_type is not None

    def _caching(self, req: _PricedRequest) -> None:
        rates, tokens = req.rates, req.tokens
        row = self.caching.setdefault(req.model["name"], [0.0, 0.0])
        row[0] += tokens["cache_read"] * (rates["input"] - rates["cache_read"])
        row[1] += sum(tokens[cls] * (rates[cls] - rates["input"]) for cls in _WRITE_CLASSES)

    def _session(self, req: _PricedRequest) -> None:
        start = req.record.timestamp[:10]
        row = self.sessions.setdefault(
            req.place.session,
            {"dollars": 0.0, "writes": 0.0, "subagents": 0.0, "project": req.place.project, "start": start},
        )
        row["dollars"] += req.dollars
        row["writes"] += req.write_dollars
        if req.scope == "subagents":
            row["subagents"] += req.dollars

    def _cost_mode(self, req: _PricedRequest) -> None:
        overhead = req.model["tokenizer_overhead"]
        self.main_output += req.tokens["output"] * req.rates["output"]
        self.skill_reads += overhead * req.rates["cache_read"]
        if req.place.session not in self.main_sessions:
            self.main_sessions.add(req.place.session)
            self.skill_writes += overhead * req.rates["cache_5m_write"]

    def facts(self) -> dict[str, Any]:
        return {
            "by_class": {
                "classes": {
                    cls: {"dollars": round(dollars, 2), "share": _share(dollars, self.total)}
                    for cls, dollars in self.by_class.items()
                },
                "formula": "tokens of each class x its list rate for the request's model and "
                "Haiku 5.5 prompt tier, x2 in Fast Mode; the classes sum to list_price_dollars",
            },
            "caching_net": _caching_facts(self.caching),
            "by_agent_type": _agent_type_facts(self),
            "top_sessions": _top_session_facts(self.sessions, self.total),
            "ceilings": _ceiling_facts(self.by_class["output"], self.total),
        }


def _caching_facts(caching: dict[str, list[float]]) -> dict[str, Any]:
    saved = sum(row[0] for row in caching.values())
    premium = sum(row[1] for row in caching.values())
    ordered = sorted(caching.items(), key=lambda kv: kv[1][0] - kv[1][1], reverse=True)
    return {
        "saved": round(saved, 2),
        "write_premium": round(premium, 2),
        "net": round(saved - premium, 2),
        "by_model": [
            {"model": name, "saved": round(s, 2), "write_premium": round(p, 2), "net": round(s - p, 2)}
            for name, (s, p) in ordered
        ],
        "formula": "saved = cache-read tokens x (input rate - cache-read rate); write premium = 5m writes x "
        "(5m write rate - input rate) + 1h writes x (1h write rate - input rate); net = saved - premium",
    }


def _scope_row(row: dict[str, Any], total: float) -> dict[str, Any]:
    models = sorted(row["models"].items(), key=lambda kv: kv[1], reverse=True)
    return {
        "dollars": round(row["dollars"], 2),
        "share": _share(row["dollars"], total),
        "requests": row["requests"],
        "cache_hit": _share(row["read"], row["prompt"]),
        "models": {name: _share(dollars, row["dollars"]) for name, dollars in models},
    }


def _agent_type_facts(spend: _SpendReport) -> dict[str, Any]:
    empty: dict[str, Any] = {"dollars": 0.0, "requests": 0, "read": 0, "prompt": 0, "models": {}}
    types = sorted(spend.types.items(), key=lambda kv: kv[1]["dollars"], reverse=True)
    return {
        "main": _scope_row(spend.scopes.get("main", empty), spend.total),
        "subagents": _scope_row(spend.scopes.get("subagents", empty), spend.total),
        "subagent_files": len(spend.subagent_files),
        "type_known_files": sum(spend.subagent_files.values()),
        "types": [{"type": name, **_scope_row(row, spend.total)} for name, row in types],
        "source": "subagent = isSidechain or a file under subagents/; type = agentType in its sibling "
        "agent-<id>.meta.json, else unknown",
    }


def _top_session_facts(sessions: dict[str, dict[str, Any]], total: float) -> list[dict[str, Any]]:
    top = sorted(sessions.items(), key=lambda kv: kv[1]["dollars"], reverse=True)[:_TOP_SESSIONS]
    return [
        {
            "session_id": session,
            "project": row["project"],
            "date": row["start"],
            "dollars": round(row["dollars"], 2),
            "share": _share(row["dollars"], total),
            "write_share": _share(row["writes"], row["dollars"]),
            "subagent_share": _share(row["subagents"], row["dollars"]),
            "resume": f"claude --resume {session} (from that project folder)",
        }
        for session, row in top
    ]


def _ceiling_facts(output: float, total: float) -> dict[str, Any]:
    share = _share(output, total)
    return {
        "output_share": share,
        "halve_output_saves_at_most": round(share / 2, 4),
        "formula": "halving billed output saves output_share / 2 of list spend at most",
        "note": "thinking is billed inside output_tokens; a brevity rule only shortens what it changes",
    }


def _cost_mode_skill(project: Path | None) -> Path | None:
    """The first cost-mode SKILL.md found in this project, ~/.claude/skills or an enabled plugin."""
    claude_dir = _claude_dir()
    roots = [project, project / DOT_CLAUDE] if project else []
    roots += [claude_dir, *_enabled_plugin_dirs(claude_dir, _json_file(claude_dir / SETTINGS_JSON))]
    candidates = (root / "skills" / "cost-mode" / "SKILL.md" for root in roots)
    return next((path for path in candidates if path.is_file()), None)


def _cost_mode_break_even(spend: _SpendReport, project: Path | None) -> dict[str, Any] | None:
    """How far cost-mode's brevity rule would have to cut main-thread output to pay for its own context.

    Hypothetical: it prices the installed SKILL.md as if it sat in every main-thread
    request. None when no cost-mode SKILL.md is found or there was no main-thread output.
    """
    skill = _cost_mode_skill(project)
    if skill is None or not spend.main_output:
        return None
    chars = len(_text_file(skill))
    context = chars / 4 * (spend.skill_reads + spend.skill_writes)
    return {
        "skill_md": str(skill),
        "chars": chars,
        "context_dollars": round(context, 2),
        "main_output_dollars": round(spend.main_output, 2),
        "required_output_cut": _share(context, spend.main_output),
        "formula": "context $ = SKILL.md chars / 4 x the model's tokenizer factor x (its cache-read rate on "
        "every main-thread request + one 5m write per main session); required cut = context $ / main-thread output $",
        "note": "Hypothetical: as if cost-mode were active on every main-thread request, counting only its "
        "brevity rule; routing and cache advice are not counted. chars / 4 is a floor on tokens.",
    }


@dataclass(slots=True)
class _ChainState:
    """The last request of one cache chain, plus the compactions recorded since it."""

    when: float | None = None
    model: str = ""
    fast: bool = False
    effort: Any = None
    version: Any = None
    carried: int = 0
    ttl: int = _TTL_5M_SECONDS
    compacted: list[str] = field(default_factory=list)


@dataclass(slots=True)
class _TtlScope:
    """Sums for the 1h-TTL what-if in one scope (main or subagents)."""

    writes_5m: int = 0
    writes_1h: int = 0
    premium: float = 0.0  # every 5m write x (1h write rate - 5m write rate)
    saved: float = 0.0  # idle 5-60 min rebuilds x (write rate - cache-read rate)
    rebuilt: int = 0  # tokens those rebuilds re-wrote
    not_rewritten: float = 0.0  # their 5m tokens x (1h - 5m rate): a 1h cache would not write them again
    models: dict[str, int] = field(default_factory=dict)  # MODELS key -> 5m write tokens


# Break causes, first match wins. Recorded causes come first (the API's own reason,
# then compaction, model and speed, which always change the cached prefix); the idle
# gap is next because it is inferred from response timestamps; then effort and
# Claude Code version. Anything else is "unknown": nothing here guesses at tool,
# CLAUDE.md or MCP changes unless diagnostics names them.


def _cause_reported(prev: _ChainState, req: _PricedRequest, gap: float | None) -> str | None:
    """message.diagnostics.cache_miss_reason, when Claude Code recorded one."""
    diagnostics = req.record.meta.get("diagnostics")
    reason = diagnostics.get("cache_miss_reason") if isinstance(diagnostics, dict) else None
    if isinstance(reason, dict):
        reason = reason.get("type") or reason.get("reason")
    return f"reported: {reason[:40]}" if isinstance(reason, str) and reason else None


def _cause_compaction(prev: _ChainState, req: _PricedRequest, gap: float | None) -> str | None:
    """The first request after a compaction: its rewrite is the price of compacting."""
    return "compaction" if prev.compacted else None


def _cause_model(prev: _ChainState, req: _PricedRequest, gap: float | None) -> str | None:
    return "model switch" if prev.model != req.record.model else None


def _cause_speed(prev: _ChainState, req: _PricedRequest, gap: float | None) -> str | None:
    return "fast mode toggle" if prev.fast != req.fast else None


def _cause_idle(prev: _ChainState, req: _PricedRequest, gap: float | None) -> str | None:
    """A gap past the TTL of the chain's last cache write, bucketed by length."""
    if gap is None or gap <= prev.ttl:
        return None
    if gap <= _TTL_1H_SECONDS:
        return _IDLE_SHORT
    return "idle 1-4 h" if gap <= _IDLE_LONG_SECONDS else "idle over 4 h"


def _cause_effort(prev: _ChainState, req: _PricedRequest, gap: float | None) -> str | None:
    """An effort change, only where it breaks the cache (see _EFFORT_KEEPS_CACHE)."""
    effort = req.record.meta.get("effort")
    if prev.effort is None or effort is None or effort == prev.effort:
        return None
    model_id = req.record.model
    keeps = any(name in model_id for name in _EFFORT_KEEPS_CACHE)
    provider = any(marker in model_id for marker in _PROVIDER_ID_MARKERS)
    return "effort change" if provider or not keeps else None


def _cause_version(prev: _ChainState, req: _PricedRequest, gap: float | None) -> str | None:
    version = req.record.meta.get("version")
    return "version change" if prev.version and version and version != prev.version else None


_BREAK_CAUSES = (
    _cause_reported, _cause_compaction, _cause_model, _cause_speed, _cause_idle, _cause_effort, _cause_version,
)


def _break_cause(prev: _ChainState, req: _PricedRequest, gap: float | None) -> str:
    return next((cause for check in _BREAK_CAUSES if (cause := check(prev, req, gap))), "unknown")


def _write_rate(req: _PricedRequest) -> float:
    """Dollars per token of this request's cache writes, weighted by its own 5m / 1h split."""
    w5, w1h = req.tokens["cache_5m_write"], req.tokens["cache_1h_write"]
    return (w5 * req.rates["cache_5m_write"] + w1h * req.rates["cache_1h_write"]) / (w5 + w1h)


def _write_ttl(req: _PricedRequest, prev: _ChainState | None) -> int:
    """TTL of the chain's newest cache entry: 1h if this request wrote any 1h tokens."""
    if not req.writes:
        return prev.ttl if prev else _TTL_5M_SECONDS
    return _TTL_1H_SECONDS if req.tokens["cache_1h_write"] else _TTL_5M_SECONDS


@dataclass
class _BreakReport:
    """Cache breaks by cause and scope, the 1h-TTL what-if, compactions and the Haiku 5.5 tier."""

    chains: dict[tuple[Path, str], _ChainState] = field(default_factory=dict)
    causes: dict[tuple[str, str], list[float]] = field(default_factory=dict)  # breaks, tokens, dollars
    sessions: dict[str, list[Any]] = field(default_factory=dict)  # breaks, dollars, project
    ttl: dict[str, _TtlScope] = field(default_factory=lambda: {"main": _TtlScope(), "subagents": _TtlScope()})
    compactions: dict[str, list[int]] = field(default_factory=dict)  # count, pre, first after, n after
    haiku: list[float] = field(default_factory=lambda: [0, 0, 0.0])  # over threshold, all, premium $

    def compaction(self, event: _TranscriptEvent) -> None:
        trigger = str(event.meta.get("trigger") or "unknown")
        row = self.compactions.setdefault(trigger, [0, 0, 0, 0])
        row[0] += 1
        pre = event.meta.get("preTokens")
        row[1] += pre if isinstance(pre, int) else 0
        self.chains.setdefault((event.path, ""), _ChainState()).compacted.append(trigger)

    def add(self, req: _PricedRequest) -> None:
        record = req.record
        inline = record.sidechain and not req.place.subagent_file
        key = (record.path, str(record.meta.get("agentId") or "") if inline else "")
        when = _epoch(record.timestamp)
        prev = self.chains.get(key)
        if prev is not None:
            self._after(prev, req, when)
        self._tally_writes(req)
        self._tally_haiku(req)
        self.chains[key] = _ChainState(
            when, record.model, req.fast, record.meta.get("effort"), record.meta.get("version"),
            req.tokens["cache_read"] + req.writes, _write_ttl(req, prev),
        )

    def _after(self, prev: _ChainState, req: _PricedRequest, when: float | None) -> None:
        """Credit any compaction to this first request after it, then test for a break."""
        for trigger in prev.compacted:
            row = self.compactions[trigger]
            row[2] += req.prompt
            row[3] += 1
        read = req.tokens["cache_read"]
        rebuilt = min(prev.carried - read, req.writes)
        if prev.carried < _BREAK_MIN_PREFIX or read >= _BREAK_READ_SHARE * prev.carried or rebuilt < _BREAK_MIN_REBUILT:
            return
        gap = when - prev.when if when is not None and prev.when is not None else None
        cause = _break_cause(prev, req, gap)
        self._tally_break(cause, req, rebuilt, rebuilt * (_write_rate(req) - req.rates["cache_read"]))

    def _tally_break(self, cause: str, req: _PricedRequest, rebuilt: int, extra: float) -> None:
        row = self.causes.setdefault((cause, req.scope), [0, 0, 0.0])
        row[0] += 1
        row[1] += rebuilt
        row[2] += extra
        session = self.sessions.setdefault(req.place.session, [0, 0.0, req.place.project])
        session[0] += 1
        session[1] += extra
        if cause == _IDLE_SHORT:
            ttl = self.ttl[req.scope]
            ttl.saved += extra
            ttl.rebuilt += rebuilt
            step_up = req.rates["cache_1h_write"] - req.rates["cache_5m_write"]
            ttl.not_rewritten += min(rebuilt, req.tokens["cache_5m_write"]) * step_up

    def _tally_writes(self, req: _PricedRequest) -> None:
        ttl = self.ttl[req.scope]
        writes_5m = req.tokens["cache_5m_write"]
        ttl.writes_5m += writes_5m
        ttl.writes_1h += req.tokens["cache_1h_write"]
        ttl.premium += writes_5m * (req.rates["cache_1h_write"] - req.rates["cache_5m_write"])
        if writes_5m:
            ttl.models[req.key] = ttl.models.get(req.key, 0) + writes_5m

    def _tally_haiku(self, req: _PricedRequest) -> None:
        """Haiku 5.5's long-prompt tier: requests over the threshold and what the tier added."""
        tier = req.model.get("long_prompt")
        if not tier:
            return
        self.haiku[1] += 1
        if req.prompt > tier["threshold"]:
            base = sum(count * req.model[_CLASS_RATES[cls]] for cls, count in req.tokens.items()) / 1_000_000
            self.haiku[0] += 1
            self.haiku[2] += req.dollars - base

    def facts(self, total: float, days: int) -> dict[str, Any]:
        return {
            "cache_breaks": _break_facts(self, total, days),
            "ttl_what_if": {
                "main": _ttl_facts("main", self.ttl["main"], days),
                "subagents": _ttl_facts("subagents", self.ttl["subagents"], days),
                "formula": "net = idle 5-60 min rebuilds x (write rate - read rate) - (5m write tokens - those "
                "rebuilds) x (1h write rate - 5m write rate); break-even rebuild share = (1h - 5m) / (1h - read)",
                "verdicts": f"do: net > 0; not yet: |net| under {_TTL_NOT_YET_SHARE:.0%} of the extra cost; "
                f"skip: net < 0; already 1h: over {_TTL_ALREADY_1H_SHARE:.0%} of writes are 1h",
            },
            "compactions": _compaction_facts(self.compactions),
            "haiku_long_prompt": _haiku_facts(self.haiku),
        }


def _break_fix_facts(causes: dict[tuple[str, str], list[float]], total: float, scale: float) -> list[dict[str, Any]]:
    """One fix per cause family with a known remedy, with its dollars and a verdict."""
    families: dict[str, float] = {}
    for (cause, _scope), row in causes.items():
        family = "idle" if cause.startswith("idle") else cause
        if family in _FIXES_BY_CAUSE:
            families[family] = families.get(family, 0.0) + row[2]
    rows = []
    for family, dollars in sorted(families.items(), key=lambda kv: kv[1], reverse=True):
        share = _share(dollars, total)
        verdict = "do" if share >= _FIX_DO_SHARE else "not yet" if share >= _FIX_NOT_YET_SHARE else "skip"
        rows.append({
            "cause": family, "verdict": verdict, "extra_dollars": round(dollars, 2), "share_of_spend": share,
            "per_30_days": round(dollars * scale, 2), "fix": _FIXES_BY_CAUSE[family],
        })
    return rows


def _break_facts(report: _BreakReport, total: float, days: int) -> dict[str, Any]:
    scale = _DAYS_PER_MONTH / days
    rows = sorted(report.causes.items(), key=lambda kv: kv[1][2], reverse=True)
    extra = sum(row[2] for row in report.causes.values())
    worst = sorted(report.sessions.items(), key=lambda kv: kv[1][1], reverse=True)[:_TOP_BREAK_SESSIONS]
    return {
        "breaks": int(sum(row[0] for row in report.causes.values())),
        "rebuilt_tokens": int(sum(row[1] for row in report.causes.values())),
        "extra_dollars": round(extra, 2),
        "share_of_spend": _share(extra, total),
        "by_cause": [
            {
                "cause": cause, "scope": scope, "breaks": int(n), "rebuilt_tokens": int(tokens),
                "extra_dollars": round(dollars, 2), "share_of_spend": _share(dollars, total),
                "per_30_days": round(dollars * scale, 2),
            }
            for (cause, scope), (n, tokens, dollars) in rows
        ],
        "top_sessions": [
            {"session_id": session, "project": project, "breaks": n, "extra_dollars": round(dollars, 2)}
            for session, (n, dollars, project) in worst
        ],
        "fixes": _break_fix_facts(report.causes, total, scale),
        "thresholds": {
            "min_prefix_tokens": _BREAK_MIN_PREFIX,
            "max_read_share": _BREAK_READ_SHARE,
            "min_rebuilt_tokens": _BREAK_MIN_REBUILT,
            "ttl_5m_seconds": _TTL_5M_SECONDS,
            "ttl_1h_seconds": _TTL_1H_SECONDS,
            "idle_long_seconds": _IDLE_LONG_SECONDS,
        },
        "cause_order": [
            "reported: <diagnostics.cache_miss_reason>", "compaction", "model switch", "fast mode toggle",
            "idle (gap past the TTL of the chain's last write)", "effort change (only where it breaks the cache)",
            "version change", "unknown",
        ],
        "formula": "re-written = min(cache read + write of the previous request in the chain - this request's "
        "cache read, this request's cache writes); extra $ = re-written x (this request's 5m/1h-weighted "
        "write rate - its cache-read rate)",
        "cause_order_why": "Recorded causes first (the API's own reason, then compaction, model and speed, which "
        "always change the cached prefix); the idle gap next because it is inferred from timestamps; then effort "
        "and Claude Code version. Tool, CLAUDE.md or MCP changes are named only when diagnostics names them.",
        "caveats": [
            "Gaps are measured between response records, so they include the next response's generation time.",
            "The first request after a compaction is counted as a compaction break: its rewrite is the price of compacting.",
            "List price: what these tokens cost on the API, not a plan bill.",
        ],
    }


def _ttl_verdict(net: float, extra: float, share_1h: float, writes_5m: int) -> str:
    if share_1h > _TTL_ALREADY_1H_SHARE:
        return "already 1h"
    if not writes_5m:
        return "n/a"
    if abs(net) < _TTL_NOT_YET_SHARE * extra:
        return "not yet"
    return "do" if net > 0 else "skip"


def _ttl_facts(scope: str, row: _TtlScope, days: int) -> dict[str, Any]:
    """1h-TTL what-if for one scope; a negative net is reported as it is, never floored."""
    scale = _DAYS_PER_MONTH / days
    extra = row.premium - row.not_rewritten
    net = row.saved - extra
    share_1h = _share(row.writes_1h, row.writes_5m + row.writes_1h)
    model = MODELS[max(row.models, key=row.models.__getitem__)] if row.models else None
    break_even = None
    if model:
        break_even = (model["cache_1h_write"] - model["cache_5m_write"]) / (model["cache_1h_write"] - model["cache_hit"])
    return {
        "setting": "promptCacheTtl" if scope == "main" else "subagentPromptCacheTtl",
        "writes_5m_tokens": row.writes_5m,
        "writes_1h_tokens": row.writes_1h,
        "write_1h_share": share_1h,
        "idle_rebuilt_tokens": row.rebuilt,
        "rebuild_share": _share(row.rebuilt, row.writes_5m),
        "break_even_share": round(break_even, 4) if break_even is not None else None,
        "break_even_model": model["name"] if model else None,
        "saved_dollars": round(row.saved, 2),
        "extra_dollars": round(extra, 2),
        "net_dollars": round(net, 2),
        "saved_per_30_days": round(row.saved * scale, 2),
        "extra_per_30_days": round(extra * scale, 2),
        "net_per_30_days": round(net * scale, 2),
        "verdict": _ttl_verdict(net, extra, share_1h, row.writes_5m),
    }


def _compaction_facts(compactions: dict[str, list[int]]) -> dict[str, Any]:
    measured = sum(row[3] for row in compactions.values())
    return {
        "by_trigger": {
            trigger: {
                "count": n,
                "pre_tokens_avg": round(pre / n) if n else 0,
                "first_prompt_after_avg": round(after / m) if m else None,
                "first_prompt_after_n": m,
            }
            for trigger, (n, pre, after, m) in sorted(compactions.items(), key=lambda kv: kv[1][0], reverse=True)
        },
        "first_prompt_after_avg": round(sum(row[2] for row in compactions.values()) / measured) if measured else None,
        "note": "first_prompt_after is the measured prompt (input + cache read + cache write) of the first "
        "request after a compaction; compactMetadata.postTokens is not used because it leaves out the fixed "
        "context. Triggers are as recorded; claude-crusts notes that idle compactions can be recorded as manual.",
    }


def _haiku_facts(haiku: list[float]) -> dict[str, Any]:
    base, tier = MODELS["haiku-5-5"], MODELS["haiku-5-5"]["long_prompt"]
    return {
        "requests_over_threshold": int(haiku[0]),
        "haiku_requests": int(haiku[1]),
        "threshold_tokens": tier["threshold"],
        "premium_dollars": round(haiku[2], 2),
        "formula": f"premium = each request over {tier['threshold']:,} prompt tokens (cache reads and writes "
        f"included) at the long-prompt rates (${tier['input']:g}/${tier['output']:g} per 1M) - the same tokens "
        f"at the base rates (${base['input']:g}/${base['output']:g})",
    }


def _limit_kind(event: _TranscriptEvent) -> str:
    """The limit a rate_limit or billing_error message names, from its wording."""
    text = str(event.meta.get("text") or "")
    named = next((kind for kind, pattern in _LIMIT_KINDS if pattern.search(text)), None)
    if named:
        return named
    return "other 429" if event.meta.get("error") == "rate_limit" else "other billing"


def _limit_hits(events: list[_TranscriptEvent], days: int) -> dict[str, Any]:
    """Claude Code's rate_limit and billing_error messages in the window, by ISO week and kind."""
    counts: dict[tuple[str, str], int] = {}
    for event in events:
        if event.kind == "error_message" and event.meta.get("error") in _LIMIT_ERRORS:
            key = (_iso_week(event.timestamp), _limit_kind(event))
            counts[key] = counts.get(key, 0) + 1
    by_week: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    for (week, kind), count in sorted(counts.items()):
        by_week[week] = by_week.get(week, 0) + count
        by_kind[kind] = by_kind.get(kind, 0) + count
    return {
        "total": sum(counts.values()),
        "by_week": by_week,
        "by_kind": dict(sorted(by_kind.items(), key=lambda kv: kv[1], reverse=True)),
        "rows": [{"week": week, "kind": kind, "count": count} for (week, kind), count in sorted(counts.items())],
        "errors": list(_LIMIT_ERRORS),
        "note": f"Claude Code's own {' and '.join(_LIMIT_ERRORS)} messages in the last {days} days of transcripts. "
        "Claude Code deletes transcripts after cleanupPeriodDays (30 by default), so older hits are gone. "
        "rate_limit covers API 429 throttling as well as plan limits; the kind comes from the message wording "
        "(code.claude.com/docs/en/costs, read 2026-11-03).",
    }


def _a1_pass(totals: _UsageTotals) -> tuple[_SpendReport, _BreakReport]:
    """Price every record once and feed both reports, with compactions merged in by time."""
    import heapq

    spend, breaks = _SpendReport(), _BreakReport()
    root = _claude_dir() / "projects"
    keys: dict[str, str | None] = {}
    places: dict[Path, _Place] = {}
    compactions = [event for event in totals.events if event.kind == "compact_boundary"]
    for item in heapq.merge(compactions, totals.records, key=lambda entry: entry.timestamp):
        if isinstance(item, _TranscriptEvent):
            breaks.compaction(item)
            continue
        request = _price(item, keys, places, root)
        if request is not None:
            spend.add(request)
            breaks.add(request)
    return spend, breaks


def _usage_reports(totals: _UsageTotals, days: int, options: argparse.Namespace | None) -> dict[str, Any]:
    """Facts for the A1 blocks: spend by class, scope, agent type and session; cache breaks; limit hits."""
    spend, breaks = _a1_pass(totals)
    facts = spend.facts()
    facts.update(breaks.facts(spend.total, days))
    project = getattr(options, "path", None)
    facts["cost_mode_break_even"] = _cost_mode_break_even(spend, Path(project) if project else None)
    facts["limit_hits"] = _limit_hits(totals.events, days)
    return facts


def _cache_break_fixes(facts: dict[str, Any]) -> list[str]:
    """Fix lines for the Cache hit rate category: causes with a known remedy, and a 1h TTL that pays."""
    fixes = [
        f"{row['fix']} {row['cause'].capitalize()} breaks cost {_usd(row['extra_dollars'])} above warm reads "
        f"({row['share_of_spend']:.1%} of list spend, about {_usd(row['per_30_days'])} per 30 days at list "
        f"price, not a bill). Verdict: {_VERDICT_RULES[row['verdict']]}."
        for row in facts["cache_breaks"]["fixes"]
        if row["verdict"] in _VERDICT_RULES
    ]
    for scope in ("main", "subagents"):
        row = facts["ttl_what_if"][scope]
        if row["verdict"] == "do":
            fixes.append(
                f'Set "{row["setting"]}": "1h" (Claude Code v2.1.242+): for {scope} requests it would have saved '
                f"{_usd(row['net_per_30_days'])} net per 30 days at list price (idle rebuilds {row['rebuild_share']:.0%} "
                f"of 5m writes, break-even {row['break_even_share']:.0%} on {row['break_even_model']}). Verdict: do."
            )
    return fixes


def _print_spend_split(facts: dict[str, Any]) -> None:
    classes = sorted(facts["by_class"]["classes"].items(), key=lambda kv: kv[1]["dollars"], reverse=True)
    print("  By token class: " + ", ".join(f"{_CLASS_LABELS[cls]} {row['share']:.1%}" for cls, row in classes))
    net = facts["caching_net"]
    print(
        f"    Caching saved {_usd(net['saved'])} vs uncached input, write premium {_usd(net['write_premium'])}, "
        f"net {_usd(net['net'])} {DIM}(saved = reads x (input - read rate); premium = writes x (write rate - input)){RESET}"
    )
    ceiling = facts["ceilings"]
    print(
        f"    Output is {ceiling['output_share']:.1%} of list spend: halving billed output saves "
        f"{ceiling['halve_output_saves_at_most']:.1%} at most {DIM}(thinking is billed inside output_tokens){RESET}"
    )


def _print_agent_split(facts: dict[str, Any]) -> None:
    split = facts["by_agent_type"]
    main, sub = split["main"], split["subagents"]
    print(
        f"  Main thread {_usd(main['dollars'])} ({main['share']:.0%}), subagents {_usd(sub['dollars'])} "
        f"({sub['share']:.0%}); agent type known for {split['type_known_files']:,} of "
        f"{split['subagent_files']:,} subagent files"
    )
    for row in split["types"][:_TOP_AGENT_TYPES]:
        mix = ", ".join(f"{name} {share:.0%}" for name, share in list(row["models"].items())[:2])
        print(
            f"    {row['type'][:24]:<24} {_usd(row['dollars']):>11} {row['share']:>4.0%}  "
            f"hit {row['cache_hit']:.0%}  {DIM}{mix}{RESET}"
        )


def _print_top_sessions(facts: dict[str, Any]) -> None:
    rows = facts["top_sessions"]
    if not rows:
        return
    print(f"  Top sessions {DIM}(full ids in --json; resume with claude --resume <id> from that project folder){RESET}")
    for row in rows:
        print(
            f"    {row['session_id'][:8]}  {row['date']}  {row['project'][-30:]:<30} {_usd(row['dollars']):>11} "
            f"{row['share']:>4.0%}  writes {row['write_share']:.0%}"
        )


def _print_cost_mode(facts: dict[str, Any]) -> None:
    row = facts.get("cost_mode_break_even")
    if not row:
        return
    print(
        f"  cost-mode break-even (hypothetical): if its SKILL.md ({row['chars']:,} chars) sat in every main-thread "
        f"request, its {_usd(row['context_dollars'])} context cost needs a {row['required_output_cut']:.1%} cut of "
        f"main-thread output ({_usd(row['main_output_dollars'])}) {DIM}(chars / 4 x tokenizer factor at the read rate "
        f"per request + one 5m write per session; brevity only, routing and cache advice not counted){RESET}"
    )


def _print_cache_breaks(facts: dict[str, Any]) -> None:
    breaks = facts["cache_breaks"]
    limits = breaks["thresholds"]
    rule = (
        f"break = cached prefix >= {limits['min_prefix_tokens']:,} tokens, read back < {limits['max_read_share']:.0%}, "
        f">= {limits['min_rebuilt_tokens']:,} re-written; extra = re-written x (write rate - read rate); "
        "gaps include response time"
    )
    if not breaks["breaks"]:
        print(f"  Cache breaks: none {DIM}({rule}){RESET}")
        return
    print(
        f"  Cache breaks: {breaks['breaks']:,} re-wrote {breaks['rebuilt_tokens']:,} tokens, "
        f"{_usd(breaks['extra_dollars'])} above warm reads ({breaks['share_of_spend']:.1%} of list spend)"
    )
    for row in breaks["by_cause"][:_TOP_BREAK_ROWS]:
        print(
            f"    {row['cause'][:28]:<28} {row['scope']:<9} {row['breaks']:>6,}  "
            f"{_usd(row['extra_dollars']):>11}  {row['share_of_spend']:>5.1%}"
        )
    worst = ", ".join(f"{row['session_id'][:8]} {_usd(row['extra_dollars'])}" for row in breaks["top_sessions"])
    print(f"    Costliest sessions: {worst}")
    print(f"    {DIM}{rule}{RESET}")


def _print_ttl_what_if(facts: dict[str, Any]) -> None:
    what_if = facts["ttl_what_if"]
    rows = [(scope, what_if[scope]) for scope in ("main", "subagents")]
    rows = [(scope, row) for scope, row in rows if row["writes_5m_tokens"] + row["writes_1h_tokens"]]
    for scope, row in rows:
        even = f"{row['break_even_share']:.1%} break-even on {row['break_even_model']}" if row["break_even_model"] else "no 5m writes"
        print(
            f"  1h TTL what-if, {scope}: {row['write_1h_share']:.0%} of writes already 1h; saves "
            f"{_usd(row['saved_per_30_days'])}, costs {_usd(row['extra_per_30_days'])}, net {_usd(row['net_per_30_days'])} "
            f"per 30 days at list price; idle rebuilds {row['rebuild_share']:.1%} of 5m writes vs {even}: {row['verdict']}"
        )
    if rows:
        print(f"    {DIM}{what_if['formula']}{RESET}")


def _print_compactions(facts: dict[str, Any]) -> None:
    compactions = facts["compactions"]
    if compactions["by_trigger"]:
        counts = ", ".join(f"{row['count']:,} {trigger}" for trigger, row in compactions["by_trigger"].items())
        after = compactions["first_prompt_after_avg"]
        tail = f"; the first request after one averaged {after:,} prompt tokens" if after else ""
        print(f"  Compactions: {counts}{tail} {DIM}(triggers as recorded; manual can include idle compactions){RESET}")
    haiku = facts["haiku_long_prompt"]
    if haiku["requests_over_threshold"]:
        print(
            f"  Haiku 5.5 over {haiku['threshold_tokens']:,} prompt tokens: {haiku['requests_over_threshold']:,} of "
            f"{haiku['haiku_requests']:,} requests paid {_usd(haiku['premium_dollars'])} above the base-tier rates "
            f"{DIM}(long-tier price - the same tokens at base rates){RESET}"
        )


def _print_limit_hits(facts: dict[str, Any]) -> None:
    hits = facts["limit_hits"]
    if not hits["total"]:
        print(f"  Limit hits: none {DIM}(rate_limit and billing_error messages in these transcripts){RESET}")
        return
    weeks = ", ".join(f"{week} {count:,}" for week, count in hits["by_week"].items())
    kinds = ", ".join(f"{kind} {count:,}" for kind, count in hits["by_kind"].items())
    print(
        f"  Limit hits: {hits['total']:,} ({weeks}; {kinds}) {DIM}(rate_limit and billing_error messages; "
        f"transcripts past cleanupPeriodDays are gone){RESET}"
    )


def _print_usage_reports(facts: dict[str, Any]) -> None:
    """Render the A1 blocks under the --usage spend table, a few lines each; --json has every row."""
    if "by_class" not in facts:
        return
    for printer in (
        _print_spend_split, _print_agent_split, _print_top_sessions, _print_cost_mode,
        _print_cache_breaks, _print_ttl_what_if, _print_compactions, _print_limit_hits,
    ):
        printer(facts)


# -- Usage reports: attribution, what-if repricing, pace and plan fit [A2] -------
#
# Privacy: on top of the transcript fields named at the top of the --usage
# section, these reports read `agentType` from each subagent's
# agent-<id>.meta.json sidecar (an undocumented on-disk format; never its
# description) and check whether ~/.claude/agents or the project's
# .claude/agents holds a file of that name. Project folders, branch names and
# session ids appear only in your own output; a --history snapshot holds
# aggregates only.

import datetime as _a2_dt  # noqa: E402 -- kept in this section so rate.py stays one file

_A2_BY_KEYS = ("project", "branch", "session", "day", "week", "version", "skill", "mcp", "plugin", "agent")
# The --json key under usage.facts.by for each --by key.
_A2_VIEWS = {
    "project": "projects", "branch": "branches", "session": "sessions", "day": "days", "week": "weeks",
    "version": "versions", "skill": "skills", "mcp": "mcp_servers", "plugin": "plugins", "agent": "agents",
}
# Tags Claude Code writes on the requests it makes while a skill, MCP server,
# plugin or agent is active (undocumented record fields): (field, noun).
_A2_TAGS = {
    "skill": ("attributionSkill", "skill"),
    "mcp": ("attributionMcpServer", "MCP server"),
    "plugin": ("attributionPlugin", "plugin"),
    "agent": ("attributionAgent", "agent"),
}
_A2_UNATTRIBUTED = "unattributed"
_A2_PROMPT_KEYS = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
_A2_WORKTREE_SUFFIX = re.compile(r"--claude-worktrees-.+$")
_A2_DRIVE_LETTER = re.compile(r"[a-z]--")
_A2_SESSION_GAP = 300  # seconds: the 5-minute cache TTL; shorter gaps count as active session time
_A2_PACE_GAP = 3_600  # seconds: gaps under 60 minutes count as active hours
_A2_LONG_PROMPT = 100_000  # a session whose p90 main-thread prompt is over this is flagged
_A2_ROWS = 5  # rows per view in the text report; --json has every row
# Monthly plan prices in USD, the same as docs/pricing-data.md (claude.com/pricing, read 2026-11-01).
_A2_PLAN_PRICES = {"pro": 20, "max": 100, "ultra": 200}
_A2_BUILT_IN_AGENTS = frozenset({"general-purpose", "Explore", "Plan"})
_A2_AGENT_ADVICE = {
    "built-in": "built-in: set CLAUDE_CODE_SUBAGENT_MODEL plus CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1, "
    "or define a same-named agent with model:",
    "fork": "a fork runs on the main conversation's model",
    "custom": "set model: in its frontmatter",
    "not found": "no definition file under ~/.claude/agents or the project's .claude/agents",
    "unknown": "no agent type on disk for these runs",
}
_A2_SNAPSHOT_SCHEMA = 1
_A2_DELTA_KEYS = (
    "requests", "sessions", "cache_hit_ratio", "prompt_p50", "prompt_p90",
    "output_share", "list_price_dollars", "dollars_per_request", "write_1h_share",
)
_A2_NEEDS_USAGE = (
    ("by", "--by"), ("what_if", "--what-if"), ("budget", "--budget"), ("plan", "--plan"), ("history", "--history"),
)
_A2_WHAT_IF_CAVEAT = (
    "Modeled from your own recorded tokens; quality not tested, and a cheaper model that needs retries or more "
    "turns raises the cost per completed task. Each request keeps its recorded text: token counts are scaled by "
    "tokenizer overhead (target / source), while output length, thinking and the cache hit pattern stay as "
    "recorded, though thinking and the minimum cacheable prompt differ by model. A request whose scaled prompt "
    "exceeds the target's context window is not priced."
)


def _a2_by_keys(value: str) -> list[str]:
    """--by: a comma list of views, each kept once."""
    keys = [part.strip().lower() for part in value.split(",") if part.strip()]
    unknown = [key for key in keys if key not in _A2_BY_KEYS]
    if unknown or not keys:
        raise argparse.ArgumentTypeError(
            f"unknown view {','.join(unknown) or value!r}; choose from {','.join(_A2_BY_KEYS)}"
        )
    return list(dict.fromkeys(keys))


def _a2_model_keys(value: str) -> list[str]:
    """--what-if: model keys (haiku-5-5, haiku-5.5) or family names (haiku, sonnet, opus, fable)."""
    keys = []
    for part in value.split(","):
        name = part.strip().lower().replace(".", "-").removeprefix("claude-")
        key = _SUCCESSORS.get(name, name)
        if key not in MODELS:
            raise argparse.ArgumentTypeError(
                f"unknown model {part.strip()!r}; valid: {', '.join([*_SUCCESSORS, *MODELS])}"
            )
        keys.append(key)
    return list(dict.fromkeys(keys))


def _a2_number(kind: type, flag: str, minimum: float) -> Any:
    """An argparse type: a number of `kind` at or above `minimum`."""

    def parse(value: str) -> Any:
        try:
            number = kind(value)
        except ValueError:
            number = None
        if number is None or not math.isfinite(number) or number < minimum:
            raise argparse.ArgumentTypeError(f"{flag} takes a number of {minimum:g} or more, not {value!r}")
        return number

    return parse


def _a2_add_flags(parser: argparse.ArgumentParser) -> None:
    """The --usage report flags, plus the --burn live view."""
    parser.add_argument(
        "--by",
        type=_a2_by_keys,
        metavar="KEYS",
        help=f"With --usage: list-price spend grouped by any of {', '.join(_A2_BY_KEYS)} (a comma list)",
    )
    parser.add_argument(
        "--what-if",
        type=_a2_model_keys,
        dest="what_if",
        metavar="MODEL[,MODEL]",
        help="With --usage: reprice your recorded tokens on other models (modeled, quality not tested)",
    )
    parser.add_argument(
        "--scope",
        choices=("all", "main", "subagents"),
        default="all",
        help="Requests the --what-if table covers (default: all); the grade always uses every request",
    )
    parser.add_argument(
        "--budget",
        type=_a2_number(float, "--budget", 0.01),
        metavar="USD",
        help="With --usage: the date this month's list-price spend crosses USD at the current pace",
    )
    parser.add_argument(
        "--plan",
        choices=tuple(_A2_PLAN_PRICES),
        help="With --usage: list-price spend per 30 days divided by the plan's monthly price",
    )
    parser.add_argument(
        "--history",
        metavar="DIR",
        help="With --usage: save an aggregates-only snapshot in DIR and compare it with the newest earlier one",
    )
    parser.add_argument(
        "--burn",
        nargs="?",
        type=_a2_number(int, "--burn", 1),
        const=60,
        metavar="MINUTES",
        help="Live view of list-price spend in the last MINUTES (default 60); skips the project grade",
    )
    parser.add_argument(
        "--watch",
        type=_a2_number(int, "--watch", 15),
        metavar="SECONDS",
        help="With --burn: redraw every SECONDS (15 or more) until Ctrl+C",
    )


@dataclass(slots=True)
class _A2Priced:
    """One request with its list price, prompt size and time, worked out once."""

    record: _UsageRecord
    key: str | None
    dollars: float
    output_dollars: float
    prompt: int
    epoch: float | None


@dataclass(slots=True)
class _A2Bucket:
    """Requests, list-price dollars and cache reads summed for one row of a view."""

    requests: int = 0
    dollars: float = 0.0
    prompt: int = 0
    cache_read: int = 0

    def add(self, item: _A2Priced) -> None:
        self.requests += 1
        self.dollars += item.dollars
        self.prompt += item.prompt
        self.cache_read += item.record.usage.get("cache_read_input_tokens") or 0

    def row(self, key: str, total: float) -> dict[str, Any]:
        return {
            "key": key,
            "requests": self.requests,
            "dollars": round(self.dollars, 4),
            "share": round(self.dollars / total, 4) if total else 0,
            "cache_hit": round(self.cache_read / self.prompt, 4) if self.prompt else 0,
        }


@dataclass
class _A2Context:
    """What every A2 report reads: the priced requests, their total and the window."""

    priced: list[_A2Priced]
    total: float
    start: float  # epoch seconds where the window, or the transcripts still on disk, begin
    now: _a2_dt.datetime
    projects: dict[Path, str] = field(default_factory=dict)
    names: dict[str, str] = field(default_factory=dict)

    @property
    def days(self) -> float:
        return max(self.now.timestamp() - self.start, 0.0) / 86_400


def _a2_epoch(timestamp: str) -> float | None:
    """Epoch seconds of a transcript timestamp; replacing Z keeps Python 3.10 parsing it."""
    try:
        return _a2_dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _a2_date(epoch: float) -> _a2_dt.date:
    """The local calendar date of an epoch time."""
    return _a2_dt.datetime.fromtimestamp(epoch).date()


def _a2_price_all(records: list[_UsageRecord]) -> list[_A2Priced]:
    """Price every request once, with the same _request_cost the totals use; oldest first."""
    keys: dict[str, str | None] = {}
    priced = []
    for record in records:
        if record.model not in keys:
            keys[record.model] = _model_key(record.model)
        key, usage = keys[record.model], record.usage
        dollars = output_dollars = 0.0
        prompt = sum(usage.get(k) or 0 for k in _A2_PROMPT_KEYS)
        if key is not None:
            dollars, prompt = _request_cost(MODELS[key], usage)
            out_rate = _rates_for_prompt(MODELS[key], prompt)["output"]
            output_dollars = (usage.get("output_tokens") or 0) * out_rate / 1_000_000
        priced.append(_A2Priced(record, key, dollars, output_dollars, prompt, _a2_epoch(record.timestamp)))
    return priced


def _a2_window_start(now: _a2_dt.datetime, days: int, history_start: str) -> float:
    """Where the window begins: `days` back, or later when older transcripts are gone."""
    start = now.timestamp() - days * 86_400
    first = _a2_epoch(history_start) if history_start else None
    return max(start, first) if first is not None else start


def _a2_add_facts(
    facts: dict[str, Any], totals: _UsageTotals, days: int, options: argparse.Namespace | None
) -> None:
    """Add the A2 reports to usage.facts: pace and startup floor always, the rest when asked for."""
    now = _a2_dt.datetime.now()
    priced = _a2_price_all(totals.records)
    total = sum(item.dollars for item in priced)
    ctx = _A2Context(priced, total, _a2_window_start(now, days, totals.history_start), now)
    facts["pace"] = _a2_pace(ctx)
    facts["startup_floor"] = _a2_startup_floor(priced)
    if getattr(options, "by", None):
        facts["by"] = _a2_views(options.by, ctx)
    if getattr(options, "what_if", None):
        facts["what_if"] = _a2_what_if(ctx, options.what_if, getattr(options, "scope", None) or "all")
    if getattr(options, "budget", None):
        facts["pace"]["budget"] = _a2_budget(ctx, facts["pace"]["month_to_date"], options.budget)
    if getattr(options, "plan", None):
        facts["plan_fit"] = _a2_plan_fit(ctx, options.plan)
    if getattr(options, "history", None):
        facts["history"] = _a2_history(Path(options.history).expanduser(), facts, totals, ctx)


# Pace, month to date, budget and plan fit.


def _a2_gaps(epochs: list[float], limit: float) -> float:
    """Seconds between consecutive times, counting only the gaps under `limit`."""
    return sum(gap for gap in (b - a for a, b in zip(epochs, epochs[1:])) if gap < limit)


def _a2_pace(ctx: _A2Context) -> dict[str, Any]:
    """List-price spend per active hour and per calendar day, plus this month to date."""
    hours = _a2_gaps(sorted(item.epoch for item in ctx.priced if item.epoch is not None), _A2_PACE_GAP) / 3_600
    days = ctx.days
    return {
        "active_hours": round(hours, 2),
        "dollars_per_active_hour": round(ctx.total / hours, 4) if hours else None,
        "days": round(days, 2),
        "dollars_per_day": round(ctx.total / days, 4) if days else None,
        "formula": (
            "dollars_per_active_hour = list-price spend / active hours, where active hours = the sum of the gaps "
            "under 60 minutes between consecutive requests, every session and subagent merged in time order; "
            "dollars_per_day = list-price spend / days covered"
        ),
        "month_to_date": _a2_month_to_date(ctx),
    }


def _a2_month_start(now: _a2_dt.datetime) -> _a2_dt.datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _a2_month_to_date(ctx: _A2Context) -> dict[str, Any]:
    """This calendar month's list-price spend, with a linear month-end projection."""
    first = _a2_month_start(ctx.now)
    since = first.timestamp()
    days_in_month = ((first + _a2_dt.timedelta(days=32)).replace(day=1) - first).days
    elapsed = (ctx.now - first).total_seconds() / 86_400
    daily = [0.0] * ctx.now.day
    for item in ctx.priced:
        if item.epoch is not None and item.epoch >= since:
            daily[min(_a2_date(item.epoch).day, ctx.now.day) - 1] += item.dollars
    spend = sum(daily)
    out: dict[str, Any] = {
        "month": first.strftime("%Y-%m"),
        "dollars": round(spend, 4),
        "days_elapsed": round(elapsed, 2),
        "days_in_month": days_in_month,
        "partial": ctx.start > since,
        "projection": None,
    }
    if out["partial"]:
        out["note"] = "the window or the transcripts on disk begin after the 1st, so month to date is incomplete"
    elif sum(1 for dollars in daily if dollars > 0) < 3:
        out["note"] = "a projection needs spend on 3 or more days this month"
    else:
        out["projection"] = _a2_projection(spend, elapsed, days_in_month, daily[:-1])
    return out


def _a2_projection(spend: float, elapsed: float, days_in_month: int, complete: list[float]) -> dict[str, Any]:
    """Month end at the month-to-date daily rate, with a band from the spread of the complete days."""
    rate = spend / elapsed
    band = None
    if len(complete) >= 2:
        mean = sum(complete) / len(complete)
        sd = math.sqrt(sum((day - mean) ** 2 for day in complete) / (len(complete) - 1))
        band = round(sd * math.sqrt(max(days_in_month - elapsed, 0.0)), 4)
    return {
        "dollars_per_day": round(rate, 4),
        "month_end": round(rate * days_in_month, 4),
        "band": band,
        "formula": (
            "month_end = month-to-date spend / days elapsed x days in month; band = +/- the sample SD of the "
            "complete days' spend x sqrt(days left)"
        ),
    }


def _a2_crossed_on(priced: list[_A2Priced], since: float, usd: float) -> str | None:
    """The local date this month's running list-price spend reached `usd`."""
    running = 0.0
    for item in priced:
        if item.epoch is not None and item.epoch >= since:
            running += item.dollars
            if running >= usd:
                return _a2_date(item.epoch).isoformat()
    return None


def _a2_budget(ctx: _A2Context, mtd: dict[str, Any], usd: float) -> dict[str, Any]:
    """When this month's list-price spend crosses `usd`: already, at this pace, or not this month."""
    first = _a2_month_start(ctx.now)
    out: dict[str, Any] = {
        "usd": usd,
        "month": mtd["month"],
        "month_to_date": mtd["dollars"],
        "crossed_on": None,
        "crossing_date": None,
        "note": mtd.get("note"),
    }
    projection = mtd["projection"]
    if mtd["partial"]:
        return out
    if mtd["dollars"] >= usd:
        out["crossed_on"] = _a2_crossed_on(ctx.priced, first.timestamp(), usd)
    elif projection:
        when = first + _a2_dt.timedelta(days=usd / projection["dollars_per_day"])
        if when.month == first.month:
            out["crossing_date"] = when.date().isoformat()
        else:
            out["note"] = f"at this pace the month ends near ${projection['month_end']:,.2f}, under the budget"
        out["formula"] = "crossing date = the 1st + budget / (month-to-date spend / days elapsed) days"
    return out


def _a2_plan_fit(ctx: _A2Context, plan: str) -> dict[str, Any]:
    """List-price spend per 30 days over the plan's monthly price."""
    price = _A2_PLAN_PRICES[plan]
    days = ctx.days
    per_30 = ctx.total * 30 / days if days else 0.0
    return {
        "plan": plan,
        "plan_usd_per_month": price,
        "days": round(days, 2),
        "list_price_dollars": round(ctx.total, 2),
        "list_price_per_30_days": round(per_30, 2),
        "ratio": round(per_30 / price, 3),
        "formula": "ratio = list-price spend x 30 / days covered / plan price per month",
        "meaning": "Above 1, the plan costs less than these tokens at list price; "
        "it says nothing about fitting the plan's usage limits.",
        "scope": "Claude Code transcripts on this machine only. The plan's usage pool is shared with Claude "
        "and Cowork too, and API, Bedrock or Google Cloud users have no plan.",
    }


def _a2_startup_floor(priced: list[_A2Priced]) -> dict[str, Any]:
    """Prompt tokens of each session's first main-thread request, per entrypoint."""
    first: dict[str, _A2Priced] = {}
    for item in priced:
        record = item.record
        if item.prompt > 0 and not record.sidechain and "subagents" not in record.path.parts:
            first.setdefault(record.session_id, item)
    groups: dict[str, list[int]] = {}
    for item in first.values():
        groups.setdefault(str(item.record.meta.get("entrypoint") or "unknown"), []).append(item.prompt)
    rows = [
        {
            "entrypoint": name,
            "sessions": len(prompts),
            "min": min(prompts),
            "p10": _percentile(prompts, 0.1),
            "median": _percentile(prompts, 0.5),
        }
        for name, prompts in sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True)
    ]
    return {
        "rows": rows,
        "basis": "The first request in the window of each main session: it carries the first message, a "
        "resumed session carries its restored context, and a session begun before the window counts from its "
        "first request inside it, so min and p10 are the floor",
        "residual_label": "built-in prompt and tools, MCP tool names and instructions, project CLAUDE.md and "
        "skills, auto memory, git status and the harness",
    }


# --by views. Every view's rows sum to usage.facts.list_price_dollars.


def _a2_group(priced: list[_A2Priced], key_of: Any) -> dict[Any, _A2Bucket]:
    buckets: dict[Any, _A2Bucket] = {}
    for item in priced:
        key = key_of(item)
        if key not in buckets:
            buckets[key] = _A2Bucket()
        buckets[key].add(item)
    return buckets


def _a2_ranked(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: row["dollars"], reverse=True)


def _a2_view_of(rows: list[dict[str, Any]], ctx: _A2Context, **extra: Any) -> dict[str, Any]:
    return {"rows": rows, "total_dollars": round(ctx.total, 4), **extra}


def _a2_views(keys: list[str], ctx: _A2Context) -> dict[str, Any]:
    if {"project", "branch", "session"} & set(keys):
        ctx.projects, ctx.names = _a2_projects(ctx.priced)
    builders = {
        "project": _a2_project_view,
        "branch": _a2_branch_view,
        "session": _a2_session_view,
        "day": _a2_day_view,
        "week": _a2_week_view,
        "version": _a2_version_view,
    }
    return {_A2_VIEWS[key]: builders[key](ctx) if key in builders else _a2_tag_view(key, ctx) for key in keys}


def _a2_project_of(path: Path, root: Path) -> str:
    """Project key: the transcript folder under projects/, worktree folders folded into their repo."""
    try:
        folder = path.relative_to(root).parts[0]
    except (ValueError, IndexError):
        folder = path.parent.name
    folder = _A2_WORKTREE_SUFFIX.sub("", folder)
    # Windows can write both c--Code-x and C--Code-x for one directory.
    return folder[0].upper() + folder[1:] if _A2_DRIVE_LETTER.match(folder) else folder


def _a2_display(cwd: str) -> str:
    """The last two segments of a working directory, with a .claude/worktrees suffix dropped."""
    path = cwd.replace("\\", "/").split("/.claude/worktrees/")[0].rstrip("/")
    return "/".join(path.split("/")[-2:])


def _a2_projects(priced: list[_A2Priced]) -> tuple[dict[Path, str], dict[str, str]]:
    """The project key of each transcript file, and a display name per key from its most common cwd."""
    root = _claude_dir() / "projects"
    keys: dict[Path, str] = {}
    cwds: dict[str, dict[str, int]] = {}
    for item in priced:
        path = item.record.path
        if path not in keys:
            keys[path] = _a2_project_of(path, root)
        cwd = item.record.meta.get("cwd")
        if isinstance(cwd, str):
            counts = cwds.setdefault(keys[path], {})
            counts[cwd] = counts.get(cwd, 0) + 1
    return keys, {key: _a2_display(max(counts, key=counts.__getitem__)) for key, counts in cwds.items()}


def _a2_project_view(ctx: _A2Context) -> dict[str, Any]:
    buckets = _a2_group(ctx.priced, lambda item: ctx.projects[item.record.path])
    rows = [{**bucket.row(key, ctx.total), "label": ctx.names.get(key, key)} for key, bucket in buckets.items()]
    return _a2_view_of(
        _a2_ranked(rows),
        ctx,
        note="key = the transcript folder under projects/, worktree folders folded into their repo; "
        "label = the last two segments of its most common working directory",
    )


def _a2_branch_view(ctx: _A2Context) -> dict[str, Any]:
    def key_of(item: _A2Priced) -> tuple[str, str]:
        return ctx.projects[item.record.path], str(item.record.meta.get("gitBranch") or "(no branch)")

    rows = []
    for (project, branch), bucket in _a2_group(ctx.priced, key_of).items():
        label = f"{ctx.names.get(project, project)} @ {branch}"
        rows.append({**bucket.row(label, ctx.total), "project": project, "branch": branch, "label": label})
    return _a2_view_of(_a2_ranked(rows), ctx)


def _a2_version_view(ctx: _A2Context) -> dict[str, Any]:
    buckets = _a2_group(ctx.priced, lambda item: str(item.record.meta.get("version") or "unknown"))
    return _a2_view_of(_a2_ranked([bucket.row(key, ctx.total) for key, bucket in buckets.items()]), ctx)


def _a2_session_row(session: str, items: list[_A2Priced], ctx: _A2Context) -> dict[str, Any]:
    bucket = _A2Bucket()
    for item in items:
        bucket.add(item)
    main = [item for item in items if not item.record.sidechain] or items
    epochs = sorted(item.epoch for item in items if item.epoch is not None)
    p90 = _percentile([item.prompt for item in main], 0.9)
    project = ctx.projects[main[0].record.path]
    return {
        **bucket.row(session, ctx.total),
        "project": ctx.names.get(project, project),
        "branch": str(main[0].record.meta.get("gitBranch") or ""),
        "start": _a2_date(epochs[0]).isoformat() if epochs else None,
        "active_minutes": round(_a2_gaps(epochs, _A2_SESSION_GAP) / 60),
        "subagent_requests": sum(item.record.sidechain for item in items),
        "output_share": round(sum(i.output_dollars for i in items) / bucket.dollars, 3) if bucket.dollars else 0,
        "p90_prompt": p90,
        "flag": "/clear or /compact" if p90 > _A2_LONG_PROMPT else "",
    }


def _a2_session_view(ctx: _A2Context) -> dict[str, Any]:
    sessions: dict[str, list[_A2Priced]] = {}
    for item in ctx.priced:
        sessions.setdefault(item.record.session_id, []).append(item)
    rows = [_a2_session_row(session, items, ctx) for session, items in sessions.items()]
    return _a2_view_of(
        _a2_ranked(rows),
        ctx,
        note="Subagent requests roll up into the session that started them. active_minutes = the sum of the gaps "
        "under 5 minutes (the cache TTL) between the session's requests; flag = a p90 main-thread prompt over "
        "100,000 tokens",
    )


def _a2_dated(ctx: _A2Context, label_of: Any) -> dict[str, _A2Bucket]:
    """Zero-filled buckets for every local date in the window, keyed by label_of(date)."""
    first, today = _a2_date(ctx.start), ctx.now.date()
    buckets = {label_of(first + _a2_dt.timedelta(days=n)): _A2Bucket() for n in range((today - first).days + 1)}
    for item in ctx.priced:
        key = label_of(_a2_date(item.epoch)) if item.epoch is not None else "unknown"
        buckets.setdefault(key, _A2Bucket()).add(item)
    return buckets


def _a2_day_view(ctx: _A2Context) -> dict[str, Any]:
    rows = [bucket.row(key, ctx.total) for key, bucket in _a2_dated(ctx, _a2_dt.date.isoformat).items()]
    checked = round(ctx.days, 3) >= 14  # --usage 14 can land a float hair under 14.0
    values = [row["dollars"] for row in rows]
    mean = sum(values) / len(values)
    sd = math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))
    for row in rows:
        row["outlier"] = checked and sd > 0 and row["dollars"] > mean + 2 * sd
    return _a2_view_of(
        rows,
        ctx,
        mean_dollars=round(mean, 4),
        sd_dollars=round(sd, 4),
        outliers_checked=checked,
        outlier_rule="heuristic: a day above the mean + 2 SD (population) of the zero-filled daily spend, "
        "checked only when the window has 14 or more days",
    )


def _a2_iso_week(day: _a2_dt.date) -> str:
    year, week, _ = day.isocalendar()
    return f"{year}-W{week:02d}"


def _a2_week_view(ctx: _A2Context) -> dict[str, Any]:
    rows = [bucket.row(key, ctx.total) for key, bucket in _a2_dated(ctx, _a2_iso_week).items()]
    return _a2_view_of(
        rows, ctx, note="ISO weeks start on Monday; plan limits reset on your account's own schedule, not on ISO weeks"
    )


def _a2_tag(item: _A2Priced, field_name: str) -> str:
    value = item.record.meta.get(field_name)
    return value if isinstance(value, str) else (str(value) if value else _A2_UNATTRIBUTED)


def _a2_tag_view(key: str, ctx: _A2Context) -> dict[str, Any]:
    """Requests grouped by one of Claude Code's attribution tags, with coverage and an unattributed row."""
    field_name, noun = _A2_TAGS[key]
    buckets = _a2_group(ctx.priced, lambda item: _a2_tag(item, field_name))
    untagged = buckets.get(_A2_UNATTRIBUTED, _A2Bucket())
    requests = len(ctx.priced)
    tagged = ctx.total - untagged.dollars
    return _a2_view_of(
        _a2_ranked([bucket.row(name, ctx.total) for name, bucket in buckets.items()]),
        ctx,
        label=f"requests Claude Code tagged with each {noun} ({field_name})",
        noun=noun,
        tagged_requests=requests - untagged.requests,
        coverage=round((requests - untagged.requests) / requests, 4) if requests else 0,
        tagged_dollars=round(tagged, 4),
        tagged_share=round(tagged / ctx.total, 4) if ctx.total else 0,
        note=f"A tag marks the requests made while that {noun} was active, whole cached prefix included; it is "
        f"not what the {noun} added. Requests with a missing or empty tag are unattributed.",
    )


# --what-if repricing.


def _a2_scaled(usage: dict[str, Any], factor: float) -> dict[str, Any]:
    """A usage block with every token count times `factor` (the tokenizer ratio)."""
    if factor == 1:
        return usage
    scaled = {k: v * factor if isinstance(v, (int, float)) else v for k, v in usage.items() if k != "cache_creation"}
    split = usage.get("cache_creation")
    if isinstance(split, dict):
        write_1h = split.get("ephemeral_1h_input_tokens") or 0
        scaled["cache_creation"] = {"ephemeral_1h_input_tokens": write_1h * factor}
    return scaled


def _a2_reprice_on(priced: list[_A2Priced], target: str) -> dict[str, Any]:
    """Modeled list price of `priced` on one target model, through _request_cost."""
    model = MODELS[target]
    dollars = no_fit_dollars = 0.0
    no_fit = 0
    for item in priced:
        factor = model["tokenizer_overhead"] / MODELS[item.key]["tokenizer_overhead"]
        if item.prompt * factor > model["context_window"]:
            no_fit += 1
            no_fit_dollars += item.dollars
            continue
        dollars += _request_cost(model, _a2_scaled(item.record.usage, factor))[0]
    return {
        "name": model["name"],
        "dollars": round(dollars, 6),
        "no_fit_requests": no_fit,
        "no_fit_actual_dollars": round(no_fit_dollars, 6),
    }


def _a2_reprice(items: list[_A2Priced], targets: list[str]) -> dict[str, Any]:
    priced = [item for item in items if item.key is not None]
    return {
        "requests": len(priced),
        "unpriced_requests": len(items) - len(priced),
        "actual_dollars": round(sum(item.dollars for item in priced), 6),
        "modeled": {target: _a2_reprice_on(priced, target) for target in targets},
    }


def _a2_agent_type(record: _UsageRecord, sidecars: dict[Path, str]) -> str:
    """A subagent's type: agentType from its meta.json sidecar, else the record's attributionAgent tag."""
    if record.path not in sidecars:
        agent_type = _json_file(record.path.with_name(f"{record.path.stem}.meta.json")).get("agentType")
        sidecars[record.path] = agent_type if isinstance(agent_type, str) else ""
    return sidecars[record.path] or str(record.meta.get("attributionAgent") or "unknown")


def _a2_agent_kind(agent_type: str, cwds: set[str]) -> str:
    """built-in, fork, custom (a definition file exists, or a plugin agent), not found, or unknown."""
    if agent_type in _A2_BUILT_IN_AGENTS:
        return "built-in"
    if agent_type in ("fork", "unknown"):
        return agent_type
    homes = [_claude_dir()] + [Path(cwd) / DOT_CLAUDE for cwd in sorted(cwds)]
    found = ":" in agent_type or any((home / "agents" / f"{agent_type}.md").is_file() for home in homes)
    return "custom" if found else "not found"


def _a2_agent_rows(subagents: list[_A2Priced], targets: list[str]) -> list[dict[str, Any]]:
    sidecars: dict[Path, str] = {}
    groups: dict[str, list[_A2Priced]] = {}
    for item in subagents:
        groups.setdefault(_a2_agent_type(item.record, sidecars), []).append(item)
    rows = []
    for agent_type, items in groups.items():
        cwds = {cwd for item in items if isinstance(cwd := item.record.meta.get("cwd"), str)}
        kind = _a2_agent_kind(agent_type, cwds)
        advice = _A2_AGENT_ADVICE[kind]
        rows.append({"agent_type": agent_type, "kind": kind, "advice": advice, **_a2_reprice(items, targets)})
    return sorted(rows, key=lambda row: row["actual_dollars"], reverse=True)


def _a2_what_if(ctx: _A2Context, targets: list[str], scope: str) -> dict[str, Any]:
    """Actual vs modeled list price per scope; --scope filters this table only, never the grade."""
    groups = {
        "main": [item for item in ctx.priced if not item.record.sidechain],
        "subagents": [item for item in ctx.priced if item.record.sidechain],
        "all": ctx.priced,
    }
    shown = ("main", "subagents", "all") if scope == "all" else (scope,)
    return {
        "targets": [{"key": key, "name": MODELS[key]["name"]} for key in targets],
        "scope": scope,
        "rows": [{"scope": name, **_a2_reprice(groups[name], targets)} for name in shown],
        "by_agent_type": _a2_agent_rows(groups["subagents"], targets) if scope != "main" else [],
        "caveat": _A2_WHAT_IF_CAVEAT,
    }


# --history snapshots: aggregates only, neutral deltas.


def _a2_tool_version() -> str:
    """The --version string, so a snapshot records which claude-rate wrote it."""
    actions = _build_parser()._actions
    return next((version for action in actions if (version := getattr(action, "version", None))), "")


def _a2_snapshot(facts: dict[str, Any], totals: _UsageTotals, ctx: _A2Context) -> dict[str, Any]:
    prompt = totals.fresh + totals.cache_read + totals.cache_write
    write_1h = sum(
        (item.record.usage.get("cache_creation") or {}).get("ephemeral_1h_input_tokens") or 0 for item in ctx.priced
    )
    requests = facts["requests"]
    return {
        "schema_version": _A2_SNAPSHOT_SCHEMA,
        "date": ctx.now.date().isoformat(),
        "tool_version": _a2_tool_version(),
        "pricing_date": _PRICING_VERIFIED_DATE,
        "days": facts["days"],
        "partial": bool(facts.get("history_start")),
        "metrics": {
            "requests": requests,
            "sessions": facts["sessions"],
            "cache_hit_ratio": round(totals.cache_read / prompt, 4) if prompt else 0,
            "prompt_p50": _percentile(totals.prompts, 0.5),
            "prompt_p90": _percentile(totals.prompts, 0.9),
            "output_share": facts["output_share"],
            "list_price_dollars": facts["list_price_dollars"],
            "dollars_per_request": round(facts["list_price_dollars"] / requests, 6) if requests else 0,
            "write_1h_share": round(write_1h / totals.cache_write, 4) if totals.cache_write else 0,
        },
        "model_shares": {row["model"]: row["share"] for row in facts["by_model"]},
    }


def _a2_compare(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Neutral before/after numbers: incomparable on a schema or window change, partial on a softer one."""
    if before.get("schema_version") != after["schema_version"] or before.get("days") != after["days"]:
        return {"status": "incomparable", "reasons": ["a different snapshot schema or --usage window"], "deltas": {}}
    checks = (
        (before.get("partial") or after["partial"], "the transcripts on disk cover less than the window in one"),
        (before.get("pricing_date") != after["pricing_date"], "prices were read on a different date"),
        (before.get("tool_version") != after["tool_version"], "a different claude-rate version wrote one of them"),
    )
    reasons = [text for differs, text in checks if differs]
    old = before.get("metrics") if isinstance(before.get("metrics"), dict) else {}
    deltas = {}
    for key in _A2_DELTA_KEYS:
        was, current = old.get(key), after["metrics"][key]
        if isinstance(was, (int, float)):
            deltas[key] = {"before": was, "after": current, "change": round(current - was, 6)}
    return {"status": "partial" if reasons else "comparable", "reasons": reasons, "deltas": deltas}


def _a2_history(directory: Path, facts: dict[str, Any], totals: _UsageTotals, ctx: _A2Context) -> dict[str, Any]:
    """Write usage-YYYY-MM-DD.json (overwritten the same day) and compare it with the newest earlier one."""
    snapshot = _a2_snapshot(facts, totals, ctx)
    name = f"usage-{snapshot['date']}.json"
    try:
        directory.mkdir(parents=True, exist_ok=True)
        earlier = sorted(path for path in directory.glob("usage-*.json") if path.name < name)
        (directory / name).write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        return {"error": f"could not write a snapshot in {directory}: {exc.strerror or exc}"}
    out: dict[str, Any] = {"file": str(directory / name), "previous": None, "snapshot": snapshot}
    if not earlier:
        return {**out, "status": "first", "reasons": [], "deltas": {}}
    return {**out, "previous": earlier[-1].name, **_a2_compare(_json_file(earlier[-1]), snapshot)}


# Text output: only the reports asked for, about 8 lines each; --json has every row.


def _a2_money(value: float) -> str:
    return f"${value:,.2f}"


def _a2_print_usage(facts: dict[str, Any]) -> None:
    if "pace" not in facts:
        return
    _a2_print_pace(facts["pace"])
    if "plan_fit" in facts:
        _a2_print_plan(facts["plan_fit"])
    _a2_print_floor(facts["startup_floor"])
    if "what_if" in facts:
        _a2_print_what_if(facts["what_if"])
    for view, data in facts.get("by", {}).items():
        printer = _A2_VIEW_PRINTERS.get(view)
        if printer:
            printer(data)
        else:
            _a2_print_table(view, data)
    if "history" in facts:
        _a2_print_history(facts["history"])


def _a2_budget_line(budget: dict[str, Any]) -> str:
    head = f"Budget {_a2_money(budget['usd'])} for {budget['month']}: "
    if budget["crossed_on"] or budget["month_to_date"] >= budget["usd"]:
        return f"{head}crossed on {budget['crossed_on'] or 'a day this month'}"
    if budget["crossing_date"]:
        return f"{head}crosses on {budget['crossing_date']} at this pace (the 1st + budget / daily rate)"
    return head + (budget.get("note") or "not crossed")


def _a2_print_pace(pace: dict[str, Any]) -> None:
    if pace["dollars_per_active_hour"] is not None:
        print(
            f"  Pace: {_a2_money(pace['dollars_per_active_hour'])} per active hour over {pace['active_hours']:,.1f} h "
            f"(gaps under 60 min between requests, all sessions merged); "
            f"{_a2_money(pace['dollars_per_day'])} per calendar day over {pace['days']:g} days"
        )
    mtd = pace["month_to_date"]
    line = f"  Month to date ({mtd['month']}): {_a2_money(mtd['dollars'])} in {mtd['days_elapsed']:g} days"
    projection = mtd["projection"]
    if projection:
        band = f" +/- {_a2_money(projection['band'])}" if projection["band"] is not None else ""
        line += (
            f"; month end {_a2_money(projection['month_end'])}{band} (spend / days elapsed x "
            f"{mtd['days_in_month']} days; +/- sample SD of daily spend x sqrt(days left))"
        )
    else:
        line += f"; {mtd['note']}"
    print(line)
    if "budget" in pace:
        print(f"  {_a2_budget_line(pace['budget'])}")


def _a2_print_plan(fit: dict[str, Any]) -> None:
    price = fit["plan_usd_per_month"]
    print(
        f"  Plan fit ({fit['plan'].title()}, ${price}/month): {_a2_money(fit['list_price_per_30_days'])} list price "
        f"per 30 days / ${price} = {fit['ratio']:g}. {fit['meaning']}"
    )
    print(f"  {DIM}{fit['formula']}, over {fit['days']:g} days. {fit['scope']}{RESET}")


def _a2_print_floor(floor: dict[str, Any]) -> None:
    if not floor["rows"]:
        return
    print("  Startup floor (prompt tokens of each session's first main-thread request):")
    for row in floor["rows"][:3]:
        print(
            f"    {row['entrypoint'][:20]:<20} {row['sessions']:>6,} sessions  min {row['min']:>9,}  "
            f"p10 {row['p10']:>9,}  median {row['median']:>9,}"
        )
    print(f"  {DIM}{floor['basis']}. The floor minus what --user counts is {floor['residual_label']}.{RESET}")


def _a2_no_fit_mark(cell: dict[str, Any]) -> str:
    return "*" if cell["no_fit_requests"] else ""


def _a2_print_what_if(what_if: dict[str, Any]) -> None:
    targets = what_if["targets"]
    print(f"  What-if repricing ({what_if['scope']} requests; modeled from your recorded tokens, quality not tested):")
    print(f"    {'scope':<10} {'actual':>12}" + "".join(f" {target['name']:>13}" for target in targets))
    for row in what_if["rows"]:
        cells = "".join(
            f" {_a2_money(row['modeled'][t['key']]['dollars']) + _a2_no_fit_mark(row['modeled'][t['key']]):>13}"
            for t in targets
        )
        print(f"    {row['scope']:<10} {_a2_money(row['actual_dollars']):>12}{cells}")
    for agent in what_if["by_agent_type"][:2]:
        costs = " or ".join(f"{_a2_money(agent['modeled'][t['key']]['dollars'])} on {t['name']}" for t in targets)
        print(
            f"    {agent['agent_type']} subagents would cost {costs} instead of "
            f"{_a2_money(agent['actual_dollars'])}; {agent['advice']}"
        )
    starred = any(_a2_no_fit_mark(cell) for row in what_if["rows"] for cell in row["modeled"].values())
    note = "* leaves out requests whose scaled prompt exceeds that model's context window. " if starred else ""
    print(f"  {DIM}{note}{what_if['caveat']}{RESET}")


def _a2_print_rows(rows: list[dict[str, Any]], total_rows: int) -> None:
    for row in rows:
        label = str(row.get("label", row["key"]))
        print(
            f"    {label[:34]:<34} {row['requests']:>8,} req  {_a2_money(row['dollars']):>11}  "
            f"{row['share']:>4.0%}  hit {row['cache_hit']:.0%}"
        )
    if total_rows > len(rows):
        print(f"    {DIM}... {total_rows - len(rows)} more row(s) in --json{RESET}")


def _a2_print_table(view: str, data: dict[str, Any]) -> None:
    """projects, branches, versions and the attribution-tag views."""
    if "noun" in data:
        article = "an" if data["noun"][0] in "aeiouAEIOUM" else "a"
        print(
            f"  Requests Claude Code tagged with {article} {data['noun']}: {data['coverage']:.0%} of requests, "
            f"{data['tagged_share']:.0%} of list price:"
        )
    else:
        print(f"  {_A2_TITLES.get(view, view)}:")
    _a2_print_rows(data["rows"][:_A2_ROWS], len(data["rows"]))
    if "noun" in data:
        print(f"  {DIM}{data['note']}{RESET}")


def _a2_print_sessions(data: dict[str, Any]) -> None:
    print("  By session (subagents rolled into their session; active = gaps under 5 min summed):")
    for row in data["rows"][:_A2_ROWS]:
        flag = f"  {YELLOW}p90 over 100K: /clear or /compact{RESET}" if row["flag"] else ""
        print(
            f"    {row['key'][:8]}  {row['project'][:24]:<24} {row['start'] or '':<10} {row['active_minutes']:>5,} min"
            f"  {_a2_money(row['dollars']):>10}  {row['share']:>4.0%}  out {row['output_share']:.0%}"
            f"  p90 {row['p90_prompt']:,}{flag}"
        )
    if len(data["rows"]) > _A2_ROWS:
        print(f"    {DIM}... {len(data['rows']) - _A2_ROWS} more session(s) in --json{RESET}")


def _a2_print_days(data: dict[str, Any]) -> None:
    rows = data["rows"]
    outliers = sum(row["outlier"] for row in rows)
    check = (
        f"{outliers} outlier day(s) above the mean + 2 SD (heuristic)"
        if data["outliers_checked"]
        else "outliers are marked on 14+ day windows only"
    )
    mean = _a2_money(data["mean_dollars"])
    print(f"  By day (local time): mean {mean}/day over {len(rows)} days; {check}. Costliest:")
    for row in _a2_ranked([row for row in rows if row["requests"]])[:_A2_ROWS]:
        mark = f"  {YELLOW}outlier{RESET}" if row["outlier"] else ""
        dollars = _a2_money(row["dollars"])
        print(f"    {row['key']:<12} {row['requests']:>8,} req  {dollars:>11}  {row['share']:>4.0%}{mark}")


def _a2_print_weeks(data: dict[str, Any]) -> None:
    print("  By ISO week (Monday start; plan limits reset on your account's own schedule, not ISO weeks):")
    latest = data["rows"][-_A2_ROWS:]
    _a2_print_rows(latest, len(latest))


_A2_TITLES = {"projects": "By project", "branches": "By branch", "versions": "By Claude Code version"}
_A2_VIEW_PRINTERS ={"sessions": _a2_print_sessions, "days": _a2_print_days, "weeks": _a2_print_weeks}
_A2_DELTA_TEXT = (
    ("requests", "requests", lambda value: f"{value:,}"),
    ("list_price_dollars", "list price", _a2_money),
    ("cache_hit_ratio", "cache hit", lambda value: f"{value:.1%}"),
    ("prompt_p50", "median prompt", lambda value: f"{value:,}"),
    ("output_share", "output share", lambda value: f"{value:.0%}"),
)


def _a2_print_history(history: dict[str, Any]) -> None:
    if "error" in history:
        print(f"  History: {history['error']}")
        return
    head = f"  History: wrote {history['file']}"
    if not history["previous"]:
        print(f"{head}; the first snapshot there, so nothing to compare yet")
        return
    reasons = f": {'; '.join(history['reasons'])}" if history["reasons"] else ""
    print(f"{head}; vs {history['previous']} ({history['status']}{reasons})")
    deltas = history["deltas"]
    parts = [
        f"{label} {show(deltas[key]['before'])} -> {show(deltas[key]['after'])}"
        for key, label, show in _A2_DELTA_TEXT
        if key in deltas
    ]
    if parts:
        print(f"    {', '.join(parts)}")


# --burn: a standalone live view that skips the project grade.


def _a2_burn(minutes: int) -> dict[str, Any]:
    """List-price spend in the last `minutes`, windowed by each request's own time."""
    totals = collect_usage(math.ceil(minutes / 1_440))
    since = time.time() - minutes * 60
    recent = [item for item in _a2_price_all(totals.records) if item.epoch is not None and item.epoch >= since]
    spend = sum(item.dollars for item in recent)
    prompt = sum(item.prompt for item in recent)
    reads = sum(item.record.usage.get("cache_read_input_tokens") or 0 for item in recent)
    models = _a2_group(recent, lambda item: MODELS[item.key]["name"] if item.key else "unpriced")
    sessions = _a2_group(recent, lambda item: item.record.session_id)
    top = max(sessions.items(), key=lambda kv: kv[1].dollars, default=None)
    return {
        "minutes": minutes,
        "requests": len(recent),
        "list_price_dollars": round(spend, 4),
        "dollars_per_hour": round(spend * 60 / minutes, 4),
        "cache_hit": round(reads / prompt, 4) if prompt else 0,
        "by_model": _a2_ranked([bucket.row(name, spend) for name, bucket in models.items()]),
        "costliest_session": {"session": top[0][:8], "dollars": round(top[1].dollars, 4)} if top else None,
    }


def _a2_print_burn(burn: dict[str, Any], json_output: bool) -> None:
    if json_output:
        print(json.dumps({"burn": burn}, indent=2))
        return
    print(f"{BOLD}claude-rate --burn{RESET} {DIM}last {burn['minutes']} min, list price from local transcripts{RESET}")
    if not burn["requests"]:
        print("  No requests in this window.")
        return
    print(
        f"  {_a2_money(burn['list_price_dollars'])} in {burn['minutes']} min = {_a2_money(burn['dollars_per_hour'])}"
        f"/hour; {burn['requests']:,} requests; cache hit {burn['cache_hit']:.1%}"
    )
    for row in burn["by_model"][:4]:
        print(f"    {row['key']:<14} {row['requests']:>7,} requests  {_a2_money(row['dollars']):>10}")
    top = burn["costliest_session"]
    if top:
        print(f"  Costliest session: {top['session']} {_a2_money(top['dollars'])}")
    print(f"  {DIM}List price = API rates for these tokens; on a plan you pay the plan price.{RESET}")


def _a2_enable_vt() -> None:
    """Let a Windows console act on the cursor codes --watch redraws with."""
    if os.name != "nt":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    except (AttributeError, OSError):
        return  # not a console: the screen is not cleared, but every redraw still prints


def _a2_watch(minutes: int, seconds: int, json_output: bool) -> None:
    live = sys.stdout.isatty()
    if live:
        _a2_enable_vt()
    try:
        while True:
            burn = _a2_burn(minutes)
            if live:
                sys.stdout.write("\033[H\033[2J")
            _a2_print_burn(burn, json_output)
            print(f"{DIM}{time.strftime('%H:%M:%S')}: redraws every {seconds}s; Ctrl+C stops{RESET}", flush=True)
            time.sleep(seconds)
    except KeyboardInterrupt:
        print()


def _a2_fail(message: str) -> None:
    print(f"claude-rate: error: {message}", file=sys.stderr)
    sys.exit(2)


def _a2_standalone(args: argparse.Namespace) -> bool:
    """Check the A2 flag combinations; run --burn (with --watch) and return True when it ran."""
    if args.watch is not None and args.burn is None:
        _a2_fail("--watch needs --burn")
    if args.burn is not None:
        if args.watch is None:
            _a2_print_burn(_a2_burn(args.burn), args.json_output)
        else:
            _a2_watch(args.burn, args.watch, args.json_output)
        return True
    needs = [flag for dest, flag in _A2_NEEDS_USAGE if getattr(args, dest) is not None]
    if needs and args.usage is None:
        _a2_fail(f"{', '.join(needs)} {'needs' if len(needs) == 1 else 'need'} --usage")
    if args.scope != "all" and not args.what_if:
        _a2_fail("--scope needs --what-if")
    return False


# -- Usage reports: tool output [A3] ---------------------------------------------
#
# Opt-in: only `--usage --tools` runs this. It is the one usage report that reads
# more than token counts: it reads tool names, tool inputs (commands, file paths,
# URLs) and tool result text from your local transcripts, on this machine only, to
# measure how much each result adds to context. It prints aggregates only: counts,
# estimated tokens, dollars and sanitised labels (a command's first word, plus a
# second word only when it looks like a subcommand; a file's last two path
# segments; a URL's host). No result text or command argument is printed, and none
# is kept once its transcript file has been read.
#
# What the numbers are:
# - Tokens are estimates: characters / 4 times the model's tokenizer_overhead.
#   Images use the patch rule on platform.claude.com/docs/en/build-with-claude/vision
#   ("Resolution and token cost", read 2026-11-03): ceil(width / 28) * ceil(height / 28)
#   visual tokens, capped at 1,568 on the standard tier and 4,784 on the
#   high-resolution tier (Claude 4.7 and later, the models whose tokenizer_overhead is
#   above 1 here). The size comes from the PNG, JPEG or GIF header, never from the
#   length of the base64 text.
# - Carry cost is an upper bound: one cache write of the result at the TTL rate of
#   the request that first carries it, plus a cache read at each later request's
#   cache_hit rate until the next compact_boundary, clamped to what the file was
#   billed for cache reads and writes. It assumes the result stays in context until
#   the compaction, which Claude Code can cut short.
# - A transcript file is its own chain (subagent files are isSidechain and separate
#   from the main session), and a tool_use_id is counted once across all files.
# - bashOutputMaxChars (code.claude.com/docs/en/settings-reference, read 2026-11-03):
#   Claude Code clamps it to 4,000-128,000 characters; unset, a valid Bash or
#   PowerShell result arrives inline up to about 30,000. Past the limit Claude gets a
#   file path plus a preview of up to 2,000 characters (code.claude.com/docs/en/
#   tools-reference, "Output limits", read 2026-11-03).

_TOOL_TOP_N = 5
_REREAD_MIN_CHARS = 400
_WHOLE_FILE_LINES = 500
_IMAGE_TOKEN_CAPS = (1_568, 4_784)
_BASH_CAPS = (10_000, 15_000)
_BASH_PREVIEW_CHARS = 2_000
_BLOB_PREFIX = '{"type":"api-request-blob"'
_TOOL_MARKERS = ('"usage"', '"tool_result"', '"compact_boundary"')
_SHELL_TOOLS = ("Bash", "PowerShell")
_TARGETED_TOOLS = ("Bash", "PowerShell", "Read", "WebFetch")
_EDIT_TOOLS = frozenset(("Edit", "Write", "MultiEdit", "NotebookEdit"))
_SEARCH_COMMANDS = frozenset(("grep", "rg", "egrep", "fgrep", "find", "fd", "ag"))
_SKIP_WORDS = frozenset(("sudo", "time", "env"))
_SETUP_COMMANDS = frozenset(("cd", "export"))
# First words whose arguments are data (text, paths, hosts, credentials), never
# subcommands: their second word is not kept.
_DATA_ARG_COMMANDS = frozenset((
    "echo", "printf", "cat", "head", "tail", "less", "more", "sed", "awk", "grep", "egrep", "fgrep", "rg",
    "find", "ls", "rm", "cp", "mv", "mkdir", "touch", "curl", "wget", "ssh", "scp", "psql", "mysql",
    "mongosh", "sqlite3", "python", "python3", "node", "ruby", "perl", "bash", "sh", "zsh", "xargs", "tee",
))
_SEGMENT_SPLIT = re.compile(r"&&|\|\||[;|\n]")
_ENV_ASSIGN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
_SUBCOMMAND = re.compile(r"[a-z][a-z0-9-]{0,23}")
_COMMAND_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,31}")
_URL_HOST = re.compile(r"[a-z][a-z0-9+.-]*://(?:[^/@?#]*@)?([^/:?#]+)", re.IGNORECASE)
_CANCEL_PHRASES = ("doesn't want to proceed", "user rejected", "interrupted by user", "request interrupted")
_BLOCK_PHRASES = (
    "permission to use", "permission for this", "has been denied", "was denied", "blocked by", "hook error",
)
# Ordered text match for the failures that are not denials or MCP errors.
_FAILURE_RULES = (
    (
        "edit precondition",
        ("has not been read", "modified since", "string to replace not found", "no changes to make", "matches of the string"),
    ),
    (
        "path not found",
        ("no such file", "does not exist", "file not found", "cannot find the path", "enoent", "not a directory"),
    ),
    ("command not found", ("command not found", "is not recognized as")),
    ("timeout", ("timed out", "timeout", "etimedout", "deadline exceeded")),
)
_FAILURE_FIXES = {
    "edit precondition": (
        "Edits failed because the file was not read first, changed after the read, or the match was not "
        "unique: have Claude re-read right before editing and quote a longer, unique old_string."
    ),
    "path not found": (
        "Paths were guessed: list the directory first, or keep a key-file map in CLAUDE.md so Claude "
        "names real paths."
    ),
    "blocked": (
        "A permission rule or hook refused calls and the model retried: allow the safe ones in "
        "permissions.allow, or make the hook's message say what to do instead."
    ),
    "command not found": (
        "Commands that are not installed: name the CLI Claude should use in CLAUDE.md, or install the "
        "missing tool."
    ),
    "timeout": (
        "Long commands hit the foreground timeout: run them in the background, or raise "
        "BASH_DEFAULT_TIMEOUT_MS."
    ),
    "mcp error": (
        "MCP calls failed: check /mcp for a disconnected or unauthenticated server, and drop servers you do not use."
    ),
}
_RUNNER_WORDS = frozenset(
    ("pytest", "vitest", "jest", "mocha", "tsc", "eslint", "ruff", "mypy", "make", "mvn", "gradle", "tox")
)
_RUNNER_LABELS = frozenset((
    "npm test", "npm run", "pnpm test", "pnpm run", "yarn test", "cargo test", "cargo build", "go test",
    "dotnet test", "dotnet build", "uv run",
))
_DUMP_WORDS = frozenset(("cat", "sed", "head", "tail", "less", "more", "type"))


@dataclass(slots=True)
class _ToolCall:
    """One tool_use, reduced to what the audit groups and compares by (never the input itself)."""

    name: str
    group: str
    label: str
    sig: int
    read_key: tuple[str, str, str] | None
    ranged: bool
    search: str | None


@dataclass(slots=True)
class _ToolResult:
    """One tool_result paired with its call. `first` is the index, within its compaction
    segment, of the first request that carries it."""

    call: _ToolCall
    chars: int
    tokens: float
    first: int
    fail: str | None
    empty: bool
    read_note: str | None = None
    whole_file: bool = False
    carry: float = 0.0
    retry_out: float = 0.0


@dataclass(slots=True)
class _Req:
    """One API request as the carry cost sees it: per-1M-token rates and what it billed."""

    write_rate: float
    read_rate: float
    out_rate: float
    out_tokens: int
    prompt: int
    measured: float
    overhead: float


@dataclass
class _ToolChain:
    """Everything one transcript file contributes. Each file is its own chain of requests."""

    sidechain: bool = False
    epoch: int = 0
    measured: float = 0.0
    overhead: float = 1.0
    growth: int = 0
    estimated: float = 0.0
    runs: int = 0
    in_runs: int = 0
    run_sig: int | None = None
    run_len: int = 0
    calls: dict[str, _ToolCall] = field(default_factory=dict)
    reqs: dict[str, _Req] = field(default_factory=dict)
    segment: list[_Req] = field(default_factory=list)
    held: list[_ToolResult] = field(default_factory=list)
    done: list[_ToolResult] = field(default_factory=list)
    last_read: dict[tuple[str, str, str], tuple[int, int]] = field(default_factory=dict)


def _bump(table: dict[Any, list[float]], key: Any, *amounts: float) -> None:
    row = table.setdefault(key, [0.0] * len(amounts))
    for i, amount in enumerate(amounts):
        row[i] += amount


@dataclass
class _ToolAgg:
    """Totals across every transcript file. `stats` holds the small named tallies."""

    seen: set[str] = field(default_factory=set)
    model_keys: dict[str, str | None] = field(default_factory=dict)
    results: int = 0
    tokens: float = 0.0
    carry: float = 0.0
    reads: int = 0
    stubs: int = 0
    cancelled: int = 0
    main_files: int = 0
    subagent_files: int = 0
    clamped_files: int = 0
    runs: int = 0
    in_runs: int = 0
    estimated: float = 0.0
    growth: int = 0
    ratios: list[float] = field(default_factory=list)
    by_tool: dict[str, list[float]] = field(default_factory=dict)
    by_target: dict[str, dict[str, list[float]]] = field(default_factory=dict)
    largest: list[tuple[float, str, float]] = field(default_factory=list)
    stats: dict[str, list[float]] = field(default_factory=dict)

    def model_key(self, model: str) -> str | None:
        if model not in self.model_keys:
            self.model_keys[model] = _model_key(model)
        return self.model_keys[model]

    def stat(self, key: str, width: int = 3) -> list[float]:
        return self.stats.get(key) or [0.0] * width

    def add(self, result: _ToolResult) -> None:
        call = result.call
        self.results += 1
        self.tokens += result.tokens
        self.carry += result.carry
        _bump(self.by_tool, call.group, 1, result.tokens, result.carry)
        name = call.name
        if call.group in _TARGETED_TOOLS:
            _bump(self.by_target.setdefault(call.group, {}), call.label, 1, result.tokens, result.carry)
            name = f"{call.group}: {call.label}"
        item = (result.tokens, name, result.carry)
        if len(self.largest) < _TOOL_TOP_N or item[0] > self.largest[-1][0]:
            self.largest = sorted([*self.largest, item], reverse=True)[:_TOOL_TOP_N]
        self._add_reads(result)
        self._add_shell(result)
        self._add_outcome(result)

    def _add_reads(self, result: _ToolResult) -> None:
        if result.call.read_key is None or result.fail is not None:
            return
        if result.read_note == "stub":
            self.stubs += 1
        elif result.chars > _REREAD_MIN_CHARS:
            self.reads += 1
            if result.read_note:
                _bump(self.stats, f"reread:{result.read_note}", 1, result.tokens, result.carry)
            if result.whole_file:
                _bump(self.stats, "whole_file", 1, result.tokens, result.carry)

    def _add_shell(self, result: _ToolResult) -> None:
        if result.call.group not in _SHELL_TOOLS or result.fail is not None:
            return
        _bump(self.stats, "shell", 1, result.tokens)
        for cap in _BASH_CAPS:
            if result.chars > cap:
                saved = (result.chars - _BASH_PREVIEW_CHARS) / result.chars
                _bump(self.stats, f"cap:{cap}", 1, result.tokens * saved, result.carry * saved)

    def _add_outcome(self, result: _ToolResult) -> None:
        search = result.call.search
        if search:
            _bump(self.stats, f"search:{search}", 1)
        if result.empty:
            _bump(self.stats, f"empty:{search}", 1)
        if result.fail == "cancelled":
            self.cancelled += 1
        elif result.fail:
            _bump(self.stats, f"fail:{result.fail}", 1, result.carry, result.retry_out)

    def add_chain(self, chain: _ToolChain) -> None:
        if chain.sidechain:
            self.subagent_files += 1
        else:
            self.main_files += 1
        self.runs += chain.runs
        self.in_runs += chain.in_runs
        self.estimated += chain.estimated
        self.growth += chain.growth
        if chain.growth:
            self.ratios.append(chain.estimated / chain.growth)


def _command_word(word: str) -> str:
    base = word.replace("\\", "/").rsplit("/", 1)[-1]
    if base.lower().endswith(".exe"):
        base = base[:-4]
    return base if _COMMAND_WORD.fullmatch(base) else "other"


def _command_label(command: str) -> str:
    """A label for a shell command that cannot carry a secret.

    The first real command word, skipping cd and export segments and leading VAR=value,
    sudo, time and env words, plus a second word only when it looks like a subcommand
    ([a-z][a-z0-9-]*) and the command is not one that takes data. Flags, paths, URLs,
    connection strings and every other argument are dropped.
    """
    for segment in _SEGMENT_SPLIT.split(command[:2_000]):
        words = segment.strip().lstrip("({").split()
        while words and (words[0] in _SKIP_WORDS or _ENV_ASSIGN.match(words[0])):
            words = words[1:]
        if not words or words[0] in _SETUP_COMMANDS:
            continue
        first = _command_word(words[0])
        if len(words) > 1 and first.lower() not in _DATA_ARG_COMMANDS and _SUBCOMMAND.fullmatch(words[1]):
            return f"{first} {words[1]}"
        return first
    return "bash"


def _tool_group(name: str) -> str:
    """The tool a result is grouped under: an MCP server's tools collapse to mcp__<server>."""
    parts = name.split("__")
    if len(parts) >= 3 and parts[0] == "mcp":
        return f"mcp__{parts[1]}"
    return "Bash" if name.lower() == "bash" else name


def _path_label(path: Any) -> str:
    """The last two segments of a path, so no home directory or project root prints."""
    if not isinstance(path, str) or not path:
        return "unknown"
    return "/".join(path.replace("\\", "/").rstrip("/").split("/")[-2:])


def _url_host(url: Any) -> str:
    match = _URL_HOST.match(url) if isinstance(url, str) else None
    return match.group(1).lower()[:60] if match else "unknown"


def _make_call(name: str, tool_input: dict[str, Any]) -> _ToolCall:
    group = _tool_group(name)
    label = name
    if group in _SHELL_TOOLS:
        label = _command_label(str(tool_input.get("command") or ""))
    elif group == "Read":
        label = _path_label(tool_input.get("file_path"))
    elif group == "WebFetch":
        label = _url_host(tool_input.get("url"))
    path = tool_input.get("file_path")
    read_key = None
    if group == "Read" and isinstance(path, str):
        read_key = (path.replace("\\", "/"), str(tool_input.get("offset")), str(tool_input.get("limit")))
    search = name if name in ("Grep", "Glob") else None
    if group in _SHELL_TOOLS and label.split(" ", 1)[0] in _SEARCH_COMMANDS:
        search = "shell search"
    return _ToolCall(
        name, group, label, hash((name, json.dumps(tool_input, sort_keys=True, default=str))), read_key,
        tool_input.get("offset") is not None or tool_input.get("limit") is not None, search,
    )


def _jpeg_size(head: bytes) -> tuple[int, int] | None:
    """(width, height) from the first start-of-frame marker of a JPEG, else None."""
    i = 2
    while i + 4 <= len(head) and head[i] == 0xFF:
        marker = head[i + 1]
        if marker == 0xFF:
            i += 1
        elif 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            if i + 9 > len(head):
                return None
            return int.from_bytes(head[i + 7:i + 9], "big"), int.from_bytes(head[i + 5:i + 7], "big")
        else:
            i += 2 + int.from_bytes(head[i + 2:i + 4], "big")
    return None


def _image_size(data: str) -> tuple[int, int] | None:
    """(width, height) of a base64 PNG, JPEG or GIF from its header alone, else None."""
    import base64  # only the image path needs it, so a run without images never loads it

    try:
        head = base64.b64decode(data[:65_536])
    except ValueError:
        return None
    if head[:8] == b"\x89PNG\r\n\x1a\n" and len(head) >= 24:
        return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")
    if head[:3] == b"GIF" and len(head) >= 10:
        return int.from_bytes(head[6:8], "little"), int.from_bytes(head[8:10], "little")
    return _jpeg_size(head) if head[:2] == b"\xff\xd8" else None


def _image_tokens(block: dict[str, Any], cap: int) -> float:
    """Visual tokens of one image block: ceil(w / 28) * ceil(h / 28), capped; the cap when unreadable."""
    source = block.get("source") if isinstance(block.get("source"), dict) else {}
    data = source.get("data")
    size = _image_size(data) if isinstance(data, str) else None
    if size is None or min(size) <= 0:
        return float(cap)
    return float(min(math.ceil(size[0] / 28) * math.ceil(size[1] / 28), cap))


def _flatten_result(content: Any, image_cap: int) -> tuple[str, float]:
    """(text, image tokens) of a tool_result's content, which is a string or a list of blocks."""
    if isinstance(content, str):
        return content, 0.0
    texts: list[str] = []
    images = 0.0
    for part in content if isinstance(content, list) else []:
        if not isinstance(part, dict):
            continue
        if part.get("type") == "text" and isinstance(part.get("text"), str):
            texts.append(part["text"])
        elif part.get("type") == "image":
            images += _image_tokens(part, image_cap)
    return "\n".join(texts), images


def _failure_class(call: _ToolCall, text: str, denial: Any) -> str:
    """Why a call failed: the structural toolDenialKind marker first, then an ordered text match.

    An MCP error is decided before the path and timeout phrases, which MCP servers also use.
    "cancelled" (you rejected or interrupted it) is not a failure and is dropped by the caller.
    """
    if denial in ("permission-rule", "automode-blocked"):
        return "blocked"
    if denial == "user-rejected":
        return "cancelled"
    low = text[:600].lower()
    if any(phrase in low for phrase in _CANCEL_PHRASES):
        return "cancelled"
    if any(phrase in low for phrase in _BLOCK_PHRASES):
        return "blocked"
    if call.group.startswith("mcp__"):
        return "mcp error"
    return next((name for name, phrases in _FAILURE_RULES if any(p in low for p in phrases)), "other")


def _is_empty_search(call: _ToolCall, text: str) -> bool:
    """A search that found nothing: Grep and Glob say so in one short line, a shell search prints nothing."""
    if len(text) > 80:
        return False
    low = text.strip().lower()
    if call.search == "shell search":
        return low in ("", "exit code 1", "(bash completed with no output)")
    return low.startswith(("no matches found", "no files found"))


def _price_request(key: str | None, usage: dict[str, Any]) -> _Req:
    """Rates and measured read+write dollars of one request, priced like _request_cost."""
    out = usage.get("output_tokens") or 0
    reads = usage.get("cache_read_input_tokens") or 0
    writes = usage.get("cache_creation_input_tokens") or 0
    prompt = (usage.get("input_tokens") or 0) + reads + writes
    if key is None:
        return _Req(0.0, 0.0, 0.0, out, prompt, 0.0, 1.0)
    model = MODELS[key]
    rates = _rates_for_prompt(model, prompt)
    split = usage.get("cache_creation") if isinstance(usage.get("cache_creation"), dict) else {}
    write_1h = split.get("ephemeral_1h_input_tokens") or 0
    speed = 2 if usage.get("speed") == "fast" and model.get("fast_mode") else 1
    ttl_rate = rates["cache_1h_write"] if write_1h > 0 and write_1h * 2 >= writes else rates["cache_5m_write"]
    measured = (
        reads * rates["cache_hit"] + (writes - write_1h) * rates["cache_5m_write"] + write_1h * rates["cache_1h_write"]
    ) / 1_000_000 * speed
    return _Req(ttl_rate * speed, rates["cache_hit"] * speed, rates["output"] * speed, out, prompt, measured, model["tokenizer_overhead"])


def _note_request(chain: _ToolChain, agg: _ToolAgg, message: dict[str, Any]) -> None:
    """Add one API request to the chain once per message id; later snapshots only raise its output."""
    message_id, usage, model = message.get("id"), message.get("usage"), message.get("model") or ""
    if not message_id or not isinstance(usage, dict) or model.startswith("<"):
        return
    seen = chain.reqs.get(message_id)
    if seen is not None:
        seen.out_tokens = max(seen.out_tokens, usage.get("output_tokens") or 0)
        return
    req = _price_request(agg.model_key(model), usage)
    chain.reqs[message_id] = req
    chain.segment.append(req)
    chain.measured += req.measured
    chain.overhead = req.overhead


def _forget_reads(chain: _ToolChain, tool_input: dict[str, Any]) -> None:
    """An edit or write of a path makes every earlier read of it stale."""
    path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if isinstance(path, str):
        target = path.replace("\\", "/")
        for key in [key for key in chain.last_read if key[0] == target]:
            del chain.last_read[key]


def _note_call(chain: _ToolChain, block: dict[str, Any]) -> None:
    name, call_id = block.get("name"), block.get("id")
    if not isinstance(name, str) or not isinstance(call_id, str):
        return
    tool_input = block.get("input") if isinstance(block.get("input"), dict) else {}
    if name in _EDIT_TOOLS:
        _forget_reads(chain, tool_input)
    chain.calls[call_id] = _make_call(name, tool_input)


def _note_read(chain: _ToolChain, result: _ToolResult, text: str, record: dict[str, Any]) -> None:
    """Mark a stub, an identical re-read (same range, same text, no edit between) or a whole-file read."""
    unchanged = record.get("toolUseResult")
    marker = isinstance(unchanged, dict) and unchanged.get("type") == "file_unchanged"
    if marker or text[:40].lstrip().lower().startswith("file unchanged"):
        result.read_note = "stub"
        return
    if result.chars <= _REREAD_MIN_CHARS:
        return
    key, digest = result.call.read_key, hash(text)
    prior = chain.last_read.get(key)
    if prior is not None and prior[0] == digest:
        result.read_note = "same context" if prior[1] == chain.epoch else "after compaction"
    chain.last_read[key] = (digest, chain.epoch)
    result.whole_file = not result.call.ranged and text.count("\n") + 1 > _WHOLE_FILE_LINES


def _note_failure_run(chain: _ToolChain, result: _ToolResult) -> None:
    """Count runs of three or more identical failing calls in a row."""
    if result.fail in (None, "cancelled"):
        chain.run_sig, chain.run_len = None, 0
        return
    if result.call.sig == chain.run_sig:
        chain.run_len += 1
    else:
        chain.run_sig, chain.run_len = result.call.sig, 1
    if chain.run_len == 3:
        chain.runs += 1
        chain.in_runs += 3
    elif chain.run_len > 3:
        chain.in_runs += 1


def _note_result(chain: _ToolChain, agg: _ToolAgg, block: dict[str, Any], record: dict[str, Any]) -> None:
    """Pair one tool_result with its tool_use; a tool_use_id is counted once across all files."""
    tool_use_id = block.get("tool_use_id")
    call = chain.calls.pop(tool_use_id, None) if isinstance(tool_use_id, str) else None
    if call is None or tool_use_id in agg.seen:
        return
    agg.seen.add(tool_use_id)
    cap = _IMAGE_TOKEN_CAPS[1] if chain.overhead > 1 else _IMAGE_TOKEN_CAPS[0]
    text, image_tokens = _flatten_result(block.get("content"), cap)
    empty = call.search is not None and _is_empty_search(call, text)
    failed = (bool(block.get("is_error")) or text.startswith("<tool_use_error>")) and not empty
    fail = _failure_class(call, text, record.get("toolDenialKind")) if failed else None
    result = _ToolResult(call, len(text), len(text) / 4 * chain.overhead + image_tokens, len(chain.segment), fail, empty)
    if fail is None and call.read_key is not None:
        _note_read(chain, result, text, record)
    _note_failure_run(chain, result)
    chain.held.append(result)


def _close_segment(chain: _ToolChain) -> None:
    """Price the carry of every result held in this compaction segment, then start a new one.

    A result is written by the first request after it and read by each later request
    in the segment: tokens * (write rate + the read rates of the requests after that one).
    """
    seg = chain.segment
    suffix = [0.0] * (len(seg) + 1)
    for i in range(len(seg) - 1, -1, -1):
        suffix[i] = suffix[i + 1] + seg[i].read_rate
    for result in chain.held:
        if result.first < len(seg):
            req = seg[result.first]
            result.carry = result.tokens * (req.write_rate + suffix[result.first + 1]) / 1_000_000
            result.retry_out = req.out_tokens * req.out_rate / 1_000_000
            if result.first >= 1:
                chain.estimated += result.tokens
    chain.growth += sum(max(0, after.prompt - before.prompt) for before, after in zip(seg, seg[1:]))
    chain.done.extend(chain.held)
    chain.held, chain.segment = [], []


def _finish_chain(chain: _ToolChain, agg: _ToolAgg) -> None:
    """Close the last segment, clamp the file's carry to what it was billed, and fold it into the totals."""
    _close_segment(chain)
    if not chain.done:
        return
    carried = sum(result.carry for result in chain.done)
    if carried > chain.measured:
        scale = chain.measured / carried
        for result in chain.done:
            result.carry *= scale
        agg.clamped_files += 1
    for result in chain.done:
        agg.add(result)
    agg.add_chain(chain)


def _blocks(message: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    """The content blocks of a message that have the given type."""
    content = message.get("content")
    if not isinstance(content, list):
        return []
    return [block for block in content if isinstance(block, dict) and block.get("type") == kind]


def _walk_line(line: str, chain: _ToolChain, agg: _ToolAgg, cutoff: str) -> None:
    """Feed one transcript line to its chain: a request, a tool_use, a tool_result or a compaction."""
    if line.startswith(_BLOB_PREFIX) or not any(marker in line for marker in _TOOL_MARKERS):
        return
    try:
        record = json.loads(line)
    except ValueError:
        return
    if not isinstance(record, dict) or (record.get("timestamp") or cutoff) < cutoff:
        return
    chain.sidechain = chain.sidechain or bool(record.get("isSidechain"))
    kind, message = record.get("type"), record.get("message")
    if kind == "system" and record.get("subtype") == "compact_boundary":
        _close_segment(chain)
        chain.epoch += 1
    elif kind == "assistant" and isinstance(message, dict):
        _note_request(chain, agg, message)
        for block in _blocks(message, "tool_use"):
            _note_call(chain, block)
    elif kind == "user" and isinstance(message, dict):
        for block in _blocks(message, "tool_result"):
            _note_result(chain, agg, block, record)


def _tool_share(part: float, whole: float) -> float:
    return round(part / whole, 3) if whole else 0.0


def _rank(table: dict[str, list[float]], total: float) -> list[dict[str, Any]]:
    """The top rows of a {name: [results, tokens, carry]} table, largest tokens first."""
    ranked = sorted(table.items(), key=lambda item: item[1][1], reverse=True)[:_TOOL_TOP_N]
    return [
        {"name": name, "results": int(row[0]), "tokens": round(row[1]), "share": _tool_share(row[1], total),
         "carry_dollars": round(row[2], 2)}
        for name, row in ranked
    ]


def _shell_targets(agg: _ToolAgg) -> dict[str, list[float]]:
    merged: dict[str, list[float]] = {}
    for tool in _SHELL_TOOLS:
        for label, row in agg.by_target.get(tool, {}).items():
            _bump(merged, label, *row)
    return merged


def _reread_facts(agg: _ToolAgg) -> dict[str, Any]:
    same, after = agg.stat("reread:same context"), agg.stat("reread:after compaction")
    whole = agg.stat("whole_file")
    identical = same[0] + after[0]
    return {
        "reads": agg.reads,
        "identical": int(identical),
        "share": _tool_share(identical, agg.reads),
        "same_context": int(same[0]),
        "after_compaction": int(after[0]),
        "tokens": round(same[1] + after[1]),
        "carry_dollars": round(same[2] + after[2], 2),
        "unchanged_stubs": agg.stubs,
        "whole_file_reads": {"results": int(whole[0]), "tokens": round(whole[1]), "carry_dollars": round(whole[2], 2)},
    }


def _cap_facts(agg: _ToolAgg) -> dict[str, Any]:
    shell = agg.stat("shell", 2)
    caps = []
    for cap in _BASH_CAPS:
        count, tokens, carry = agg.stat(f"cap:{cap}")
        caps.append({
            "cap": cap, "results_over": int(count), "tokens": round(tokens),
            "share_of_bash_tokens": _tool_share(tokens, shell[1]), "carry_dollars": round(carry, 2),
        })
    return {"bash_results": int(shell[0]), "preview_chars": _BASH_PREVIEW_CHARS, "caps": caps}


def _failure_facts(agg: _ToolAgg) -> dict[str, Any]:
    classes = [
        {"class": key[5:], "count": int(row[0]), "carry_dollars": round(row[1], 2),
         "retry_output_dollars": round(row[2], 2), "fix": _FAILURE_FIXES.get(key[5:])}
        for key, row in agg.stats.items() if key.startswith("fail:")
    ]
    classes.sort(key=lambda row: row["count"], reverse=True)
    total = sum(row["count"] for row in classes)
    return {
        "total": total, "share": _tool_share(total, agg.results), "cancelled_dropped": agg.cancelled,
        "classes": classes, "repeat_runs": {"runs": agg.runs, "failures_in_runs": agg.in_runs},
    }


def _search_facts(agg: _ToolAgg) -> dict[str, Any]:
    kinds = sorted(key[7:] for key in agg.stats if key.startswith("search:"))
    by_type = [
        {"type": kind, "searches": int(agg.stat(f"search:{kind}", 1)[0]), "empty": int(agg.stat(f"empty:{kind}", 1)[0])}
        for kind in kinds
    ]
    searches = sum(row["searches"] for row in by_type)
    empty = sum(row["empty"] for row in by_type)
    return {"searches": searches, "empty": empty, "share": _tool_share(empty, searches), "by_type": by_type}


def _calibration_facts(agg: _ToolAgg) -> dict[str, Any]:
    ratios = sorted(agg.ratios)
    return {
        "estimated_tokens": round(agg.estimated),
        "measured_growth_tokens": agg.growth,
        "ratio": round(agg.estimated / agg.growth, 3) if agg.growth else 0.0,
        "median_session_ratio": round(ratios[len(ratios) // 2], 3) if ratios else 0.0,
        "sessions": len(ratios),
    }


def _tool_fixes(facts: dict[str, Any]) -> list[str]:
    """One fix line per kind of finding, chosen from what the tables above show."""
    labels = [row["name"] for row in facts["bash_commands"]]
    firsts = {label.split(" ", 1)[0] for label in labels}
    fixes = []
    if firsts & _RUNNER_WORDS or set(labels) & _RUNNER_LABELS:
        fixes.append(
            "Test and build runners are among your largest Bash results: lower bashOutputMaxChars in settings "
            "so a long log arrives as a file path plus a short preview (the what-if rows show the size), or "
            "trim the output to failures with a hook."
        )
    if firsts & _DUMP_WORDS:
        fixes.append(
            "cat, sed, head and tail dumps put whole file ranges in context: find the lines with grep -n, "
            "then Read with offset and limit."
        )
    mcp = next((row["name"] for row in facts["by_tool"] if row["name"].startswith("mcp__")), None)
    if mcp:
        fixes.append(
            f"{mcp} is among the largest result sources: MAX_MCP_OUTPUT_TOKENS caps each response, "
            "or call the service's CLI or a narrower tool instead."
        )
    if facts["rereads"]["identical"]:
        fixes.append(
            "Identical re-reads: read a file once per context, use offset and limit for the part you need, "
            "and keep a key-file map in CLAUDE.md so files are not reopened after /compact."
        )
    if facts["rereads"]["whole_file_reads"]["results"]:
        fixes.append(f"Whole-file Reads of files over {_WHOLE_FILE_LINES} lines: use offset and limit, or grep -n first.")
    fixes.extend(row["fix"] for row in facts["failures"]["classes"][:2] if row["fix"])
    if facts["empty_searches"]["empty"]:
        fixes.append(
            "Empty searches: give Grep and Glob a path or type filter, or describe the code layout in CLAUDE.md."
        )
    return fixes


def _tool_output_facts(agg: _ToolAgg) -> dict[str, Any]:
    total = agg.tokens
    facts: dict[str, Any] = {
        "files": {"main": agg.main_files, "subagent": agg.subagent_files},
        "results": agg.results,
        "estimated_tokens": round(total),
        "carry_dollars": round(agg.carry, 2),
        "clamped_files": agg.clamped_files,
        "basis": {
            "tokens": "estimate: characters / 4 times the model's tokenizer_overhead; images by 28-pixel patches",
            "carry": "upper bound: one cache write plus a cache read per later request until the next compaction, capped per file",
        },
        "by_tool": _rank(agg.by_tool, total),
        "bash_commands": _rank(_shell_targets(agg), total),
        "read_files": _rank(agg.by_target.get("Read", {}), total),
        "web_domains": _rank(agg.by_target.get("WebFetch", {}), total),
        "largest": [
            {"name": name, "results": 1, "tokens": round(tokens), "share": _tool_share(tokens, total),
             "carry_dollars": round(carry, 2)}
            for tokens, name, carry in agg.largest
        ],
        "rereads": _reread_facts(agg),
        "bash_cap_what_if": _cap_facts(agg),
        "failures": _failure_facts(agg),
        "empty_searches": _search_facts(agg),
        "calibration": _calibration_facts(agg),
    }
    facts["fixes"] = _tool_fixes(facts)
    return facts


def collect_tool_output(days: int) -> dict[str, Any]:
    """Audit the tool results in the last `days` days of transcripts: see the comment above.

    One pass over the same files collect_usage reads (lines that cannot hold a request,
    tool_use, tool_result or compaction are skipped before parsing, and so are the
    api-request-blob lines that re-carry whole request bodies). Returns the facts for
    usage.facts.tool_output.
    """
    agg = _ToolAgg()
    root = _claude_dir() / "projects"
    floor = time.time() - days * 86_400
    cutoff = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(floor))
    for path in sorted(root.rglob("*.jsonl")) if root.is_dir() else []:
        if path.stat().st_mtime < floor:
            continue
        chain = _ToolChain()
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                _walk_line(line, chain, agg, cutoff)
        _finish_chain(chain, agg)
    return _tool_output_facts(agg)


def _fmt_tokens(tokens: float) -> str:
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.1f}M"
    if tokens >= 10_000:
        return f"{tokens / 1_000:.0f}K"
    return f"{tokens:,.0f}"


def _print_tool_rows(title: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    print(f"    {title}")
    for row in rows:
        print(
            f"      {row['name'][:46]:<46} {row['results']:>7,}  ~{_fmt_tokens(row['tokens']):>6} tok  "
            f"{row['share']:>4.0%}  carry <= ${row['carry_dollars']:,.2f}"
        )


def _print_read_lines(rereads: dict[str, Any]) -> None:
    if not rereads["reads"]:
        print(f"    {DIM}Identical re-reads: no Read results over {_REREAD_MIN_CHARS} characters.{RESET}")
        return
    print(
        f"    Identical re-reads: {rereads['identical']:,} of {rereads['reads']:,} reads ({rereads['share']:.1%}) "
        f"repeated an earlier read of the same range with the same text and no edit between"
    )
    print(
        f"      {rereads['same_context']:,} in one context, {rereads['after_compaction']:,} after a compaction; "
        f"~{_fmt_tokens(rereads['tokens'])} tokens, carry <= ${rereads['carry_dollars']:,.2f}"
    )
    if rereads["unchanged_stubs"]:
        print(f"      {DIM}Claude Code already answered {rereads['unchanged_stubs']:,} repeat read(s) with an 'unchanged' stub.{RESET}")
    whole = rereads["whole_file_reads"]
    if whole["results"]:
        print(
            f"    Whole-file Reads of files over {_WHOLE_FILE_LINES} lines: {whole['results']:,} results, "
            f"~{_fmt_tokens(whole['tokens'])} tokens, carry <= ${whole['carry_dollars']:,.2f}"
        )


def _print_cap_lines(caps: dict[str, Any]) -> None:
    if not caps["bash_results"]:
        return
    print(
        f"    {DIM}If bashOutputMaxChars were lower, a result over it would arrive as a file path plus a "
        f"{caps['preview_chars']:,}-character preview (upper bound: assumes the file is never read):{RESET}"
    )
    for row in caps["caps"]:
        print(
            f"      {row['cap']:>6,} chars: {row['results_over']:,} of {caps['bash_results']:,} Bash results over, "
            f"~{_fmt_tokens(row['tokens'])} tokens ({row['share_of_bash_tokens']:.1%} of Bash result tokens), "
            f"carry <= ${row['carry_dollars']:,.2f}"
        )


def _print_failure_lines(failures: dict[str, Any], searches: dict[str, Any]) -> None:
    if failures["total"]:
        dropped = f"; {failures['cancelled_dropped']:,} you cancelled are not counted" if failures["cancelled_dropped"] else ""
        print(f"    Failures: {failures['total']:,} results ({failures['share']:.1%} of all){dropped}")
        for row in failures["classes"]:
            print(
                f"      {row['class']:<18} {row['count']:>6,}  carry <= ${row['carry_dollars']:,.2f}"
                f" + retry output <= ${row['retry_output_dollars']:,.2f}"
            )
        runs = failures["repeat_runs"]
        if runs["runs"]:
            print(f"      {runs['runs']:,} run(s) of 3+ identical failing calls in a row ({runs['failures_in_runs']:,} calls)")
    if searches["searches"]:
        kinds = ", ".join(f"{row['type']} {row['empty']:,} of {row['searches']:,}" for row in searches["by_type"])
        print(f"    Empty searches: {searches['empty']:,} of {searches['searches']:,} ({searches['share']:.1%}): {kinds}")


def _print_tool_output(tools: dict[str, Any], show_fixes: bool) -> None:
    """Render usage.facts.tool_output under the --usage section."""
    print()
    print(
        f"  {BOLD}Tool output{RESET} {DIM}(--tools: tokens are estimates from result text; reads tool names, "
        f"inputs and result text locally, prints aggregates only){RESET}"
    )
    if not tools["results"]:
        print(f"    {DIM}No tool results in this window.{RESET}")
        return
    files = tools["files"]
    print(
        f"    {tools['results']:,} results, ~{_fmt_tokens(tools['estimated_tokens'])} tokens; "
        f"carry cost <= ${tools['carry_dollars']:,.2f} (upper bound, cache-aware)"
    )
    print(
        f"    {DIM}From {files['main']:,} main and {files['subagent']:,} subagent transcript file(s), each its own chain; "
        f"carry resets at every compaction and is capped at each file's billed cache reads and writes "
        f"({tools['clamped_files']:,} file(s) hit the cap).{RESET}"
    )
    _print_tool_rows("By tool (results, ~tokens, share of all result tokens, carry)", tools["by_tool"])
    _print_tool_rows("Top Bash commands", tools["bash_commands"])
    _print_tool_rows("Largest single results", tools["largest"])
    _print_read_lines(tools["rereads"])
    _print_cap_lines(tools["bash_cap_what_if"])
    _print_failure_lines(tools["failures"], tools["empty_searches"])
    calibration = tools["calibration"]
    if calibration["sessions"]:
        print(
            f"    {DIM}Check: estimated result tokens are {calibration['ratio']:.0%} of the measured prompt growth between "
            f"requests (median file {calibration['median_session_ratio']:.0%}); results are only part of that growth, "
            f"so a figure over 100% means the characters / 4 estimate runs high.{RESET}"
        )
    if show_fixes:
        for fix in tools["fixes"]:
            print(f"  {MAGENTA}*{RESET} [Tool output] {fix}")
    elif tools["fixes"]:
        print(f"  {DIM}{len(tools['fixes'])} tool-output suggestion(s) -- add --fix to see them.{RESET}")


# -- Live modes: statusline, transcript pricing, cache guard [C] -----------------
#
# These run inside a live Claude Code session, so each returns before the project
# scan and never raises: a status line that exits non-zero or prints nothing goes
# blank, and a hook's stdout must be one JSON object. They read Claude Code's
# statusLine and hook payloads (model ids, token counts, cache, limit and cost
# fields, ids and paths) and, from transcripts, usage records and prompt ids; never
# message content. Every dollar claude-rate computes here is a list-price estimate
# from MODELS.

_LIMIT_WINDOWS = (("five_hour", "5h", 18_000), ("seven_day", "7d", 604_800))
_HOOK_DEADLINE_S = 3.0
# Starting point to tune, not a measurement: a smaller resume is cheap to re-cache.
_CACHE_GUARD_MIN_TOKENS = 50_000
_TAIL_BYTES = 4 * 1024 * 1024
_TURN_SAMPLE = 10
_STATE_VERSION = 1
_STATE_KEEP_DAYS = 2
_LOCK_WAIT_S = 2.0
_LOCK_STALE_S = 30.0
_PROMPT_ID = re.compile(r'"promptId":\s*"([^"]+)"')
_LIST_PRICE = "list-price estimate"
_SUBSCRIPTION_NOTE = "on a Pro, Max or Ultra plan it is API-equivalent value, not your bill"


def _number(value: Any) -> float | None:
    """A finite number from a payload field, else None (JSON true and false are not numbers)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def _field(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    return value if isinstance(value, dict) else {}


def _span(seconds: float) -> str:
    """A short duration such as 45s, 42m, 1h05m or 2d19h."""
    whole = max(0, int(seconds))
    days, hours, minutes = whole // 86_400, whole // 3_600 % 24, whole // 60 % 60
    if days:
        return f"{days}d{hours}h"
    if hours:
        return f"{hours}h{minutes:02d}m"
    return f"{minutes}m" if minutes else f"{whole}s"


def _short_tokens(tokens: float) -> str:
    if tokens >= 999_500:
        return f"{tokens / 1_000_000:.1f}M"
    return f"{tokens / 1_000:.0f}K" if tokens >= 1_000 else f"{tokens:.0f}"


def _live_usd(dollars: float) -> str:
    return "<$0.01" if 0 < dollars < 0.005 else f"${dollars:,.2f}"


def _paint(text: str, code: str, color: bool) -> str:
    """Wrap text in an ANSI colour when colour is on and a code is given.

    Not the GREEN/YELLOW/RED constants above: those are empty unless stdout is a
    terminal, and Claude Code reads a status line through a pipe.
    """
    return f"\033[{code}m{text}\033[0m" if color and code else text


def _level(value: float, warn: float, alert: float) -> str:
    """ANSI code for a percentage: red from `alert`, yellow from `warn`. Display choices, not measurements."""
    if value >= alert:
        return "31"
    return "33" if value >= warn else ""


def _recache_dollars(model_id: str, tokens: float, ttl: Any, fast: bool) -> float | None:
    """Net list price of re-writing `tokens` to the cache instead of reading them warm.

    tokens x (write rate at the TTL - cache read rate) / 1M from MODELS, with the
    Haiku 5.5 long-prompt tier and the Fast Mode 2x that _request_cost applies.
    None for an unknown model or TTL.
    """
    key = _model_key(model_id)
    write = {"5m": "cache_5m_write", "1h": "cache_1h_write"}.get(ttl) if isinstance(ttl, str) else None
    if key is None or write is None:
        return None
    rates = _rates_for_prompt(MODELS[key], tokens)
    dollars = tokens * (rates[write] - rates["cache_hit"]) / 1_000_000
    return dollars * 2 if fast and MODELS[key]["fast_mode"] else dollars


def _cache_state(cache: dict[str, Any], model_id: str, fast: bool, now: float, color: bool) -> list[str]:
    """'cache warm (1h), cold in 42m' plus 'if cold +$0.35', or 'cache cold' plus the next turn's re-cache."""
    tokens = _number(cache.get("recache_tokens_if_cold"))
    dollars = _recache_dollars(model_id, tokens, cache.get("ttl"), fast) if tokens else None
    if cache.get("warm") is True:
        ttl = cache.get("ttl")
        head = _paint(f"cache warm ({ttl})" if isinstance(ttl, str) else "cache warm", "32", color)
        expires = _number(cache.get("expires_at"))
        if expires is not None and expires > now:
            head += f", cold in {_span(expires - now)}"
        return [head] + ([f"if cold +{_live_usd(dollars)}"] if dollars is not None else [])
    tail = f"next turn re-caches {_short_tokens(tokens)}" if tokens else ""
    if tail and dollars is not None:
        tail += f", +{_live_usd(dollars)}"
    return [_paint("cache cold", "33", color)] + ([tail] if tail else [])


def _miss_text(cache: dict[str, Any]) -> str | None:
    """'misses 2 (last: tools_changed)'; no cause when Claude Code could not name one."""
    misses = _number(cache.get("misses"))
    if not misses:
        return None
    causes = _field(cache, "last_miss_cause").get("causes")
    names = "+".join(str(c) for c in causes) if isinstance(causes, list) else ""
    return f"misses {misses:.0f} (last: {names})" if names else f"misses {misses:.0f}"


def _cache_segment(cache: dict[str, Any], model_id: str, fast: bool, now: float, color: bool) -> str:
    if cache.get("caching_observed") is False:
        return "cache off (no cache tokens reported)"
    parts = _cache_state(cache, model_id, fast, now, color)
    hit = _number(cache.get("hit_ratio"))
    if hit is not None:
        parts.append(f"hit {hit:.0%}")
    miss = _miss_text(cache)
    if miss:
        parts.append(miss)
    return " | ".join(parts)


def _head_segments(payload: dict[str, Any], color: bool) -> list[str]:
    """Model with effort and a fast tag, context fill, and Claude Code's own session cost estimate."""
    model = _field(payload, "model")
    name = " ".join(str(p) for p in (model.get("display_name") or model.get("id") or "Claude", _field(payload, "effort").get("level")) if p)
    if payload.get("fast_mode") is True:
        name += " fast"
    used = _number(_field(payload, "context_window").get("used_percentage"))
    parts = [name, _paint(f"ctx {used:.0f}%", _level(used, 60, 80), color) if used is not None else "ctx --"]
    dollars = _number(_field(payload, "cost").get("total_cost_usd"))
    if dollars is not None:
        parts.append(f"{_live_usd(dollars)} est")
    return parts


def _clean_percent(value: Any) -> float | None:
    """A rate-limit used_percentage, or None when it cannot be one.

    Over 101 is invalid (Claude-Code-Usage-Monitor guards the same case: a bad value
    can carry the resets_at epoch); 100 to 101 is clamped to 100.
    """
    pct = _number(value)
    if pct is None or pct < 0 or pct > 101:
        return None
    return min(pct, 100.0)


def _limit_segment(window: Any, label: str, length: int, now: float, color: bool) -> str | None:
    """'5h 62% (+12) resets 1h40m': used share, pace against an even burn, and the reset.

    Pace is used% minus the elapsed share of the window. When the current rate uses
    the rest before the reset, 'out 50m' is the run-out time, elapsed x (100 - used)
    / used, computed fresh on each run with no state file. A window whose resets_at
    has passed is skipped.
    """
    if not isinstance(window, dict):
        return None
    used = _clean_percent(window.get("used_percentage"))
    resets = _number(window.get("resets_at"))
    if used is None or resets is None or now >= resets:
        return None
    left = resets - now
    elapsed = min(float(length), max(0.0, length - left))
    note = f"{used - elapsed / length * 100:+.0f}"
    if used >= 100:
        note = "at limit"
    elif used > 0 and elapsed > 0 and elapsed * (100 - used) / used < left:
        note += f", out {_span(elapsed * (100 - used) / used)}"
    return _paint(f"{label} {used:.0f}% ({note}) resets {_span(left)}", _level(used, 75, 90), color)


def _spend_segment(spend: Any, now: float) -> str | None:
    """'spend $314.12/$500.00 monthly', or 'spend 63%' until the dollar fields arrive. No pace."""
    if not isinstance(spend, dict):
        return None
    resets = _number(spend.get("resets_at"))
    if resets is not None and now >= resets:
        return None
    used, limit = _number(spend.get("used_usd")), _number(spend.get("limit_usd"))
    period = spend.get("period") if isinstance(spend.get("period"), str) else ""
    if used is not None and limit:
        return f"spend {_live_usd(used)}/{_live_usd(limit)} {period}".rstrip()
    pct = _number(spend.get("used_percentage"))
    return f"spend {pct:.0f}%" if pct is not None and pct >= 0 else None


def _limit_segments(limits: Any, now: float, color: bool) -> list[str]:
    if not isinstance(limits, dict):
        return []
    parts = [_limit_segment(limits.get(key), label, length, now, color) for key, label, length in _LIMIT_WINDOWS]
    parts.append(_spend_segment(limits.get("spend_limit"), now))
    return [part for part in parts if part]


def format_statusline(payload: dict[str, Any], now: float, color: bool | None = None) -> str:
    """At most two status-line rows from Claude Code's statusLine JSON (code.claude.com/docs/en/statusline).

    Row 1: model, effort and fast tag, context fill, Claude Code's own session cost
    estimate (cost.total_cost_usd) and the rate-limit windows. Row 2, once the
    payload has prompt_cache (v2.1.251+): cache state and countdown, the net list
    price of letting it go cold, hit ratio and misses. `now` is epoch seconds,
    passed in so tests can fix it; colour is on unless NO_COLOR is set.
    """
    if color is None:
        color = not os.environ.get("NO_COLOR")
    rows = [" | ".join(_head_segments(payload, color) + _limit_segments(payload.get("rate_limits"), now, color))]
    cache = payload.get("prompt_cache")
    if isinstance(cache, dict):
        model_id = str(_field(payload, "model").get("id") or "")
        rows.append(_cache_segment(cache, model_id, payload.get("fast_mode") is True, now, color))
    return "\n".join(rows)


def _stdin_json() -> dict[str, Any]:
    """The JSON object on stdin, read as UTF-8 whatever the console code page; {} for any other JSON."""
    data = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace") or "{}")
    return data if isinstance(data, dict) else {}


def _run_statusline() -> int:
    """--statusline: print the rows and exit 0 whatever the input, so the status line never blanks."""
    if sys.stdin is None or sys.stdin.isatty():
        print("claude-rate --statusline reads Claude Code's statusLine JSON on stdin; "
              "templates/settings/statusline.json shows how to wire it.")
        return 0
    try:
        print(format_statusline(_stdin_json(), time.time()))
    except Exception:  # outer boundary: a status line must print something and exit 0
        print("claude-rate: no status data")
    return 0


def _session_files(path: Path) -> tuple[Path, list[Path]]:
    """The session's main transcript, then every transcript under <session>/subagents/.

    Subagent and workflow transcripts live in that folder beside <session>.jsonl; a
    path inside it is mapped back to its session's main transcript.
    """
    parts = path.parts
    if "subagents" in parts[1:]:
        cut = len(parts) - 1 - parts[::-1].index("subagents")
        session_dir = Path(*parts[:cut])
        path = session_dir.parent / f"{session_dir.name}.jsonl"
    side = path.parent / path.stem / "subagents"
    return path, [path, *(sorted(side.rglob("*.jsonl")) if side.is_dir() else [])]


def _local_day(timestamp: str, today: str) -> str:
    """The local calendar day of a transcript timestamp (written in UTC), else `today`."""
    from datetime import datetime  # local import: only the live modes need it

    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d")
    except ValueError:
        return today


def _empty_state() -> dict[str, Any]:
    return {"version": _STATE_VERSION, "files": {}, "seen": {}, "days": {}, "sessions": {}, "turns": {}}


def _load_state(path: Path) -> dict[str, Any]:
    """The saved pricing state, or an empty one when it is missing, unreadable or another version."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _empty_state()
    if not isinstance(data, dict) or data.get("version") != _STATE_VERSION:
        return _empty_state()
    for key, value in _empty_state().items():
        if not isinstance(data.get(key), type(value)):
            data[key] = value
    return data


def _remove(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass


def _save_state(path: Path, state: dict[str, Any], today: str) -> bool:
    """Drop entries older than _STATE_KEEP_DAYS days, then replace the state file atomically."""
    from datetime import date, timedelta

    floor = (date.fromisoformat(today) - timedelta(days=_STATE_KEEP_DAYS)).isoformat()
    state["seen"] = {day: ids for day, ids in state["seen"].items() if day >= floor}
    state["days"] = {day: total for day, total in state["days"].items() if day >= floor}
    for section in ("files", "sessions", "turns"):
        rows = state[section].items()
        state[section] = {k: v for k, v in rows if isinstance(v, dict) and str(v.get("touched", "")) >= floor}
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        tmp.write_text(json.dumps(state, separators=(",", ":")), encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        _remove(tmp)
        return False
    return True


def _lock_age(lock: Path) -> float:
    try:
        return time.time() - lock.stat().st_mtime
    except OSError:
        return 0.0


def _take_lock(lock: Path) -> bool:
    """Create `lock` exclusively, waiting up to _LOCK_WAIT_S; a lock older than _LOCK_STALE_S is taken over."""
    deadline = time.monotonic() + _LOCK_WAIT_S
    try:
        lock.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False
    while True:
        try:
            os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            return True
        except (FileExistsError, PermissionError):
            if _lock_age(lock) > _LOCK_STALE_S:
                _remove(lock)
                continue
        except OSError:
            return False
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.02)


@dataclass
class _Scan:
    """What one --transcript call updates: the state, this session's row, and today's date."""

    state: dict[str, Any]
    session: dict[str, Any]
    sid: str
    today: str


def _session_row(state: dict[str, Any], sid: str, today: str) -> dict[str, Any]:
    empty = {"dollars": 0.0, "requests": 0, "unpriced": 0, "prompts": 0, "by_model": {}, "first": "", "last": ""}
    row = state["sessions"].setdefault(sid, empty)
    row["touched"] = today
    return row


def _seen(state: dict[str, Any], message_id: str) -> list[Any] | None:
    for ids in state["seen"].values():
        held = ids.get(message_id)
        if held is not None:
            return held
    return None


def _add_dollars(scan: _Scan, record: _UsageRecord, key: str | None, prompt: str, day: str, delta: float) -> None:
    session = scan.session
    session["dollars"] += delta
    if key:
        name = MODELS[key]["name"]
        session["by_model"][name] = session["by_model"].get(name, 0.0) + delta
    if record.timestamp:
        session["first"] = min(session["first"] or record.timestamp, record.timestamp)
        session["last"] = max(session["last"], record.timestamp)
    scan.state["days"][day] = scan.state["days"].get(day, 0.0) + delta
    if prompt:
        turn = scan.state["turns"].setdefault(prompt, {"dollars": 0.0, "session": scan.sid})
        turn["dollars"] += delta
        turn["touched"] = scan.today


def _price_record(scan: _Scan, record: _UsageRecord, prompt: str) -> None:
    """Add one request to the session, day and turn totals, once per message id.

    A message id seen before (a later streamed snapshot of the same response, or
    history a resumed session copied) adds only what its larger snapshot adds.
    """
    out = record.usage.get("output_tokens") or 0
    key = _model_key(record.model)
    dollars = _request_cost(MODELS[key], record.usage)[0] if key else 0.0
    held = _seen(scan.state, record.message_id)
    day = _local_day(record.timestamp, scan.today)
    if held is None:
        scan.state["seen"].setdefault(day, {})[record.message_id] = [dollars, out]
        scan.session["requests" if key else "unpriced"] += 1
        delta = dollars
    elif out > held[1]:
        delta = dollars - held[0]
        held[0], held[1] = dollars, out
    else:
        return
    _add_dollars(scan, record, key, prompt, day, delta)


def _scan_line(scan: _Scan, entry: dict[str, Any], raw: bytes, path: Path, main: bool) -> None:
    """Track the prompt id the line belongs to, and price it when it is a billed request."""
    if b'"promptId"' in raw:
        match = _PROMPT_ID.search(raw.decode("utf-8", errors="replace"))
        if match and match.group(1) != entry.get("prompt"):
            entry["prompt"] = match.group(1)
            scan.session["prompts"] += main
    if b'"usage"' in raw and b'"assistant"' in raw:
        record = _transcript_entry(raw.decode("utf-8", errors="replace"), path)
        if isinstance(record, _UsageRecord):
            _price_record(scan, record, str(entry.get("prompt") or ""))


def _scan_file(scan: _Scan, path: Path, main: bool) -> None:
    """Price the complete lines `path` gained since its saved byte offset.

    The offset only moves past a newline: Claude Code writes transcripts
    asynchronously, so a half-written last line is left for the next call. A file
    shorter than its offset was rewritten and is read again from the start (ids
    already seen still count once).
    """
    entry = scan.state["files"].setdefault(str(path), {"offset": 0, "prompt": ""})
    entry["touched"] = scan.today
    try:
        handle = path.open("rb")
    except OSError:
        return
    with handle:
        size = handle.seek(0, os.SEEK_END)
        offset = entry.get("offset")
        offset = offset if isinstance(offset, int) and 0 <= offset <= size else 0
        handle.seek(offset)
        for raw in handle:
            if not raw.endswith(b"\n"):
                break
            offset += len(raw)
            _scan_line(scan, entry, raw, path, main)
    entry["offset"] = offset


def _scan_session(state: dict[str, Any], main: Path, files: list[Path], today: str) -> None:
    scan = _Scan(state, _session_row(state, main.stem, today), main.stem, today)
    for path in files:
        _scan_file(scan, path, path == main)


def _transcript_json(state: dict[str, Any], main: Path, files: list[Path], today: str, status: str) -> dict[str, Any]:
    session = state["sessions"].get(main.stem, {})
    prompt = str(state["files"].get(str(main), {}).get("prompt") or "")
    turn = state["turns"].get(prompt, {}) if prompt else {}
    by_model = sorted(session.get("by_model", {}).items(), key=lambda kv: -kv[1])
    covers = "this session" if status == "none" else f"every transcript this state file read in the last {_STATE_KEEP_DAYS + 1} days"
    return {
        "transcript": str(main),
        "session_id": main.stem,
        "basis": _LIST_PRICE,
        "found": main.is_file(),
        "files": len(files),
        "dollars": round(session.get("dollars", 0.0), 4),
        "requests": session.get("requests", 0),
        "unpriced": session.get("unpriced", 0),
        "prompts": session.get("prompts", 0),
        "first": session.get("first") or None,
        "last": session.get("last") or None,
        "by_model": {name: round(dollars, 4) for name, dollars in by_model},
        "turn": {"prompt_id": prompt or None, "dollars": round(turn.get("dollars", 0.0), 4)},
        "day": {"date": today, "dollars": round(state["days"].get(today, 0.0), 4), "covers": covers},
        "state": status,
    }


def transcript_report(path: Path, state_path: Path | None = None) -> dict[str, Any]:
    """List-price spend of one session: its transcript plus its subagent transcripts.

    Returns the session total, the current turn (the last prompt id in the main
    transcript) and today's total as plain data. Each message id counts once, at its
    largest usage snapshot, priced by _request_cost. With `state_path`, the byte
    offset of every file, the totals and the seen message ids persist there, so a
    call reads only new bytes, and every session priced with the same state file
    shares one id set and one day total. Parallel callers take turns through a lock
    file; one that cannot get it within _LOCK_WAIT_S gets the last saved totals,
    marked "busy".
    """
    main, files = _session_files(path)
    today = time.strftime("%Y-%m-%d")
    if state_path is None:
        state = _empty_state()
        _scan_session(state, main, files, today)
        return _transcript_json(state, main, files, today, "none")
    lock = state_path.with_name(f"{state_path.name}.lock")
    if not _take_lock(lock):
        return _transcript_json(_load_state(state_path), main, files, today, "busy")
    try:
        state = _load_state(state_path)
        _scan_session(state, main, files, today)
        status = "saved" if _save_state(state_path, state, today) else "unsaved"
    finally:
        _remove(lock)
    return _transcript_json(state, main, files, today, status)


def _run_transcript(path: str, state: str | None) -> int:
    """--transcript: print the session's list-price spend as one JSON object, exit 0."""
    try:
        report = transcript_report(Path(path).expanduser(), Path(state).expanduser() if state else None)
    except Exception as error:  # outer boundary: hooks parse this output, so it is always JSON
        report = {"transcript": path, "basis": _LIST_PRICE, "dollars": 0.0, "error": type(error).__name__}
    print(json.dumps(report))
    return 0


def _ttl_write_key(ttl: Any) -> str:
    return "cache_1h_write" if ttl == "1h" else "cache_5m_write"


def _model_name(model_id: str) -> str:
    key = _model_key(model_id)
    return MODELS[key]["name"] if key else (model_id or "the new model")


def _tail_requests(path: Path) -> list[_UsageRecord]:
    """The last _TURN_SAMPLE main-thread requests in the final _TAIL_BYTES of a transcript."""
    try:
        with path.open("rb") as handle:
            handle.seek(max(0, handle.seek(0, os.SEEK_END) - _TAIL_BYTES))
            lines = handle.read().decode("utf-8", errors="replace").splitlines()
    except OSError:
        return []
    best: dict[str, _UsageRecord] = {}
    for line in lines:
        entry = _transcript_entry(line, path)
        if isinstance(entry, _UsageRecord) and not entry.sidechain:
            _keep_latest(best, entry)
    return sorted(best.values(), key=lambda r: r.timestamp)[-_TURN_SAMPLE:]


def _turn_delta(transcript: Any, from_key: str, to_key: str) -> tuple[float, int] | None:
    """(median list-price change per request on the new model, requests sampled), or None.

    Each recent main-thread request's own usage is priced on both models, so the
    figure assumes the same tokens on both.
    """
    records = _tail_requests(Path(transcript)) if isinstance(transcript, str) and transcript else []
    costs = ((_request_cost(MODELS[to_key], r.usage)[0], _request_cost(MODELS[from_key], r.usage)[0]) for r in records)
    deltas = sorted(to_cost - from_cost for to_cost, from_cost in costs)
    if not deltas:
        return None
    mid = len(deltas) // 2
    return (deltas[mid] if len(deltas) % 2 else (deltas[mid - 1] + deltas[mid]) / 2), len(deltas)


def _switch_cost(payload: dict[str, Any], tokens: float) -> tuple[float, str] | None:
    """The cost of writing the prompt to the new model's cache, and who priced it."""
    estimate = _number(payload.get("estimated_cache_write_usd"))
    bases = {
        "catalog": "Claude Code's list-price estimate",
        "configured": "Claude Code's estimate at your organization's rates",
        "default": "Claude Code's guess: it has no price for this model and assumed a default rate",
    }
    if estimate is not None:
        return estimate, bases.get(str(payload.get("pricing")), "Claude Code's estimate")
    key = _model_key(str(payload.get("to_model") or ""))
    if key is None:
        return None
    rate = _rates_for_prompt(MODELS[key], tokens)[_ttl_write_key(payload.get("cache_ttl"))]
    return tokens * rate / 1_000_000, "claude-rate's list-price estimate"


def _stay_cost(from_key: str | None, tokens: float, warm: bool, ttl: Any) -> float | None:
    """The next request's prompt on the current model: a cache read while warm, a re-write once cold."""
    if from_key is None:
        return None
    rates = _rates_for_prompt(MODELS[from_key], tokens)
    return tokens * rates["cache_hit" if warm else _ttl_write_key(ttl)] / 1_000_000


def _payback_text(payload: dict[str, Any], from_key: str | None, to_key: str | None, extra: float) -> str:
    """The per-request effect from recent turns; a break-even only when the new model is cheaper."""
    sample = _turn_delta(payload.get("transcript_path"), from_key, to_key) if from_key and to_key else None
    if sample is None:
        return ""
    delta, count = sample
    text = f" Requests like your last {count} (same tokens on both models) cost ~{_live_usd(abs(delta))}"
    if delta >= 0:
        return f"{text} more each on {MODELS[to_key]['name']}."
    text += f" less each on {MODELS[to_key]['name']}"
    return f"{text}, so the switch pays back after about {math.ceil(extra / -delta)} of them." if extra > 0 else f"{text}."


def _switch_message(payload: dict[str, Any]) -> str | None:
    """systemMessage for PreModelSwitch: what re-caching costs and how it compares with staying."""
    tokens = _number(payload.get("context_tokens")) or 0.0
    cost = _switch_cost(payload, tokens) if tokens > 0 else None
    if cost is None:
        return None
    from_id, to_id = str(payload.get("from_model") or ""), str(payload.get("to_model") or "")
    from_key, to_key = _model_key(from_id), _model_key(to_id)
    warm = payload.get("prompt_cache_warm") is True
    text = (
        f"[cache-guard] Switching {_model_name(from_id)} to {_model_name(to_id)} re-sends {_short_tokens(tokens)} "
        f"tokens: ~{_live_usd(cost[0])} to write them to the new model's cache ({cost[1]})."
    )
    stay = _stay_cost(from_key, tokens, warm, payload.get("cache_ttl"))
    if stay is not None:
        extra = cost[0] - stay
        action = "read the warm cache" if warm else "re-write the cold cache"
        change = f"adds ~{_live_usd(extra)}" if extra >= 0 else f"saves ~{_live_usd(-extra)}"
        text += f" Staying would {action} for ~{_live_usd(stay)}, so the switch {change}."
        text += _payback_text(payload, from_key, to_key, extra)
    return f"{text} Dollars are list price unless noted; {_SUBSCRIPTION_NOTE}."


def _min_resume_tokens() -> int:
    try:
        return int(os.environ.get("CACHE_GUARD_MIN_TOKENS") or _CACHE_GUARD_MIN_TOKENS)
    except ValueError:
        return _CACHE_GUARD_MIN_TOKENS


def _resume_price(payload: dict[str, Any], tokens: float) -> str:
    estimate = _number(payload.get("estimated_cache_write_usd"))
    if estimate is not None:
        return f", ~{_live_usd(estimate)} (Claude Code's estimate)"
    key = _model_key(str(payload.get("model") or ""))
    if key is None:
        return ""
    rate = _rates_for_prompt(MODELS[key], tokens)["cache_5m_write"]
    return f", ~{_live_usd(tokens * rate / 1_000_000)} (claude-rate's estimate at the 5-minute write rate)"


def _resume_message(payload: dict[str, Any]) -> str | None:
    """systemMessage for SessionStart resume or fork once the prompt cache has likely expired."""
    source = payload.get("source")
    tokens = _number(payload.get("context_tokens")) or 0.0
    expired = payload.get("prompt_cache_likely_expired") is True
    if source not in ("resume", "fork") or not expired or tokens < _min_resume_tokens():
        return None
    idle = _number(payload.get("seconds_since_last_response"))
    when = f" after {_span(idle)}" if idle else ""
    return (
        f"[cache-guard] {'Resuming' if source == 'resume' else 'Forking'}{when}: the prompt cache has likely expired, "
        f"so the first request re-writes {_short_tokens(tokens)} tokens{_resume_price(payload, tokens)}. "
        "If you do not need the old context, /rename this session to find it later, then /clear or start "
        f"a fresh session. List price; {_SUBSCRIPTION_NOTE}."
    )


def cache_guard(payload: dict[str, Any]) -> dict[str, str] | None:
    """The cache-guard hook's output for one payload: {"systemMessage": ...} or None.

    PreModelSwitch prices the switch; SessionStart resume|fork prices a stale
    resume. It never returns permissionDecision: "allow" would skip Claude Code's
    own warm-cache confirmation on /model, and "ask" would repeat it.
    """
    handlers = {"PreModelSwitch": _switch_message, "SessionStart": _resume_message}
    handler = handlers.get(str(payload.get("hook_event_name")))
    message = handler(payload) if handler else None
    return {"systemMessage": message} if message else None


def _run_hook(name: str) -> int:
    """--hook cache-guard: print one JSON object or nothing within _HOOK_DEADLINE_S, then exit 0.

    A PreModelSwitch hook that reaches its timeout blocks the switch, so the work
    runs in a daemon thread that is abandoned at the deadline, not waited on.
    """
    import threading  # local import: only the hook mode needs it

    if sys.stdin is None or sys.stdin.isatty():
        print(f"claude-rate --hook {name} reads a hook payload on stdin; see hooks/cache-guard.sh.", file=sys.stderr)
        return 0
    out: list[str] = []

    def work() -> None:
        try:
            result = cache_guard(_stdin_json())
        except Exception:  # outer boundary: a hook fails open
            return
        if result:
            out.append(json.dumps(result))

    worker = threading.Thread(target=work, daemon=True)
    worker.start()
    worker.join(_HOOK_DEADLINE_S)
    if out:
        print(out[0])
    return 0


# -- Main rate function ------------------------------------------------------

_SCORERS = (
    score_claude_md,
    score_file_read_exclusions,
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

    _, claude_md_chars, _ = _gather_claude_md(project)
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
_PRICING_VERIFIED_DATE = "2026-11-10"


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
    print(
        f"{BOLD}Total:{RESET} {result.score}/{result.max_score}  ({grade_c}{result.grade}{RESET})"
    )
    print()
    print(
        f"{BOLD}Estimated monthly cost{RESET} "
        f"{DIM}(30 turns/session, 3 sessions/day, 22 days; each turn reads the last one from cache){RESET}"
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
    print(
        f"Verified against Anthropic pricing as of: {DIM}{_PRICING_VERIFIED_DATE}{RESET}"
    )
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
            print(
                f"{DIM}Run with --fix to see {unfixed} copy-pasteable fix suggestion(s).{RESET}"
            )

    print()


def _print_scope(scope: ScopeResult, show_fixes: bool) -> None:
    """Render a --user or --usage section: bars, findings, grade, then fixes."""
    print()
    print(f"{BOLD}{scope.name}{RESET}")
    print(f"{DIM}{'-' * 60}{RESET}")
    if not scope.categories:
        return
    _print_category_lines(scope.categories)
    grade_c = grade_ansi(scope.grade)
    print(f"  {BOLD}Score:{RESET} {scope.score}/{scope.max_score}  ({grade_c}{scope.grade}{RESET})")
    startup = scope.facts.get("startup")
    if isinstance(startup, dict) and startup.get("line"):
        print(f"  {DIM}{startup['line']}{RESET}")
    fixes = [(c.name, f) for c in scope.categories for f in c.fixes]
    if show_fixes:
        for name, fix in fixes:
            print(f"  {MAGENTA}*{RESET} [{name}] {fix}")
    elif fixes:
        print(f"  {DIM}{len(fixes)} suggestion(s) -- add --fix to see them.{RESET}")


def _print_usage_facts(facts: dict[str, Any]) -> None:
    """Render list-price spend by model for the --usage section."""
    if not facts.get("requests"):
        print(f"  {DIM}No transcripts found in the last {facts.get('days')} days.{RESET}")
        return
    print(
        f"  {facts['requests']:,} requests in {facts['sessions']:,} session(s) "
        f"({facts['transcript_files']:,} transcript files); "
        f"list-price total ${facts['list_price_dollars']:,.2f}, "
        f"{facts['output_share']:.0%} of it output"
    )
    for row in facts["by_model"][:6]:
        print(f"    {row['model']:<14} {row['requests']:>7,} requests  ${row['dollars']:>10,.2f}  {row['share']:>4.0%}")
    print(
        f"  {DIM}List price = what these tokens cost on the API. On a Pro, Max or Ultra plan you pay the "
        f"plan price; use this to compare models and habits, not as a bill.{RESET}"
    )
    if facts.get("unpriced_requests"):
        listed = ", ".join(f"{row['model']} ({row['requests']:,})" for row in facts.get("unpriced", []))
        print(
            f"  {DIM}{facts['unpriced_requests']:,} request(s) on models without a price row were counted "
            f"but not priced: {listed}.{RESET}"
        )
    if facts.get("history_start"):
        print(
            f"  {DIM}Transcripts on disk start {facts['history_start']}, so this covers less than {facts['days']} days "
            f"(Claude Code deletes transcripts after cleanupPeriodDays, 30 by default).{RESET}"
        )


# -- CLI entry point ---------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="claude-rate",
        description="Rate the cost-efficiency of a Claude / AI setup in a local project directory; "
        "add --user to grade your user-level setup and --usage to grade measured usage.",
        epilog="Source: https://github.com/Sagargupta16/claude-cost-optimizer",
    )
    parser.add_argument(
        "path", nargs="?", default=".", help="Project directory (default: current dir)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Emit machine-readable JSON",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        dest="show_fixes",
        help="Show copy-pasteable fix suggestions",
    )
    parser.add_argument(
        "--strict", action="store_true", help="Exit with status 1 if grade is below B"
    )
    parser.add_argument(
        "--user",
        action="store_true",
        help="Also grade your user-level setup (~/.claude): global instructions, skill "
        "listing, user MCP servers, user settings and Read deny rules",
    )
    parser.add_argument(
        "--usage",
        nargs="?",
        type=int,
        const=_USAGE_DAYS_DEFAULT,
        metavar="DAYS",
        help="Also grade your measured usage from local Claude Code transcripts "
        f"(default: last {_USAGE_DAYS_DEFAULT} days): cache hit rate, context size, "
        "model mix and list-price spend per model",
    )
    # [A2] flags
    _a2_add_flags(parser)

    # [A3] flags
    parser.add_argument(
        "--tools",
        action="store_true",
        help="With --usage, also audit tool output: which tool results fill context and what carrying "
        "them costs (cache-aware, an upper bound). Reads tool names, inputs and result text locally "
        "and prints aggregates only",
    )

    # [B1] flags
    parser.add_argument(
        "--max-context-tokens",
        type=int,
        metavar="N",
        help="Exit with status 1 when the always-loaded instructions are estimated over N tokens: "
        "chars / 4 over CLAUDE.md, .claude/CLAUDE.md, CLAUDE.local.md, .claude/rules files without "
        "paths frontmatter and the files they @import, plus ~/.claude/CLAUDE.md and its unscoped "
        "rules with --user. Ignores the 1.3x tokenizer overhead of 4.7+ models",
    )

    # [C] flags
    parser.add_argument(
        "--statusline",
        action="store_true",
        help="Read Claude Code's statusLine JSON on stdin and print at most two status rows: "
        "context, rate limits, cache countdown and the list price of a cold re-cache",
    )
    parser.add_argument(
        "--transcript",
        metavar="PATH",
        help="Price one session transcript plus its subagent transcripts at list price; prints JSON",
    )
    parser.add_argument(
        "--state",
        metavar="FILE",
        help="With --transcript: keep byte offsets, totals and seen message ids in FILE so each "
        "call reads only new lines; sessions that share FILE share one day total",
    )
    parser.add_argument(
        "--hook",
        choices=["cache-guard"],
        help="Run as a Claude Code hook: cache-guard prices a PreModelSwitch, or a stale "
        "SessionStart resume or fork, from the payload on stdin",
    )

    parser.add_argument("--version", action="version", version="claude-rate 0.4.1")
    return parser


def _emit(result: RateResult, scopes: list[ScopeResult], args: argparse.Namespace) -> None:
    """Print the project grade plus any --user / --usage scopes, as JSON or as a report."""
    if args.json_output:
        payload = result.to_dict()
        payload.update({"user" if s.name.startswith("Your Claude") else "usage": s.to_dict() for s in scopes})
        print(json.dumps(payload, indent=2))
        return
    print_report(result, show_fixes=args.show_fixes)
    for scope in scopes:
        _print_scope(scope, args.show_fixes)
        if "facts" in scope.to_dict() and scope.facts.get("days"):
            _print_usage_facts(scope.facts)
            # [A1] usage printers
            _print_usage_reports(scope.facts)

            # [A2] usage printers
            _a2_print_usage(scope.facts)

            # [A3] usage printers
            if "tool_output" in scope.facts:
                _print_tool_output(scope.facts["tool_output"], args.show_fixes)

    if scopes:
        print()


def main() -> None:
    args = _build_parser().parse_args()
    if args.tools and args.usage is None:
        print(f"{RED}Error:{RESET} --tools needs --usage", file=sys.stderr)
        sys.exit(2)
    # [C] standalone modes: return before the project scan
    if args.statusline:
        sys.exit(_run_statusline())
    if args.transcript:
        sys.exit(_run_transcript(args.transcript, args.state))
    if args.hook:
        sys.exit(_run_hook(args.hook))

    # [A2] standalone modes
    if _a2_standalone(args):
        return

    if not Path(args.path).is_dir():
        print(f"{RED}Error:{RESET} '{args.path}' is not a directory", file=sys.stderr)
        sys.exit(2)
    project = Path(args.path).resolve()

    result = rate(project)
    scopes = []
    if args.user:
        scopes.append(rate_user(project))
    if args.usage is not None:
        scopes.append(rate_usage(max(1, args.usage), args))

    _emit(result, scopes, args)
    # [B1] exit gates
    if args.max_context_tokens is not None and _over_context_budget(project, args.max_context_tokens, args.user):
        sys.exit(1)

    if args.strict and result.grade in ("C", "D", "F"):
        sys.exit(1)


if __name__ == "__main__":
    main()
