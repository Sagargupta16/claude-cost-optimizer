"""Tests for scripts/check-live-pricing.py, run against a trimmed page excerpt.

The fixture holds only the Model pricing and Fast mode pricing tables, and the
rates in MODELS below are frozen copies, so a legitimate rate change in rate.py
never turns these tests red; they check the parsing and the drift rules.

    python -m unittest discover -s scripts/tests -v
"""

from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "check-live-pricing.py"
FIXTURE = HERE / "fixtures" / "pricing-2026-11-03.md"

spec = importlib.util.spec_from_file_location("check_live_pricing", SCRIPT)
live = importlib.util.module_from_spec(spec)
sys.modules["check_live_pricing"] = live
spec.loader.exec_module(live)


def model(name, rates, fast=False, long_prompt=None):
    inp, out, hit, write_5m, write_1h = rates
    row = {
        "name": name,
        "input": inp,
        "output": out,
        "cache_hit": hit,
        "cache_5m_write": write_5m,
        "cache_1h_write": write_1h,
        "fast_mode": fast,
    }
    if long_prompt:
        row["long_prompt"] = long_prompt
    return row


MODELS = {
    "fable-5-1": model("Fable 5.1", (10, 50, 0.25, 12.5, 20)),
    "fable-5": model("Fable 5", (10, 50, 1, 12.5, 20)),
    "opus-5-5": model("Opus 5.5", (4, 20, 0.2, 5, 8), fast=True),
    "opus-5": model("Opus 5", (5, 25, 0.5, 6.25, 10), fast=True),
    "opus-4-8": model("Opus 4.8", (5, 25, 0.5, 6.25, 10), fast=True),
    "opus-4-7": model("Opus 4.7", (5, 25, 0.5, 6.25, 10)),
    "opus-4-6": model("Opus 4.6", (5, 25, 0.5, 6.25, 10)),
    "sonnet-5-5": model("Sonnet 5.5", (2, 10, 0.1, 2.5, 4)),
    "sonnet-5": model("Sonnet 5", (2, 10, 0.2, 2.5, 4)),
    "sonnet-4-6": model("Sonnet 4.6", (3, 15, 0.3, 3.75, 6)),
    "haiku-5-5": model(
        "Haiku 5.5",
        (0.1, 0.5, 0.01, 0.125, 0.2),
        long_prompt={
            "threshold": 100_000,
            "input": 0.5,
            "output": 2.5,
            "cache_hit": 0.05,
            "cache_5m_write": 0.625,
            "cache_1h_write": 1,
        },
    ),
    "haiku-4-5": model("Haiku 4.5", (1, 5, 0.1, 1.25, 2)),
}
ALIASES = {
    "mythos-5-1": "fable-5-1",
    "mythos-5": "fable-5",
    "opus-4-5": "opus-4-6",
    "sonnet-4-5": "sonnet-4-6",
}


def page() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def report_for(text: str, models=None) -> "live.Report":
    return live.compare(
        live.parse_model_table(text),
        live.parse_fast_table(text),
        models or MODELS,
        ALIASES,
    )


def edit_row(text: str, name: str, old: str, new: str) -> str:
    """Replace `old` with `new` on the one table row whose name cell starts `name`."""
    out, hit = [], 0
    for line in text.splitlines():
        if line.startswith(f"| {name} ") or line.startswith(f"| {name}<"):
            line, hit = line.replace(old, new), hit + 1
        out.append(line)
    assert hit == 1, f"{name!r} matched {hit} rows"
    return "\n".join(out)


class ParsePage(unittest.TestCase):
    def test_model_table_has_every_row(self):
        rows = live.parse_model_table(page())
        self.assertEqual(len(rows), 21)
        names = {row.name for row in rows}
        self.assertIn("Fable 5.1", names)
        self.assertIn("Opus 4.1", names)  # retired link with nested parentheses
        self.assertIn("Haiku 3.5", names)

    def test_footnote_marks_do_not_break_prices(self):
        by_name = {row.name: row for row in live.parse_model_table(page())}
        self.assertEqual(by_name["Fable 5.1"].rates["cache_hit"], 0.25)
        self.assertEqual(by_name["Sonnet 5"].rates["input"], 2)
        self.assertEqual(by_name["Sonnet 5"].rates["output"], 10)

    def test_haiku_55_has_two_tiers_at_100000(self):
        rows = [r for r in live.parse_model_table(page()) if r.name == "Haiku 5.5"]
        self.assertEqual([r.tier for r in rows], ["low", "long"])
        self.assertEqual({r.threshold for r in rows}, {100_000})
        self.assertEqual(rows[1].rates["input"], 0.5)

    def test_fast_table_splits_a_combined_cell(self):
        fast = live.parse_fast_table(page())
        self.assertEqual(fast[0].names, ("Opus 5.5",))
        self.assertEqual(fast[1].names, ("Opus 5", "Opus 4.8"))
        self.assertEqual(fast[1].rates, {"input": 10, "output": 50})

    def test_reworded_column_headers_still_parse(self):
        text = page().replace("Cache hits and refreshes", "Cache hit price")
        text = text.replace("Base input tokens", "Input price")
        self.assertEqual(len(live.parse_model_table(text)), 21)

    def test_missing_column_is_a_parse_failure(self):
        text = page().replace("5m cache writes", "Short writes")
        with self.assertRaises(live.ParseError):
            live.parse_model_table(text)

    def test_missing_section_is_a_parse_failure(self):
        with self.assertRaises(live.ParseError):
            live.parse_model_table("# Pricing\n\nNo tables here.\n")
        with self.assertRaises(live.ParseError):
            live.parse_fast_table(page().replace("### Fast mode pricing", "### Speed"))


class Compare(unittest.TestCase):
    def test_fixture_matches_frozen_rates(self):
        report = report_for(page())
        self.assertEqual(report.drift, [])
        self.assertEqual(report.compared, 93)
        statuses = {line.label: line.status for line in report.models}
        self.assertEqual(statuses["Opus 4.1"], "not carried (known)")
        self.assertEqual(statuses["Mythos 5.1"], "ok (priced like Fable 5.1)")

    def test_a_changed_rate_is_drift(self):
        changed = copy.deepcopy(MODELS)
        changed["opus-5-5"]["cache_hit"] = 0.4
        report = report_for(page(), changed)
        self.assertEqual(len(report.drift), 1)
        self.assertIn("Opus 5.5 cache_hit: rate.py has $0.40", report.drift[0])
        self.assertIn("the page has $0.20", report.drift[0])

    def test_a_model_missing_from_the_page_is_drift(self):
        text = "\n".join(
            line
            for line in page().splitlines()
            if not line.startswith("| Claude Opus 4.6")
        )
        report = report_for(text)
        self.assertEqual(len(report.drift), 1)
        self.assertIn("rate.py carries Opus 4.6", report.drift[0])

    def test_an_unknown_new_model_is_drift(self):
        row = next(l for l in page().splitlines() if l.startswith("| Claude Opus 5.5"))
        text = page().replace(row, row + "\n" + row.replace("Opus 5.5", "Opus 5.6"))
        report = report_for(text)
        self.assertEqual(len(report.drift), 1)
        self.assertIn("the page lists Opus 5.6", report.drift[0])
        self.assertIn("NEW MODEL", {line.status for line in report.models})

    def test_an_alias_priced_differently_is_drift(self):
        text = edit_row(page(), "Claude Opus 4.5", "$0.50 / MTok", "$0.60 / MTok")
        report = report_for(text)
        self.assertEqual(len(report.drift), 1)
        self.assertIn("Opus 4.5 cache_hit: rate.py has $0.50", report.drift[0])

    def test_a_moved_haiku_threshold_is_drift(self):
        text = page().replace("over 100,000 tokens", "over 200,000 tokens")
        report = report_for(text)
        self.assertEqual(len(report.drift), 1)
        self.assertIn("switches tier at 200,000", report.drift[0])

    def test_a_missing_haiku_tier_is_drift(self):
        text = "\n".join(
            line for line in page().splitlines() if "over 100,000 tokens" not in line
        )
        report = report_for(text)
        self.assertTrue(any("page lists [low]" in d for d in report.drift))

    def test_fast_mode_must_stay_2x_base(self):
        text = page().replace("$8 USD / MTok", "$9 USD / MTok")
        report = report_for(text)
        self.assertEqual(len(report.drift), 1)
        self.assertIn("Fast mode Opus 5.5 input: 2x rate.py is $8", report.drift[0])

    def test_a_model_dropped_from_fast_mode_is_drift(self):
        text = page().replace("Claude Opus 5 / Claude Opus 4.8", "Claude Opus 5")
        report = report_for(text)
        self.assertEqual(len(report.drift), 1)
        self.assertIn("fast_mode for Opus 4.8", report.drift[0])


class Fetch(unittest.TestCase):
    def test_three_attempts_then_a_fetch_error(self):
        sleep = mock.Mock()
        boom = urllib.error.URLError("no route")
        with mock.patch.object(live.urllib.request, "urlopen", side_effect=boom) as get:
            with self.assertRaises(live.FetchError) as caught:
                live.fetch("https://example.test/p.md", sleep=sleep)
        self.assertEqual(get.call_count, 3)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [2, 4])
        self.assertIn("after 3 attempts", str(caught.exception))

    def test_a_retry_can_succeed(self):
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b"## Model pricing"
        sleep = mock.Mock()
        outcomes = [urllib.error.URLError("blip"), response]
        with mock.patch.object(live.urllib.request, "urlopen", side_effect=outcomes):
            text = live.fetch("https://example.test/p.md", sleep=sleep)
        self.assertEqual(text, "## Model pricing")
        sleep.assert_called_once_with(2)

    def test_the_request_names_itself(self):
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b"x"
        with mock.patch.object(
            live.urllib.request, "urlopen", return_value=response
        ) as get:
            live.fetch("https://example.test/p.md")
        sent = get.call_args.args[0]
        self.assertIn("claude-cost-optimizer", sent.get_header("User-agent"))


class LoadRates(unittest.TestCase):
    def test_the_real_rate_py_is_readable(self):
        models, aliases = live.load_rates(live.DEFAULT_RATE_PY)
        self.assertGreaterEqual(len(models), 12)
        self.assertIn("mythos-5-1", aliases)
        for row in models.values():
            for name in live.RATE_FIELDS:
                self.assertIn(name, row)

    def test_a_non_literal_table_is_a_parse_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "rate.py"
            bad.write_text(
                "MODELS = dict(a=1)\n_PRICE_ALIASES = {}\n", encoding="utf-8"
            )
            with self.assertRaises(live.ParseError):
                live.load_rates(bad)


class Main(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)

    def rate_py(self, models) -> Path:
        path = self.tmp / "rate.py"
        path.write_text(f"MODELS = {models!r}\n_PRICE_ALIASES = {ALIASES!r}\n")
        return path

    def run_main(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = live.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_clean_run_exits_0(self):
        code, out, _ = self.run_main(
            "--file", str(FIXTURE), "--rate-py", str(self.rate_py(MODELS))
        )
        self.assertEqual(code, 0)
        self.assertIn("0 drift", out)

    def test_drift_exits_1_and_lists_it(self):
        changed = copy.deepcopy(MODELS)
        changed["sonnet-5-5"]["output"] = 12
        code, out, _ = self.run_main(
            "--file", str(FIXTURE), "--rate-py", str(self.rate_py(changed))
        )
        self.assertEqual(code, 1)
        self.assertIn("DRIFT (1):", out)
        self.assertIn("Sonnet 5.5 output: rate.py has $12", out)

    def test_markdown_prints_the_per_model_table(self):
        code, out, _ = self.run_main(
            "--markdown", "--file", str(FIXTURE), "--rate-py", str(self.rate_py(MODELS))
        )
        self.assertEqual(code, 0)
        self.assertIn("| Fable 5.1 | $10 | $12.50 | $20 | $0.25 | $50 | ok |", out)
        self.assertIn("| Haiku 5.5 (prompts over 100,000) | $0.50 |", out)

    def test_an_unparseable_page_exits_2(self):
        bad = self.tmp / "page.md"
        bad.write_text("# Pricing\n", encoding="utf-8")
        code, out, err = self.run_main(
            "--markdown", "--file", str(bad), "--rate-py", str(self.rate_py(MODELS))
        )
        self.assertEqual(code, 2)
        self.assertTrue(err.startswith("check-live-pricing: parse failed"))
        self.assertIn("could not complete", out)

    def test_a_failed_download_exits_2_with_the_fetch_marker(self):
        failure = live.FetchError("https://example.test: no route")
        with mock.patch.object(live, "fetch", side_effect=failure):
            code, _, err = self.run_main("--rate-py", str(self.rate_py(MODELS)))
        self.assertEqual(code, 2)
        self.assertTrue(err.startswith("check-live-pricing: fetch failed"))


if __name__ == "__main__":
    unittest.main()
