#!/usr/bin/env python3
"""Run the cost-mode eval: arms x cases x reps over `claude --bare -p`.

Every run is a real model call that costs money, so nothing is called until you
pass --yes, --max-cost-usd and --cli-version. Start with --dry-run: it prints the
plan, the run count and the cost cap and calls nothing.

    python benchmarks/cost-mode-eval/run.py --dry-run
    python benchmarks/cost-mode-eval/run.py --yes --max-cost-usd 25 --cli-version 2.1.312

The method this follows is benchmarks/METHOD.md. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import evalkit

RESULTS_ROOT = evalkit.HERE / "results"
SCHEMA = 1
PER_RUN_USD = 0.60
TIMEOUT_S = 900
MAX_CONSECUTIVE_ERRORS = 3


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="print the plan, run count and cost cap; call nothing",
    )
    p.add_argument(
        "--yes",
        action="store_true",
        help="the maintainer approved this run count and cap",
    )
    p.add_argument(
        "--max-cost-usd",
        type=float,
        help="hard ceiling on the batch's summed total_cost_usd",
    )
    p.add_argument(
        "--cli-version",
        help="the claude version this run is pinned to (claude --version)",
    )
    p.add_argument(
        "--model",
        default="opus-5-5",
        choices=sorted(evalkit.MODEL_IDS),
        help="rate.py MODELS key",
    )
    p.add_argument(
        "--model-id",
        help="id passed to --model when the platform's id differs (Bedrock, Google Cloud)",
    )
    p.add_argument(
        "--effort", default="medium", choices=["low", "medium", "high", "xhigh", "max"]
    )
    p.add_argument(
        "--arms",
        default=",".join(evalkit.DEFAULT_ARMS),
        help=f"of: {', '.join(evalkit.ARMS)}",
    )
    p.add_argument("--cases", help="comma list of case ids (default: all)")
    p.add_argument(
        "--reps", type=int, default=evalkit.N_REPS, help="runs per arm and case"
    )
    p.add_argument("--seed", type=int, default=evalkit.SEED, help="seeds the run order")
    p.add_argument(
        "--per-run-usd",
        type=float,
        default=PER_RUN_USD,
        help="--max-budget-usd for each run",
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=TIMEOUT_S,
        help="seconds before one run is abandoned",
    )
    p.add_argument("--out", help="results folder (default: results/<utc time>-<model>)")
    p.add_argument(
        "--resume",
        action="store_true",
        help="continue an existing --out folder, skipping finished runs",
    )
    p.add_argument(
        "--keep-work",
        action="store_true",
        help="keep each run's temp working folder for inspection",
    )
    p.add_argument(
        "--claude-arg",
        action="append",
        default=[],
        help="extra claude flag, as --claude-arg=--flag",
    )
    return p.parse_args(argv)


def die(message: str, code: int = 2) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def split_list(text: str | None) -> list[str]:
    return [part.strip() for part in (text or "").split(",") if part.strip()]


def select(args: argparse.Namespace) -> tuple[list[str], list[dict[str, Any]]]:
    arms = split_list(args.arms)
    unknown = [a for a in arms if a not in evalkit.ARMS]
    if unknown:
        die(f"unknown arm(s): {', '.join(unknown)}")
    return arms, evalkit.load_cases(split_list(args.cases) or None)


def build_plan(
    arms: list[str], case_ids: list[str], reps: int, seed: int
) -> list[dict[str, Any]]:
    """Randomized blocks: one block is a (rep, case) pair with every arm in a shuffled order.

    Stopping early (the cost cap) then leaves every arm with the same cases and reps.
    """
    rng = random.Random(seed)
    plan = []
    for rep in range(1, reps + 1):
        order = list(case_ids)
        rng.shuffle(order)
        for case_id in order:
            block = list(arms)
            rng.shuffle(block)
            plan.extend({"arm": arm, "case": case_id, "rep": rep} for arm in block)
    return plan


def run_id(item: dict[str, Any]) -> str:
    return f"{item['arm']}__{item['case']}__r{item['rep']}"


def model_id_for(args: argparse.Namespace) -> str:
    return args.model_id or evalkit.MODEL_IDS[args.model]


# -- Dry run -----------------------------------------------------------------------


def print_plan(
    args: argparse.Namespace,
    arms: list[str],
    cases: list[dict[str, Any]],
    plan: list[dict[str, Any]],
) -> None:
    runs = len(plan)
    worst = runs * args.per_run_usd
    print("cost-mode eval plan (dry run: no call is made)")
    print(f"  model        {args.model} -> {model_id_for(args)}")
    print(f"  effort       {args.effort}")
    print(
        "  claude       version is read and pinned on a real run (--cli-version); this dry run does not start claude"
    )
    print(
        f"  tools        {evalkit.TOOLS} in every arm (no Bash; checks run after the session)"
    )
    print(f"  seed         {args.seed} (run order)")
    print(f"  arms ({len(arms)})")
    for arm in arms:
        extra = _arm_note(arm)
        print(f"    {arm:<20} {evalkit.ARMS[arm]['role']:<9} {extra}")
    print(f"  cases ({len(cases)})")
    for case in cases:
        gain = "gain expected" if case["expect_gain"] else "no gain expected"
        print(
            f"    {case['id']:<22} {case['category']:<10} {len(case['graders'])} grader(s), {gain}"
        )
    print(
        f"  reps         {args.reps} per arm and case (n declared in METHOD.md: {evalkit.N_REPS})"
    )
    print(
        f"  runs         {len(arms)} arms x {len(cases)} cases x {args.reps} reps x 1 model = {runs}"
    )
    print(f"  per-run cap  ${args.per_run_usd:.2f} (--max-budget-usd on each run)")
    print(
        f"  worst case   {runs} runs x ${args.per_run_usd:.2f} = ${worst:,.2f}  (a ceiling, not an estimate)"
    )
    _print_cap(args, runs)
    if evalkit.CONTROL_ARM not in arms:
        print(
            f"  note         control arm {evalkit.CONTROL_ARM!r} is not selected; summarize.py has nothing to compare to"
        )
    print("  first block  " + ", ".join(run_id(item) for item in plan[: len(arms)]))
    print(
        "A real run needs --yes --max-cost-usd N --cli-version V. State the run count and the cap when asking for approval."
    )


def _arm_note(arm: str) -> str:
    text = evalkit.append_text(arm)
    if text is not None:
        return (
            f"appends {len(text)} characters (sha256 {evalkit.sha256_text(text)[:12]})"
        )
    return (
        "loads the plugin with --plugin-dir"
        if evalkit.ARMS[arm]["role"] == "installed"
        else "no extra text"
    )


def _print_cap(args: argparse.Namespace, runs: int) -> None:
    if args.max_cost_usd is None:
        print(
            "  cost cap     not set; a real run refuses to start without --max-cost-usd"
        )
        return
    fits = int(args.max_cost_usd // args.per_run_usd)
    print(
        f"  cost cap     ${args.max_cost_usd:,.2f} on summed total_cost_usd (a client estimate)"
    )
    print(
        f"               the batch stops before a run that could cross it; at the per-run cap that is {fits} of {runs} runs"
    )


# -- Real run ----------------------------------------------------------------------


def guard(args: argparse.Namespace) -> None:
    missing = []
    if not args.yes:
        missing.append("--yes")
    if not args.max_cost_usd or args.max_cost_usd <= 0:
        missing.append("--max-cost-usd N")
    if not args.cli_version:
        missing.append("--cli-version V")
    if missing:
        die(
            f"refusing to call claude without {', '.join(missing)}. Every run costs money: run --dry-run, "
            "get the run count and cap approved, then pass them."
        )
    if args.max_cost_usd < args.per_run_usd:
        die(
            f"--max-cost-usd {args.max_cost_usd} is below one run's budget (--per-run-usd {args.per_run_usd})"
        )


def claude_version(claude: str) -> str:
    done = subprocess.run(
        [claude, "--version"], capture_output=True, text=True, timeout=60
    )
    found = re.search(r"\d+\.\d+\.\d+", done.stdout)
    return found.group(0) if found else done.stdout.strip()


def parse_result(stdout: str) -> dict[str, Any] | None:
    """The result object of `--output-format json` (a single object, or the last result in a list)."""
    try:
        data = json.loads(stdout)
    except ValueError:
        return None
    if isinstance(data, list):
        data = next(
            (
                d
                for d in reversed(data)
                if isinstance(d, dict) and d.get("type") == "result"
            ),
            None,
        )
    return data if isinstance(data, dict) else None


class Batch:
    """One invocation: owns the results folder, the running totals and the stop rules."""

    def __init__(
        self,
        args: argparse.Namespace,
        claude: str,
        arms: list[str],
        cases: list[dict[str, Any]],
    ) -> None:
        self.args = args
        self.claude = claude
        self.cases = {c["id"]: c for c in cases}
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        # Absolute: claude runs with a temp working folder, so a relative path would break there.
        self.out = (
            Path(args.out) if args.out else RESULTS_ROOT / f"{stamp}-{args.model}"
        ).resolve()
        self.cfg = self.out / "cfg"
        self.raw = self.out / "raw"
        for folder in (self.cfg, self.raw, self.out / "append"):
            folder.mkdir(parents=True, exist_ok=True)
        self.append_files = self._write_append_files(arms)
        self.runs: list[dict[str, Any]] = []
        self.manifest: dict[str, Any] = {}
        self.status: dict[str, Any] = {"complete": False, "stopped_reason": None}
        self.spent = 0.0
        self.error_streak = 0

    def _write_append_files(self, arms: list[str]) -> dict[str, Path]:
        files = {}
        for arm in arms:
            text = evalkit.append_text(arm)
            if text is not None:
                path = self.out / "append" / f"{arm}.txt"
                path.write_text(text, encoding="utf-8", newline="")
                files[arm] = path
        return files

    def load_existing(self) -> None:
        path = self.out / "results.json"
        if self.args.resume and path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            self.runs = data["runs"]
            self.spent = sum(r.get("total_cost_usd") or 0.0 for r in self.runs)

    def save(self, planned: int) -> None:
        self.status.update(
            planned=planned,
            done=len(self.runs),
            spent_client_estimate_usd=round(self.spent, 6),
        )
        payload = {
            "schema": SCHEMA,
            "manifest": self.manifest,
            "status": self.status,
            "runs": self.runs,
        }
        tmp = self.out / "results.json.tmp"
        tmp.write_text(json.dumps(payload, indent=1), encoding="utf-8")
        os.replace(tmp, self.out / "results.json")

    def command(self, arm: str, session_id: str) -> list[str]:
        cmd = [
            self.claude, "--bare", "-p", "--output-format", "json",
            "--model", model_id_for(self.args), "--effort", self.args.effort,
            "--tools", evalkit.TOOLS, "--permission-mode", "acceptEdits",
            "--max-budget-usd", f"{self.args.per_run_usd:.2f}", "--session-id", session_id,
        ]  # fmt: skip
        if arm in self.append_files:
            cmd += ["--append-system-prompt-file", str(self.append_files[arm])]
        if evalkit.ARMS[arm]["role"] == "installed":
            cmd += ["--plugin-dir", str(evalkit.REPO_ROOT)]
        return cmd + list(self.args.claude_arg)

    def env(self) -> dict[str, str]:
        return {
            **os.environ,
            "CLAUDE_CONFIG_DIR": str(self.cfg),
            "DISABLE_AUTOUPDATER": "1",
        }

    def execute(self, item: dict[str, Any]) -> dict[str, Any]:
        case = self.cases[item["case"]]
        session_id = str(uuid.uuid4())
        workdir = Path(tempfile.mkdtemp(prefix="cmeval-"))
        try:
            if case["fixture"]:
                shutil.copytree(case["fixture"], workdir, dirs_exist_ok=True)
            started = time.monotonic()
            stdout, stderr, result = self._call(
                self.command(item["arm"], session_id), case["prompt"], workdir
            )
            wall = time.monotonic() - started
            (self.raw / f"{run_id(item)}.txt").write_text(
                f"{stdout}\n--- stderr ---\n{stderr}", encoding="utf-8"
            )
            transcript = evalkit.read_transcript(self.cfg, session_id)
            text = str((result or {}).get("result") or "")
            graded = evalkit.grade(
                case, workdir, text, transcript["tools"] if transcript else None
            )
        finally:
            if not self.args.keep_work:
                shutil.rmtree(workdir, ignore_errors=True)
        return make_record(item, result, transcript, graded, wall, text)

    def _call(
        self, cmd: list[str], prompt: str, workdir: Path
    ) -> tuple[str, str, dict[str, Any] | None]:
        try:
            done = subprocess.run(
                cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
                cwd=workdir, env=self.env(), timeout=self.args.timeout,
            )  # fmt: skip
        except subprocess.TimeoutExpired:
            return "", "timeout", None
        return done.stdout, done.stderr[-400:], parse_result(done.stdout)


def make_record(
    item: dict[str, Any],
    result: dict[str, Any] | None,
    transcript: dict[str, Any] | None,
    graded: dict[str, Any],
    wall_s: float,
    text: str,
) -> dict[str, Any]:
    """One run as it is stored: numbers and verdicts only, no reply text, paths or session ids."""
    result = result or {}
    requests = transcript["requests"] if transcript else None
    models = (
        sorted({r["model"] for r in requests})
        if requests
        else sorted(result.get("modelUsage") or {})
    )
    return {
        "run_id": run_id(item),
        "arm": item["arm"],
        "case": item["case"],
        "rep": item["rep"],
        # A run that ended in an error (budget cap, API error, timeout) is a fail
        # even if the files check out: the user would not have got a finished answer.
        "passed": graded["passed"] and not (result.get("is_error") or not result),
        "checks": graded["checks"],
        "is_error": bool(result.get("is_error")) or not result,
        "subtype": result.get("subtype") or ("no_json" if not result else None),
        "num_turns": result.get("num_turns"),
        "duration_ms": result.get("duration_ms"),
        "wall_s": round(wall_s, 1),
        "usage": evalkit.slim_usage(result.get("usage") or {}),
        "total_cost_usd": result.get("total_cost_usd"),
        "requests": requests,
        "tools_used": transcript["tools"] if transcript else None,
        "skill_activated": bool(transcript and transcript["skill"]),
        "models_seen": models,
        "result_chars": len(text),
    }


def build_manifest(
    args: argparse.Namespace,
    batch: Batch,
    arms: list[str],
    plan: list[dict[str, Any]],
    version: str,
) -> dict[str, Any]:
    skill = evalkit.SKILL_MD.read_text(encoding="utf-8")
    return {
        "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model_key": args.model,
        "model_id": model_id_for(args),
        "effort": args.effort,
        "cli_version": version,
        "python": platform.python_version(),
        "system": platform.system(),
        "tools": evalkit.TOOLS,
        "permission_mode": "acceptEdits",
        "seed": args.seed,
        "declared_reps": evalkit.N_REPS,
        "reps_requested": args.reps,
        "planned_runs": len(plan),
        "per_run_usd": args.per_run_usd,
        "max_cost_usd": args.max_cost_usd,
        "extra_claude_args": list(args.claude_arg),
        "skill_md_sha256": evalkit.sha256_text(skill.replace("\r\n", "\n")),
        "arms": {a: _arm_manifest(a) for a in arms},
        "cases": {
            cid: {
                "category": c["category"],
                "expect_gain": c["expect_gain"],
                "sha256": c["sha256"],
            }
            for cid, c in batch.cases.items()
        },
    }


def _arm_manifest(arm: str) -> dict[str, Any]:
    text = evalkit.append_text(arm)
    return {
        "role": evalkit.ARMS[arm]["role"],
        "level": evalkit.ARMS[arm].get("level"),
        "append_chars": len(text) if text is not None else 0,
        "append_sha256": evalkit.sha256_text(text) if text is not None else None,
    }


def sanity_gate(record: dict[str, Any]) -> str | None:
    """After the first real run: what is wrong with this setup, so the other runs are never spent on it."""
    if record["subtype"] == "no_json":
        return "claude printed no JSON result (look at raw/ in the results folder for its stderr; is it signed in with an API key or provider credentials, which --bare requires?)"
    if not record["usage"]:
        return "the result carried no usage block"
    if record["requests"] is None:
        return "no transcript under cfg/projects for the session; per-request pricing and tool_used checks need it"
    return None


def run_batch(batch: Batch, plan: list[dict[str, Any]]) -> None:
    args = batch.args
    done_ids = {r["run_id"] for r in batch.runs}
    todo = [item for item in plan if run_id(item) not in done_ids]
    first = True
    for number, item in enumerate(todo, start=len(done_ids) + 1):
        if batch.spent + args.per_run_usd > args.max_cost_usd:
            batch.status["stopped_reason"] = "cap"
            print(
                f"stopping before {run_id(item)}: ${batch.spent:.2f} spent, the next run could cross the ${args.max_cost_usd:.2f} cap"
            )
            return
        record = batch.execute(item)
        batch.runs.append(record)
        batch.spent += record["total_cost_usd"] or 0.0
        batch.save(len(plan))
        verdict = "pass" if record["passed"] else "FAIL"
        print(
            f"[{number}/{len(plan)}] {run_id(item)} {verdict} ${record['total_cost_usd'] or 0.0:.4f} (spent ${batch.spent:.2f} of ${args.max_cost_usd:.2f})"
        )
        problem = sanity_gate(record) if first else None
        first = False
        if problem:
            batch.status["stopped_reason"] = "sanity"
            print(f"stopped after one run: {problem}", file=sys.stderr)
            return
        batch.error_streak = batch.error_streak + 1 if record["is_error"] else 0
        if batch.error_streak >= MAX_CONSECUTIVE_ERRORS:
            batch.status["stopped_reason"] = "errors"
            print(
                f"stopped: {MAX_CONSECUTIVE_ERRORS} runs in a row errored",
                file=sys.stderr,
            )
            return
    batch.status["complete"] = True


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    arms, cases = select(args)
    plan = build_plan(arms, [c["id"] for c in cases], args.reps, args.seed)
    if args.dry_run:
        print_plan(args, arms, cases, plan)
        return 0
    guard(args)
    claude = shutil.which("claude")
    if not claude:
        die("claude is not on PATH")
    version = claude_version(claude)
    if version != args.cli_version:
        die(f"installed claude is {version}, the run is pinned to {args.cli_version}")
    batch = Batch(args, claude, arms, cases)
    batch.load_existing()
    batch.manifest = build_manifest(args, batch, arms, plan, version)
    try:
        run_batch(batch, plan)
    except KeyboardInterrupt:
        batch.status["stopped_reason"] = "interrupted"
    if claude_version(claude) != version:
        batch.status["stopped_reason"] = "claude version changed during the run"
        batch.status["complete"] = False
    batch.save(len(plan))
    print(f"results: {batch.out / 'results.json'}")
    print(
        f"next:    python benchmarks/cost-mode-eval/summarize.py {batch.out / 'results.json'}"
    )
    return 0 if batch.status["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
