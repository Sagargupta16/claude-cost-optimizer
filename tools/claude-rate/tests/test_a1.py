"""Fixture tests for the --usage reports: cache breaks, spend by class and session, limit hits.

Stdlib only (unittest). Run from the repo root:

    python -m unittest discover -s tools/claude-rate/tests -v

The fixture is a synthetic Claude Code config dir (CLAUDE_CONFIG_DIR) with one
cache break per cause, a compaction, a 1-hour cache write, Haiku 5.5 requests over
its 100K-token tier, a subagent file with its meta.json plus a nested one without,
an unpriced model and three limit messages. Every expected dollar figure is written
out as arithmetic from the posted per-1M rates in docs/pricing-data.md.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

_RATE_PY = Path(__file__).resolve().parent.parent / "rate.py"
_spec = importlib.util.spec_from_file_location("rate", _RATE_PY)
assert _spec
assert _spec.loader
rate = importlib.util.module_from_spec(_spec)
sys.modules["rate"] = rate  # dataclasses resolve annotations through sys.modules
_spec.loader.exec_module(rate)

# Two days ago at 10:00 UTC, so every record sits inside a 30-day window.
BASE = (datetime.now(timezone.utc) - timedelta(days=2)).replace(
    hour=10, minute=0, second=0, microsecond=0
)
OPUS, SONNET, OPUS_47, HAIKU = (
    "claude-opus-5-5",
    "claude-sonnet-5-5",
    "claude-opus-4-7",
    "claude-haiku-5-5",
)
SKILL_CHARS = 4_000


def per_m(tokens: float, dollars_per_million: float) -> float:
    return tokens * dollars_per_million / 1_000_000


def ts(minutes: float) -> str:
    return (BASE + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def request(
    mid: str,
    minutes: float,
    model: str,
    session: str,
    *,
    read: int = 0,
    write: int = 0,
    write_1h: int = 0,
    fresh: int = 0,
    out: int = 100,
    speed: str = "standard",
    effort: str = "xhigh",
    version: str = "2.1.300",
    agent: str | None = None,
    diagnostics: dict | None = None,
) -> dict:
    usage = {
        "input_tokens": fresh,
        "cache_read_input_tokens": read,
        "cache_creation_input_tokens": write + write_1h,
        "output_tokens": out,
        "speed": speed,
        "cache_creation": {
            "ephemeral_5m_input_tokens": write,
            "ephemeral_1h_input_tokens": write_1h,
        },
    }
    message = {"id": mid, "model": model, "usage": usage}
    if diagnostics:
        message["diagnostics"] = diagnostics
    record = {
        "type": "assistant",
        "timestamp": ts(minutes),
        "sessionId": session,
        "isSidechain": agent is not None,
        "effort": effort,
        "version": version,
        "message": message,
    }
    if agent:
        record["agentId"] = agent
    return record


def limit_message(minutes: float, session: str, error: str, text: str) -> dict:
    return {
        "type": "assistant",
        "timestamp": ts(minutes),
        "sessionId": session,
        "isApiErrorMessage": True,
        "error": error,
        "message": {
            "id": f"err-{minutes}",
            "model": "<synthetic>",
            "content": [{"type": "text", "text": text}],
        },
    }


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Compact separators, as Claude Code writes them ('"isApiErrorMessage":true').
    path.write_text(
        "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in records),
        encoding="utf-8",
    )


def build_fixture(config_dir: Path) -> None:
    projects = config_dir / "projects"
    s1 = [
        request("s1-1", 0, OPUS, "S1", fresh=10, write=50_000, out=1_000),
        request("s1-2", 1, OPUS, "S1", read=50_000, write=2_000, out=500),
        # 19 minutes after a 5m write: idle 5-60 min.
        request("s1-3", 20, OPUS, "S1", write=54_000, out=500),
        {
            "type": "system",
            "subtype": "compact_boundary",
            "timestamp": ts(25),
            "sessionId": "S1",
            "compactMetadata": {
                "trigger": "auto",
                "preTokens": 54_000,
                "postTokens": 5_000,
            },
        },
        request("s1-4", 25.5, OPUS, "S1", fresh=5, write=20_000, out=800),
        request("s1-5", 26, SONNET, "S1", write=22_000),
        request("s1-6", 27, SONNET, "S1", read=22_000, write_1h=3_000),
        # 23 minutes later, but the last write was 1h: the version change is the cause.
        request("s1-7", 50, SONNET, "S1", write=25_000, version="2.1.301"),
        # Effort change on Sonnet 5.5 keeps the cache, so this break stays unknown.
        request(
            "s1-8", 51, SONNET, "S1", write=25_000, version="2.1.301", effort="low"
        ),
    ]
    write_jsonl(projects / "proj-a" / "S1.jsonl", s1)
    sub = projects / "proj-a" / "S1" / "subagents"
    write_jsonl(
        sub / "agent-a1.jsonl",
        [
            request(
                "a1-1", 5, HAIKU, "S1", fresh=100, write=99_950, out=1_000, agent="a1"
            ),
            request(
                "a1-2",
                6,
                HAIKU,
                "S1",
                fresh=100,
                read=99_950,
                write=50,
                out=500,
                agent="a1",
            ),
        ],
    )
    (sub / "agent-a1.meta.json").write_text(
        json.dumps({"agentType": "Explore"}), encoding="utf-8"
    )
    write_jsonl(
        sub / "workflows" / "wf_1" / "agent-b2.jsonl",
        [
            request("b2-1", 7, HAIKU, "S1", fresh=10, write=5_000, agent="b2"),
        ],
    )
    write_jsonl(
        projects / "proj-b" / "S2.jsonl",
        [
            request("s2-1", 60, OPUS, "S2", write=30_000),
            request("s2-2", 61, OPUS, "S2", write=30_000, speed="fast"),
            limit_message(
                65, "S2", "rate_limit", "You've hit your weekly limit - resets 3pm"
            ),
            limit_message(
                66,
                "S2",
                "rate_limit",
                "API Error: Request rejected (429) - Too many tokens",
            ),
            limit_message(
                67, "S2", "billing_error", "You've hit your monthly spend limit"
            ),
        ],
    )
    write_jsonl(
        projects / "proj-b" / "S3.jsonl",
        [
            request("s3-1", 120, OPUS_47, "S3", write=10_000, effort="high"),
            request("s3-2", 121, OPUS_47, "S3", write=10_000, effort="low"),
            request(
                "s3-3",
                122,
                OPUS_47,
                "S3",
                write=10_000,
                effort="low",
                diagnostics={"cache_miss_reason": {"type": "tools_changed"}},
            ),
            request("s3-4", 423, OPUS_47, "S3", write=10_000, effort="low"),
        ],
    )
    write_jsonl(
        projects / "proj-b" / "S4.jsonl",
        [
            request("s4-1", 130, "claude-mystery-9", "S4", write=1_000),
            request("s4-2", 131, "claude-mystery-9", "S4", write=1_000),
        ],
    )
    skill = config_dir / "skills" / "cost-mode" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("x" * SKILL_CHARS, encoding="utf-8")


class _Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        build_fixture(Path(cls._tmp.name))
        cls._env = mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": cls._tmp.name})
        cls._env.start()
        cls.totals = rate.collect_usage(30)
        cls.spend, cls.breaks = rate._a1_pass(cls.totals)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._env.stop()
        cls._tmp.cleanup()


class ClassDollars(unittest.TestCase):
    def test_classes_sum_to_request_cost_with_fast_mode(self) -> None:
        usage = {
            "input_tokens": 10,
            "cache_read_input_tokens": 1_000,
            "cache_creation_input_tokens": 3_000,
            "cache_creation": {"ephemeral_1h_input_tokens": 1_000},
            "output_tokens": 200,
            "speed": "fast",
        }
        classes = rate._class_dollars(rate.MODELS["opus-5-5"], usage)
        total, _ = rate._request_cost(rate.MODELS["opus-5-5"], usage)
        self.assertAlmostEqual(sum(classes.values()), total, places=12)
        self.assertAlmostEqual(classes["output"], per_m(200, 20.00 * 2), places=12)
        self.assertAlmostEqual(
            classes["cache_1h_write"], per_m(1_000, 8.00 * 2), places=12
        )


class CacheBreaks(_Fixture):
    def test_one_break_per_cause(self) -> None:
        expected = {
            ("idle 5-60 min", "main"): (52_000, per_m(52_000, 5.00 - 0.20)),
            ("compaction", "main"): (20_000, per_m(20_000, 5.00 - 0.20)),
            ("model switch", "main"): (20_000, per_m(20_000, 2.50 - 0.10)),
            ("version change", "main"): (25_000, per_m(25_000, 2.50 - 0.10)),
            ("unknown", "main"): (25_000, per_m(25_000, 2.50 - 0.10)),
            ("fast mode toggle", "main"): (30_000, per_m(30_000, (5.00 - 0.20) * 2)),
            ("effort change", "main"): (10_000, per_m(10_000, 6.25 - 0.50)),
            ("reported: tools_changed", "main"): (10_000, per_m(10_000, 6.25 - 0.50)),
            ("idle over 4 h", "main"): (10_000, per_m(10_000, 6.25 - 0.50)),
        }
        self.assertEqual(set(self.breaks.causes), set(expected))
        for key, (tokens, dollars) in expected.items():
            breaks, rebuilt, extra = self.breaks.causes[key]
            self.assertEqual((breaks, rebuilt), (1, tokens), key)
            self.assertAlmostEqual(extra, dollars, places=12, msg=key)

    def test_ttl_what_if_main_reports_a_negative_net(self) -> None:
        ttl = self.breaks.ttl["main"]
        saved = per_m(52_000, 5.00 - 0.20)
        premium = (
            per_m(50_000 + 2_000 + 54_000 + 20_000, 8.00 - 5.00)  # Opus 5.5, S1
            + per_m(22_000 + 25_000 + 25_000, 4.00 - 2.50)  # Sonnet 5.5, S1
            + per_m(30_000, 8.00 - 5.00)
            + per_m(30_000, (8.00 - 5.00) * 2)  # Opus 5.5, S2, second one fast
            + per_m(4 * 10_000, 10.00 - 6.25)  # Opus 4.7, S3
        )
        extra = premium - per_m(
            52_000, 8.00 - 5.00
        )  # the idle rebuild would not be written again
        self.assertAlmostEqual(ttl.saved, saved, places=12)
        self.assertAlmostEqual(ttl.premium - ttl.not_rewritten, extra, places=12)
        facts = rate._ttl_facts("main", ttl, 30)
        self.assertAlmostEqual(facts["net_dollars"], round(saved - extra, 2))
        self.assertLess(facts["net_dollars"], 0)
        self.assertEqual(facts["verdict"], "skip")
        self.assertEqual(facts["break_even_model"], "Opus 5.5")
        self.assertAlmostEqual(
            facts["break_even_share"], round((8.00 - 5.00) / (8.00 - 0.20), 4)
        )
        self.assertEqual(ttl.writes_1h, 3_000)

    def test_ttl_what_if_subagents(self) -> None:
        ttl = self.breaks.ttl["subagents"]
        premium = per_m(99_950 + 50, 1.00 - 0.625) + per_m(
            5_000, 0.20 - 0.125
        )  # long tier, then base
        self.assertAlmostEqual(ttl.premium, premium, places=12)
        self.assertEqual(rate._ttl_facts("subagents", ttl, 30)["verdict"], "skip")

    def test_compaction_by_trigger_uses_the_first_live_prompt(self) -> None:
        self.assertEqual(self.breaks.compactions, {"auto": [1, 54_000, 5 + 20_000, 1]})

    def test_haiku_long_prompt_premium(self) -> None:
        long_tier = (
            per_m(100, 0.50)
            + per_m(99_950, 0.625)
            + per_m(1_000, 2.50)
            + per_m(100, 0.50)
            + per_m(99_950, 0.05)
            + per_m(50, 0.625)
            + per_m(500, 2.50)
        )
        base = (
            per_m(100, 0.10)
            + per_m(99_950, 0.125)
            + per_m(1_000, 0.50)
            + per_m(100, 0.10)
            + per_m(99_950, 0.01)
            + per_m(50, 0.125)
            + per_m(500, 0.50)
        )
        over, haiku, premium = self.breaks.haiku
        self.assertEqual((over, haiku), (2, 3))
        self.assertAlmostEqual(premium, long_tier - base, places=12)


class SpendBySession(_Fixture):
    def test_classes_sum_to_list_price(self) -> None:
        listed = sum(row["dollars"] for row in self.totals.by_model.values())
        self.assertAlmostEqual(sum(self.spend.by_class.values()), listed, places=9)
        self.assertAlmostEqual(self.spend.total, listed, places=9)

    def test_subagents_by_type_and_session_rollup(self) -> None:
        facts = rate._agent_type_facts(self.spend)
        self.assertEqual((facts["subagent_files"], facts["type_known_files"]), (2, 1))
        explore = (
            per_m(100, 0.50)
            + per_m(99_950, 0.625)
            + per_m(1_000, 2.50)
            + per_m(100, 0.50)
            + per_m(99_950, 0.05)
            + per_m(50, 0.625)
            + per_m(500, 2.50)
        )
        unknown = per_m(10, 0.10) + per_m(5_000, 0.125) + per_m(100, 0.50)
        self.assertAlmostEqual(
            self.spend.types["Explore"]["dollars"], explore, places=12
        )
        self.assertAlmostEqual(
            self.spend.types["unknown"]["dollars"], unknown, places=12
        )
        self.assertAlmostEqual(
            self.spend.sessions["S1"]["subagents"], explore + unknown, places=12
        )
        self.assertEqual(set(self.spend.sessions), {"S1", "S2", "S3"})

    def test_cost_mode_break_even(self) -> None:
        reads = 1.3 * (
            4 * 0.20 + 4 * 0.10 + 0.20 + 0.40 + 4 * 0.50
        )  # every main request, cache-read rate
        writes = 1.3 * (
            5.00 + 5.00 + 6.25
        )  # one 5m write per main session, first request's model
        context = per_m(SKILL_CHARS / 4, reads + writes)
        output = (
            per_m(1_000 + 500 + 500 + 800, 20.00)
            + per_m(4 * 100, 10.00)
            + per_m(100, 20.00)
            + per_m(100, 40.00)
            + per_m(4 * 100, 25.00)
        )
        facts = rate._cost_mode_break_even(self.spend, None)
        self.assertIsNotNone(facts)
        self.assertEqual(facts["chars"], SKILL_CHARS)
        self.assertAlmostEqual(facts["required_output_cut"], round(context / output, 4))


class LimitHitsAndFacts(_Fixture):
    def test_limit_hits_by_kind(self) -> None:
        hits = rate._limit_hits(self.totals.events, 30)
        week = "{}-W{:02d}".format(*BASE.isocalendar()[:2])
        self.assertEqual(hits["total"], 3)
        self.assertEqual(hits["by_week"], {week: 3})
        self.assertEqual(
            hits["by_kind"], {"other 429": 1, "spend limit": 1, "weekly": 1}
        )

    def test_usage_facts_keys_and_grade_categories(self) -> None:
        scope = rate.rate_usage(30)
        for key in (
            "cache_breaks",
            "ttl_what_if",
            "compactions",
            "haiku_long_prompt",
            "by_class",
            "caching_net",
            "by_agent_type",
            "top_sessions",
            "unpriced",
            "ceilings",
            "cost_mode_break_even",
            "limit_hits",
        ):
            self.assertIn(key, scope.facts)
        self.assertEqual(
            scope.facts["unpriced"], [{"model": "claude-mystery-9", "requests": 2}]
        )
        self.assertEqual(
            [c.name for c in scope.categories],
            ["Cache hit rate", "Context size", "Model mix"],
        )
        self.assertEqual(scope.facts["cache_breaks"]["breaks"], 9)
        json.dumps(scope.facts)  # serialisable for --json

    def test_text_blocks_print(self) -> None:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rate._print_usage_reports(rate.rate_usage(30).facts)
        text = out.getvalue()
        for label in (
            "By token class",
            "Main thread",
            "Top sessions",
            "cost-mode break-even",
            "Cache breaks",
            "1h TTL what-if, main",
            "Compactions",
            "Haiku 5.5 over",
            "Limit hits: 3",
        ):
            self.assertIn(label, text)


if __name__ == "__main__":
    unittest.main()
