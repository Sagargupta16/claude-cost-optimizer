"""Shared pieces of the cost-mode eval: cases, arms, graders, transcript reading.

Standard library only. run.py (runs the arms) and summarize.py (prints the
tables) both import this file; nothing here calls a model.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
EVALS_DIR = HERE / "evals"
SKILL_MD = REPO_ROOT / "skills" / "cost-mode" / "SKILL.md"
RATE_PY = REPO_ROOT / "tools" / "claude-rate" / "rate.py"

# Declared in benchmarks/METHOD.md before any run. Changing them is a method change.
SEED = 20261103
N_REPS = 5
BOOTSTRAP_ITERS = 5000
# Every arm gets the same file tools and nothing else: no Bash, so the Bash
# restrictions of `claude plugin eval` never apply and every pass/fail check is
# run by the harness after the session instead of by the model.
TOOLS = "Read,Edit,Write,Grep,Glob"
CONTROL_TEXT = "Answer concisely."

# rate.py MODELS key -> the id passed to `claude --model` on the Anthropic API.
# On Bedrock or Google Cloud pass --model-id KEY=ID with that platform's id.
MODEL_IDS = {
    "opus-5-5": "claude-opus-5-5",
    "sonnet-5-5": "claude-sonnet-5-5",
    "haiku-5-5": "claude-haiku-5-5",
}

# role: baseline (no extra text), control (the terse prompt every saving is
# measured against), noise (a copy of the control, to size run-to-run noise),
# forced (SKILL.md plus a level line, appended as system prompt, so the skill is
# active by construction), installed (the plugin loaded as a user would have it,
# so it fires only when its description matches).
ARMS: dict[str, dict[str, str]] = {
    "none": {"role": "baseline"},
    "concise": {"role": "control"},
    "concise-b": {"role": "noise"},
    "costmode-lite": {"role": "forced", "level": "lite"},
    "costmode-standard": {"role": "forced", "level": "standard"},
    "costmode-strict": {"role": "forced", "level": "strict"},
    "costmode-installed": {"role": "installed"},
}
DEFAULT_ARMS = [name for name in ARMS if name != "costmode-installed"]
CONTROL_ARM = "concise"
NOISE_ARM = "concise-b"


def load_rate() -> Any:
    """Import tools/claude-rate/rate.py the way its own tests do."""
    spec = importlib.util.spec_from_file_location("rate", RATE_PY)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {RATE_PY}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["rate"] = module  # dataclasses resolve annotations through sys.modules
    spec.loader.exec_module(module)
    return module


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def append_text(arm: str) -> str | None:
    """The system-prompt text an arm appends, or None when it appends nothing."""
    role = ARMS[arm]["role"]
    if role in ("control", "noise"):
        return CONTROL_TEXT
    if role == "forced":
        body = SKILL_MD.read_text(encoding="utf-8").replace("\r\n", "\n")
        parts = body.split("---", 2)  # drop the YAML frontmatter
        skill = parts[2] if len(parts) == 3 else body
        return f"{skill.strip()}\n\nCost mode is active. Level: {ARMS[arm]['level']}."
    return None


# -- Cases ---------------------------------------------------------------------


def load_cases(names: list[str] | None = None) -> list[dict[str, Any]]:
    """Every case under evals/ (or just `names`), validated, in name order."""
    cases = []
    for folder in sorted(p for p in EVALS_DIR.iterdir() if (p / "case.json").is_file()):
        spec = json.loads((folder / "case.json").read_text(encoding="utf-8"))
        prompt = (folder / "prompt.md").read_text(encoding="utf-8").strip()
        fixture = folder / "fixture"
        digest = sha256_text(
            json.dumps(spec, sort_keys=True) + prompt + _tree_digest(fixture)
        )
        case = {
            **spec,
            "prompt": prompt,
            "fixture": fixture if fixture.is_dir() else None,
            "sha256": digest,
        }
        _check_case(folder.name, case)
        cases.append(case)
    wanted = names or [c["id"] for c in cases]
    unknown = sorted(set(wanted) - {c["id"] for c in cases})
    if unknown:
        raise SystemExit(f"unknown case(s): {', '.join(unknown)}")
    return [c for c in cases if c["id"] in wanted]


def _tree_digest(folder: Path) -> str:
    if not folder.is_dir():
        return ""
    parts = [
        f"{p.relative_to(folder).as_posix()}:{p.read_bytes().hex()}"
        for p in sorted(folder.rglob("*"))
        if p.is_file()
    ]
    return sha256_text("\n".join(parts))


def _check_case(folder_name: str, case: dict[str, Any]) -> None:
    if case.get("id") != folder_name:
        raise SystemExit(
            f"case id {case.get('id')!r} does not match its folder {folder_name!r}"
        )
    for grader in case["graders"]:
        if grader["type"] not in GRADERS:
            raise SystemExit(f"{folder_name}: unknown grader type {grader['type']!r}")
        if "pattern" in grader:
            re.compile(grader["pattern"], _flags(grader))


# -- Graders (all run by the harness, outside the session) -----------------------


def _flags(grader: dict[str, Any]) -> int:
    table = {"i": re.IGNORECASE, "s": re.DOTALL, "m": re.MULTILINE}
    flags = 0
    for char in grader.get("flags", ""):
        flags |= table[char]
    return flags


def _grade_regex(grader: dict[str, Any], ctx: dict[str, Any]) -> tuple[bool, str]:
    found = re.search(grader["pattern"], ctx["result"], _flags(grader)) is not None
    return found == grader.get("match", True), ""


def _grade_file_regex(grader: dict[str, Any], ctx: dict[str, Any]) -> tuple[bool, str]:
    files = [p for p in sorted(ctx["workdir"].glob(grader["glob"])) if p.is_file()]
    regex = re.compile(grader["pattern"], _flags(grader))
    hits = [
        p
        for p in files
        if regex.search(p.read_text(encoding="utf-8", errors="replace"))
    ]
    if grader.get("match", True):
        return bool(hits), ("no matching file" if not hits else "")
    return not hits, (f"{len(hits)} file(s) still match" if hits else "")


def _grade_command(grader: dict[str, Any], ctx: dict[str, Any]) -> tuple[bool, str]:
    argv = [
        sys.executable if a == "python" and i == 0 else a
        for i, a in enumerate(grader["argv"])
    ]
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}
    try:
        done = subprocess.run(
            argv,
            cwd=ctx["workdir"],
            env=env,
            capture_output=True,
            text=True,
            timeout=grader.get("timeout", 60),
        )
    except subprocess.TimeoutExpired:
        return False, "timeout"
    return done.returncode == 0, f"rc={done.returncode}"


_JSON_TYPES: dict[str, Any] = {
    "string": str,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def _grade_json_keys(grader: dict[str, Any], ctx: dict[str, Any]) -> tuple[bool, str]:
    body = ctx["result"].strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body, re.DOTALL)
    try:
        obj = json.loads(fenced.group(1) if fenced else body)
    except ValueError:
        return False, "reply is not JSON"
    if not isinstance(obj, dict):
        return False, "reply is not an object"
    for key, name in grader.get("require", {}).items():
        wanted = _JSON_TYPES.get(name)
        value = obj.get(key)
        number_ok = (
            name == "number"
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
        )
        if not (number_ok or (wanted is not None and isinstance(value, wanted))):
            return False, f"key {key} is not a {name}"
    for key, value in grader.get("equals", {}).items():
        if obj.get(key) != value:
            return False, f"key {key} has the wrong value"
    return True, ""


def _grade_tool_used(grader: dict[str, Any], ctx: dict[str, Any]) -> tuple[bool, str]:
    if ctx["tools"] is None:
        return False, "no transcript"
    used = bool(set(grader["tools"]) & set(ctx["tools"]))
    return used == grader.get("match", True), ""


GRADERS = {
    "regex": _grade_regex,
    "file_regex": _grade_file_regex,
    "command": _grade_command,
    "json_keys": _grade_json_keys,
    "tool_used": _grade_tool_used,
}


def grade(
    case: dict[str, Any], workdir: Path, result: str, tools: list[str] | None
) -> dict[str, Any]:
    """Run every grader of `case`; the run passes only when all of them do."""
    ctx = {"workdir": workdir, "result": result, "tools": tools}
    checks = []
    for grader in case["graders"]:
        ok, detail = GRADERS[grader["type"]](grader, ctx)
        checks.append(
            {
                "type": grader["type"],
                "label": grader.get("label", ""),
                "ok": ok,
                "detail": detail,
            }
        )
    return {"passed": all(c["ok"] for c in checks), "checks": checks}


# -- Transcript ------------------------------------------------------------------

_USAGE_KEYS = (
    "input_tokens",
    "cache_read_input_tokens",
    "cache_creation_input_tokens",
    "output_tokens",
    "speed",
)


def slim_usage(usage: dict[str, Any]) -> dict[str, Any]:
    """The usage fields the cost math reads (the same set rate.py keeps)."""
    slim = {key: usage[key] for key in _USAGE_KEYS if usage.get(key)}
    split = usage.get("cache_creation")
    if isinstance(split, dict) and split.get("ephemeral_1h_input_tokens"):
        slim["cache_creation"] = {
            "ephemeral_1h_input_tokens": split["ephemeral_1h_input_tokens"]
        }
    return slim


def read_transcript(config_dir: Path, session_id: str) -> dict[str, Any] | None:
    """Per-request usage and the tools used, from one session's transcript.

    A response is written as one record per content block, all with the same
    message id; the record with the most output tokens is the final count, the
    same rule rate.py uses. Returns None when the file is not there.
    """
    found = sorted((config_dir / "projects").glob(f"*/{session_id}.jsonl"))
    if not found:
        return None
    requests: dict[str, dict[str, Any]] = {}
    tools: set[str] = set()
    skill = False
    for line in found[0].read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            record = json.loads(line)
        except ValueError:
            continue
        message = (
            record.get("message")
            if isinstance(record, dict) and record.get("type") == "assistant"
            else None
        )
        if not isinstance(message, dict) or record.get("isSidechain"):
            continue
        for block in message.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                tools.add(str(block.get("name")))
                skill = skill or (
                    block.get("name") == "Skill"
                    and "cost-mode" in json.dumps(block.get("input"))
                )
        _keep_request(requests, message)
    return {"requests": list(requests.values()), "tools": sorted(tools), "skill": skill}


def _keep_request(requests: dict[str, dict[str, Any]], message: dict[str, Any]) -> None:
    model = message.get("model") or ""
    usage = message.get("usage")
    if not message.get("id") or not isinstance(usage, dict) or model.startswith("<"):
        return
    held = requests.get(message["id"])
    if held is None or (usage.get("output_tokens") or 0) > (
        held.get("output_tokens") or 0
    ):
        requests[message["id"]] = {**slim_usage(usage), "model": model}
