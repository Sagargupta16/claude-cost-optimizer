"""Golden-value tests for claude-rate's cost math.

Stdlib only (unittest), like rate.py itself. Run from the repo root:

    python -m unittest discover -s tools/claude-rate/tests -v

Every expected dollar figure is written out as arithmetic from the posted
per-1M rates in docs/pricing-data.md, not read back from rate.py.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_RATE_PY = Path(__file__).resolve().parent.parent / "rate.py"
_spec = importlib.util.spec_from_file_location("rate", _RATE_PY)
assert _spec
assert _spec.loader
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
        self.assertAlmostEqual(est["per_session"], session, places=2)
        self.assertAlmostEqual(est["per_month"], session * 3 * 22, places=2)
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

    def test_snapshot_region_and_provider_forms(self) -> None:
        cases = {
            "claude-opus-5-5": "opus-5-5",
            "claude-opus-4-1@20250805": "opus-4-1",  # Google Cloud form
            "claude-haiku-4-5-20251001": "haiku-4-5",
            "us.anthropic.claude-opus-5-5[1m]": "opus-5-5",
            "eu.anthropic.claude-sonnet-5-5-v1:0": "sonnet-5-5",
            "apac.anthropic.claude-haiku-5-5-v1:0": "haiku-5-5",
            "global.anthropic.claude-opus-5-5-v1:0": "opus-5-5",
            "anthropic/claude-opus-5-5": "opus-5-5",
            "arn:aws:bedrock:us-east-1:123456789012:inference-profile/us.anthropic.claude-opus-5-5-v1:0": "opus-5-5",
        }
        for model_id, key in cases.items():
            self.assertEqual(rate._model_key(model_id), key, model_id)

    def test_retired_models_and_their_aliases(self) -> None:
        cases = {
            "claude-opus-4-1-20250805": "opus-4-1",
            "anthropic.claude-opus-4-1-20250805-v1:0": "opus-4-1",
            "claude-opus-4-20250514": "opus-4-1",  # Opus 4 bills as Opus 4.1
            "claude-sonnet-4-20250514": "sonnet-4-6",  # Sonnet 4 bills as Sonnet 4.6
            "claude-3-5-haiku-20241022": "haiku-3-5",  # the version comes first
            "anthropic.claude-3-5-haiku-20241022-v1:0": "haiku-3-5",
            "claude-3-5-haiku-latest": "haiku-3-5",
        }
        for model_id, key in cases.items():
            self.assertEqual(rate._model_key(model_id), key, model_id)

    def test_unknown_point_releases_stay_unpriced(self) -> None:
        # A substring match priced the first two at Opus 5 and Fable 5 rates.
        for model_id in (
            "claude-opus-5-6",
            "claude-fable-5-2",
            "claude-sonnet-5-7-20270101",
            "gpt-5",
            "opus",
            "claude-opus",
            "claude-3-7-sonnet-20250219",
            "claude-opus-5-5-extra",
            "us.openai.gpt-6.1-sol",
        ):
            self.assertIsNone(rate._model_key(model_id), model_id)


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


class RetiredRows(unittest.TestCase):
    """Models off the Claude API that Bedrock or Google Cloud still serve (pricing page, read 2026-11-03)."""

    def test_posted_rates(self) -> None:
        # input, 5-minute write, 1-hour write, cache read, output
        expected = {
            "opus-4-1": (15.00, 18.75, 30.00, 1.50, 75.00),
            "haiku-3-5": (0.80, 1.00, 1.60, 0.08, 4.00),
        }
        fields = ("input", "cache_5m_write", "cache_1h_write", "cache_hit", "output")
        for key, rates in expected.items():
            row = rate.MODELS[key]
            self.assertEqual(tuple(row[f] for f in fields), rates, key)
            self.assertEqual(row["lifecycle"], "legacy", key)

    def test_migration_advice_names_the_current_model(self) -> None:
        facts = {
            "by_model": [
                {"key": "opus-4-1", "share": 0.6, "requests": 120},
                {"key": "haiku-3-5", "share": 0.4, "requests": 30},
            ]
        }
        fixes = rate._legacy_fixes(facts)
        self.assertEqual(len(fixes), 2)
        self.assertIn("legacy Opus 4.1 ($15/$75 per 1M). Opus 5.5 is $4/$20", fixes[0])
        self.assertIn("legacy Haiku 3.5 ($0.8/$4 per 1M). Haiku 5.5 is $0.1/$0.5", fixes[1])
        self.assertEqual(rate._score_models(facts, 0).score, 0)  # all spend is legacy


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _agent(name: str, *lines: str) -> str:
    return "\n".join(["---", f"name: {name}", f"description: {name} agent", *lines, "---", "body", ""])


class SubagentFindings(unittest.TestCase):
    def findings(self, files: dict[str, str], env: dict[str, str] | None = None) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            for relative, text in files.items():
                _write(Path(tmp) / relative, text)
            return rate._subagent_findings(Path(tmp), env or {})

    def test_missing_model_is_named_but_inherit_and_pinned_are_not(self) -> None:
        found = self.findings(
            {
                "a.md": _agent("a", "tools: Read"),
                "b.md": _agent("b", "model: inherit", "tools: Read"),
                "c.md": _agent("c", "model: sonnet", "tools: Read"),
            }
        )
        self.assertEqual(len(found), 1)
        self.assertIn("name no `model`", found[0])
        self.assertIn("a.md", found[0])
        self.assertNotIn("b.md", found[0])
        self.assertNotIn("c.md", found[0])

    def test_subagent_model_env_covers_missing_models(self) -> None:
        found = self.findings({"a.md": _agent("a", "tools: Read")}, {"CLAUDE_CODE_SUBAGENT_MODEL": "haiku"})
        self.assertEqual(found, [])

    def test_haiku_alias_flagged_only_on_a_provider_without_a_pin(self) -> None:
        files = {"h.md": _agent("h", "model: haiku  # cheap search", "tools: Read")}
        bedrock = {"CLAUDE_CODE_USE_BEDROCK": "1"}
        found = self.findings(files, bedrock)
        self.assertEqual(len(found), 1)
        self.assertIn("On Bedrock that alias is Haiku 4.5 ($1/$5 per 1M), not Haiku 5.5", found[0])
        self.assertEqual(self.findings(files, {}), [])
        self.assertEqual(self.findings(files, {**bedrock, "ANTHROPIC_DEFAULT_HAIKU_MODEL": "claude-haiku-5-5"}), [])
        self.assertEqual(self.findings(files, {"CLAUDE_CODE_USE_BEDROCK": "0"}), [])

    def test_legacy_full_id_names_the_current_model(self) -> None:
        found = self.findings(
            {
                "old.md": _agent("old", "model: claude-opus-4-8", "tools: Read"),
                "alias.md": _agent("alias", "model: sonnet", "tools: Read"),
                "new.md": _agent("new", "model: claude-opus-5-5", "tools: Read"),
            }
        )
        self.assertEqual(len(found), 1)
        self.assertIn("old.md (claude-opus-4-8 $5/$25 -> Opus 5.5 $4/$20)", found[0])
        self.assertNotIn("alias.md", found[0])
        self.assertNotIn("new.md", found[0])

    def test_open_tools_is_info_and_either_key_clears_it(self) -> None:
        found = self.findings(
            {
                "open.md": _agent("open", "model: sonnet"),
                "allow.md": _agent("allow", "model: sonnet", "tools: Read"),
                "deny.md": _agent("deny", "model: sonnet", "disallowedTools: Bash"),
            }
        )
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0].startswith("info: "))
        self.assertIn("open.md", found[0])
        self.assertNotIn("allow.md", found[0])
        self.assertNotIn("deny.md", found[0])

    def test_subfolders_are_scanned_and_files_without_a_name_are_skipped(self) -> None:
        found = self.findings({"team/deep/a.md": _agent("a", "tools: Read"), "README.md": "no frontmatter\n"})
        self.assertEqual(len(found), 1)
        self.assertIn("team/deep/a.md", found[0])
        self.assertNotIn("README.md", found[0])

    def test_long_name_lists_are_cut(self) -> None:
        files = {f"a{i}.md": _agent(f"a{i}", "tools: Read") for i in range(6)}
        self.assertIn("a0.md, a1.md, a2.md, a3.md, +2 more", self.findings(files)[0])

    def test_shipped_templates_are_clean_and_load(self) -> None:
        templates = Path(__file__).resolve().parents[3] / "templates" / "agents"
        found = rate._subagent_findings(templates, {"CLAUDE_CODE_USE_BEDROCK": "1", "ANTHROPIC_DEFAULT_HAIKU_MODEL": "x"})
        self.assertEqual(found, [])
        scout = rate._frontmatter(rate._text_file(templates / "scout.md"))
        self.assertEqual((scout["model"], scout["effort"], scout["tools"]), ("haiku", "low", "Read, Grep, Glob"))
        self.assertEqual(sorted(p.name for p in templates.glob("*.md")), ["implementer.md", "reviewer.md", "scout.md"])

    def test_project_agent_points_need_a_named_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write(project / ".claude" / "agents" / "README.md", "notes\n")
            self.assertEqual(rate._score_subagents(project), (0, None))
            _write(project / ".claude" / "agents" / "x" / "a.md", _agent("a"))
            self.assertEqual(rate._score_subagents(project), (3, "custom subagent(s) defined"))

    def test_project_env_reads_the_settings_env_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write(project / ".claude" / "settings.json", json.dumps({"env": {"CLAUDE_CODE_USE_BEDROCK": "1"}}))
            self.assertEqual(rate._project_env(project)["CLAUDE_CODE_USE_BEDROCK"], "1")


def _skill(name: str, description: str = "", *lines: str) -> str:
    return "\n".join(["---", f"name: {name}", f"description: {description}", *lines, "---", "body", ""])


class SkillListing(unittest.TestCase):
    def state(self, skills: dict[str, str], user: dict | None = None, project: dict | None = None):
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp) / "home" / ".claude"
            for name, text in skills.items():
                _write(claude_dir / "skills" / name / "SKILL.md", text)
            if project is None:
                return rate._skill_listing_state(claude_dir, user or {}, None)
            _write(Path(tmp) / "proj" / ".claude" / "settings.json", json.dumps(project))
            return rate._skill_listing_state(claude_dir, user or {}, Path(tmp) / "proj")

    def test_cap_is_one_percent_of_the_pinned_models_window_in_characters(self) -> None:
        small = self.state({}, {"model": "claude-haiku-4-5"})  # a 200,000-token window
        self.assertEqual((small.window, small.cap_chars), (200_000, 8_000))
        self.assertIn("Haiku 4.5, the pinned model", small.basis)
        alias = self.state({}, {"model": "sonnet[1m]"})
        self.assertEqual((alias.window, alias.cap_chars), (1_000_000, 40_000))

    def test_unpinned_or_unknown_model_assumes_the_flagship_and_says_so(self) -> None:
        for settings, reason in (({}, "no model pinned"), ({"model": "gpt-5"}, "`gpt-5` is not a model")):
            listing = self.state({}, settings)
            self.assertEqual(listing.window, 1_000_000)
            self.assertIn("Opus 5.5 assumed", listing.basis)
            self.assertIn(reason, listing.basis)

    def test_fraction_and_model_come_from_the_project_over_the_user(self) -> None:
        listing = self.state(
            {},
            {"model": "claude-opus-5-5", "skillListingBudgetFraction": 0.02},
            {"model": "claude-haiku-4-5", "skillListingBudgetFraction": 0.05},
        )
        self.assertEqual((listing.window, listing.fraction, listing.cap_chars), (200_000, 0.05, 40_000))
        for bad in (0, 1.5, "0.5", True):
            self.assertEqual(self.state({}, {"skillListingBudgetFraction": bad}).fraction, 0.01)

    def test_skill_overrides_and_invocation_flag_shrink_the_listing(self) -> None:
        skills = {
            "on": _skill("on", "x" * 100),
            "short": _skill("short", "x" * 100),
            "gone": _skill("gone", "x" * 100),
            "manual": _skill("manual", "x" * 100),
            "flag": _skill("flag", "x" * 100, "disable-model-invocation: true"),
        }
        overrides = {"short": "name-only", "gone": "off", "manual": "user-invocable-only"}
        chars = {name: size for name, size, _ in self.state(skills, {"skillOverrides": overrides}).entries}
        self.assertEqual(chars, {"on": 102, "short": 5, "gone": 0, "manual": 0, "flag": 0})
        project = self.state(skills, {"skillOverrides": {"on": "off"}}, {"skillOverrides": {"on": "name-only"}})
        self.assertEqual({name: size for name, size, _ in project.entries}["on"], 2)

    def test_description_cap_per_skill_is_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(Path(tmp) / "SKILL.md", _skill("big", "x" * 5_000, "when_to_use: y"))
            self.assertEqual(rate._skill_listing_chars(path), 1_536 + len("big"))

    def test_sent_listing_is_capped_but_never_drops_a_name(self) -> None:
        over = rate._SkillListing([("a", 6_000, 1), ("b", 6_000, 1)], 0, 8_000, 0.01, 200_000, "x")
        self.assertTrue(over.over_cap)
        self.assertEqual(over.sent_chars, 8_000)
        names_only = rate._SkillListing([("a", 100, 60), ("b", 100, 60)], 0, 50, 0.01, 200_000, "x")
        self.assertEqual(names_only.sent_chars, 120)
        under = rate._SkillListing([("a", 100, 1)], 0, 8_000, 0.01, 200_000, "x")
        self.assertFalse(under.over_cap)
        self.assertEqual(under.sent_chars, 100)

    def test_over_cap_report_says_removing_a_skill_restores_another_only_then(self) -> None:
        skills = {f"s{i}": _skill(f"s{i}", "x" * 1_500) for i in range(8)}  # about 12,000 characters
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp) / ".claude"
            for name, text in skills.items():
                _write(claude_dir / "skills" / name / "SKILL.md", text)
            capped = rate.score_user_skills(claude_dir, {"model": "claude-haiku-4-5"})
            roomy = rate.score_user_skills(claude_dir, {"model": "claude-opus-5-5"})
        self.assertIn("listing cap, so Claude Code drops the descriptions", " ".join(capped.findings))
        self.assertIn("Removing one skill mostly restores another skill's description", " ".join(capped.findings))
        self.assertIn("cap ~2,000 tokens = 1% of 200,000 (Haiku 4.5, the pinned model)", capped.detail)
        self.assertNotIn("Removing one skill", " ".join(roomy.findings))
        self.assertNotIn("listing cap", " ".join(roomy.findings))

    def test_points_follow_the_tokens_that_are_sent(self) -> None:
        def points(chars: int) -> int:
            listing = rate._SkillListing([("a", chars, 1)], 0, 10**9, 0.01, 1_000_000, "x")
            return rate.score_user_skills(Path("."), {}, None, listing).score

        sizes = (4_000, 4_004, 10_000, 20_000, 20_004, 40_000, 40_004)  # characters; a token is 4 of them
        self.assertEqual([points(chars) for chars in sizes], [20, 16, 16, 11, 6, 6, 2])


class UserScope(unittest.TestCase):
    def test_subagent_descriptions_warn_above_fifteen_thousand_tokens(self) -> None:
        items = [("a", 9_000), ("b", 6_000)]
        self.assertEqual(rate._subagent_description_findings(items), [])
        found = rate._subagent_description_findings([*items, ("c", 1)])
        self.assertEqual(len(found), 1)
        self.assertIn("~15,001 tokens, over the 15,000-token level", found[0])
        self.assertIn("Largest: a ~9,000, b ~6,000, c ~1", found[0])

    def test_description_tokens_count_every_agents_directory_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            _write(home / ".claude" / "agents" / "a.md", _agent("a"))
            dirs = rate._subagent_dirs(home / ".claude", {}, home)  # the project is the home folder
            self.assertEqual(len(dirs), 1)
            self.assertEqual(rate._subagent_description_tokens(dirs), [("a", 2)])  # "a agent" is 7 characters

    def test_rate_user_keeps_its_grade_scale_and_reports_startup_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            claude_dir = home / ".claude"
            _write(claude_dir / "CLAUDE.md", "x" * 400)
            _write(claude_dir / "skills" / "keep" / "SKILL.md", _skill("keep", "d" * 80))
            _write(claude_dir / "skills" / "drop" / "SKILL.md", _skill("drop", "d" * 80))
            _write(claude_dir / "agents" / "a.md", _agent("a", "tools: Read"))
            _write(claude_dir / "settings.json", json.dumps({"model": "opus", "skillOverrides": {"drop": "off"}}))
            project = Path(tmp) / "proj"
            _write(project / ".claude" / "agents" / "p.md", _agent("p", "model: sonnet", "tools: Read"))
            environ = {"CLAUDE_CONFIG_DIR": str(claude_dir), "HOME": str(home), "USERPROFILE": str(home)}
            with mock.patch.dict(os.environ, environ):
                os.environ.pop("CLAUDE_CODE_SUBAGENT_MODEL", None)
                result = rate.rate_user(project)
        self.assertEqual(result.max_score, 100)  # the same five categories as before
        self.assertEqual(len(result.categories), 5)
        startup = result.facts["startup"]
        self.assertEqual(startup["window"], 1_000_000)
        # CLAUDE.md 400/4 + the "keep" skill (4 + 80)/4 + one description of 7 characters per agent, rounded up
        self.assertEqual(startup["tokens"], 100 + 21 + 2 + 2)
        loads = {item["name"]: item["load"] for item in startup["top"]}
        self.assertEqual(loads["CLAUDE.md"], "always-on, pays in full")
        self.assertEqual(loads["keep"], "listing entry")
        self.assertNotIn("drop", loads)
        self.assertTrue(startup["line"].startswith("Startup tokens (estimate, chars/4): ~"))
        self.assertTrue(any("name no `model`" in f for c in result.categories for f in c.findings))
        json.dumps(result.to_dict())


class RateProject(unittest.TestCase):
    def test_empty_project_grades_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = rate.rate(Path(tmp)).to_dict()
        self.assertIn(result["grade"], {"A+", "A", "B", "C", "D", "F"})
        self.assertLessEqual(result["score"], result["max_score"])


if __name__ == "__main__":
    unittest.main()
