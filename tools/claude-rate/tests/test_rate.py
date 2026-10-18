"""Golden-value tests for claude-rate's cost math.

Stdlib only (unittest), like rate.py itself. Run from the repo root:

    python -m unittest discover -s tools/claude-rate/tests -v

Every expected dollar figure is written out as arithmetic from the posted
per-1M rates in docs/pricing-data.md, not read back from rate.py.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

_RATE_PY = Path(__file__).resolve().parent.parent / "rate.py"
_spec = importlib.util.spec_from_file_location("rate", _RATE_PY)
assert _spec and _spec.loader
rate = importlib.util.module_from_spec(_spec)
sys.modules["rate"] = rate  # dataclasses resolve annotations through sys.modules
_spec.loader.exec_module(rate)


def per_m(tokens: float, dollars_per_million: float) -> float:
    return tokens * dollars_per_million / 1_000_000


class RatesForPrompt(unittest.TestCase):
    def test_haiku_5_5_low_tier_up_to_100k(self) -> None:
        rates = rate._rates_for_prompt(rate.MODELS["haiku-5-5"], 100_000)
        self.assertEqual(
            (rates["input"], rates["output"], rates["cache_hit"]), (0.10, 0.50, 0.01)
        )

    def test_haiku_5_5_high_tier_from_100_001(self) -> None:
        rates = rate._rates_for_prompt(rate.MODELS["haiku-5-5"], 100_001)
        self.assertEqual(
            (rates["input"], rates["output"], rates["cache_hit"]), (0.50, 2.50, 0.05)
        )

    def test_flat_models_ignore_prompt_length(self) -> None:
        self.assertEqual(
            rate._rates_for_prompt(rate.MODELS["opus-5-5"], 900_000)["input"], 4.00
        )


class RequestCost(unittest.TestCase):
    """One transcript usage block priced the way Anthropic bills it."""

    def test_opus_5_5_every_token_class(self) -> None:
        usage = {
            "input_tokens": 1_000,
            "cache_read_input_tokens": 50_000,
            "cache_creation_input_tokens": 3_000,
            "cache_creation": {"ephemeral_1h_input_tokens": 1_000},
            "output_tokens": 800,
        }
        dollars, prompt = rate._request_cost(rate.MODELS["opus-5-5"], usage)
        expected = (
            per_m(1_000, 4.00)  # fresh input
            + per_m(50_000, 0.20)  # cache read, 0.05x
            + per_m(2_000, 5.00)  # 5-minute write, 1.25x
            + per_m(1_000, 8.00)  # 1-hour write, 2x
            + per_m(800, 20.00)  # output
        )
        self.assertAlmostEqual(dollars, expected, places=12)
        self.assertAlmostEqual(dollars, 0.048, places=12)
        self.assertEqual(prompt, 54_000)

    def test_haiku_5_5_prompt_length_counts_cache_reads(self) -> None:
        # 100 fresh + 99,901 cache read = 100,001 prompt tokens: the whole request
        # moves to the high tier, output included.
        usage = {
            "input_tokens": 100,
            "cache_read_input_tokens": 99_901,
            "output_tokens": 1_000,
        }
        dollars, prompt = rate._request_cost(rate.MODELS["haiku-5-5"], usage)
        self.assertEqual(prompt, 100_001)
        self.assertAlmostEqual(
            dollars,
            per_m(100, 0.50) + per_m(99_901, 0.05) + per_m(1_000, 2.50),
            places=12,
        )

    def test_fast_mode_doubles_only_where_supported(self) -> None:
        usage = {"input_tokens": 10_000, "output_tokens": 1_000, "speed": "fast"}
        opus, _ = rate._request_cost(rate.MODELS["opus-5-5"], usage)
        sonnet, _ = rate._request_cost(rate.MODELS["sonnet-5-5"], usage)
        self.assertAlmostEqual(
            opus, 2 * (per_m(10_000, 4.00) + per_m(1_000, 20.00)), places=12
        )
        self.assertAlmostEqual(
            sonnet, per_m(10_000, 2.00) + per_m(1_000, 10.00), places=12
        )


class EstimateCosts(unittest.TestCase):
    def test_opus_5_5_session_matches_closed_form(self) -> None:
        # No CLAUDE.md, no MCP: turn t carries (3,500 system + 2,000 file read +
        # 1,500t history) x 1.3 tokenizer overhead. Turn 0 writes it all at $5; each
        # later turn reads the previous prompt at $0.20 and writes 1,950 at $5; 650
        # output tokens a turn at $20.
        prompts = [(3_500 + 2_000 + 1_500 * t) * 1.3 for t in range(30)]
        session = (
            per_m(prompts[0], 5.00)
            + sum(
                per_m(prompts[t - 1], 0.20) + per_m(prompts[t] - prompts[t - 1], 5.00)
                for t in range(1, 30)
            )
            + per_m(30 * 650, 20.00)
        )
        est = rate.estimate_costs(0, 0)["opus-5-5"]
        self.assertEqual(est["per_session"], round(session, 2))
        self.assertEqual(est["per_month"], round(session * 3 * 22, 2))
        self.assertEqual(est["per_session"], 0.91)

    def test_more_context_never_costs_less(self) -> None:
        small = rate.estimate_costs(4_000, 1)
        large = rate.estimate_costs(40_000, 6)
        for key in rate.MODELS:
            self.assertGreaterEqual(
                large[key]["per_session"], small[key]["per_session"], key
            )


class ModelKey(unittest.TestCase):
    def test_transcript_ids_map_to_priced_models(self) -> None:
        cases = {
            "claude-opus-5-5[1m]": "opus-5-5",
            "us.anthropic.claude-opus-5-20260724-v1:0": "opus-5",
            "anthropic.claude-sonnet-5-5": "sonnet-5-5",
            "claude-haiku-5-5": "haiku-5-5",
            "claude-mythos-5-1": "fable-5-1",  # same price as Fable 5.1
        }
        for model_id, key in cases.items():
            self.assertEqual(rate._model_key(model_id), key, model_id)

    def test_unknown_model_is_unpriced(self) -> None:
        self.assertIsNone(rate._model_key("gpt-5"))


class RateTable(unittest.TestCase):
    def test_cache_write_multipliers(self) -> None:
        for key, model in rate.MODELS.items():
            self.assertAlmostEqual(
                model["cache_5m_write"], model["input"] * 1.25, places=9, msg=key
            )
            self.assertAlmostEqual(
                model["cache_1h_write"], model["input"] * 2, places=9, msg=key
            )

    def test_three_cache_read_multipliers(self) -> None:
        expected = {"fable-5-1": 0.025, "opus-5-5": 0.05, "sonnet-5-5": 0.05}
        for key, model in rate.MODELS.items():
            self.assertAlmostEqual(
                model["cache_hit"] / model["input"],
                expected.get(key, 0.1),
                places=9,
                msg=key,
            )


class RateProject(unittest.TestCase):
    def test_empty_project_grades_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = rate.rate(Path(tmp)).to_dict()
        self.assertIn(result["grade"], {"A+", "A", "B", "C", "D", "F"})
        self.assertLessEqual(result["score"], result["max_score"])


if __name__ == "__main__":
    unittest.main()
