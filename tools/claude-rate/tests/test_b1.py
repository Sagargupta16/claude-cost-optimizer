"""Tests for the project-audit checks added in claude-rate 0.4.0.

Stdlib only (unittest), like rate.py. Run from the repo root:

    python -m unittest discover -s tools/claude-rate/tests -v

The cost-control table below is repeated, case for case, in
site/src/utils/repoAnalyzer.test.ts, so the CLI, the badge generator, the audit
Action and the web analyzer are checked against one rubric.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def _load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, REPO / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


rate = _load("rate", "tools/claude-rate/rate.py")
generate = _load("badge_generate", "tools/badge-generator/generate.py")
audit = _load("cost_audit", "tools/actions/claude-cost-audit/audit.py")

# (settings, counts as a cost control). Same cases as repoAnalyzer.test.ts.
COST_CONTROL_CASES: list[tuple[dict, bool]] = [
    ({}, False),
    ({"autoCompactWindow": 200000}, True),
    ({"autoCompactWindow": 1000000}, False),
    ({"autoCompactWindow": 99999}, False),
    ({"autoCompactWindow": "200000"}, False),
    ({"modelSettings": {"claude-haiku-5-5": {"autoCompactWindow": 100000}}}, True),
    ({"modelSettings": {"claude-opus-5-5": {"autoCompactWindow": "auto"}}}, False),
    ({"env": {"CLAUDE_CODE_AUTO_COMPACT_WINDOW": "200k"}}, True),
    ({"env": {"CLAUDE_CODE_AUTO_COMPACT_WINDOW": "1M"}}, False),
    ({"env": {"CLAUDE_CODE_AUTO_COMPACT_WINDOW": "200"}}, False),
    ({"env": {"MAX_MCP_OUTPUT_TOKENS": "10000"}}, True),
    ({"env": {"MAX_MCP_OUTPUT_TOKENS": "25000"}}, False),
    ({"env": {"MAX_MCP_OUTPUT_TOKENS": "10k"}}, False),
    ({"env": {"CLAUDE_CODE_SUBAGENT_MODEL": "haiku"}}, False),
    (
        {
            "env": {
                "CLAUDE_CODE_SUBAGENT_MODEL": "haiku",
                "CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "1",
            }
        },
        True,
    ),
    (
        {
            "model": "claude-sonnet-5-5",
            "env": {
                "CLAUDE_CODE_SUBAGENT_MODEL": "sonnet",
                "CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "1",
            },
        },
        False,
    ),
    (
        {
            "model": "claude-opus-5-5",
            "env": {
                "CLAUDE_CODE_SUBAGENT_MODEL": "claude-sonnet-5-5",
                "CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "1",
            },
        },
        True,
    ),
    (
        {
            "env": {
                "CLAUDE_CODE_SUBAGENT_MODEL": "opus",
                "CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "1",
            }
        },
        False,
    ),
    ({"bashOutputMaxChars": 10000}, False),
    ({"env": {"BASH_MAX_OUTPUT_LENGTH": "10000"}}, False),
    ({"effortLevel": "medium"}, True),
    ({"fastMode": True}, False),
]


def _project(files: dict[str, str]) -> Path:
    root = Path(tempfile.mkdtemp()).resolve()
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


class CostControlParity(unittest.TestCase):
    def test_python_graders_agree_on_every_case(self) -> None:
        for settings, expected in COST_CONTROL_CASES:
            with self.subTest(settings=settings):
                self.assertEqual(bool(rate._cost_control_signals(settings)), expected)
                self.assertEqual(generate.has_cost_controls(settings), expected)
                self.assertEqual(audit.has_cost_controls(settings), expected)


class SettingsFindings(unittest.TestCase):
    def _findings(self, settings: dict) -> list[str]:
        root = _project({".claude/settings.json": json.dumps(settings)})
        self.addCleanup(shutil.rmtree, root, True)
        findings = rate.score_settings(root).findings
        self.assertEqual(len(findings), len(generate.settings_findings(settings)))
        self.assertEqual(len(findings), len(audit.settings_findings(settings)))
        return findings

    def test_haiku_alias_on_the_anthropic_api_gets_the_price_line_note(self) -> None:
        findings = self._findings({"model": "haiku"})
        self.assertEqual(len(findings), 1)
        self.assertIn("$0.50/$2.50", findings[0])

    def test_haiku_alias_on_bedrock_is_haiku_4_5_and_gets_no_note(self) -> None:
        self.assertEqual(
            self._findings({"model": "haiku", "env": {"CLAUDE_CODE_USE_BEDROCK": "1"}}),
            [],
        )

    def test_a_haiku_window_under_1m_silences_the_note(self) -> None:
        settings = {
            "model": "claude-haiku-5-5",
            "modelSettings": {"claude-haiku-5-5": {"autoCompactWindow": 100000}},
        }
        self.assertEqual(self._findings(settings), [])

    def test_a_window_for_another_model_does_not_count_for_haiku(self) -> None:
        settings = {
            "model": "claude-haiku-5-5",
            "modelSettings": {"claude-opus-5-5": {"autoCompactWindow": 200000}},
        }
        self.assertEqual(len(self._findings(settings)), 1)

    def test_max_subagents_per_session_is_reported_as_a_no_op(self) -> None:
        findings = self._findings(
            {"env": {"CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION": "50"}}
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("no-op", findings[0])


class McpAndHookAdvice(unittest.TestCase):
    def test_mcp_finding_does_not_say_a_custom_base_url_turns_tool_search_off(
        self,
    ) -> None:
        servers = {f"s{i}": {"command": "x"} for i in range(6)}
        root = _project({".mcp.json": json.dumps({"mcpServers": servers})})
        self.addCleanup(shutil.rmtree, root, True)
        finding = rate.score_mcp_servers(root).findings[0]
        self.assertNotIn("ANTHROPIC_BASE_URL", finding)
        self.assertIn("ENABLE_TOOL_SEARCH=false", finding)

    def test_no_hooks_fix_uses_the_settings_example_shape(self) -> None:
        example = json.loads(
            (REPO / "hooks" / "settings-example.json").read_text(encoding="utf-8")
        )
        # The fix shows the core pair; settings-example.json also carries opt-in events.
        self.assertLessEqual(set(rate._HOOK_EXAMPLE["hooks"]), set(example["hooks"]))
        for groups in rate._HOOK_EXAMPLE["hooks"].values():
            self.assertEqual(groups[0]["hooks"][0]["type"], "command")
        root = _project({})
        self.addCleanup(shutil.rmtree, root, True)
        fix = rate.score_hooks(root).fixes[0]
        self.assertIn("SessionEnd", fix)
        self.assertNotIn("CLAUDE_TOKEN_COUNT", fix)


class HookHygiene(unittest.TestCase):
    def setUp(self) -> None:
        secret = "sk-test-not-a-real-key-1234567890"
        hooks = {
            "PreToolUse": [
                "bash hooks/bare.sh",
                {"matcher": "Bash", "hooks": [{"command": "echo hi"}]},
                {
                    "matcher": ".*",
                    "hooks": [{"type": "command", "command": "bash hooks/guard.sh"}],
                },
                {
                    "matcher": ".*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f'TOKEN={secret} bash "$CLAUDE_PROJECT_DIR"/hooks/gone.sh',
                        }
                    ],
                },
            ],
            "Stop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": 'bash "$CLAUDE_PROJECT_DIR"/hooks/summary.sh',
                        }
                    ]
                }
            ],
            "SessionStart": [
                {"hooks": [{"type": "command", "command": "echo started"}]}
            ],
        }
        local = {"hooks": {"Stop": hooks["Stop"]}}
        self.secret = secret
        self.root = _project(
            {
                ".claude/settings.json": json.dumps({"hooks": hooks}),
                ".claude/settings.local.json": json.dumps(local),
                "hooks/guard.sh": "exit 0\n",
                "hooks/summary.sh": 'claude -p "summarize the session" >> log.txt\n',
            }
        )
        self.addCleanup(shutil.rmtree, self.root, True)
        self.problems = rate._hook_problems(self.root)

    def test_each_problem_is_found_once(self) -> None:
        self.assertEqual(
            self.problems["malformed"],
            ["settings.json PreToolUse[0]", "settings.json PreToolUse[1].hooks[0]"],
        )
        self.assertEqual(
            self.problems["relative"],
            ["settings.json PreToolUse[2].hooks[0] (hooks/guard.sh)"],
        )
        self.assertEqual(
            self.problems["missing"],
            ["settings.json PreToolUse[3].hooks[0] (hooks/gone.sh)"],
        )
        # The same Stop handler in settings.local.json runs once, so it is reported once.
        self.assertEqual(
            self.problems["headless"],
            ["settings.json Stop[0].hooks[0] (hooks/summary.sh)"],
        )
        self.assertEqual(
            self.problems["session_start"], ["settings.json SessionStart[0].hooks[0]"]
        )

    def test_findings_never_print_the_command_text(self) -> None:
        payload = json.dumps(rate.rate(self.root).to_dict())
        self.assertNotIn(self.secret, payload)
        self.assertNotIn("summarize the session", payload)

    def test_hooks_score_is_unchanged_by_the_findings(self) -> None:
        self.assertEqual(rate.score_hooks(self.root).score, 10)


class DeadLoad(unittest.TestCase):
    def setUp(self) -> None:
        claude_md = "\n".join(
            [
                "# Project",
                "Read [`../../CLAUDE.md`](../../CLAUDE.md) and [`.claude/resources/`](../../.claude/resources/README.md).",
                "- See `docs/guide.md` and `docs/missing.md`.",
                "- Globs `docs/*.md`, commands `npm test` and URLs `https://x.test/a.md` are skipped.",
                "- [link](docs/also-missing.md) and [ok](docs/guide.md#top)",
                "@docs/imported.md",
                "@AGENTS.md",
                "Always run the full test suite before you open a pull request.",
                "```",
                "`docs/in-fence.md`",
                "```",
                "",
            ]
        )
        nested = "\n".join(
            [
                "- **Always run the full test suite** before you open a pull request",
                "Always run the full test suit before you open a pull request.",
                "",
            ]
        )
        self.root = _project(
            {
                "CLAUDE.md": claude_md,
                ".claude/CLAUDE.md": nested,
                "docs/guide.md": "guide\n",
                "docs/imported.md": "x" * 400,
            }
        )
        self.addCleanup(shutil.rmtree, self.root, True)

    def test_stale_references_skip_escapes_labels_globs_and_fences(self) -> None:
        self.assertEqual(
            rate._stale_refs(self.root, "CLAUDE.md"),
            [
                "CLAUDE.md:3 docs/missing.md",
                "CLAUDE.md:5 docs/also-missing.md",
                "CLAUDE.md:7 @AGENTS.md",
            ],
        )

    def test_exact_and_near_repeats(self) -> None:
        repeats, _ = rate._repeated_lines(self.root, rate._instruction_files(self.root))
        self.assertEqual(
            repeats,
            [
                ".claude/CLAUDE.md:1 repeats CLAUDE.md:8",
                ".claude/CLAUDE.md:2 repeats CLAUDE.md:8 (near)",
            ],
        )

    def test_this_repo_has_no_stale_references(self) -> None:
        # Its CLAUDE.md keeps the workspace stacking preamble (../../ links).
        self.assertEqual(rate._stale_refs(REPO, "CLAUDE.md"), [])

    def test_max_context_tokens_gate_counts_imports_and_sets_the_exit_code(
        self,
    ) -> None:
        files = dict(rate.always_loaded_files(self.root))
        self.assertIn("docs/imported.md", files)
        script = REPO / "tools" / "claude-rate" / "rate.py"
        over = subprocess.run(
            [
                sys.executable,
                str(script),
                str(self.root),
                "--json",
                "--max-context-tokens",
                "10",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(over.returncode, 1)
        self.assertIn("--max-context-tokens", over.stderr)
        under = subprocess.run(
            [
                sys.executable,
                str(script),
                str(self.root),
                "--json",
                "--max-context-tokens",
                "100000",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(under.returncode, 0)
        self.assertEqual(
            audit.always_loaded(self.root), rate.always_loaded_files(self.root)
        )


class RepeatedLinesParity(unittest.TestCase):
    def test_same_exact_repeats_as_the_web_analyzer(self) -> None:
        # The fixture of findRepeatedLines in site/src/utils/repoAnalyzer.test.ts.
        claude_md = "\n".join(
            [
                "# Project",
                "- See `docs/guide.md` and `docs/missing.md`.",
                "Always run the full test suite before you open a pull request.",
                "```",
                "Always run the full test suite before you open a pull request.",
                "```",
                "| Always run the full test suite before you open a pull request |",
                "short line",
                "",
            ]
        )
        nested = "\n".join(
            [
                "---",
                "description: Always run the full test suite before you open a pull request",
                "---",
                "- **Always run the full test suite** before you open a pull request",
                "1. always   RUN the full test suite before you open a pull request!",
            ]
        )
        root = _project({"CLAUDE.md": claude_md, ".claude/CLAUDE.md": nested})
        self.addCleanup(shutil.rmtree, root, True)
        repeats, _ = rate._repeated_lines(root, rate._instruction_files(root))
        self.assertEqual(
            repeats, [".claude/CLAUDE.md:4 repeats CLAUDE.md:3", ".claude/CLAUDE.md:5 repeats CLAUDE.md:3"]
        )
        self.assertEqual(
            rate._normalized_line("  * **Keep** `CLAUDE.md`   under 200 lines.  "), "keep claude.md under 200 lines"
        )


@unittest.skipIf(shutil.which("git") is None, "git is not installed")
class DetectedReadDeny(unittest.TestCase):
    def test_committed_dist_is_never_denied(self) -> None:
        root = _project(
            {
                ".gitignore": "dist/\nnode_modules/\n",
                "dist/app.js": "built\n",
                "node_modules/pkg/index.js": "dep\n",
                "web/app.min.js": "min\n",
                "package-lock.json": "{}\n",
            }
        )
        self.addCleanup(shutil.rmtree, root, True)
        for args in (
            ["init", "-q"],
            ["add", "-f", "dist/app.js", "web/app.min.js", ".gitignore"],
        ):
            subprocess.run(
                ["git", "-C", str(root), *args], check=True, capture_output=True
            )
        self.assertEqual(
            rate._detected_read_deny(root),
            [
                "Read(./.env)",
                "Read(./.env.*)",
                "Read(node_modules/**)",
                "Read(*.min.js)",
                "Read(./package-lock.json)",
            ],
        )

    def test_existing_rules_cover_by_segment(self) -> None:
        rules = ["Read(.env)", "Read(./node_modules/**)", "Read(*.lock)"]
        self.assertTrue(rate._deny_covered("Read(node_modules/**)", rules))
        self.assertTrue(rate._deny_covered("Read(./.env)", rules))
        self.assertFalse(rate._deny_covered("Read(./.env.*)", rules))
        self.assertTrue(rate._deny_covered("Read(./yarn.lock)", rules))

    def test_this_repo_gets_no_new_deny_lines(self) -> None:
        settings, _ = rate._load_settings(REPO)
        rules = rate._read_deny_rules(settings)
        self.assertEqual(
            [
                r
                for r in rate._detected_read_deny(REPO)
                if not rate._deny_covered(r, rules)
            ],
            [],
        )


class DetectedReadDenyWithoutGit(unittest.TestCase):
    def test_a_folder_outside_any_repository_falls_back_to_gitignore_lines(
        self,
    ) -> None:
        root = _project(
            {".gitignore": "build/\n", "build/out.txt": "x\n", "coverage/x.txt": "y\n"}
        )
        self.addCleanup(shutil.rmtree, root, True)
        if rate._in_git_repo(root):
            self.skipTest("the temp directory sits inside a git repository")
        self.assertEqual(
            rate._detected_read_deny(root),
            ["Read(./.env)", "Read(./.env.*)", "Read(build/**)"],
        )
        self.assertEqual(rate.rate(root).grade, "F")


if __name__ == "__main__":
    unittest.main()
