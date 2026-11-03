"""Tests for claude-rate --usage --tools (the tool-output audit).

Stdlib only (unittest). Run from the repo root:

    python -m unittest discover -s tools/claude-rate/tests -v

Fixtures are synthetic transcript lines built here. Every expected dollar figure is
arithmetic from the posted Opus 5.5 rates in docs/pricing-data.md ($5.00 per 1M for a
5-minute cache write, $0.20 for a cache read), not read back from rate.py.
"""

from __future__ import annotations

import base64
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

_RATE_PY = Path(__file__).resolve().parent.parent / "rate.py"
_spec = importlib.util.spec_from_file_location("rate", _RATE_PY)
assert _spec
assert _spec.loader
rate = importlib.util.module_from_spec(_spec)
sys.modules["rate"] = rate  # dataclasses resolve annotations through sys.modules
_spec.loader.exec_module(rate)

WRITE_5M = 5.00  # Opus 5.5, USD per 1M tokens
CACHE_READ = 0.20
BIG = 100_000  # cache-read tokens per request, so a clamp never fires by accident


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def use(call_id: str, name: str, **tool_input: object) -> dict:
    return {"type": "tool_use", "id": call_id, "name": name, "input": tool_input}


def request(
    mid: str,
    *blocks: dict,
    read: int = BIG,
    write: int = 0,
    out: int = 10,
    side: bool = False,
) -> dict:
    usage = {
        "input_tokens": 5,
        "cache_read_input_tokens": read,
        "cache_creation_input_tokens": write,
        "output_tokens": out,
    }
    message = {
        "id": mid,
        "model": "claude-opus-5-5",
        "usage": usage,
        "content": list(blocks),
    }
    return {
        "type": "assistant",
        "isSidechain": side,
        "sessionId": "s",
        "timestamp": stamp(),
        "message": message,
    }


def reply(
    call_id: str,
    content: object,
    *,
    error: bool = False,
    side: bool = False,
    **extra: object,
) -> dict:
    block = {
        "type": "tool_result",
        "tool_use_id": call_id,
        "content": content,
        "is_error": error,
    }
    record = {
        "type": "user",
        "isSidechain": side,
        "sessionId": "s",
        "timestamp": stamp(),
        "message": {"role": "user", "content": [block]},
    }
    record.update(extra)
    return record


def boundary() -> dict:
    return {
        "type": "system",
        "subtype": "compact_boundary",
        "timestamp": stamp(),
        "compactMetadata": {"trigger": "auto"},
    }


def dump(record: dict) -> str:
    return json.dumps(record, separators=(",", ":"))


def walk(*lines: object) -> "rate._ToolAgg":
    """Feed records (dicts) or raw lines (str) through one transcript file's chain."""
    agg, chain = rate._ToolAgg(), rate._ToolChain()
    for line in lines:
        rate._walk_line(line if isinstance(line, str) else dump(line), chain, agg, "")
    rate._finish_chain(chain, agg)
    return agg


def png(width: int, height: int) -> str:
    header = (
        b"\x89PNG\r\n\x1a\n"
        + (13).to_bytes(4, "big")
        + b"IHDR"
        + width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
    )
    return base64.b64encode(header + b"\x08\x06\x00\x00\x00").decode()


def jpeg(width: int, height: int) -> str:
    app0 = b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    sof = (
        b"\xff\xc0\x00\x11\x08"
        + height.to_bytes(2, "big")
        + width.to_bytes(2, "big")
        + b"\x03\x01\x22\x00\x02\x11\x01\x03\x11\x01"
    )
    return base64.b64encode(b"\xff\xd8" + app0 + sof).decode()


READ_TEXT = "line\n" * 600  # 3,000 characters, 601 lines


class Carry(unittest.TestCase):
    def test_one_write_then_a_read_per_later_request(self) -> None:
        # 4,000 chars / 4 * 1.3 (Opus 5.5 tokenizer) = 1,300 tokens: written by m2, read by m3 and m4.
        agg = walk(
            request("m1", use("t1", "Bash", command="git status")),
            reply("t1", "x" * 4_000),
            request("m2"),
            request("m3"),
            request("m4"),
        )
        self.assertAlmostEqual(agg.tokens, 1_300)
        self.assertAlmostEqual(
            agg.carry, 1_300 * (WRITE_5M + 2 * CACHE_READ) / 1_000_000, places=9
        )

    def test_carry_stops_at_the_compaction(self) -> None:
        agg = walk(
            request("m1", use("t1", "Bash", command="git status")),
            reply("t1", "x" * 4_000),
            request("m2"),
            boundary(),
            request("m3"),
            request("m4"),
        )
        self.assertAlmostEqual(agg.carry, 1_300 * WRITE_5M / 1_000_000, places=9)

    def test_carry_is_clamped_to_what_the_file_was_billed(self) -> None:
        # Three requests that each wrote 10 tokens and read none: the file was billed 3 * 10 * $5.00 / 1M.
        agg = walk(
            request("m1", use("t1", "Bash", command="git status"), read=0, write=10),
            reply("t1", "x" * 4_000),
            request("m2", read=0, write=10),
            request("m3", read=0, write=10),
        )
        self.assertAlmostEqual(agg.carry, 3 * 10 * WRITE_5M / 1_000_000, places=9)
        self.assertEqual(agg.clamped_files, 1)

    def test_a_result_with_no_later_request_carries_nothing(self) -> None:
        agg = walk(
            request("m1", use("t1", "Bash", command="ls")), reply("t1", "x" * 4_000)
        )
        self.assertEqual((agg.results, agg.carry), (1, 0.0))

    def test_calibration_compares_estimate_with_prompt_growth(self) -> None:
        agg = walk(
            request("m1", use("t1", "Bash", command="git status"), read=BIG),
            reply("t1", "x" * 4_000),
            request("m2", read=BIG + 2_000),
        )
        self.assertEqual(agg.growth, 2_000)
        self.assertAlmostEqual(agg.estimated, 1_300)


class Counting(unittest.TestCase):
    def test_blob_line_and_repeated_user_record_count_once(self) -> None:
        call = request("m1", use("t1", "Bash", command="git status"))
        result = reply("t1", "x" * 4_000)
        blob = (
            '{"type":"api-request-blob","sessionId":"s","hash":"h","message":'
            + dump(result)
            + "}"
        )
        agg = walk(call, blob, result, result)
        self.assertEqual(agg.results, 1)

    def test_a_tool_use_id_counts_once_across_files(self) -> None:
        agg = rate._ToolAgg()
        for _ in range(
            2
        ):  # a resumed session copies earlier records into a second file
            chain = rate._ToolChain()
            rate._walk_line(
                dump(request("m1", use("t1", "Bash", command="ls"))), chain, agg, ""
            )
            rate._walk_line(dump(reply("t1", "x" * 400)), chain, agg, "")
            rate._finish_chain(chain, agg)
        self.assertEqual(agg.results, 1)

    def test_mcp_tools_collapse_to_their_server(self) -> None:
        agg = walk(
            request("m1", use("t1", "mcp__srv__alpha"), use("t2", "mcp__srv__beta")),
            reply("t1", "x" * 2_000),
            reply("t2", "y" * 2_000),
        )
        self.assertEqual(agg.by_tool["mcp__srv"][0], 2)

    def test_subagent_file_is_its_own_chain(self) -> None:
        main, side = rate._ToolChain(), rate._ToolChain()
        agg = rate._ToolAgg()
        for chain, side_flag, ids in (
            (main, False, ("m1", "t1")),
            (side, True, ("m9", "t9")),
        ):
            rate._walk_line(
                dump(
                    request(ids[0], use(ids[1], "Bash", command="ls"), side=side_flag)
                ),
                chain,
                agg,
                "",
            )
            rate._walk_line(
                dump(reply(ids[1], "x" * 400, side=side_flag)), chain, agg, ""
            )
            rate._walk_line(dump(request(ids[0] + "b", side=side_flag)), chain, agg, "")
            rate._finish_chain(chain, agg)
        self.assertEqual((agg.main_files, agg.subagent_files), (1, 1))

    def test_images_use_the_patch_rule_from_the_header(self) -> None:
        cap_high, cap_standard = rate._IMAGE_TOKEN_CAPS[1], rate._IMAGE_TOKEN_CAPS[0]
        self.assertEqual(
            rate._image_tokens({"source": {"data": png(1000, 1000)}}, cap_high), 36 * 36
        )
        self.assertEqual(
            rate._image_tokens({"source": {"data": jpeg(800, 600)}}, cap_high), 29 * 22
        )
        self.assertEqual(
            rate._image_tokens({"source": {"data": png(2000, 2000)}}, cap_standard),
            cap_standard,
        )
        self.assertEqual(
            rate._image_tokens({"source": {"data": "not an image"}}, cap_standard),
            cap_standard,
        )

    def test_image_result_is_priced_by_pixels_not_base64_length(self) -> None:
        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": png(1000, 1000),
                },
            }
        ]
        agg = walk(
            request("m1", use("t1", "Read", file_path="/r/shot.png")),
            reply("t1", content),
        )
        self.assertAlmostEqual(agg.tokens, 1_296)


class Labels(unittest.TestCase):
    def test_leading_cd_export_env_and_sudo_are_skipped(self) -> None:
        self.assertEqual(
            rate._command_label("cd /repo && export FOO=bar && git diff --stat"),
            "git diff",
        )
        self.assertEqual(rate._command_label("AWS_KEY=abc123 aws s3 ls"), "aws s3")
        self.assertEqual(rate._command_label("sudo time pytest -q tests"), "pytest")
        self.assertEqual(rate._command_label("npm run build"), "npm run")

    def test_arguments_never_reach_the_label(self) -> None:
        secret = "psql postgresql://user:SECRETPW@db.example.com/prod -c 'select 1'"
        self.assertEqual(rate._command_label(secret), "psql")
        self.assertEqual(rate._command_label("echo hunter2"), "echo")
        self.assertEqual(
            rate._command_label("curl -H 'Authorization: Bearer abc' https://x.test"),
            "curl",
        )
        self.assertEqual(rate._command_label("$(cat /etc/secret) arg"), "other")

    def test_paths_and_hosts_are_shortened(self) -> None:
        self.assertEqual(
            rate._path_label("C:\\Users\\me\\proj\\src\\app.py"), "src/app.py"
        )
        self.assertEqual(
            rate._url_host("https://user:pw@Docs.Example.com/a/b?q=1"),
            "docs.example.com",
        )


class Reads(unittest.TestCase):
    def read(self, call_id: str, text: str = READ_TEXT, **extra: object) -> list[dict]:
        return [
            request("m" + call_id, use(call_id, "Read", file_path="/r/a.py")),
            reply(call_id, text, **extra),
        ]

    def tally(self, agg: "rate._ToolAgg", key: str) -> int:
        return int(agg.stat(key)[0])

    def test_identical_reread_in_one_context(self) -> None:
        agg = walk(*self.read("t1"), *self.read("t2"))
        self.assertEqual((agg.reads, self.tally(agg, "reread:same context")), (2, 1))

    def test_an_edit_between_two_reads_clears_the_match(self) -> None:
        edit = [
            request("me", use("te", "Edit", file_path="/r/a.py")),
            reply("te", "ok"),
        ]
        agg = walk(*self.read("t1"), *edit, *self.read("t2"))
        self.assertEqual(self.tally(agg, "reread:same context"), 0)

    def test_reread_split_before_and_after_compaction(self) -> None:
        agg = walk(*self.read("t1"), *self.read("t2"), boundary(), *self.read("t3"))
        self.assertEqual(self.tally(agg, "reread:same context"), 1)
        self.assertEqual(self.tally(agg, "reread:after compaction"), 1)

    def test_a_different_range_is_not_a_reread(self) -> None:
        ranged = [
            request("mr", use("tr", "Read", file_path="/r/a.py", offset=10, limit=50)),
            reply("tr", READ_TEXT),
        ]
        agg = walk(*self.read("t1"), *ranged)
        self.assertEqual(self.tally(agg, "reread:same context"), 0)

    def test_claude_codes_unchanged_stub_is_not_a_reread(self) -> None:
        stub = "File unchanged since your last Read. Refer to that earlier tool_result instead."
        agg = walk(
            *self.read("t1"),
            *self.read("t2", stub, toolUseResult={"type": "file_unchanged"}),
        )
        self.assertEqual(
            (agg.stubs, agg.reads, self.tally(agg, "reread:same context")), (1, 1, 0)
        )

    def test_short_reads_are_below_the_floor(self) -> None:
        agg = walk(*self.read("t1", "short"), *self.read("t2", "short"))
        self.assertEqual((agg.reads, self.tally(agg, "reread:same context")), (0, 0))

    def test_whole_file_read_over_the_line_threshold(self) -> None:
        agg = walk(*self.read("t1"))
        self.assertEqual(self.tally(agg, "whole_file"), 1)


class Outcomes(unittest.TestCase):
    def test_failures_are_classified_and_cancellations_dropped(self) -> None:
        missing = "Exit code 127\nsh: tsc: command not found"
        agg = walk(
            request(
                "m1",
                use("a1", "Bash", command="npm run build"),
                use("a2", "Bash", command="npm run build"),
                use("a3", "Bash", command="npm run build"),
            ),
            reply("a1", missing, error=True),
            reply("a2", missing, error=True),
            reply("a3", missing, error=True),
            request("m2", use("b1", "Edit", file_path="/r/a.py")),
            reply(
                "b1",
                "<tool_use_error>File has not been read yet. Read it first.</tool_use_error>",
                error=True,
            ),
            request("m3", use("c1", "mcp__srv__alpha")),
            reply("c1", "No such file or directory", error=True),
            request("m4", use("d1", "Bash", command="rm -rf x")),
            reply(
                "d1",
                "Permission to use Bash has been denied.",
                error=True,
                toolDenialKind="permission-rule",
            ),
            request("m5", use("e1", "Bash", command="ls")),
            reply(
                "e1",
                "The user doesn't want to proceed.",
                error=True,
                toolDenialKind="user-rejected",
            ),
            request("m6"),
        )
        counts = {
            key[5:]: int(row[0])
            for key, row in agg.stats.items()
            if key.startswith("fail:")
        }
        self.assertEqual(
            counts,
            {
                "command not found": 3,
                "edit precondition": 1,
                "mcp error": 1,
                "blocked": 1,
            },
        )
        self.assertEqual((agg.cancelled, agg.runs, agg.in_runs), (1, 1, 3))

    def test_failure_is_priced_by_its_carry_plus_the_retry_output(self) -> None:
        agg = walk(
            request("m1", use("t1", "Bash", command="tsc")),
            reply("t1", "x" * 4_000, error=True),
            request("m2", out=500),
        )
        carry, retry = agg.stat("fail:other")[1:]
        self.assertAlmostEqual(carry, 1_300 * WRITE_5M / 1_000_000, places=9)
        self.assertAlmostEqual(
            retry, 500 * 20.0 / 1_000_000, places=9
        )  # Opus 5.5 output $20 per 1M

    def test_empty_searches(self) -> None:
        agg = walk(
            request(
                "m1",
                use("g1", "Grep", pattern="x"),
                use("g2", "Grep", pattern="y"),
                use("g3", "Glob", pattern="*.zz"),
            ),
            reply("g1", "No matches found"),
            reply("g2", "src/a.py:3:hit"),
            reply("g3", "No files found"),
            request("m2", use("s1", "Bash", command="cd src && grep -rn foo .")),
            reply("s1", "(Bash completed with no output)"),
        )
        facts = rate._search_facts(agg)
        self.assertEqual((facts["searches"], facts["empty"]), (4, 3))

    def test_bash_cap_what_if(self) -> None:
        agg = walk(
            request(
                "m1",
                use("t1", "Bash", command="pytest -q"),
                use("t2", "Bash", command="cat big.log"),
            ),
            reply("t1", "x" * 20_000),
            reply("t2", "y" * 12_000),
            request("m2"),
        )
        facts = rate._cap_facts(agg)
        self.assertEqual([row["results_over"] for row in facts["caps"]], [2, 1])
        # 20,000 chars = 6,500 tokens: all but the 2,000-character preview is saved at a 15,000 cap.
        self.assertEqual(facts["caps"][1]["tokens"], round(6_500 * 18_000 / 20_000))


class EndToEnd(unittest.TestCase):
    def run_cli(self, config: Path, *flags: str) -> str:
        env = {**os.environ, "CLAUDE_CONFIG_DIR": str(config)}
        proc = subprocess.run(
            [sys.executable, str(_RATE_PY), str(config), "--usage", *flags],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        return proc.stdout

    def make_config(self, root: Path) -> Path:
        project = root / "projects" / "p"
        project.mkdir(parents=True)
        lines = [
            request(
                "m1",
                use(
                    "t1",
                    "Bash",
                    command="cd /r && psql postgresql://user:SECRETPW@db.example.com/x",
                ),
            ),
            reply("t1", "x" * 4_000),
            request("m2"),
        ]
        (project / "main.jsonl").write_text(
            "\n".join(dump(line) for line in lines) + "\n", encoding="utf-8"
        )
        return root

    def test_tools_flag_adds_the_block_and_never_prints_an_argument(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = self.make_config(Path(tmp))
            text = self.run_cli(config, "--tools")
            as_json = json.loads(self.run_cli(config, "--tools", "--json"))
        self.assertIn("Tool output", text)
        self.assertNotIn("SECRETPW", text)
        self.assertNotIn("SECRETPW", json.dumps(as_json))
        self.assertEqual(as_json["usage"]["facts"]["tool_output"]["results"], 1)

    def test_without_the_flag_nothing_is_read_or_printed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = self.make_config(Path(tmp))
            text = self.run_cli(config)
        self.assertNotIn("Tool output", text)

    def test_collect_reports_the_files_it_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = self.make_config(Path(tmp))
            with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(config)}):
                facts = rate.collect_tool_output(30)
        self.assertEqual(facts["files"], {"main": 1, "subagent": 0})


if __name__ == "__main__":
    unittest.main()
