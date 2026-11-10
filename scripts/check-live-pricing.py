#!/usr/bin/env python3
"""Compare rate.py's per-model rates with Anthropic's live pricing page.

check-pricing-sync.py proves the files agree with each other, and
check-rate-values.py proves every code copy agrees with rate.py. Neither asks
whether rate.py agrees with Anthropic, so a price change is found at the next
manual sweep. This script asks: it fetches the pricing page as Markdown, parses
the "Model pricing" table and the "Fast mode pricing" table, and reports

  - a rate that differs from MODELS in tools/claude-rate/rate.py,
  - a model rate.py carries that the page no longer lists,
  - a model the page lists that rate.py neither carries nor names in
    KNOWN_UNCARRIED below (the new-model alarm),
  - a Fast Mode price that is not 2x the model's own base rate.

It reads rates only. Plan names, flags and retirement dates still need the
manual sweep described in docs/pricing-data.md; this is the alarm, not the fix.

Parse rules (the page is Markdown, so the rules are about its tables):

  - Columns are matched by keyword on the lower-cased header text (input, 5m,
    1h, cache hit, output), so a reworded column still parses. A column that
    cannot be found, or is found twice, is a parse failure.
  - A name cell loses its <sup>n</sup> footnote marks, then everything from its
    first " (" on, then the leading "Claude ". That also drops the retired
    notes, whose link text holds nested parentheses.
  - "(for prompts up to N tokens)" and "(for prompts over N tokens)" mark the
    two price tiers of one model; N is the tier threshold.
  - A price cell is its first dollar amount ("$12.50 / MTok", "$8 USD / MTok").
  - The Fast mode table may put two models in one cell ("Claude Opus 5 /
    Claude Opus 4.8").
  - A page row for a model rate.py holds as an alias (_PRICE_ALIASES) is
    compared with the aliased model's rates, because that is how rate.py prices
    it.

Exit 0 when every rate agrees, 1 on drift, 2 when the page could not be fetched
or parsed. On exit 2 stderr starts with "check-live-pricing: fetch failed" or
"check-live-pricing: parse failed"; .github/workflows/pricing-drift.yml reads
that line to open an issue for a parse failure but only fail the run for a
network failure.

Usage:
    python scripts/check-live-pricing.py
    python scripts/check-live-pricing.py --markdown
    python scripts/check-live-pricing.py --file saved-page.md
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import http.client
import re
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

PRICING_URL = "https://platform.claude.com/docs/en/about-claude/pricing.md"
USER_AGENT = (
    "claude-cost-optimizer-pricing-drift "
    "(+https://github.com/Sagargupta16/claude-cost-optimizer)"
)
FETCH_ATTEMPTS = 3
FETCH_TIMEOUT_SECONDS = 30
DEFAULT_RATE_PY = Path(__file__).resolve().parents[1] / "tools/claude-rate/rate.py"

# Names on the live page (without "Claude ") that rate.py does not carry on
# purpose: models retired from the Claude API that only Bedrock or Google Cloud
# still serve. Anything else the page lists and rate.py lacks is a new model.
# A name here that rate.py later gains a row or alias for is simply compared.
KNOWN_UNCARRIED = frozenset({"Opus 4.1", "Opus 4", "Sonnet 4", "Haiku 3.5"})

# rate.py field -> keywords that find its column in the page header.
PRICE_COLUMNS = {
    "input": ("input",),
    "cache_5m_write": ("5m",),
    "cache_1h_write": ("1h",),
    "cache_hit": ("cache hit", "cache read"),
    "output": ("output",),
}
FAST_COLUMNS = {"input": ("input",), "output": ("output",)}
RATE_FIELDS = tuple(PRICE_COLUMNS)

_SUP = re.compile(r"<sup>.*?</sup>", re.IGNORECASE | re.DOTALL)
_PRICE = re.compile(r"\$\s*([\d,]*\.?\d+)")
_TIER = re.compile(r"\(for prompts (up to|over) ([\d,]+) tokens\)", re.IGNORECASE)
_SEPARATOR = re.compile(r"^\|[\s:|-]+\|$")


class FetchError(Exception):
    """The pricing page could not be downloaded."""


class ParseError(Exception):
    """The page, or rate.py, is not shaped the way this script expects."""


@dataclass(frozen=True)
class LiveRow:
    name: str  # "Opus 4.1": the page's name without "Claude " or notes
    tier: str  # "" one price, "low" up to the threshold, "long" over it
    threshold: int | None
    rates: dict[str, float]


@dataclass(frozen=True)
class FastRow:
    names: tuple[str, ...]
    rates: dict[str, float]


@dataclass
class Line:
    label: str
    status: str
    values: tuple[float, ...]


@dataclass
class Report:
    models: list[Line] = field(default_factory=list)
    fast: list[Line] = field(default_factory=list)
    drift: list[str] = field(default_factory=list)
    compared: int = 0


# -- fetching ----------------------------------------------------------------


def fetch(
    url: str = PRICING_URL,
    attempts: int = FETCH_ATTEMPTS,
    sleep=time.sleep,
) -> str:
    """GET the page, trying `attempts` times with a growing pause between tries."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as r:
                return r.read().decode("utf-8")
        except (OSError, http.client.HTTPException, UnicodeDecodeError) as exc:
            last = exc
            if attempt < attempts:
                sleep(2**attempt)
    raise FetchError(f"{url}: {last} (after {attempts} attempts)")


# -- reading rate.py ---------------------------------------------------------


def load_rates(path: Path) -> tuple[dict[str, dict], dict[str, str]]:
    """Read MODELS and _PRICE_ALIASES from rate.py without importing it."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found: dict[str, object] = {}
        for node in tree.body:
            target, value = _assignment(node)
            if target in ("MODELS", "_PRICE_ALIASES"):
                found[target] = ast.literal_eval(value)
    except (OSError, SyntaxError, ValueError) as exc:
        raise ParseError(f"{path.as_posix()}: {exc}") from exc
    if set(found) != {"MODELS", "_PRICE_ALIASES"}:
        raise ParseError(f"{path.as_posix()}: MODELS or _PRICE_ALIASES not found")
    models, aliases = found["MODELS"], found["_PRICE_ALIASES"]
    for key, row in models.items():
        needed = ("name", *RATE_FIELDS)
        if any(f not in row for f in needed):
            raise ParseError(f"{path.as_posix()}: MODELS[{key!r}] lacks a rate field")
    return models, aliases


def _assignment(node: ast.stmt) -> tuple[str | None, ast.expr | None]:
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id, node.value
    if (
        isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
    ):
        return node.targets[0].id, node.value
    return None, None


def _alias_name(key: str) -> str:
    """'opus-4-5' -> 'Opus 4.5', the page's spelling of an alias key."""
    head, *version = key.split("-")
    return f"{head.title()} {'.'.join(version)}".strip()


def name_index(models: dict[str, dict], aliases: dict[str, str]) -> dict[str, str]:
    """Page name -> rate.py key, for MODELS rows first and then alias keys."""
    index = {row["name"]: key for key, row in models.items()}
    for key in aliases:
        index.setdefault(_alias_name(key), key)
    return index


# -- parsing the page --------------------------------------------------------


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _section(text: str, heading: str) -> str:
    """The text under `heading`, up to the next heading of the same or higher level."""
    level = len(heading) - len(heading.lstrip("#"))
    start = re.search(rf"^{re.escape(heading)}[ \t]*$", text, re.MULTILINE | re.I)
    if not start:
        raise ParseError(f"no '{heading}' section on the page")
    rest = text[start.end() :]
    end = re.search(rf"^#{{1,{level}}} ", rest, re.MULTILINE)
    return rest[: end.start()] if end else rest


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _table(section: str, title: str) -> tuple[list[str], list[list[str]]]:
    """Header cells and body rows of the first Markdown table in `section`."""
    lines = [line.strip() for line in section.splitlines()]
    first = next((i for i, line in enumerate(lines) if line.startswith("|")), None)
    if first is None:
        raise ParseError(f"{title}: no table")
    block = []
    for line in lines[first:]:
        if not line.startswith("|"):
            break
        block.append(line)
    if len(block) < 3 or not _SEPARATOR.match(block[1]):
        raise ParseError(f"{title}: table has no header, separator and rows")
    return _cells(block[0]), [_cells(line) for line in block[2:]]


def _find_columns(
    header: list[str], wanted: dict[str, tuple[str, ...]], title: str
) -> dict[str, int]:
    cells = [_normalize(cell) for cell in header]
    if "model" not in cells[0]:
        raise ParseError(f"{title}: first column is not the model ({header[0]!r})")
    found: dict[str, int] = {}
    for role, words in wanted.items():
        hits = [i for i in range(1, len(cells)) if any(w in cells[i] for w in words)]
        if len(hits) != 1:
            raise ParseError(
                f"{title}: expected exactly one '{words[0]}' column, found {len(hits)}"
                f" in {header}"
            )
        found[role] = hits[0]
    if len(set(found.values())) != len(found):
        raise ParseError(f"{title}: two rate fields matched the same column")
    return found


def _clean_name(cell: str) -> str:
    name = _SUP.sub("", cell).split(" (", 1)[0].strip()
    return re.sub(r"^Claude\s+", "", name)


def _tier(cell: str) -> tuple[str, int | None]:
    """('low' | 'long' | '', threshold) from a '(for prompts up to N tokens)' note."""
    match = _TIER.search(_SUP.sub("", cell))
    if not match:
        return "", None
    kind = "low" if match.group(1).lower() == "up to" else "long"
    return kind, int(match.group(2).replace(",", ""))


def _price(cell: str, what: str) -> float:
    match = _PRICE.search(_SUP.sub("", cell))
    if not match:
        raise ParseError(f"{what}: no dollar amount in {cell!r}")
    return float(match.group(1).replace(",", ""))


def _rates(cells: list[str], columns: dict[str, int], what: str) -> dict[str, float]:
    if len(cells) <= max(columns.values()):
        raise ParseError(f"{what}: row has {len(cells)} cells, fewer than the header")
    return {role: _price(cells[i], what) for role, i in columns.items()}


def parse_model_table(text: str) -> list[LiveRow]:
    title = "Model pricing"
    header, body = _table(_section(text, "## Model pricing"), title)
    columns = _find_columns(header, PRICE_COLUMNS, title)
    rows = []
    for cells in body:
        name = _clean_name(cells[0])
        if not name:
            raise ParseError(f"{title}: a row has no model name")
        kind, threshold = _tier(cells[0])
        rows.append(LiveRow(name, kind, threshold, _rates(cells, columns, name)))
    return rows


def parse_fast_table(text: str) -> list[FastRow]:
    title = "Fast mode pricing"
    header, body = _table(_section(text, "### Fast mode pricing"), title)
    columns = _find_columns(header, FAST_COLUMNS, title)
    rows = []
    for cells in body:
        names = tuple(_clean_name(part) for part in _SUP.sub("", cells[0]).split(" / "))
        rows.append(FastRow(names, _rates(cells, columns, " / ".join(names))))
    return rows


# -- comparing ---------------------------------------------------------------


def _money(amount: float) -> str:
    """$12.50, $0.20, $0.125, $10: two decimals at least when there are decimals."""
    text = f"{amount:g}"
    if "." in text and len(text.split(".")[1]) < 2:
        text += "0"
    return f"${text}"


def _differs(a: float, b: float) -> bool:
    return abs(a - b) > 1e-9


def _tier_label(row: LiveRow) -> str:
    if row.tier == "low":
        return f"{row.name} (prompts up to {row.threshold:,})"
    if row.tier == "long":
        return f"{row.name} (prompts over {row.threshold:,})"
    return row.name


def _row_problems(row: LiveRow, ours: dict) -> tuple[list[str], int]:
    """Drift messages for one page row, and how many rate values were compared."""
    label = _tier_label(row)
    long_tier = ours.get("long_prompt")
    expected = long_tier if row.tier == "long" else ours
    if expected is None:
        return [f"{label}: the page prices long prompts apart, rate.py has no tier"], 0
    problems = [
        f"{label} {name}: rate.py has {_money(expected[name])}, "
        f"the page has {_money(row.rates[name])}"
        for name in RATE_FIELDS
        if _differs(row.rates[name], expected[name])
    ]
    compared = len(RATE_FIELDS)
    if row.tier and long_tier:
        compared += 1
        if row.threshold != long_tier["threshold"]:
            problems.append(
                f"{label}: the page switches tier at {row.threshold:,} tokens, "
                f"rate.py at {long_tier['threshold']:,}"
            )
    return problems, compared


def _tiers(tiers: list[str]) -> str:
    return ", ".join(tier or "single price" for tier in tiers)


def _tier_problems(name: str, group: list[LiveRow], ours: dict) -> list[str]:
    wanted = ["low", "long"] if "long_prompt" in ours else [""]
    found = sorted(row.tier for row in group)
    if found == sorted(wanted):
        return []
    return [
        f"{name}: the page lists [{_tiers(found)}], "
        f"rate.py expects [{_tiers(sorted(wanted))}]"
    ]


def _compare_group(
    report: Report,
    name: str,
    group: list[LiveRow],
    index: dict[str, str],
    models: dict[str, dict],
    aliases: dict[str, str],
    known: frozenset[str],
) -> None:
    key = index.get(name)
    if key is None:
        status = "not carried (known)" if name in known else "NEW MODEL"
        if name not in known:
            report.drift.append(
                f"the page lists {name}, which rate.py does not carry and "
                "KNOWN_UNCARRIED does not name: add a row or an alias to rate.py, "
                "or list it in KNOWN_UNCARRIED"
            )
        for row in group:
            values = tuple(row.rates[f] for f in RATE_FIELDS)
            report.models.append(Line(_tier_label(row), status, values))
        return
    target = aliases.get(key, key)
    ours = models[target]
    group_problems = _tier_problems(name, group, ours)
    ok = "ok" if target == key else f"ok (priced like {ours['name']})"
    for row in group:
        problems, compared = _row_problems(row, ours)
        report.compared += compared
        report.drift += problems
        status = "DRIFT" if problems or group_problems else ok
        values = tuple(row.rates[f] for f in RATE_FIELDS)
        report.models.append(Line(_tier_label(row), status, values))
    report.drift += group_problems


def _compare_fast(
    report: Report,
    fast_rows: list[FastRow],
    index: dict[str, str],
    models: dict[str, dict],
    aliases: dict[str, str],
) -> None:
    listed = {name: row for row in fast_rows for name in row.names}
    for name, row in listed.items():
        # An alias (Mythos 5.2 -> Fable 5.2) has no MODELS row of its own.
        key = index.get(name, "")
        ours = models.get(aliases.get(key, key))
        problems = []
        if ours is None or not ours.get("fast_mode"):
            problems.append(
                f"Fast mode table lists {name}, but rate.py has no fast_mode model "
                "with that name"
            )
        else:
            for role in FAST_COLUMNS:
                report.compared += 1
                if _differs(row.rates[role], 2 * ours[role]):
                    problems.append(
                        f"Fast mode {name} {role}: 2x rate.py is "
                        f"{_money(2 * ours[role])}, the page has "
                        f"{_money(row.rates[role])}"
                    )
        report.drift += problems
        values = (row.rates["input"], row.rates["output"])
        report.fast.append(Line(name, "DRIFT" if problems else "ok", values))
    for row in models.values():
        if row.get("fast_mode") and row["name"] not in listed:
            report.drift.append(
                f"rate.py has fast_mode for {row['name']}, but the Fast mode table no "
                "longer lists it"
            )


def compare(
    rows: list[LiveRow],
    fast_rows: list[FastRow],
    models: dict[str, dict],
    aliases: dict[str, str],
    known: frozenset[str] = KNOWN_UNCARRIED,
) -> Report:
    report = Report()
    index = name_index(models, aliases)
    groups: dict[str, list[LiveRow]] = {}
    for row in rows:
        groups.setdefault(row.name, []).append(row)
    for name, group in groups.items():
        _compare_group(report, name, group, index, models, aliases, known)
    for name, key in index.items():
        if name not in groups:
            report.drift.append(
                f"rate.py carries {name} ({key}), but the page has no row for it"
            )
    _compare_fast(report, fast_rows, index, models, aliases)
    return report


# -- output ------------------------------------------------------------------


def render_text(report: Report, source: str) -> str:
    out = [f"check-live-pricing: {source}"]
    out += [f"  {line.label:<44} {line.status}" for line in report.models]
    out += [f"  {'fast mode: ' + line.label:<44} {line.status}" for line in report.fast]
    if report.drift:
        out += ["", f"DRIFT ({len(report.drift)}):"]
        out += [f"  - {problem}" for problem in report.drift]
    out += ["", _summary(report)]
    return "\n".join(out)


def render_markdown(report: Report, source: str) -> str:
    head = (
        "| Model | Base input | 5m cache write | 1h cache write | Cache hit | Output |"
    )
    out = ["## Live pricing check", "", f"Source: {source}", "", f"{head} Status |"]
    out.append("| --- | ---: | ---: | ---: | ---: | ---: | --- |")
    for line in report.models:
        cells = " | ".join(_money(v) for v in line.values)
        out.append(f"| {line.label} | {cells} | {line.status} |")
    out += [
        "",
        "| Fast mode model | Input | Output | Status |",
        "| --- | ---: | ---: | --- |",
    ]
    for line in report.fast:
        cells = " | ".join(_money(v) for v in line.values)
        out.append(f"| {line.label} | {cells} | {line.status} |")
    out.append("")
    if report.drift:
        out += [f"### Drift ({len(report.drift)})", ""]
        out += [f"- {problem}" for problem in report.drift]
        out += [
            "",
            "Re-read the page, then follow the Sync checklist in "
            "`docs/pricing-data.md`. This check reads rates only.",
            "",
        ]
    out.append(_summary(report))
    return "\n".join(out)


def _summary(report: Report) -> str:
    return (
        f"{report.compared} rate values compared across {len(report.models)} table "
        f"rows and {len(report.fast)} Fast mode rows: "
        f"{len(report.drift)} drift."
    )


def _fail(kind: str, exc: Exception, markdown: bool) -> int:
    print(f"check-live-pricing: {kind}: {exc}", file=sys.stderr)
    if markdown:
        print(f"## Live pricing check could not complete\n\n{kind}: {exc}")
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--file", type=Path, help="read a saved copy of the page instead of fetching"
    )
    parser.add_argument(
        "--rate-py", type=Path, default=DEFAULT_RATE_PY, help="rate.py to compare"
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="print the per-model table as Markdown, for an issue or a PR body",
    )
    args = parser.parse_args(argv)

    try:
        if args.file:
            page = args.file.read_text(encoding="utf-8")
            source = args.file.as_posix()
        else:
            page = fetch()
            today = dt.datetime.now(tz=dt.timezone.utc).date().isoformat()
            source = f"{PRICING_URL}, read {today}"
    except (FetchError, OSError) as exc:
        return _fail("fetch failed", exc, args.markdown)

    try:
        models, aliases = load_rates(args.rate_py)
        report = compare(
            parse_model_table(page), parse_fast_table(page), models, aliases
        )
    except ParseError as exc:
        return _fail("parse failed", exc, args.markdown)

    render = render_markdown if args.markdown else render_text
    print(render(report, source))
    return 1 if report.drift else 0


if __name__ == "__main__":
    sys.exit(main())
