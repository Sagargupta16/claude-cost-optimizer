#!/usr/bin/env python3
"""Fail when any copy of a per-model rate disagrees with the canonical table.

The rates live in seven code files, because each tool has to run on its own:
claude-rate streams into `python -` with no install, the site bundles its own
TypeScript module, the MCP server and the VS Code extension ship separately,
and the hook is plain shell. check-pricing-sync.py only checks that their
"verified <date>" stamps agree; it says so in its own docstring ("check 1
enforces *agreement* with rate.py, not correctness"). A typo in one copy of a
rate -- $0.02 for $0.20 -- passed CI. This script compares the values.

Canonical sources:

  - Rates: MODELS in tools/claude-rate/rate.py (the same file that holds the
    canonical verified date). Mythos 5.1 and Mythos 5 reuse Fable 5.1 and
    Fable 5 pricing, as rate.py's _PRICE_ALIASES says.
  - Minimum cacheable prompt: MODELS in site/src/utils/pricing.ts, the only
    complete copy of that field; the MCP server's copy must agree with it.
  - Models rate.py does not carry (Opus 4.5, Opus 4.1, Sonnet 4.5, Haiku 3.5,
    Mythos Preview): every copy that has one must agree with every other. A
    model with a single copy has nothing to agree with, so its rates are only
    as good as that copy; the site's vitest suite checks the 1.25x and 2x
    cache-write multipliers on every pricing.ts row.

Copies checked: site/src/utils/pricing.ts, tools/mcp-cost-server/src/index.ts,
tools/vscode-extension/src/costEstimator.ts, tools/token-estimator/estimate.py,
tools/usage-analyzer/analyze.py and hooks/cost-logger.sh. Each file's model
keys are mapped explicitly below, so a model added to a copy without a mapping
fails the check instead of being skipped silently.

Exit 0 when every value agrees, 1 with a per-value report otherwise.
Run from the repo root: python scripts/check-rate-values.py .
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

RATE_PY = Path("tools/claude-rate/rate.py")
PRICING_TS = Path("site/src/utils/pricing.ts")
MCP_TS = Path("tools/mcp-cost-server/src/index.ts")
VSCODE_TS = Path("tools/vscode-extension/src/costEstimator.ts")
ESTIMATE_PY = Path("tools/token-estimator/estimate.py")
ANALYZE_PY = Path("tools/usage-analyzer/analyze.py")
COST_LOGGER = Path("hooks/cost-logger.sh")

# Same price under another name (rate.py _PRICE_ALIASES).
PRICE_ALIASES = {"mythos-5-1": "fable-5-1", "mythos-5": "fable-5"}

# Local key -> canonical key, per file. "@fast" marks a Fast Mode row (2x base).
PRICING_TS_NAMES = {
    "Fable 5.1": "fable-5-1",
    "Fable 5": "fable-5",
    "Opus 5.5": "opus-5-5",
    "Opus 5": "opus-5",
    "Opus 4.8": "opus-4-8",
    "Opus 4.7": "opus-4-7",
    "Opus 4.6": "opus-4-6",
    "Opus 4.5": "opus-4-5",
    "Sonnet 5.5": "sonnet-5-5",
    "Sonnet 5": "sonnet-5",
    "Sonnet 4.6": "sonnet-4-6",
    "Sonnet 4.5": "sonnet-4-5",
    "Haiku 5.5": "haiku-5-5",
    "Haiku 4.5": "haiku-4-5",
    "Mythos 5.1": "mythos-5-1",
    "Mythos 5": "mythos-5",
    "Mythos Preview": "mythos-preview",
}
# The MCP server and the VS Code extension share one key scheme: bare family
# names are the current flagship.
ALIAS_KEYS = {
    "fable": "fable-5-1",
    "fable-5": "fable-5",
    "opus": "opus-5-5",
    "opus-5": "opus-5",
    "opus-4.8": "opus-4-8",
    "opus-4.7": "opus-4-7",
    "opus-4.6": "opus-4-6",
    "sonnet": "sonnet-5-5",
    "sonnet-5": "sonnet-5",
    "sonnet-4.6": "sonnet-4-6",
    "haiku": "haiku-5-5",
    "haiku-4.5": "haiku-4-5",
}
ESTIMATE_KEYS = {
    "fable": "fable-5-1",
    "fable_5": "fable-5",
    "opus": "opus-5-5",
    "opus_5": "opus-5",
    "opus_4_8": "opus-4-8",
    "opus_4_7": "opus-4-7",
    "opus_4_6": "opus-4-6",
    "sonnet": "sonnet-5-5",
    "sonnet_5": "sonnet-5",
    "sonnet_4_6": "sonnet-4-6",
    "haiku": "haiku-5-5",
    "haiku_4_5": "haiku-4-5",
    "mythos": "mythos-5-1",
    "fast_mode": "opus-5-5@fast",
    "fast_mode_opus_5": "opus-5@fast",
}
ANALYZE_KEYS = {
    **ALIAS_KEYS,
    "opus-4.5": "opus-4-5",
    "opus-4.1": "opus-4-1",
    "sonnet-4.5": "sonnet-4-5",
    "haiku-3.5": "haiku-3-5",
}
# Model ids fed through the hook's `case "$MODEL"` patterns, and the model whose
# rates each must land on.
HOOK_PROBES = {
    "opus": "opus-5-5",
    "claude-opus-5-5": "opus-5-5",
    "claude-opus-5": "opus-5",
    "claude-opus-4-8": "opus-4-8",
    "claude-opus-4-6": "opus-4-6",
    "claude-sonnet-5-5": "sonnet-5-5",
    "claude-sonnet-5": "sonnet-5",
    "claude-sonnet-4-6": "sonnet-4-6",
    "claude-sonnet-4-5-20250929": "sonnet-4-5",
    "claude-haiku-5-5": "haiku-5-5",
    "claude-haiku-4-5-20251001": "haiku-4-5",
    "claude-3-5-haiku-20241022": "haiku-3-5",
    "claude-fable-5-1": "fable-5-1",
    "claude-mythos-5-1": "mythos-5-1",
}

RATE_FIELDS = ("input", "output", "cache_hit", "cache_5m_write", "cache_1h_write")
TS_FIELDS = {
    "inputPer1M": "input",
    "outputPer1M": "output",
    "cacheHitPer1M": "cache_hit",
    "cacheWrite5mPer1M": "cache_5m_write",
    "cacheWrite1hPer1M": "cache_1h_write",
    "inputPerMillion": "input",
    "outputPerMillion": "output",
    "cacheHitPerMillion": "cache_hit",
    "cacheHit": "cache_hit",
    "threshold": "threshold",
    "minCacheTokens": "min_cache",
}


@dataclass(frozen=True)
class Value:
    file: Path
    local_key: str
    model: str  # canonical key, possibly with "@fast"
    field: str  # "input", "long_prompt.output", "min_cache", ...
    amount: float | bool


class ParseError(Exception):
    pass


# -- parsing helpers ---------------------------------------------------------


def _assigned_literal(path: Path, name: str, root: Path) -> dict:
    """Evaluate a module-level `name = {...}` dict, resolving string-constant keys."""
    tree = ast.parse((root / path).read_text(encoding="utf-8"))
    constants: dict[str, object] = {}
    for node in tree.body:
        target = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            target, value = node.target, node.value
        if not isinstance(target, ast.Name):
            continue
        if target.id == name:
            return _eval(value, constants)
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            constants[target.id] = value.value
    raise ParseError(f"{path.as_posix()}: no module-level {name} = {{...}}")


def _eval(node: ast.AST, constants: dict[str, object]):
    if isinstance(node, ast.Name) and node.id in constants:
        return constants[node.id]
    if isinstance(node, ast.Dict):
        return {
            _eval(k, constants): _eval(v, constants)
            for k, v in zip(node.keys, node.values)
        }
    return ast.literal_eval(node)


def _ts_object(path: Path, decl: str, root: Path) -> dict:
    """Parse a numbers-only TypeScript object literal (`const decl ... = { ... }`) as JSON."""
    text = (root / path).read_text(encoding="utf-8")
    start = text.find(decl)
    if start < 0:
        raise ParseError(f"{path.as_posix()}: declaration {decl!r} not found")
    open_at = text.find("= {", start)
    if open_at < 0:
        raise ParseError(f"{path.as_posix()}: no object literal after {decl!r}")
    body = "\n".join(
        re.sub(r"//.*$", "", line) for line in text[open_at + 2 :].splitlines()
    )
    depth = 0
    for i, ch in enumerate(body):
        depth += ch == "{"
        depth -= ch == "}"
        if depth == 0:
            literal = body[: i + 1]
            break
    else:
        raise ParseError(f"{path.as_posix()}: unbalanced braces after {decl!r}")
    literal = re.sub(r"(?<=\d)_(?=\d)", "", literal)
    literal = re.sub(r"([{,]\s*)([A-Za-z_][\w]*)\s*:", r'\1"\2":', literal)
    literal = re.sub(r",(\s*[}\]])", r"\1", literal)
    try:
        return json.loads(literal)
    except json.JSONDecodeError as exc:
        raise ParseError(
            f"{path.as_posix()}: {decl} is not a plain object literal ({exc})"
        ) from exc


def _unmapped(path: Path, keys, mapping: dict[str, str]) -> None:
    missing = sorted(set(keys) - set(mapping))
    if missing:
        raise ParseError(
            f"{path.as_posix()}: no canonical mapping for {missing}; add them to check-rate-values.py"
        )


def _row_values(
    path: Path, key: str, model: str, row: dict, fields: dict[str, str]
) -> list[Value]:
    """Values from one row of a dict rate table; a nested dict is its long_prompt block."""
    out = []
    for name, raw in row.items():
        if isinstance(raw, dict):
            out += [
                Value(path, key, model, f"long_prompt.{fields.get(sub, sub)}", val)
                for sub, val in raw.items()
                if isinstance(val, (int, float))
            ]
            continue
        field = fields.get(name, name)
        is_rate = field in RATE_FIELDS or field == "min_cache"
        if is_rate and isinstance(raw, (int, float)) and not isinstance(raw, bool):
            out.append(Value(path, key, model, field, raw))
    return out


def _from_rows(
    path: Path,
    rows: dict,
    mapping: dict[str, str],
    fields: dict[str, str] | None = None,
) -> list[Value]:
    _unmapped(path, rows, mapping)
    return [
        value
        for key, row in rows.items()
        for value in _row_values(path, key, mapping[key], row, fields or {})
    ]


# -- per-file readers --------------------------------------------------------


# pricing.ts is indented two spaces per level: entries at 2, fields at 4,
# longPrompt fields at 6.
_TS_ENTRY = re.compile(r"^ {2}'?([\w-]+)'?: \{\n(.*?)^ {2}\},", re.M | re.S)
_TS_NAME = re.compile(r"^ {4}name: '([^']+)'", re.M)
_TS_LONG_PROMPT = re.compile(r"^ {4}longPrompt: \{\n(.*?)^ {4}\},", re.M | re.S)
_TS_FAST = re.compile(r"^ {4}fastModeCapable: (true|false)", re.M)
_TS_TOP_FIELD = re.compile(r"^ {4}(\w+): ([\d_.]+),", re.M)
_TS_LONG_FIELD = re.compile(r"^ {6}(\w+): ([\d_.]+),", re.M)


def _ts_rates(
    pattern: re.Pattern[str], text: str, local: str, model: str, prefix: str
) -> list[Value]:
    return [
        Value(
            PRICING_TS,
            local,
            model,
            prefix + TS_FIELDS[field],
            float(raw.replace("_", "")),
        )
        for field, raw in pattern.findall(text)
        if field in TS_FIELDS
    ]


def _pricing_entry(local: str, body: str) -> list[Value]:
    name = _TS_NAME.search(body)
    if not name:
        raise ParseError(f"{PRICING_TS.as_posix()}: entry {local!r} has no name")
    if name.group(1) not in PRICING_TS_NAMES:
        raise ParseError(
            f"{PRICING_TS.as_posix()}: no canonical mapping for {name.group(1)!r}; add it to check-rate-values.py"
        )
    model = PRICING_TS_NAMES[name.group(1)]
    long_prompt = _TS_LONG_PROMPT.search(body)
    top = body.replace(long_prompt.group(0), "") if long_prompt else body
    out = _ts_rates(_TS_TOP_FIELD, top, local, model, "")
    fast = _TS_FAST.search(top)
    if fast:
        out.append(
            Value(PRICING_TS, local, model, "fast_mode", fast.group(1) == "true")
        )
    if long_prompt:
        out += _ts_rates(
            _TS_LONG_FIELD, long_prompt.group(1), local, model, "long_prompt."
        )
    return out


def read_pricing_ts(root: Path) -> list[Value]:
    text = (root / PRICING_TS).read_text(encoding="utf-8")
    block = text[text.index("export const MODELS") :]
    out = [
        value
        for match in _TS_ENTRY.finditer(block)
        for value in _pricing_entry(match.group(1), match.group(2))
    ]
    if not out:
        raise ParseError(f"{PRICING_TS.as_posix()}: no MODELS entries parsed")
    return out


def read_mcp(root: Path) -> list[Value]:
    rows = _ts_object(MCP_TS, "const PRICING", root)
    return _from_rows(MCP_TS, rows, ALIAS_KEYS, TS_FIELDS)


def read_vscode(root: Path) -> list[Value]:
    base = _ts_object(VSCODE_TS, "export const PRICING", root)
    cache = _ts_object(VSCODE_TS, "export const CACHE_HIT_PRICING", root)
    long_prompt = _ts_object(VSCODE_TS, "export const LONG_PROMPT_PRICING", root)
    out = _from_rows(VSCODE_TS, base, ALIAS_KEYS)
    _unmapped(VSCODE_TS, cache, ALIAS_KEYS)
    out += [
        Value(VSCODE_TS, k, ALIAS_KEYS[k], "cache_hit", v) for k, v in cache.items()
    ]
    _unmapped(VSCODE_TS, long_prompt, ALIAS_KEYS)
    for key, row in long_prompt.items():
        out += [
            Value(
                VSCODE_TS, key, ALIAS_KEYS[key], f"long_prompt.{TS_FIELDS.get(f, f)}", v
            )
            for f, v in row.items()
        ]
    return out


def read_estimate(root: Path) -> list[Value]:
    return _from_rows(
        ESTIMATE_PY,
        _assigned_literal(ESTIMATE_PY, "MODEL_PRICING", root),
        ESTIMATE_KEYS,
    )


def read_analyze(root: Path) -> list[Value]:
    return _from_rows(
        ANALYZE_PY, _assigned_literal(ANALYZE_PY, "MODEL_PRICING", root), ANALYZE_KEYS
    )


def read_cost_logger(root: Path) -> list[Value]:
    text = (root / COST_LOGGER).read_text(encoding="utf-8")
    case = re.search(r'case "\$MODEL" in\n(.*?)\nesac', text, re.S)
    if not case:
        raise ParseError(f'{COST_LOGGER.as_posix()}: no case "$MODEL" block')
    branches = []
    for patterns, body in re.findall(
        r"^ {2}([^\n#][^\n]*?)\)\n(.*?);;", case.group(1), re.M | re.S
    ):
        rates = dict(re.findall(r"RATE_(INPUT|OUTPUT)=([\d.]+)", body))
        # Shell `\[` is a literal bracket; fnmatch spells that `[[]`.
        globs = [
            p.replace("\\[", "[[]").replace("\\]", "]") for p in patterns.split("|")
        ]
        branches.append((globs, rates))
    out = []
    for probe, model in HOOK_PROBES.items():
        for globs, rates in branches:
            if any(fnmatch.fnmatchcase(probe, g) for g in globs):
                out.append(
                    Value(COST_LOGGER, probe, model, "input", float(rates["INPUT"]))
                )
                out.append(
                    Value(COST_LOGGER, probe, model, "output", float(rates["OUTPUT"]))
                )
                break
        else:
            raise ParseError(
                f"{COST_LOGGER.as_posix()}: no case branch matches {probe!r}"
            )
    return out


READERS = (
    read_pricing_ts,
    read_mcp,
    read_vscode,
    read_estimate,
    read_analyze,
    read_cost_logger,
)


# -- comparison --------------------------------------------------------------


def canonical_rates(root: Path) -> dict[str, dict[str, float | bool]]:
    models = _assigned_literal(RATE_PY, "MODELS", root)
    flat: dict[str, dict[str, float | bool]] = {}
    for key, row in models.items():
        entry: dict[str, float | bool] = {f: row[f] for f in RATE_FIELDS}
        entry["fast_mode"] = row["fast_mode"]
        for f, v in (row.get("long_prompt") or {}).items():
            entry[f"long_prompt.{f}"] = v
        flat[key] = entry
        if row["fast_mode"]:
            flat[f"{key}@fast"] = {
                "input": row["input"] * 2,
                "output": row["output"] * 2,
            }
    for alias, target in PRICE_ALIASES.items():
        flat[alias] = flat[target]
    return flat


def _same(a: float | bool, b: float | bool) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    return abs(float(a) - float(b)) < 1e-9


def _against_rate_py(values: list[Value], canon: dict) -> list[str]:
    """1. Rates against rate.py."""
    errors = []
    for v in values:
        if v.field == "min_cache" or v.model not in canon:
            continue
        expected = canon[v.model].get(v.field)
        if expected is not None and not _same(v.amount, expected):
            errors.append(
                f"{v.file.as_posix()}: {v.local_key} {v.field} = {v.amount}, but rate.py has {expected} for {v.model}"
            )
    return errors


def _against_cache_floors(values: list[Value]) -> list[str]:
    """2. Minimum cacheable prompt against pricing.ts."""
    floors = {
        v.model: v.amount
        for v in values
        if v.file == PRICING_TS and v.field == "min_cache"
    }
    return [
        f"{v.file.as_posix()}: {v.local_key} minCacheTokens = {v.amount}, but pricing.ts has {floors.get(v.model)}"
        for v in values
        if v.field == "min_cache"
        and v.file != PRICING_TS
        and not _same(v.amount, floors.get(v.model, -1))
    ]


def _across_copies(values: list[Value], canon: dict) -> list[str]:
    """3. Models rate.py does not carry: every copy must agree."""
    groups: dict[tuple[str, str], list[Value]] = {}
    for v in values:
        if v.model not in canon and v.field != "min_cache":
            groups.setdefault((v.model, v.field), []).append(v)
    errors = []
    for (model, field), group in sorted(groups.items()):
        if any(not _same(g.amount, group[0].amount) for g in group):
            seen = ", ".join(
                f"{g.file.as_posix()} {g.local_key}={g.amount}" for g in group
            )
            errors.append(f"{model} {field} disagrees across copies: {seen}")
    return errors


def check(root: Path) -> tuple[list[str], int, int]:
    canon = canonical_rates(root)
    values = [v for reader in READERS for v in reader(root)]
    errors = (
        _against_rate_py(values, canon)
        + _against_cache_floors(values)
        + _across_copies(values, canon)
    )
    files = len({v.file for v in values})
    return errors, len(values), files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "root", nargs="?", default=".", type=Path, help="repo root (default: .)"
    )
    args = parser.parse_args()
    try:
        errors, count, files = check(args.root)
    except (ParseError, OSError, KeyError, ValueError) as exc:
        print(f"check-rate-values: could not read a rate table: {exc}", file=sys.stderr)
        return 1
    if errors:
        print(f"check-rate-values: {len(errors)} value(s) disagree:", file=sys.stderr)
        for line in errors:
            print(f"  {line}", file=sys.stderr)
        return 1
    print(
        f"OK, {count} values in {files} copies agree with {RATE_PY.as_posix()} (rates)"
        f" and {PRICING_TS.as_posix()} (cache floors)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
