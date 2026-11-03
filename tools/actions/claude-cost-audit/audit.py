#!/usr/bin/env python3
"""
Claude Cost Audit -- CI-optimized version

Same analysis as badge-generator/generate.py but designed for GitHub Actions:
  - Always outputs JSON to stdout
  - Sets GITHUB_OUTPUT variables (grade, score, badge_url, context_tokens)
  - Exit code 0 on success, 1 on error or when --max-context-tokens is exceeded

Usage (in a composite action step):
    python audit.py /path/to/project
    python audit.py /path/to/project --max-context-tokens 8000
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

# -- Scoring ------------------------------------------------------------------

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
    "`.claudeignore` is not read by Claude Code -- its permissions docs say the "
    "file has no effect. Move its patterns into permissions.deny as Read(...) rules."
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


# Shared rubric, added 2026-11-03 (settings, env-vars and model-config references,
# read that day): an auto-compact window under the 1,000,000 default (top-level
# autoCompactWindow, a modelSettings entry, or env CLAUDE_CODE_AUTO_COMPACT_WINDOW),
# env MAX_MCP_OUTPUT_TOKENS under its 25,000 default, and env
# CLAUDE_CODE_SUBAGENT_MODEL on haiku or sonnet only with
# CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1 and a family other than the main model's.
# bashOutputMaxChars does not count: the docs frame it as a way to raise the limit.
WINDOW_RANGE = (100_000, 1_000_000)
MCP_OUTPUT_DEFAULT = 25_000
TOKEN_COUNT = re.compile(r"\s*([0-9]+)\s*([kKmM]?)\s*")
TOKEN_SCALE = {"": 1, "k": 1_000, "m": 1_000_000}
# On these providers the `haiku` alias is Haiku 4.5, not Haiku 5.5.
PROVIDER_FLAGS = (
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_FOUNDRY",
    "CLAUDE_CODE_USE_ANTHROPIC_AWS",
    "CLAUDE_CODE_USE_MANTLE",
)
MODEL_FAMILIES = ("haiku", "sonnet", "opus", "fable", "mythos")
DEAD_SUBAGENT_KEY_FINDING = (
    "env CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION does nothing: it was removed in v2.1.224 and is "
    "now a no-op (code.claude.com/docs/en/env-vars, read 2026-11-03). "
    "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS limits how many subagents run at once."
)
HAIKU_WINDOW_FINDING = (
    "model is Haiku 5.5 with no auto-compact window. It auto-compacts at about 967K tokens by "
    "default (code.claude.com/docs/en/model-config, read 2026-11-03), but a request whose prompt "
    "is over 100,000 tokens pays $0.50/$2.50 per 1M on the whole request instead of $0.10/$0.50, "
    "5x. Run /autocompact 100k in a Haiku 5.5 session, or set modelSettings "
    '{"claude-haiku-5-5": {"autoCompactWindow": 100000}}.'
)


def _object(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _setting_tokens(value: object) -> int | None:
    """A token count from a settings key, which takes a JSON number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return int(value)


def _env_tokens(value: object, suffixes: bool = True) -> int | None:
    """A token count from an env value: 200000 or "200000", plus "200k" or "1M" when `suffixes`."""
    if not isinstance(value, str):
        return _setting_tokens(value)
    match = TOKEN_COUNT.fullmatch(value)
    if match is None or (match[2] and not suffixes):
        return None
    return int(match[1]) * TOKEN_SCALE[match[2].lower()]


def _model_family(model: object) -> str | None:
    text = model.lower() if isinstance(model, str) else ""
    return next((family for family in MODEL_FAMILIES if family in text), None)


def _window_set(data: dict) -> bool:
    """An auto-compact window under the 1M default: top-level, per model, or the env variable."""
    low, high = WINDOW_RANGE
    values = [_setting_tokens(data.get("autoCompactWindow"))]
    values += [_setting_tokens(_object(conf).get("autoCompactWindow")) for conf in _object(data.get("modelSettings")).values()]
    values.append(_env_tokens(_object(data.get("env")).get("CLAUDE_CODE_AUTO_COMPACT_WINDOW")))
    return any(value is not None and low <= value < high for value in values)


def _env_controls(data: dict) -> bool:
    """A lower MCP output cap, or a forced subagent model cheaper than the main one."""
    env = _object(data.get("env"))
    mcp_cap = _env_tokens(env.get("MAX_MCP_OUTPUT_TOKENS"), suffixes=False)
    if mcp_cap is not None and 0 < mcp_cap < MCP_OUTPUT_DEFAULT:
        return True
    forced = str(env.get("CLAUDE_CODE_SUBAGENT_MODEL_FORCE", "")).strip() == "1"
    family = _model_family(env.get("CLAUDE_CODE_SUBAGENT_MODEL"))
    return forced and family in ("haiku", "sonnet") and family != _model_family(data.get("model"))


def settings_findings(data: dict) -> list[str]:
    """A dead env key and the Haiku 5.5 price line; neither changes the score."""
    env = _object(data.get("env"))
    findings = [DEAD_SUBAGENT_KEY_FINDING] if "CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION" in env else []
    model = data.get("model")
    name = model.strip().lower() if isinstance(model, str) else ""
    on_provider = any(str(env.get(f, "")).strip().lower() not in ("", "0", "false", "none") for f in PROVIDER_FLAGS)
    on_haiku_5_5 = "haiku-5-5" in name or (name == "haiku" and not on_provider)
    haiku_view = {
        "autoCompactWindow": data.get("autoCompactWindow"),
        "env": env,
        "modelSettings": {m: c for m, c in _object(data.get("modelSettings")).items() if "haiku" in m.lower()},
    }
    if on_haiku_5_5 and not _window_set(haiku_view):
        findings.append(HAIKU_WINDOW_FINDING)
    return findings


def has_cost_controls(data: dict) -> bool:
    """Whether settings.json configures a real spend-bounding setting.

    Kept in step with `_cost_control_signals` in tools/claude-rate/rate.py,
    `has_cost_controls` in tools/badge-generator/generate.py, and
    `computeCostControls` in site/src/utils/repoAnalyzer.ts. This used to test
    budgetCap / costLimit / maxCostPerSession / budget; none of those is in the
    Claude Code settings schema (checked 2026-09-06 against
    https://www.schemastore.org/claude-code-settings.json, 142 top-level
    properties, no spend cap among them), so the audit credited a key the
    product ignores.

    Value-aware on purpose: "fastMode": true doubles the bill and a high
    "effortLevel" raises it, so presence of the key is not enough.
    "alwaysThinkingEnabled": false does not count: it has no effect on Opus 5.5,
    Sonnet 5.5, Haiku 5.5 or the Fable models, which always think
    (code.claude.com/docs/en/settings-reference, read 2026-11-01).
    """
    effort = data.get("effortLevel")
    if isinstance(effort, str) and effort.strip().lower() in ("low", "medium"):
        return True
    cap = data.get("maxEffortLevel")
    if isinstance(cap, str) and cap.strip().lower() in ("low", "medium", "high", "xhigh"):
        return True
    if data.get("fastMode") is False or data.get("fastModePerSessionOptIn") is True:
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
    return _window_set(data) or _env_controls(data)


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
        "findings": settings_findings(data),
    }


def score_mcp(project: Path) -> dict:
    """Score MCP server count from settings.json."""
    path = _resolve_inside(project, SETTINGS_JSON)
    if path is None or not path.is_file():
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


# -- Always-loaded instructions estimate (--max-context-tokens) ---------------
#
# chars / 4 over the files Claude Code loads at launch from the project:
# CLAUDE.md, .claude/CLAUDE.md, CLAUDE.local.md, .claude/rules/ files without
# `paths` frontmatter, and the files they @import, up to four hops
# (code.claude.com/docs/en/memory, read 2026-11-03). The same estimate as
# `claude-rate --max-context-tokens` without --user; it ignores the 1.3x
# tokenizer overhead of 4.7+ models.

INSTRUCTION_FILES = ("CLAUDE.md", ".claude/CLAUDE.md")
LOCAL_INSTRUCTIONS = "CLAUDE.local.md"
IMPORT_HOPS = 4
FENCE = re.compile(r"\s*(```|~~~)")
MD_LINK = re.compile(r"\[[^\]\n]*\]\(([^)\s]+)[^)]*\)")
CODE_SPAN = re.compile(r"`[^`\n]+`")
IMPORT_REF = re.compile(r"(?<!\w)@([^\s`]+)")
URL_SCHEME = re.compile(r"[A-Za-z][\w+.-]*:")


def _checked_ref(ref: str) -> bool:
    """URLs, home or absolute paths, globs, placeholders and variables are not followed."""
    return not (
        not ref
        or URL_SCHEME.match(ref)
        or ref.startswith(("/", "~", "$", "-", "\\"))
        or any(ch in ref for ch in "*?[]{}<>$% \t")
    )


def _unscoped_rules(project: Path) -> list[str]:
    """.claude/rules/ files with no `paths` key in their frontmatter."""
    rules = project / ".claude" / "rules"
    found: list[str] = []
    for rule in sorted(rules.rglob("*.md")) if rules.is_dir() else []:
        lines = rule.read_text(encoding="utf-8", errors="replace").splitlines()
        head: list[str] = []
        if lines and lines[0].strip() == "---":
            end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), len(lines))
            head = lines[1:end]
        if not any(line.startswith("paths:") for line in head):
            found.append(rule.relative_to(project).as_posix())
    return found


def _imports_of(project: Path, name: str) -> list[str]:
    """Files inside the project that one instruction file @imports and that exist."""
    lines = (_read_inside(project, name) or "").splitlines()
    if lines and lines[0].strip() == "---":
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        lines = lines if end is None else lines[end + 1 :]
    base = (project / name).parent
    found: list[str] = []
    fenced = False
    for line in lines:
        if FENCE.match(line):
            fenced = not fenced
            continue
        refs = [] if fenced else IMPORT_REF.findall(CODE_SPAN.sub(" ", MD_LINK.sub(" ", line)))
        for ref in (r.rstrip(".,;:!?)").split("#", 1)[0] for r in refs):
            target = (base / ref).resolve()
            if _checked_ref(ref) and target.is_relative_to(project) and target.is_file():
                found.append(target.relative_to(project).as_posix())
    return found


def always_loaded(project: Path) -> list[tuple[str, int]]:
    """(path, chars) for each always-loaded instruction file, followed imports included."""
    candidates = [*INSTRUCTION_FILES, *_unscoped_rules(project), LOCAL_INSTRUCTIONS]
    names = [name for name in candidates if _read_inside(project, name) is not None]
    seen, frontier = set(names), list(names)
    for _ in range(IMPORT_HOPS):
        frontier = [ref for name in frontier for ref in _imports_of(project, name)]
        frontier = [ref for ref in dict.fromkeys(frontier) if ref not in seen]
        seen.update(frontier)
        names += frontier
    return [(name, len(_read_inside(project, name) or "")) for name in names]


def set_github_output(key: str, value: str) -> None:
    """Append a key=value pair to GITHUB_OUTPUT if running in Actions."""
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(f"{key}={value}\n")


def main() -> None:
    parser = argparse.ArgumentParser(prog="audit.py", description="Claude Cost Audit for CI")
    parser.add_argument("path", help="Project directory to audit")
    parser.add_argument(
        "--max-context-tokens",
        type=int,
        default=0,
        metavar="N",
        help="Exit 1 when the always-loaded instructions estimate is over N tokens (0 = off)",
    )
    args = parser.parse_args()

    project = Path(args.path)
    if not project.is_dir():
        print(f"Error: '{args.path}' is not a directory", file=sys.stderr)
        sys.exit(1)
    project = project.resolve()

    result = audit(project)
    files = always_loaded(project)
    context_tokens = math.ceil(sum(chars for _, chars in files) / 4)
    result["always_loaded"] = {
        "tokens": context_tokens,
        "files": [{"path": name, "tokens": math.ceil(chars / 4)} for name, chars in files],
    }

    # Always output JSON
    print(json.dumps(result, indent=2))

    # Set GitHub Actions outputs
    set_github_output("grade", result["grade"])
    set_github_output("score", str(result["score"]))
    set_github_output("badge_url", result["badge_url"])
    set_github_output("context_tokens", str(context_tokens))

    if args.max_context_tokens > 0 and context_tokens > args.max_context_tokens:
        biggest = sorted(files, key=lambda f: f[1], reverse=True)[:3]
        listed = ", ".join(f"{name} ~{math.ceil(chars / 4):,}" for name, chars in biggest)
        print(
            f"::error::Always-loaded instructions are ~{context_tokens:,} tokens, over "
            f"max-context-tokens {args.max_context_tokens:,}. Largest: {listed}.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
