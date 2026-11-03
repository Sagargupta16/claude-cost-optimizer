#!/usr/bin/env python3
"""Print the cost-mode eval tables from the results.json that run.py wrote.

    python benchmarks/cost-mode-eval/summarize.py results/<run>/results.json

Per arm: pass rate, billed output tokens (thinking included) with median, min and
max as separate columns, cache read and write, list-price cost re-priced with
rate.py, and cost per passed task. Against the control: the percent change with a
fixed-seed bootstrap interval, the quality gate (exact McNemar test on paired
pass/fail), and whether the change is larger than the noise arm's. Then a
per-model break-even. Nothing is extrapolated to a month; losing arms are printed.
Method: benchmarks/METHOD.md. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from pathlib import Path
from typing import Any, Callable

import evalkit

RATE = evalkit.load_rate()
MIN_DISCORDANT = (
    5  # fewer discordant pairs than this and the quality gate is "not powered"
)
ALPHA = 0.05

Runs = list[dict[str, Any]]


# -- Loading and per-run numbers ---------------------------------------------------


def load(path: Path) -> dict[str, Any]:
    path = path / "results.json" if path.is_dir() else path
    data = json.loads(path.read_text(encoding="utf-8"))
    if "runs" not in data or "manifest" not in data:
        raise SystemExit(f"{path} is not a results.json written by run.py")
    return data


def list_cost(model: dict[str, Any], run: dict[str, Any]) -> float | None:
    """List-price dollars for one run, or None when it cannot be priced exactly.

    Per request when the transcript is there (the only exact way for Haiku 5.5, which
    prices each request by its own prompt length). From run totals only for a model
    with one rate, because cost is linear in tokens there.
    """
    requests = run.get("requests")
    if requests:
        return sum(RATE._request_cost(model, q)[0] for q in requests)
    if model.get("long_prompt") or not run.get("usage"):
        return None
    return RATE._request_cost(model, run["usage"])[0]


def enrich(runs: Runs, model: dict[str, Any]) -> None:
    for run in runs:
        requests = run.get("requests")
        source = requests if requests else [run.get("usage") or {}]
        run["_out"] = sum(q.get("output_tokens") or 0 for q in source)
        run["_read"] = sum(q.get("cache_read_input_tokens") or 0 for q in source)
        run["_write"] = sum(q.get("cache_creation_input_tokens") or 0 for q in source)
        run["_list"] = list_cost(model, run)
        run["_client"] = run.get("total_cost_usd")
        first = requests[0] if requests else None
        run["_first"] = (
            sum(
                first.get(k) or 0
                for k in (
                    "input_tokens",
                    "cache_read_input_tokens",
                    "cache_creation_input_tokens",
                )
            )
            if first
            else None
        )


# -- Statistics --------------------------------------------------------------------


def med(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def passed(runs: Runs) -> Runs:
    return [r for r in runs if r["passed"]]


def cost_key(*groups: Runs) -> str | None:
    """'_list' when every run in every group has a list price, else '_client' when all have that, else None."""
    runs = [r for g in groups for r in g]
    for key in ("_list", "_client"):
        if runs and all(r[key] is not None for r in runs):
            return key
    return None


def output_stat(runs: Runs, _key: str | None) -> float | None:
    return med([r["_out"] for r in passed(runs)])


def cost_stat(runs: Runs, key: str | None) -> float | None:
    """Cost per passed task: everything the arm spent, failures included, over its passes."""
    wins = len(passed(runs))
    if not wins or key is None:
        return None
    return sum(r[key] for r in runs) / wins


def pct_change(arm: float | None, control: float | None) -> float | None:
    if arm is None or control in (None, 0):
        return None
    return (arm - control) / control * 100


def by_case(runs: Runs) -> dict[str, Runs]:
    groups: dict[str, Runs] = {}
    for run in runs:
        groups.setdefault(run["case"], []).append(run)
    return groups


def bootstrap(
    arm: Runs,
    control: Runs,
    stat: Callable[[Runs, str | None], float | None],
    key: str | None,
    label: str,
    seed: int,
    iters: int,
) -> tuple[float | None, float | None, float | None]:
    """(point, low, high) percent change of `stat`, arm against control.

    Runs are resampled with replacement inside each case, so every resample keeps the
    case mix. The generator is seeded from the seed and the label, so a rerun prints
    the same interval.
    """
    point = pct_change(stat(arm, key), stat(control, key))
    rng = random.Random(f"{seed}:{label}")
    arm_groups, control_groups = by_case(arm), by_case(control)
    draws = []
    for _ in range(iters):
        a = [r for g in arm_groups.values() for r in rng.choices(g, k=len(g))]
        c = [r for g in control_groups.values() for r in rng.choices(g, k=len(g))]
        draw = pct_change(stat(a, key), stat(c, key))
        if draw is not None:
            draws.append(draw)
    if point is None or len(draws) < iters / 2:
        return point, None, None
    draws.sort()
    return (
        point,
        draws[int(0.025 * (len(draws) - 1))],
        draws[int(0.975 * (len(draws) - 1))],
    )


def mcnemar_exact(worse: int, better: int) -> float:
    """Two-sided exact McNemar p-value from the discordant pair counts."""
    n = worse + better
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(worse, better) + 1)) / 2**n
    return min(1.0, 2 * tail)


def paired_counts(arm: Runs, control: Runs) -> tuple[int, int, int]:
    """(regressions, improvements, pairs): control passes and arm fails, the reverse, matched (case, rep)."""
    a = {(r["case"], r["rep"]): r["passed"] for r in arm}
    c = {(r["case"], r["rep"]): r["passed"] for r in control}
    keys = a.keys() & c.keys()
    return (
        sum(1 for k in keys if c[k] and not a[k]),
        sum(1 for k in keys if a[k] and not c[k]),
        len(keys),
    )


def quality_gate(worse: int, better: int) -> tuple[float, str]:
    p = mcnemar_exact(worse, better)
    discordant = worse + better
    if discordant < MIN_DISCORDANT:
        return p, f"not powered ({discordant} discordant)"
    if p < ALPHA:
        return p, "regression" if worse > better else "improvement"
    return p, "no difference detected"


def noise_verdict(
    point: float | None,
    low: float | None,
    high: float | None,
    noise: tuple[float | None, float | None, float | None] | None,
) -> str:
    if point is None or low is None or high is None:
        return "-"
    if low <= 0 <= high:
        return "within noise (interval spans 0)"
    if (
        noise
        and noise[1] is not None
        and noise[2] is not None
        and abs(point) <= max(abs(noise[1]), abs(noise[2]))
    ):
        return "within noise (inside the noise arm's interval)"
    return "exceeds noise: " + ("lower" if point < 0 else "higher")


# -- Formatting --------------------------------------------------------------------


def num(x: float | None) -> str:
    return "-" if x is None else f"{x:,.0f}"


def usd(x: float | None) -> str:
    return "-" if x is None else f"${x:,.4f}"


def pct(x: float | None) -> str:
    return "-" if x is None else f"{x:+.1f}"


def rate_per_m(x: float) -> str:
    """A posted per-million rate with at least two decimals ($0.20, $12.50, $0.125)."""
    text = f"{x:.3f}"
    return "$" + (text[:-1] if text.endswith("0") else text)


def table(title: str, headers: list[str], rows: list[list[Any]]) -> None:
    print(f"\n### {title}\n")
    print("| " + " | ".join(headers) + " |")
    print("|" + "|".join("---" for _ in headers) + "|")
    for row in rows:
        print("| " + " | ".join(str(cell) for cell in row) + " |")


# -- Tables ------------------------------------------------------------------------


def banner(data: dict[str, Any], by_arm: dict[str, Runs]) -> None:
    m, s = data["manifest"], data["status"]
    print(
        f"# cost-mode eval: {m['model_id']} (rate.py key {m['model_key']}), effort {m['effort']}, claude {m['cli_version']}"
    )
    print(
        f"\nstarted {m['started_utc']}, seed {m['seed']}, {s.get('done', len(data['runs']))} of {s.get('planned', m['planned_runs'])} planned runs"
    )
    cells = [
        len([r for r in runs if r["case"] == c])
        for runs in by_arm.values()
        for c in m["cases"]
    ]
    least = min(cells) if cells else 0
    if s.get("stopped_reason") or not s.get("complete") or least < m["declared_reps"]:
        print(
            f"\nPILOT: not the declared n. Fewest reps in any arm and case: {least} (declared {m['declared_reps']}). Stopped: {s.get('stopped_reason') or 'no'}."
        )
    missing = sum(1 for r in data["runs"] if r.get("requests") is None)
    odd = sum(
        1
        for r in data["runs"]
        if any(m["model_key"] not in seen for seen in r.get("models_seen") or [])
    )
    if missing:
        print(
            f"\nwarning: {missing} run(s) have no transcript, so they are priced from run totals or client estimates only"
        )
    if odd:
        print(f"\nwarning: {odd} run(s) report a model other than the pinned one")
    print(
        "\nOut columns count passed runs only. Cost columns count every run. 'Client est.' is Claude Code's total_cost_usd, an estimate, not a bill."
    )


def quality_and_output(by_arm: dict[str, Runs]) -> None:
    rows = []
    for arm, runs in by_arm.items():
        ok = passed(runs)
        outs = [r["_out"] for r in ok]
        skill = (
            f"{sum(r['skill_activated'] for r in runs)}/{len(runs)}"
            if arm == "costmode-installed"
            else ("forced" if arm.startswith("costmode-") else "-")
        )
        rows.append(
            [
                arm,
                len(runs),
                len(ok),
                f"{100 * len(ok) / len(runs):.0f}%",
                num(med(outs)),
                num(min(outs, default=None)),
                num(max(outs, default=None)),
                sum(1 for r in runs if r["is_error"]),
                skill,
            ]
        )
    table(
        "Quality and billed output (thinking included)",
        [
            "Arm",
            "Runs",
            "Passed",
            "Pass rate",
            "Out med",
            "Out min",
            "Out max",
            "Errors",
            "Skill fired",
        ],
        rows,
    )


def cache_and_cost(by_arm: dict[str, Runs]) -> None:
    rows = []
    for arm, runs in by_arm.items():
        key = cost_key(runs)
        basis = {"_list": "list (rate.py)", "_client": "client est.", None: "none"}[key]
        listed = [r["_list"] for r in runs if r["_list"] is not None]
        full = len(listed) == len(runs)
        client = [r["_client"] for r in runs if r["_client"] is not None]
        rows.append([
            arm, num(med([r["_read"] for r in runs])), num(med([r["_write"] for r in runs])),
            usd(med(listed) if full else None), usd(min(listed) if full else None), usd(max(listed) if full else None),
            usd(med(client)), usd(cost_stat(runs, key)), basis,
        ])  # fmt: skip
    table(
        "Cache and cost per run",
        [
            "Arm",
            "Cache read med",
            "Cache write med",
            "List $/run med",
            "List min",
            "List max",
            "Client est. $/run med",
            "$ per passed task",
            "Basis",
        ],
        rows,
    )


def versus_control(
    by_arm: dict[str, Runs], control: str, noise: str, args: argparse.Namespace
) -> None:
    ctrl = by_arm[control]
    results: dict[str, dict[str, tuple[float | None, float | None, float | None]]] = {}
    for arm, runs in by_arm.items():
        if arm == control:
            continue
        key = cost_key(runs, ctrl)
        results[arm] = {
            "out": bootstrap(
                runs, ctrl, output_stat, key, f"{arm}:out", args.seed, args.iters
            ),
            "cost": bootstrap(
                runs, ctrl, cost_stat, key, f"{arm}:cost", args.seed, args.iters
            ),
        }
    noise_res = results.get(noise)
    rows = []
    for arm, res in results.items():
        verdicts = [
            (
                "noise arm"
                if arm == noise
                else noise_verdict(
                    *res[k],
                    None if arm == noise else noise_res[k] if noise_res else None,
                )
            )
            for k in ("out", "cost")
        ]
        rows.append(
            [
                arm,
                *map(pct, res["out"]),
                verdicts[0],
                *map(pct, res["cost"]),
                verdicts[1],
            ]
        )
    headers = [
        "Arm",
        "Out % chg",
        "Out low",
        "Out high",
        "Out vs noise",
        "$/passed % chg",
        "$ low",
        "$ high",
        "Cost vs noise",
    ]
    table(
        f"Change against the control ({control}), 95% bootstrap interval, {args.iters} resamples, seed {args.seed}",
        headers,
        rows,
    )
    if noise_res is None:
        print(
            f"\nno {noise} arm in this file: nothing sizes the run-to-run noise, so no saving here can be called larger than noise."
        )


def quality_gate_table(by_arm: dict[str, Runs], control: str) -> None:
    rows = []
    for arm, runs in by_arm.items():
        if arm == control:
            continue
        worse, better, pairs = paired_counts(runs, by_arm[control])
        p, label = quality_gate(worse, better)
        rows.append([arm, pairs, worse, better, f"{p:.3f}", label])
    table(
        f"Quality gate against {control} (exact McNemar on matched case and rep)",
        ["Arm", "Pairs", "Regressions", "Improvements", "p", "Gate"],
        rows,
    )


def per_case(by_arm: dict[str, Runs], manifest: dict[str, Any]) -> None:
    rows = []
    for case, info in manifest["cases"].items():
        cells = []
        for runs in by_arm.values():
            mine = [r for r in runs if r["case"] == case]
            ok = [r["_out"] for r in mine if r["passed"]]
            cells.append(f"{num(med(ok))} ({len(ok)}/{len(mine)})")
        rows.append(
            [case + ("" if info["expect_gain"] else " (no gain expected)"), *cells]
        )
    table(
        "Median billed output tokens per case, passed runs (passed/runs)",
        ["Case", *by_arm],
        rows,
    )


def injected_tokens(arm: Runs, control: Runs) -> float | None:
    """Median over cases of the first-request prompt size the arm adds over the control."""
    diffs = []
    for case in {r["case"] for r in arm}:
        a = [r["_first"] for r in arm if r["case"] == case and r["_first"] is not None]
        c = [
            r["_first"]
            for r in control
            if r["case"] == case and r["_first"] is not None
        ]
        if a and c:
            diffs.append(med(a) - med(c))
    return med(diffs)


def break_even(
    by_arm: dict[str, Runs],
    control: str,
    manifest: dict[str, Any],
    args: argparse.Namespace,
) -> None:
    arms = [
        a for a in by_arm if a.startswith("costmode-") and a != "costmode-installed"
    ]
    if not arms:
        return
    ctrl = by_arm[control]
    facts = {}
    for arm in arms:
        measured = injected_tokens(by_arm[arm], ctrl)
        injected = measured if measured is not None else args.injected_tokens
        turns = args.turns or med(
            [r["num_turns"] for r in by_arm[arm] if r.get("num_turns")]
        )
        saved = None
        if (a := output_stat(by_arm[arm], None)) is not None and (
            c := output_stat(ctrl, None)
        ) is not None:
            saved = c - a
        facts[arm] = (injected, turns, saved)
    rows = []
    for key, model in RATE.MODELS.items():
        if model["lifecycle"] != "active" and key != manifest["model_key"]:
            continue
        for tier, rates in [("", model)] + (
            [(" over 100K prompt", model["long_prompt"])]
            if model.get("long_prompt")
            else []
        ):
            cells = [_break_even_cell(*facts[arm][:2], rates) for arm in arms]
            rows.append(
                [
                    model["name"] + tier,
                    rate_per_m(rates["cache_5m_write"]),
                    rate_per_m(rates["cache_hit"]),
                    rate_per_m(rates["output"]),
                    *cells,
                ]
            )
    table(
        "Break-even: output tokens a run must save to repay the injected text",
        ["Model", "5m write $/M", "Cache read $/M", "Output $/M", *arms],
        rows,
    )
    print(
        "\nformula: injected tokens x (5-minute write rate + (turns - 1) x cache read rate) / output rate; every rate from rate.py MODELS."
    )
    for arm in arms:
        _print_fact(arm, facts[arm], manifest)


def _break_even_cell(
    injected: float | None, turns: float | None, rates: dict[str, Any]
) -> str:
    if injected is None or turns is None:
        return "-"
    return num(
        injected
        * (rates["cache_5m_write"] + (turns - 1) * rates["cache_hit"])
        / rates["output"]
    )


def _print_fact(
    arm: str,
    fact: tuple[float | None, float | None, float | None],
    manifest: dict[str, Any],
) -> None:
    injected, turns, saved = fact
    if injected is None:
        print(
            f"- {arm}: injected tokens not measured (no per-request data); pass --injected-tokens N"
        )
        return
    model = RATE.MODELS[manifest["model_key"]]
    verdict = ""
    if saved is not None and turns is not None:
        cost = injected * (model["cache_5m_write"] + (turns - 1) * model["cache_hit"])
        net = (saved * model["output"] - cost) / 1_000_000
        verdict = f"; net per run on {model['name']} (prompts up to 100K) {'+' if net >= 0 else '-'}${abs(net):.4f} ({'saves' if net >= 0 else 'costs more'})"
    print(
        f"- {arm}: injected {num(injected)} tokens, {turns or 0:.0f} turns, median output saved per run {num(saved)} tokens{verdict}"
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("results", type=Path, help="results.json (or the folder holding it)")
    p.add_argument(
        "--control",
        default=evalkit.CONTROL_ARM,
        help="the arm every change is measured against",
    )
    p.add_argument(
        "--noise",
        default=evalkit.NOISE_ARM,
        help="the control-vs-control arm that sizes run-to-run noise",
    )
    p.add_argument(
        "--iters", type=int, default=evalkit.BOOTSTRAP_ITERS, help="bootstrap resamples"
    )
    p.add_argument("--seed", type=int, default=evalkit.SEED)
    p.add_argument(
        "--turns",
        type=float,
        help="turns per run for the break-even (default: the arm's median)",
    )
    p.add_argument(
        "--injected-tokens",
        type=float,
        help="injected tokens for the break-even when the file has no per-request data",
    )
    args = p.parse_args(argv)
    data = load(args.results)
    manifest = data["manifest"]
    enrich(data["runs"], RATE.MODELS[manifest["model_key"]])
    by_arm = {
        arm: [r for r in data["runs"] if r["arm"] == arm] for arm in manifest["arms"]
    }
    by_arm = {arm: runs for arm, runs in by_arm.items() if runs}
    banner(data, by_arm)
    quality_and_output(by_arm)
    cache_and_cost(by_arm)
    if args.control in by_arm:
        versus_control(by_arm, args.control, args.noise, args)
        quality_gate_table(by_arm, args.control)
    else:
        print(
            f"\nno {args.control} arm in this file: nothing to compare against.",
            file=sys.stderr,
        )
    per_case(by_arm, manifest)
    if args.control in by_arm:
        break_even(by_arm, args.control, manifest, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
