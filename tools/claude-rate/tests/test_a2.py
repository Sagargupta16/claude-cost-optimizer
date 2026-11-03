"""Tests for the --usage attribution, what-if, pace, plan-fit and history reports.

Stdlib only (unittest), like rate.py. Run from the repo root:

    python -m unittest discover -s tools/claude-rate/tests -v

Every expected dollar figure is written out as arithmetic from the posted
per-1M rates in docs/pricing-data.md, not read back from rate.py. Fixture
timestamps sit at 12:00Z, so their local date is the same in any timezone
within 12 hours of UTC.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import os
import re
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

_RATE_PY = Path(__file__).resolve().parent.parent / "rate.py"
_REPO = Path(__file__).resolve().parents[3]
if "rate" in sys.modules:
    rate = sys.modules["rate"]
else:
    _spec = importlib.util.spec_from_file_location("rate", _RATE_PY)
    assert _spec
    assert _spec.loader
    rate = importlib.util.module_from_spec(_spec)
    sys.modules["rate"] = rate  # dataclasses resolve annotations through sys.modules
    _spec.loader.exec_module(rate)


def per_m(tokens: float, dollars_per_million: float) -> float:
    return tokens * dollars_per_million / 1_000_000


# Hand-computed list prices of the fixture requests (USD per 1M from docs/pricing-data.md).
# r1 Opus 5.5: 1,000 fresh, 50,000 cache read, 2,000 5m write, 500 output.
R1_OPUS = (
    per_m(1_000, 4) + per_m(50_000, 0.20) + per_m(2_000, 5) + per_m(500, 20)
)  # 0.034
R1_HAIKU = (
    per_m(1_000, 0.10) + per_m(50_000, 0.01) + per_m(2_000, 0.125) + per_m(500, 0.50)
)  # 0.0011
# r2 Opus 5.5: 100 fresh, 60,000 cache read, 1,000 5m write, 1,000 output.
R2_OPUS = (
    per_m(100, 4) + per_m(60_000, 0.20) + per_m(1_000, 5) + per_m(1_000, 20)
)  # 0.0374
R2_HAIKU = (
    per_m(100, 0.10) + per_m(60_000, 0.01) + per_m(1_000, 0.125) + per_m(1_000, 0.50)
)  # 0.001235
# r3 Sonnet 4.6 subagent: 80,000 cache read, 1,000 output. On Haiku 5.5 the 4.7+
# tokenizer makes 1.3x the tokens: 104,000 cache read, over the 100K tier.
R3_SONNET_46 = per_m(80_000, 0.30) + per_m(1_000, 15)  # 0.039
R3_HAIKU = per_m(104_000, 0.05) + per_m(1_300, 2.50)  # 0.00845
# r4 Opus 5.5 in a worktree: 2,000 fresh, 200 output.
R4_OPUS = per_m(2_000, 4) + per_m(200, 20)  # 0.012
R4_HAIKU = per_m(2_000, 0.10) + per_m(200, 0.50)  # 0.0003
# r5 Sonnet 5.5: 5,000 fresh, 10,000 5m write, 300 output.
R5_SONNET = per_m(5_000, 2) + per_m(10_000, 2.50) + per_m(300, 10)  # 0.038
R5_HAIKU = per_m(5_000, 0.10) + per_m(10_000, 0.125) + per_m(300, 0.50)  # 0.0019
TOTAL = R1_OPUS + R2_OPUS + R3_SONNET_46 + R4_OPUS + R5_SONNET  # 0.1604


def _stamp(days_ago: int, minute: int = 0) -> str:
    noon = datetime.now(timezone.utc).replace(
        hour=12, minute=minute, second=0, microsecond=0
    )
    return (noon - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _line(
    msg_id: str,
    model: str,
    usage: dict,
    ts: str,
    session: str,
    *,
    sidechain: bool = False,
    **meta: str,
) -> str:
    record = {
        "type": "assistant",
        "timestamp": ts,
        "sessionId": session,
        "isSidechain": sidechain,
        "message": {
            "id": msg_id,
            "model": model,
            "usage": usage,
            "content": [{"type": "text", "text": "SECRET"}],
        },
        **meta,
    }
    return json.dumps(record)


def build_fixture(config_dir: Path) -> None:
    """Two projects (one with a worktree folder), a subagent file with its meta.json,
    attribution-tagged records, a streamed duplicate, an unpriced model, across 5 days."""
    projects = config_dir / "projects"
    alpha = projects / "-home-u-code-alpha"
    worktree = projects / "-home-u-code-alpha--claude-worktrees-feat-x"
    beta = projects / "-home-u-code-beta"
    agents = alpha / "s1" / "subagents"
    for folder in (alpha, worktree, beta, agents):
        folder.mkdir(parents=True, exist_ok=True)
    common = {
        "cwd": "/home/u/code/alpha",
        "gitBranch": "main",
        "version": "2.1.300",
        "entrypoint": "cli",
    }
    r1 = {
        "input_tokens": 1_000,
        "cache_read_input_tokens": 50_000,
        "cache_creation_input_tokens": 2_000,
        "output_tokens": 500,
    }
    (alpha / "s1.jsonl").write_text(
        "\n".join(
            [
                _line(
                    "r1",
                    "claude-opus-5-5",
                    {**r1, "output_tokens": 100},
                    _stamp(1),
                    "s1",
                    **common,
                ),
                _line(
                    "r1",
                    "claude-opus-5-5",
                    r1,
                    _stamp(1),
                    "s1",
                    attributionSkill="fix-all",
                    **common,
                ),
                _line(
                    "r2",
                    "claude-opus-5-5",
                    {
                        "input_tokens": 100,
                        "cache_read_input_tokens": 60_000,
                        "cache_creation_input_tokens": 1_000,
                        "output_tokens": 1_000,
                    },
                    _stamp(1, 2),
                    "s1",
                    attributionMcpServer="github",
                    **common,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (agents / "agent-a1.jsonl").write_text(
        _line(
            "r3",
            "claude-sonnet-4-6",
            {"cache_read_input_tokens": 80_000, "output_tokens": 1_000},
            _stamp(1, 1),
            "s1",
            sidechain=True,
            attributionAgent="general-purpose",
            **common,
        )
        + "\n",
        encoding="utf-8",
    )
    (agents / "agent-a1.meta.json").write_text(
        json.dumps({"agentType": "general-purpose", "description": "SECRET task text"}),
        encoding="utf-8",
    )
    (worktree / "s2.jsonl").write_text(
        _line(
            "r4",
            "claude-opus-5-5",
            {"input_tokens": 2_000, "output_tokens": 200},
            _stamp(3),
            "s2",
            cwd="/home/u/code/alpha/.claude/worktrees/feat-x",
            gitBranch="feat-x",
            version="2.1.301",
            entrypoint="cli",
        )
        + "\n",
        encoding="utf-8",
    )
    beta_meta = {
        "cwd": "/home/u/code/beta",
        "gitBranch": "main",
        "version": "2.1.301",
        "entrypoint": "claude-desktop",
    }
    (beta / "s3.jsonl").write_text(
        "\n".join(
            [
                _line(
                    "r5",
                    "claude-sonnet-5-5",
                    {
                        "input_tokens": 5_000,
                        "cache_creation_input_tokens": 10_000,
                        "output_tokens": 300,
                    },
                    _stamp(5),
                    "s3",
                    attributionPlugin="orrery",
                    **beta_meta,
                ),
                _line(
                    "r6",
                    "gpt-x",
                    {"input_tokens": 999, "output_tokens": 9},
                    _stamp(5, 5),
                    "s3",
                    **beta_meta,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _options(**overrides: object) -> argparse.Namespace:
    base = {
        "by": None,
        "what_if": None,
        "scope": "all",
        "budget": None,
        "plan": None,
        "history": None,
    }
    return argparse.Namespace(**{**base, **overrides})


def _record(
    model: str, usage: dict, days_ago: float = 1, *, sidechain: bool = False
) -> object:
    ts = (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime(
        "%Y-%m-%dT%H:%M:%S.000Z"
    )
    path = Path("projects/p/s.jsonl")
    return rate._UsageRecord(
        f"m{id(usage)}", model, usage, ts, "s", path, sidechain, {}
    )


class FixtureReports(unittest.TestCase):
    """The reports over a temp CLAUDE_CONFIG_DIR, through rate_usage like the CLI."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        build_fixture(Path(cls.tmp.name))
        views = list(rate._A2_BY_KEYS)
        cls.history = Path(cls.tmp.name) / "history"
        options = _options(
            by=views,
            what_if=["haiku-5-5"],
            plan="max",
            budget=1000.0,
            history=str(cls.history),
        )
        with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": cls.tmp.name}):
            cls.facts = rate.rate_usage(7, options).facts

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def test_total_matches_hand_arithmetic(self) -> None:
        self.assertAlmostEqual(self.facts["list_price_dollars"], round(TOTAL, 2))
        self.assertEqual(self.facts["requests"], 6)

    def test_every_view_sums_to_the_total(self) -> None:
        for name, view in self.facts["by"].items():
            with self.subTest(view=name):
                self.assertAlmostEqual(
                    sum(row["dollars"] for row in view["rows"]), TOTAL, places=3
                )
                self.assertEqual(sum(row["requests"] for row in view["rows"]), 6)

    def test_worktree_folds_into_its_project(self) -> None:
        rows = {row["label"]: row for row in self.facts["by"]["projects"]["rows"]}
        self.assertEqual(set(rows), {"code/alpha", "code/beta"})
        self.assertAlmostEqual(
            rows["code/alpha"]["dollars"],
            R1_OPUS + R2_OPUS + R3_SONNET_46 + R4_OPUS,
            places=6,
        )
        self.assertEqual(rows["code/alpha"]["key"], "-home-u-code-alpha")

    def test_subagent_rolls_up_to_its_session(self) -> None:
        rows = {row["key"]: row for row in self.facts["by"]["sessions"]["rows"]}
        self.assertEqual(set(rows), {"s1", "s2", "s3"})
        self.assertAlmostEqual(
            rows["s1"]["dollars"], R1_OPUS + R2_OPUS + R3_SONNET_46, places=6
        )
        self.assertEqual(rows["s1"]["subagent_requests"], 1)
        self.assertEqual(
            rows["s1"]["active_minutes"], 2
        )  # requests at 12:00, 12:01, 12:02

    def test_attribution_tags_and_coverage(self) -> None:
        skills = self.facts["by"]["skills"]
        rows = {row["key"]: row["dollars"] for row in skills["rows"]}
        self.assertAlmostEqual(rows["fix-all"], R1_OPUS, places=6)
        self.assertAlmostEqual(rows[rate._A2_UNATTRIBUTED], TOTAL - R1_OPUS, places=6)
        self.assertEqual(skills["tagged_requests"], 1)
        self.assertAlmostEqual(skills["coverage"], round(1 / 6, 4))
        self.assertIn("tagged with each skill", skills["label"])
        mcp = {
            row["key"]: row["dollars"]
            for row in self.facts["by"]["mcp_servers"]["rows"]
        }
        self.assertAlmostEqual(mcp["github"], R2_OPUS, places=6)
        agents = {
            row["key"]: row["dollars"] for row in self.facts["by"]["agents"]["rows"]
        }
        self.assertAlmostEqual(agents["general-purpose"], R3_SONNET_46, places=6)

    def test_days_are_zero_filled_without_outliers_under_14_days(self) -> None:
        days = self.facts["by"]["days"]
        # No older transcripts are on disk, so the window starts at the oldest
        # record (5 days back): one row per date from then to today.
        self.assertEqual(len(days["rows"]), 6)
        self.assertEqual(sum(row["dollars"] > 0 for row in days["rows"]), 3)
        self.assertFalse(days["outliers_checked"])
        self.assertFalse(any(row["outlier"] for row in days["rows"]))

    def test_what_if_haiku_matches_hand_arithmetic(self) -> None:
        rows = {row["scope"]: row for row in self.facts["what_if"]["rows"]}
        main_haiku = R1_HAIKU + R2_HAIKU + R4_HAIKU + R5_HAIKU
        self.assertAlmostEqual(
            rows["main"]["modeled"]["haiku-5-5"]["dollars"], main_haiku, places=6
        )
        self.assertAlmostEqual(
            rows["subagents"]["modeled"]["haiku-5-5"]["dollars"], R3_HAIKU, places=6
        )
        self.assertAlmostEqual(rows["all"]["actual_dollars"], TOTAL, places=6)
        self.assertEqual(rows["all"]["unpriced_requests"], 1)
        agent = self.facts["what_if"]["by_agent_type"][0]
        self.assertEqual(
            (agent["agent_type"], agent["kind"]), ("general-purpose", "built-in")
        )
        self.assertIn("CLAUDE_CODE_SUBAGENT_MODEL", agent["advice"])

    def test_startup_floor_skips_subagents(self) -> None:
        rows = {row["entrypoint"]: row for row in self.facts["startup_floor"]["rows"]}
        self.assertEqual(
            rows["cli"]["sessions"], 2
        )  # s1 and s2; the subagent file is not a session start
        self.assertEqual(rows["cli"]["min"], 2_000)  # r4
        self.assertEqual(rows["cli"]["median"], 53_000)  # r1: 1,000 + 50,000 + 2,000
        self.assertEqual(rows["claude-desktop"]["min"], 15_000)  # r5

    def test_pace_plan_and_budget_keys(self) -> None:
        pace = self.facts["pace"]
        self.assertIn("month_to_date", pace)
        self.assertIn("budget", pace)
        # Gaps under 60 minutes: r5 -> r6 (5 min) and r1 -> r3 -> r2 (1 + 1 min).
        self.assertAlmostEqual(pace["active_hours"], round(7 / 60, 2))
        fit = self.facts["plan_fit"]
        self.assertAlmostEqual(fit["ratio"], TOTAL * 30 / fit["days"] / 100, places=2)
        self.assertTrue(
            4 < fit["days"] < 6
        )  # the oldest record is 5 days back at 12:00Z

    def test_history_snapshot_holds_no_paths_or_ids(self) -> None:
        text = (
            self.history / f"usage-{datetime.now().date().isoformat()}.json"
        ).read_text(encoding="utf-8")
        for secret in ("alpha", "beta", "home", "s1", "fix-all", "SECRET", "main"):
            self.assertNotIn(secret, text)
        self.assertEqual(self.facts["history"]["status"], "first")

    def test_no_message_text_reaches_the_output(self) -> None:
        self.assertNotIn("SECRET", json.dumps(self.facts))


class WhatIfMath(unittest.TestCase):
    def test_identity_target_equals_source(self) -> None:
        usage = {
            "input_tokens": 1_000,
            "cache_read_input_tokens": 50_000,
            "cache_creation_input_tokens": 2_000,
            "output_tokens": 500,
        }
        priced = rate._a2_price_all([_record("claude-opus-5-5", usage)])
        self.assertAlmostEqual(
            rate._a2_reprice(priced, ["opus-5-5"])["modeled"]["opus-5-5"]["dollars"],
            R1_OPUS,
        )

    def test_scaled_prompt_over_the_context_window_is_not_priced(self) -> None:
        # Opus 5.5 -> Haiku 4.5 scales by 1.0 / 1.3: 300,000 -> 230,769 (over 200,000);
        # 130,000 -> 100,000 cache read at $0.10 = $0.01.
        big = rate._a2_price_all(
            [_record("claude-opus-5-5", {"cache_read_input_tokens": 300_000})]
        )
        small = rate._a2_price_all(
            [_record("claude-opus-5-5", {"cache_read_input_tokens": 130_000})]
        )
        cell = rate._a2_reprice(big + small, ["haiku-4-5"])["modeled"]["haiku-4-5"]
        self.assertEqual(cell["no_fit_requests"], 1)
        self.assertAlmostEqual(cell["no_fit_actual_dollars"], per_m(300_000, 0.20))
        self.assertAlmostEqual(cell["dollars"], per_m(100_000, 0.10), places=6)

    def test_family_names_resolve_and_unknown_models_fail(self) -> None:
        self.assertEqual(
            rate._a2_model_keys("haiku,Sonnet-5.5"), ["haiku-5-5", "sonnet-5-5"]
        )
        with self.assertRaises(argparse.ArgumentTypeError) as caught:
            rate._a2_model_keys("gpt-5")
        self.assertIn("haiku-5-5", str(caught.exception))


class Outliers(unittest.TestCase):
    def _day_view(self, window_days: int) -> dict:
        records = [
            _record("claude-opus-5-5", {"output_tokens": 500_000}, days_ago=3)
        ]  # $10 at $20 per 1M
        priced = rate._a2_price_all(records)
        now = datetime.now()
        ctx = rate._A2Context(
            priced,
            sum(p.dollars for p in priced),
            now.timestamp() - window_days * 86_400,
            now,
        )
        return rate._a2_day_view(ctx)

    def test_one_big_day_is_an_outlier_on_a_20_day_window(self) -> None:
        view = self._day_view(20)
        self.assertTrue(view["outliers_checked"])
        self.assertEqual(sum(row["outlier"] for row in view["rows"]), 1)

    def test_no_outliers_on_a_7_day_window(self) -> None:
        view = self._day_view(7)
        self.assertFalse(any(row["outlier"] for row in view["rows"]))


class Timestamps(unittest.TestCase):
    def test_z_suffix_parses_as_utc(self) -> None:
        expected = datetime(
            2026, 9, 28, 9, 15, 58, 772_000, tzinfo=timezone.utc
        ).timestamp()
        self.assertEqual(rate._a2_epoch("2026-09-28T09:15:58.772Z"), expected)
        self.assertIsNone(rate._a2_epoch(""))


class PlanPrices(unittest.TestCase):
    def test_plan_prices_equal_pricing_data(self) -> None:
        text = (_REPO / "docs" / "pricing-data.md").read_text(encoding="utf-8")
        for plan, name in (("pro", "Pro"), ("max", "Max"), ("ultra", "Ultra")):
            match = re.search(rf"{name} \$(\d+)/mo", text)
            assert match, name
            self.assertEqual(rate._A2_PLAN_PRICES[plan], int(match.group(1)))


class History(unittest.TestCase):
    def test_deltas_against_an_earlier_snapshot_are_neutral(self) -> None:
        before = {
            "schema_version": 1,
            "days": 7,
            "partial": False,
            "pricing_date": rate._PRICING_VERIFIED_DATE,
            "tool_version": rate._a2_tool_version(),
            "metrics": {"requests": 4, "list_price_dollars": 1.0},
        }
        after = {
            **before,
            "metrics": {key: 0 for key in rate._A2_DELTA_KEYS} | {"requests": 6},
        }
        result = rate._a2_compare(before, after)
        self.assertEqual(result["status"], "comparable")
        self.assertEqual(
            result["deltas"]["requests"], {"before": 4, "after": 6, "change": 2}
        )
        self.assertNotIn("saved", json.dumps(result))
        self.assertEqual(
            rate._a2_compare({**before, "days": 30}, after)["status"], "incomparable"
        )


class Cli(unittest.TestCase):
    def _run(self, *argv: str) -> tuple[int, str]:
        err = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["claude-rate", *argv]),
            contextlib.redirect_stderr(err),
        ):
            with (
                contextlib.redirect_stdout(io.StringIO()),
                self.assertRaises(SystemExit) as caught,
            ):
                rate.main()
        return int(caught.exception.code or 0), err.getvalue()

    def test_report_flags_need_usage(self) -> None:
        code, err = self._run(".", "--by", "session")
        self.assertEqual(code, 2)
        self.assertIn("--by needs --usage", err)

    def test_unknown_view_and_model_are_rejected(self) -> None:
        self.assertEqual(self._run(".", "--usage", "--by", "repo")[0], 2)
        code, err = self._run(".", "--usage", "--what-if", "gpt-5")
        self.assertEqual(code, 2)
        self.assertIn("opus-5-5", err)

    def test_watch_needs_burn_and_15_seconds(self) -> None:
        self.assertEqual(self._run("--watch", "20")[0], 2)
        self.assertEqual(self._run("--burn", "--watch", "5")[0], 2)


if __name__ == "__main__":
    unittest.main()
