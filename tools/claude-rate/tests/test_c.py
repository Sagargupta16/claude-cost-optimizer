"""Golden-value tests for claude-rate's live modes: --statusline, --transcript, --hook cache-guard.

Stdlib only (unittest). Run from the repo root:

    python -m unittest discover -s tools/claude-rate/tests -v

Every expected dollar figure is written out as arithmetic from the posted per-1M
rates in docs/pricing-data.md, not read back from rate.py.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

_RATE_PY = Path(__file__).resolve().parent.parent / "rate.py"
_spec = importlib.util.spec_from_file_location("rate_c", _RATE_PY)
assert _spec
assert _spec.loader
rate = importlib.util.module_from_spec(_spec)
sys.modules["rate_c"] = rate  # dataclasses resolve annotations through sys.modules
_spec.loader.exec_module(rate)

NOW = 1_800_000_000.0


def per_m(tokens: float, dollars_per_million: float) -> float:
    return tokens * dollars_per_million / 1_000_000


def docs_sample() -> dict:
    """The statusLine JSON sample from code.claude.com/docs/en/statusline (read 2026-11-03), trimmed."""
    return {
        "model": {"id": "claude-opus-5-5", "display_name": "Opus"},
        "cost": {"total_cost_usd": 0.01234},
        "context_window": {"used_percentage": 8},
        "prompt_cache": {
            "warm": True,
            "caching_observed": True,
            "ttl": "1h",
            "expires_at": NOW + 42 * 60,
            "misses": 2,
            "hit_ratio": 0.91,
            "last_miss_cause": {
                "causes": ["tools_changed"],
                "tools_added": 2,
                "tools_removed": 0,
            },
            "recache_tokens_if_cold": 45000,
        },
        "fast_mode": False,
        "effort": {"level": "high"},
    }


class RecacheDollars(unittest.TestCase):
    def test_docs_sample_opus_5_5_1h(self) -> None:
        # Opus 5.5: 1h write $8.00, cache read $0.20.
        got = rate._recache_dollars("claude-opus-5-5", 45_000, "1h", False)
        self.assertAlmostEqual(got, per_m(45_000, 8.00 - 0.20))  # $0.351

    def test_5m_ttl_uses_the_5m_write(self) -> None:
        got = rate._recache_dollars("claude-opus-5-5", 45_000, "5m", False)
        self.assertAlmostEqual(got, per_m(45_000, 5.00 - 0.20))  # $0.216

    def test_fast_mode_doubles_on_a_fast_model(self) -> None:
        got = rate._recache_dollars("claude-opus-5-5", 45_000, "1h", True)
        self.assertAlmostEqual(got, 2 * per_m(45_000, 8.00 - 0.20))

    def test_fast_mode_ignored_on_a_model_without_it(self) -> None:
        # Sonnet 5.5: 1h write $4.00, cache read $0.10.
        got = rate._recache_dollars("claude-sonnet-5-5", 45_000, "1h", True)
        self.assertAlmostEqual(got, per_m(45_000, 4.00 - 0.10))

    def test_haiku_5_5_long_prompt_tier_over_100k(self) -> None:
        # Haiku 5.5 above 100,000 prompt tokens: 5m write $0.625, cache read $0.05.
        got = rate._recache_dollars("claude-haiku-5-5", 150_000, "5m", False)
        self.assertAlmostEqual(got, per_m(150_000, 0.625 - 0.05))

    def test_haiku_5_5_low_tier(self) -> None:
        # Haiku 5.5 up to 100,000: 5m write $0.125, cache read $0.01.
        got = rate._recache_dollars("claude-haiku-5-5", 90_000, "5m", False)
        self.assertAlmostEqual(got, per_m(90_000, 0.125 - 0.01))

    def test_unknown_model_or_ttl_has_no_dollar(self) -> None:
        self.assertIsNone(
            rate._recache_dollars("my-gateway-model", 45_000, "1h", False)
        )
        self.assertIsNone(rate._recache_dollars("claude-opus-5-5", 45_000, None, False))


class StatusLine(unittest.TestCase):
    def line(self, payload: dict) -> str:
        return rate.format_statusline(payload, NOW, color=False)

    def test_docs_sample(self) -> None:
        self.assertEqual(
            self.line(docs_sample()),
            "Opus high | ctx 8% | $0.01 est\n"
            "cache warm (1h), cold in 42m | if cold +$0.35 | hit 91% | misses 2 (last: tools_changed)",
        )

    def test_no_prompt_cache_is_one_row(self) -> None:
        payload = docs_sample()
        del payload["prompt_cache"]
        self.assertEqual(self.line(payload), "Opus high | ctx 8% | $0.01 est")

    def test_null_context_and_fast_tag(self) -> None:
        payload = docs_sample()
        payload["context_window"]["used_percentage"] = None
        payload["fast_mode"] = True
        self.assertTrue(self.line(payload).startswith("Opus high fast | ctx -- |"))

    def test_cold_cache_prices_the_next_turn(self) -> None:
        payload = docs_sample()
        payload["prompt_cache"].update(warm=False, expires_at=None)
        self.assertIn(
            "cache cold | next turn re-caches 45K, +$0.35 |", self.line(payload)
        )

    def test_recache_null_after_compaction(self) -> None:
        payload = docs_sample()
        payload["prompt_cache"]["recache_tokens_if_cold"] = None
        self.assertNotIn("$0.35", self.line(payload))
        self.assertIn("cache warm (1h), cold in 42m | hit 91%", self.line(payload))

    def test_expires_at_null_drops_the_countdown(self) -> None:
        payload = docs_sample()
        payload["prompt_cache"]["expires_at"] = None
        self.assertIn("cache warm (1h) | if cold", self.line(payload))

    def test_caching_not_observed(self) -> None:
        payload = docs_sample()
        payload["prompt_cache"] = {"warm": False, "caching_observed": False}
        self.assertTrue(
            self.line(payload).endswith("\ncache off (no cache tokens reported)")
        )

    def test_hit_ratio_null_and_no_cause(self) -> None:
        payload = docs_sample()
        payload["prompt_cache"].update(hit_ratio=None, last_miss_cause=None)
        row = self.line(payload).splitlines()[1]
        self.assertNotIn("hit", row)
        self.assertTrue(row.endswith("| misses 2"))

    def test_several_causes(self) -> None:
        payload = docs_sample()
        payload["prompt_cache"]["last_miss_cause"] = {
            "causes": ["tools_changed", "ttl_expired_5m"]
        }
        self.assertIn(
            "misses 2 (last: tools_changed+ttl_expired_5m)", self.line(payload)
        )

    def test_unknown_model_drops_the_dollar(self) -> None:
        payload = docs_sample()
        payload["model"] = {"id": "my-gateway-model", "display_name": "Gateway"}
        self.assertNotIn("if cold", self.line(payload))

    def test_colour_on_and_off(self) -> None:
        self.assertIn(
            "\033[32m", rate.format_statusline(docs_sample(), NOW, color=True)
        )
        self.assertNotIn(
            "\033[", rate.format_statusline(docs_sample(), NOW, color=False)
        )


class RateLimitSegments(unittest.TestCase):
    def seg(self, used: object, left: float, length: int = 18_000) -> str | None:
        window = {"used_percentage": used, "resets_at": NOW + left}
        return rate._limit_segment(window, "5h", length, NOW, False)

    def test_pace_behind_even_burn(self) -> None:
        # 6,000 s left of 18,000: elapsed 12,000 = 66.7% of the window; 62 - 66.7 = -4.7.
        # Run-out 12,000 x 38 / 62 = 7,355 s, after the reset, so no ETA.
        self.assertEqual(self.seg(62, 6_000), "5h 62% (-5) resets 1h40m")

    def test_run_out_before_reset(self) -> None:
        # 10,800 s left: elapsed 7,200 = 40%; pace 80 - 40 = +40; run-out 7,200 x 20 / 80 = 1,800 s.
        self.assertEqual(self.seg(80, 10_800), "5h 80% (+40, out 30m) resets 3h00m")

    def test_seven_day_window(self) -> None:
        # 4 days left of 7: elapsed 3 days = 42.9%; 41.2 - 42.9 = -1.7; run-out 3d x 58.8 / 41.2 = 4.28d, after reset.
        seg = rate._limit_segment(
            {"used_percentage": 41.2, "resets_at": NOW + 4 * 86_400},
            "7d",
            604_800,
            NOW,
            False,
        )
        self.assertEqual(seg, "7d 41% (-2) resets 4d0h")

    def test_over_101_is_invalid(self) -> None:
        self.assertIsNone(self.seg(1_738_425_600, 6_000))

    def test_100_to_101_clamps(self) -> None:
        self.assertEqual(self.seg(100.6, 6_000), "5h 100% (at limit) resets 1h40m")

    def test_expired_window_is_skipped(self) -> None:
        self.assertIsNone(self.seg(50, 0))
        self.assertIsNone(self.seg(50, -60))

    def test_bool_is_not_a_percentage(self) -> None:
        self.assertIsNone(self.seg(True, 6_000))

    def test_absent_five_hour_window(self) -> None:
        limits = {"seven_day": {"used_percentage": 41.2, "resets_at": NOW + 4 * 86_400}}
        self.assertEqual(
            rate._limit_segments(limits, NOW, False), ["7d 41% (-2) resets 4d0h"]
        )

    def test_spend_limit_with_and_without_dollars(self) -> None:
        spend = {"used_percentage": 62.8, "resets_at": NOW + 86_400}
        self.assertEqual(rate._spend_segment(spend, NOW), "spend 63%")
        spend.update(used_usd=314.12, limit_usd=500, period="monthly")
        self.assertEqual(
            rate._spend_segment(spend, NOW), "spend $314.12/$500.00 monthly"
        )


def iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def local_noon(days_ago: int = 0) -> datetime:
    today = (
        datetime.now().astimezone().replace(hour=12, minute=0, second=0, microsecond=0)
    )
    return today - timedelta(days=days_ago)


def user(prompt: str, when: datetime) -> str:
    return json.dumps(
        {
            "type": "user",
            "promptId": prompt,
            "timestamp": iso(when),
            "message": {"role": "user", "content": "x"},
        }
    )


def assistant(
    mid: str, model: str, usage: dict, when: datetime, sidechain: bool = False
) -> str:
    message = {"id": mid, "model": model, "role": "assistant", "usage": usage}
    return json.dumps(
        {
            "type": "assistant",
            "isSidechain": sidechain,
            "timestamp": iso(when),
            "message": message,
        }
    )


# Opus 5.5: 1,000 fresh x $4 + 10,000 cache read x $0.20 + 2,000 5m write x $5 + 500 out x $20.
USAGE_A = {
    "input_tokens": 1000,
    "cache_read_input_tokens": 10000,
    "cache_creation_input_tokens": 2000,
    "output_tokens": 500,
}
DOLLARS_A = per_m(1000, 4) + per_m(10000, 0.20) + per_m(2000, 5.00) + per_m(500, 20)
# Haiku 5.5 low tier: 2,000 fresh x $0.10 + 1,000 out x $0.50.
USAGE_B = {"input_tokens": 2000, "output_tokens": 1000}
DOLLARS_B = per_m(2000, 0.10) + per_m(1000, 0.50)


class TranscriptPricing(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.state = self.root / "state" / "spend-state.json"
        self.main = self.root / "s1.jsonl"
        noon = local_noon()
        lines = [
            user("p1", noon),
            assistant(
                "msg_A", "claude-opus-5-5", dict(USAGE_A, output_tokens=1), noon
            ),  # first streamed snapshot
            assistant("msg_A", "claude-opus-5-5", USAGE_A, noon),  # final snapshot
        ]
        self.write(self.main, lines)
        sub = self.root / "s1" / "subagents" / "workflows" / "wf_1"
        sub.mkdir(parents=True)
        self.write(
            sub / "agent-b.jsonl",
            [
                user("p1", noon),
                assistant("msg_B", "claude-haiku-5-5", USAGE_B, noon, True),
            ],
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def write(path: Path, lines: list[str], tail: str = "") -> None:
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write("".join(f"{line}\n" for line in lines) + tail)

    def test_session_plus_subagents_once_per_message(self) -> None:
        report = rate.transcript_report(self.main)
        self.assertAlmostEqual(report["dollars"], round(DOLLARS_A + DOLLARS_B, 4))
        self.assertEqual(
            (report["requests"], report["files"], report["state"]), (2, 2, "none")
        )
        self.assertEqual(report["turn"]["prompt_id"], "p1")
        self.assertAlmostEqual(
            report["day"]["dollars"], round(DOLLARS_A + DOLLARS_B, 4)
        )

    def test_subagent_path_maps_to_its_session(self) -> None:
        sub = next((self.root / "s1").rglob("agent-b.jsonl"))
        self.assertEqual(rate.transcript_report(sub)["session_id"], "s1")

    def test_state_reads_only_new_bytes_and_keeps_the_larger_snapshot(self) -> None:
        first = rate.transcript_report(self.main, self.state)
        self.assertEqual(first["state"], "saved")
        later = local_noon()
        # A later snapshot of msg_A with more output adds only its difference: 300 more out x $20.
        self.write(
            self.main,
            [
                assistant(
                    "msg_A", "claude-opus-5-5", dict(USAGE_A, output_tokens=800), later
                )
            ],
        )
        second = rate.transcript_report(self.main, self.state)
        self.assertAlmostEqual(
            second["dollars"], round(DOLLARS_A + per_m(300, 20) + DOLLARS_B, 4)
        )
        self.assertEqual(second["requests"], 2)

    def test_half_written_last_line_waits(self) -> None:
        rate.transcript_report(self.main, self.state)
        line = assistant("msg_C", "claude-haiku-5-5", USAGE_B, local_noon())
        self.write(self.main, [], tail=line[:40])
        partial = rate.transcript_report(self.main, self.state)
        self.assertAlmostEqual(partial["dollars"], round(DOLLARS_A + DOLLARS_B, 4))
        self.write(self.main, [], tail=line[40:] + "\n")
        done = rate.transcript_report(self.main, self.state)
        self.assertAlmostEqual(done["dollars"], round(DOLLARS_A + 2 * DOLLARS_B, 4))
        self.assertEqual(done["requests"], 3)

    def test_day_rollover_keeps_yesterday_out_of_today(self) -> None:
        self.write(
            self.main,
            [assistant("msg_Y", "claude-haiku-5-5", USAGE_B, local_noon(days_ago=1))],
        )
        report = rate.transcript_report(self.main, self.state)
        self.assertAlmostEqual(report["dollars"], round(DOLLARS_A + 2 * DOLLARS_B, 4))
        self.assertAlmostEqual(
            report["day"]["dollars"], round(DOLLARS_A + DOLLARS_B, 4)
        )

    def test_resumed_session_copy_counts_once_in_the_day(self) -> None:
        rate.transcript_report(self.main, self.state)
        resumed = self.root / "s2.jsonl"
        noon = local_noon()
        self.write(
            resumed,
            [
                user("p2", noon),
                assistant("msg_A", "claude-opus-5-5", USAGE_A, noon),
                assistant("msg_D", "claude-haiku-5-5", USAGE_B, noon),
            ],
        )
        report = rate.transcript_report(resumed, self.state)
        self.assertAlmostEqual(report["dollars"], round(DOLLARS_B, 4))
        self.assertAlmostEqual(
            report["day"]["dollars"], round(DOLLARS_A + 2 * DOLLARS_B, 4)
        )
        self.assertEqual(
            report["turn"], {"prompt_id": "p2", "dollars": round(DOLLARS_B, 4)}
        )

    def test_new_prompt_starts_a_new_turn(self) -> None:
        noon = local_noon()
        self.write(
            self.main,
            [user("p2", noon), assistant("msg_E", "claude-haiku-5-5", USAGE_B, noon)],
        )
        report = rate.transcript_report(self.main, self.state)
        self.assertEqual(
            report["turn"], {"prompt_id": "p2", "dollars": round(DOLLARS_B, 4)}
        )
        self.assertEqual(report["prompts"], 2)

    def test_busy_lock_returns_saved_totals(self) -> None:
        rate.transcript_report(self.main, self.state)
        lock = self.state.with_name(self.state.name + ".lock")
        lock.touch()
        wait = rate._LOCK_WAIT_S
        rate._LOCK_WAIT_S = 0.05
        try:
            report = rate.transcript_report(self.main, self.state)
        finally:
            rate._LOCK_WAIT_S = wait
        self.assertEqual(report["state"], "busy")
        self.assertAlmostEqual(report["dollars"], round(DOLLARS_A + DOLLARS_B, 4))

    def test_stale_lock_is_taken_over(self) -> None:
        self.state.parent.mkdir(parents=True)
        lock = self.state.with_name(self.state.name + ".lock")
        lock.touch()
        old = time.time() - 120
        os.utime(lock, (old, old))
        self.assertEqual(
            rate.transcript_report(self.main, self.state)["state"], "saved"
        )
        self.assertFalse(lock.exists())


SWITCH = {
    "hook_event_name": "PreModelSwitch",
    "from_model": "claude-sonnet-5",
    "to_model": "claude-opus-5",
    "context_tokens": 182340,
    "prompt_cache_warm": True,
    "cache_ttl": "5m",
    "estimated_cache_write_usd": 1.1396,
    "pricing": "catalog",
}
RESUME = {
    "hook_event_name": "SessionStart",
    "source": "resume",
    "model": "claude-opus-5",
    "seconds_since_last_response": 5400,
    "context_tokens": 182340,
    "prompt_cache_likely_expired": True,
    "estimated_cache_write_usd": 1.1396,
}


class CacheGuard(unittest.TestCase):
    def message(self, payload: dict) -> str:
        out = rate.cache_guard(payload)
        assert out is not None
        self.assertEqual(set(out), {"systemMessage"})  # never a permissionDecision
        return out["systemMessage"]

    def test_docs_switch_warm(self) -> None:
        # Staying reads 182,340 tokens on Sonnet 5 at $0.20 = $0.036; 1.1396 - 0.036468 = $1.10 more.
        text = self.message(SWITCH)
        self.assertIn("~$1.14 to write them", text)
        self.assertIn(
            "Staying would read the warm cache for ~$0.04, so the switch adds ~$1.10.",
            text,
        )

    def test_switch_cold_compares_with_a_rewrite(self) -> None:
        # Cold: staying re-writes at Sonnet 5's 5m $2.50 = $0.456; 1.1396 - 0.45585 = $0.68.
        text = self.message(dict(SWITCH, prompt_cache_warm=False))
        self.assertIn(
            "re-write the cold cache for ~$0.46, so the switch adds ~$0.68.", text
        )

    def test_default_pricing_is_flagged(self) -> None:
        self.assertIn(
            "assumed a default rate", self.message(dict(SWITCH, pricing="default"))
        )

    def test_no_context_no_message(self) -> None:
        self.assertIsNone(rate.cache_guard(dict(SWITCH, context_tokens=0)))

    def test_estimate_missing_uses_list_price(self) -> None:
        # Opus 5.5 5m write $5.00: 182,340 x 5.00 / 1M = $0.91.
        payload = dict(
            SWITCH, to_model="claude-opus-5-5", estimated_cache_write_usd=None
        )
        self.assertIn("~$0.91 to write them", self.message(payload))

    def transcript(self) -> str:
        tmp = tempfile.NamedTemporaryFile(
            "w", suffix=".jsonl", delete=False, encoding="utf-8"
        )
        usage = {
            "input_tokens": 100,
            "cache_read_input_tokens": 182340,
            "output_tokens": 1000,
        }
        with tmp:
            for n in range(3):
                tmp.write(
                    assistant(f"msg_{n}", "claude-opus-5-5", usage, local_noon()) + "\n"
                )
        self.addCleanup(os.unlink, tmp.name)
        return tmp.name

    def test_downgrade_pays_back(self) -> None:
        # Per request on Opus 5.5: 182,340 x 0.20 + 100 x 4 + 1,000 x 20 = $0.056868;
        # on Sonnet 5.5: 182,340 x 0.10 + 100 x 2 + 1,000 x 10 = $0.028434; saves $0.028434.
        # Switch: 182,340 x 2.50 (Sonnet 5.5 5m write) - 182,340 x 0.20 (Opus 5.5 read) = $0.419382.
        saving = (
            per_m(182340, 0.20)
            + per_m(100, 4)
            + per_m(1000, 20)
            - (per_m(182340, 0.10) + per_m(100, 2) + per_m(1000, 10))
        )
        extra = per_m(182340, 2.50) - per_m(182340, 0.20)
        self.assertEqual(int(-(-extra // saving)), 15)
        payload = dict(
            SWITCH,
            from_model="claude-opus-5-5",
            to_model="claude-sonnet-5-5",
            estimated_cache_write_usd=per_m(182340, 2.50),
            transcript_path=self.transcript(),
        )
        text = self.message(payload)
        self.assertIn(
            "cost ~$0.03 less each on Sonnet 5.5, so the switch pays back after about 15 of them.",
            text,
        )

    def test_upgrade_prints_cost_only(self) -> None:
        payload = dict(
            SWITCH,
            from_model="claude-sonnet-5-5",
            to_model="claude-opus-5-5",
            estimated_cache_write_usd=per_m(182340, 5.00),
            transcript_path=self.transcript(),
        )
        text = self.message(payload)
        self.assertIn("cost ~$0.03 more each on Opus 5.5.", text)
        self.assertNotIn("pays back", text)
        self.assertNotIn("never", text)

    def test_docs_resume(self) -> None:
        text = self.message(RESUME)
        self.assertIn("Resuming after 1h30m", text)
        self.assertIn("re-writes 182K tokens, ~$1.14 (Claude Code's estimate)", text)
        self.assertIn("/rename this session", text)
        self.assertNotIn("/handoff", text)

    def test_resume_quiet_cases(self) -> None:
        self.assertIsNone(
            rate.cache_guard(dict(RESUME, prompt_cache_likely_expired=False))
        )
        self.assertIsNone(rate.cache_guard(dict(RESUME, context_tokens=40_000)))
        self.assertIsNone(rate.cache_guard(dict(RESUME, source="startup")))

    def test_hook_deadline_abandons_slow_work(self) -> None:
        slow = rate.cache_guard
        deadline = rate._HOOK_DEADLINE_S
        rate.cache_guard = lambda payload: time.sleep(5) or {"systemMessage": "late"}
        rate._HOOK_DEADLINE_S = 0.1
        stdin = sys.stdin
        sys.stdin = io.TextIOWrapper(io.BytesIO(json.dumps(SWITCH).encode()))
        out = io.StringIO()
        start = time.monotonic()
        try:
            with contextlib.redirect_stdout(out):
                code = rate._run_hook("cache-guard")
        finally:
            rate.cache_guard, rate._HOOK_DEADLINE_S, sys.stdin = slow, deadline, stdin
        self.assertEqual((code, out.getvalue()), (0, ""))
        self.assertLess(time.monotonic() - start, 1.0)


if __name__ == "__main__":
    unittest.main()
