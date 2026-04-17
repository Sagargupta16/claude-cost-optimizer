#!/usr/bin/env python3
"""
Claude Code Usage Analyzer

Analyzes Claude Code session data to identify cost hotspots,
usage patterns, and optimization opportunities.

Scans a directory for Claude session files (JSON/JSONL) and produces
a summary report with cost estimates and recommendations.

Usage:
    python analyze.py ~/.claude/projects/
    python analyze.py ./sessions/ --top 10
    python analyze.py ~/.claude/projects/ --sort cost
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Claude model pricing per 1M tokens (as of April 2026)
# "opus" = current flagship Opus 4.7; "opus-4.6" = legacy.
# Opus 4.7 and 4.6 share the same posted rate but 4.7's new tokenizer
# consumes up to ~35% more tokens for the same source text.
MODEL_PRICING = {
    "opus": {"input": 5.00, "output": 25.00, "cache_hit": 0.50},
    "opus-4.6": {"input": 5.00, "output": 25.00, "cache_hit": 0.50},
    "sonnet": {"input": 3.00, "output": 15.00, "cache_hit": 0.30},
    "haiku": {"input": 1.00, "output": 5.00, "cache_hit": 0.10},
}

# Fallback: default model for cost estimation when not specified in data
DEFAULT_MODEL = "sonnet"

# ANSI color codes
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RED = "\033[31m"
RESET = "\033[0m"


def supports_color() -> bool:
    """Check if the terminal supports ANSI color codes."""
    if os.getenv("NO_COLOR"):
        return False
    if os.getenv("FORCE_COLOR"):
        return True
    if not hasattr(sys.stdout, "isatty"):
        return False
    return sys.stdout.isatty()


def c(code: str, text: str) -> str:
    """Conditionally apply ANSI color code."""
    if not supports_color():
        return text
    return f"{code}{text}{RESET}"


def format_number(n: int) -> str:
    """Format a number with comma separators."""
    return f"{n:,}"


def format_cost(cost: float) -> str:
    """Format a dollar amount with appropriate precision."""
    if cost < 0.01:
        return f"${cost:.4f}"
    if cost < 1.00:
        return f"${cost:.3f}"
    return f"${cost:.2f}"


def calculate_cost(
    input_tokens: int, output_tokens: int, model: str = DEFAULT_MODEL
) -> float:
    """Calculate total cost for given token counts."""
    pricing = MODEL_PRICING.get(model, MODEL_PRICING[DEFAULT_MODEL])
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return input_cost + output_cost


def detect_model(text: str) -> str:
    """Attempt to detect the model name from text content."""
    text_lower = text.lower()
    if "opus" in text_lower:
        return "opus"
    if "haiku" in text_lower:
        return "haiku"
    if "sonnet" in text_lower:
        return "sonnet"
    return DEFAULT_MODEL


def scan_directory(directory: str) -> list[Path]:
    """Recursively find all JSON and JSONL files in a directory."""
    root = Path(directory)
    if not root.exists():
        print(f"{c(RED, 'Error:')} Directory not found: {directory}", file=sys.stderr)
        sys.exit(1)
    if not root.is_dir():
        print(f"{c(RED, 'Error:')} Not a directory: {directory}", file=sys.stderr)
        sys.exit(1)

    files = []
    for ext in ("*.json", "*.jsonl"):
        files.extend(root.rglob(ext))
    return sorted(files)


def parse_jsonl(file_path: Path) -> list[dict]:
    """Parse a JSONL file, returning a list of records."""
    records = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass  # Skip malformed lines silently
    except (OSError, UnicodeDecodeError):
        pass
    return records


def parse_json(file_path: Path) -> dict | list | None:
    """Parse a JSON file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None


def extract_session_data(file_path: Path) -> dict | None:
    """
    Extract session metrics from a Claude session file.

    Attempts to parse various known formats of Claude Code session data.
    Returns a normalized dict with session metrics, or None if unparseable.
    """
    if file_path.suffix == ".jsonl":
        records = parse_jsonl(file_path)
        if not records:
            return None
        return _extract_from_records(records, file_path)
    else:
        data = parse_json(file_path)
        if data is None:
            return None
        if isinstance(data, list):
            return _extract_from_records(data, file_path)
        if isinstance(data, dict):
            return _extract_from_single(data, file_path)
        return None


def _extract_from_records(records: list[dict], file_path: Path) -> dict | None:
    """Extract metrics from a list of message/event records."""
    total_input = 0
    total_output = 0
    turn_count = 0
    model = DEFAULT_MODEL
    tool_calls = []
    timestamps = []

    for record in records:
        # Try common field patterns for token usage
        usage = record.get("usage", {})
        if isinstance(usage, dict):
            total_input += usage.get("input_tokens", 0)
            total_output += usage.get("output_tokens", 0)

        # Alternative: top-level token fields
        total_input += record.get("input_tokens", 0)
        total_output += record.get("output_tokens", 0)

        # Count turns (messages from the assistant)
        role = record.get("role", "")
        if role == "assistant":
            turn_count += 1

        # Detect model
        record_model = record.get("model", "")
        if record_model:
            model = detect_model(record_model)

        # Track tool usage
        if record.get("type") == "tool_use" or record.get("tool_name"):
            tool_name = record.get("tool_name") or record.get("name", "unknown")
            tool_calls.append(tool_name)

        # Look inside content arrays for tool_use blocks
        content = record.get("content", [])
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tool_calls.append(block.get("name", "unknown"))

        # Collect timestamps
        ts = record.get("timestamp") or record.get("created_at")
        if ts:
            timestamps.append(str(ts))

    if total_input == 0 and total_output == 0 and turn_count == 0:
        return None

    return {
        "file": str(file_path),
        "name": file_path.stem,
        "input_tokens": total_input,
        "output_tokens": total_output,
        "total_tokens": total_input + total_output,
        "turns": max(turn_count, 1),
        "model": model,
        "cost": calculate_cost(total_input, total_output, model),
        "tool_calls": tool_calls,
        "first_timestamp": min(timestamps) if timestamps else None,
        "last_timestamp": max(timestamps) if timestamps else None,
    }


def _extract_from_single(data: dict, file_path: Path) -> dict | None:
    """Extract metrics from a single session summary object."""
    usage = data.get("usage", data.get("token_usage", {}))
    if isinstance(usage, dict):
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
    else:
        input_tokens = data.get("input_tokens", 0)
        output_tokens = data.get("output_tokens", 0)

    total = input_tokens + output_tokens
    if total == 0:
        return None

    model_str = data.get("model", "")
    model = detect_model(model_str) if model_str else DEFAULT_MODEL
    turns = data.get("turns", data.get("turn_count", 1))

    return {
        "file": str(file_path),
        "name": data.get("name", data.get("project", file_path.stem)),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total,
        "turns": max(turns, 1),
        "model": model,
        "cost": calculate_cost(input_tokens, output_tokens, model),
        "tool_calls": [],
        "first_timestamp": None,
        "last_timestamp": None,
    }


def identify_hotspots(sessions: list[dict]) -> list[str]:
    """Identify cost hotspots and return recommendations."""
    hotspots = []

    # Check for sessions with very high per-turn token usage
    for session in sessions:
        avg_tokens = session["total_tokens"] / session["turns"]
        if avg_tokens > 50_000:
            hotspots.append(
                f"Session '{session['name']}' averages {format_number(int(avg_tokens))} "
                f"tokens/turn. Consider trimming context or using .claudeignore."
            )

    # Check for heavy file read patterns
    all_tools = []
    for session in sessions:
        all_tools.extend(session.get("tool_calls", []))

    if all_tools:
        read_count = sum(
            1 for t in all_tools if t.lower() in ("read", "read_file", "readfile")
        )
        total_tools = len(all_tools)
        if total_tools > 0 and read_count / total_tools > 0.4:
            hotspots.append(
                f"File reads account for {read_count}/{total_tools} "
                f"({read_count * 100 // total_tools}%) of tool calls. "
                f"Use .claudeignore to exclude large/irrelevant files."
            )

    # Check for expensive model usage on many turns
    opus_sessions = [s for s in sessions if s["model"] == "opus"]
    if opus_sessions:
        opus_turns = sum(s["turns"] for s in opus_sessions)
        total_turns = sum(s["turns"] for s in sessions)
        if total_turns > 0 and opus_turns / total_turns > 0.5:
            hotspots.append(
                f"Opus is used for {opus_turns}/{total_turns} "
                f"({opus_turns * 100 // total_turns}%) of turns. "
                f"Switch routine tasks to Sonnet or Haiku for major savings."
            )

    # Check for long sessions
    long_sessions = [s for s in sessions if s["turns"] > 100]
    if long_sessions:
        hotspots.append(
            f"{len(long_sessions)} session(s) exceed 100 turns. "
            f"Long sessions accumulate context. Start fresh sessions more often."
        )

    return hotspots


def generate_recommendations(sessions: list[dict]) -> list[str]:
    """Generate general cost-saving recommendations based on analysis."""
    recommendations = []

    if not sessions:
        return ["No session data found. Ensure the directory contains Claude session files."]

    total_cost = sum(s["cost"] for s in sessions)
    total_input = sum(s["input_tokens"] for s in sessions)
    total_output = sum(s["output_tokens"] for s in sessions)

    if total_input > 0:
        input_ratio = total_input / (total_input + total_output)
        if input_ratio > 0.85:
            recommendations.append(
                "Input tokens dominate your usage ({:.0f}%). Focus on reducing "
                "context size: trim CLAUDE.md, use .claudeignore, avoid reading "
                "large files.".format(input_ratio * 100)
            )

    # Model-specific recommendations
    models_used = set(s["model"] for s in sessions)
    if models_used == {"opus"}:
        recommendations.append(
            "You're using Opus exclusively. Consider Sonnet for standard coding "
            "tasks and Haiku for simple lookups to save 40-80% on those turns."
        )

    avg_turns = sum(s["turns"] for s in sessions) / len(sessions)
    if avg_turns > 40:
        recommendations.append(
            f"Average session length is {avg_turns:.0f} turns. Starting fresh "
            f"sessions more frequently can prevent context accumulation."
        )

    if total_cost > 0:
        recommendations.append(
            f"Estimated total spend: {format_cost(total_cost)}. "
            f"Review the most expensive sessions above for quick wins."
        )

    return recommendations


def print_summary(sessions: list[dict], top_n: int, sort_by: str):
    """Print the full analysis report."""
    if not sessions:
        print(f"\n{c(YELLOW, '  No valid session data found in the specified directory.')}")
        print(f"  {c(DIM, 'Ensure the directory contains Claude Code JSON/JSONL session files.')}\n")
        return

    total_input = sum(s["input_tokens"] for s in sessions)
    total_output = sum(s["output_tokens"] for s in sessions)
    total_tokens = sum(s["total_tokens"] for s in sessions)
    total_cost = sum(s["cost"] for s in sessions)
    total_turns = sum(s["turns"] for s in sessions)

    # Header
    print()
    print(c(BOLD, "  Claude Code Usage Report"))
    print(c(DIM, "  " + "=" * 56))
    print()

    # Overview
    print(c(BOLD, "  Overview"))
    print(c(DIM, "  " + "-" * 56))
    print(f"  Sessions analyzed:  {c(CYAN, str(len(sessions)))}")
    print(f"  Total turns:        {format_number(total_turns)}")
    print(f"  Total tokens:       {c(BOLD, format_number(total_tokens))}")
    print(f"    Input tokens:     {format_number(total_input)}")
    print(f"    Output tokens:    {format_number(total_output)}")
    print(f"  Estimated cost:     {c(YELLOW, format_cost(total_cost))}")
    if total_turns > 0:
        avg_per_turn = total_tokens / total_turns
        print(f"  Avg tokens/turn:    {format_number(int(avg_per_turn))}")
    print()

    # Sort sessions
    if sort_by == "cost":
        sorted_sessions = sorted(sessions, key=lambda s: s["cost"], reverse=True)
    elif sort_by == "tokens":
        sorted_sessions = sorted(sessions, key=lambda s: s["total_tokens"], reverse=True)
    elif sort_by == "turns":
        sorted_sessions = sorted(sessions, key=lambda s: s["turns"], reverse=True)
    else:
        sorted_sessions = sorted(sessions, key=lambda s: s["cost"], reverse=True)

    # Top sessions
    display_sessions = sorted_sessions[:top_n]
    print(c(BOLD, f"  Top {len(display_sessions)} Sessions (by {sort_by})"))
    print(c(DIM, "  " + "-" * 56))
    print(
        f"  {'#':<4} {'Session':<24} {'Tokens':>10} {'Turns':>7} {'Cost':>10}"
    )
    print(f"  {'':.<4} {'':.<24} {'':.<10} {'':.<7} {'':.<10}")

    for i, session in enumerate(display_sessions, 1):
        name = session["name"][:22]
        print(
            f"  {i:<4} {name:<24} "
            f"{format_number(session['total_tokens']):>10} "
            f"{session['turns']:>7} "
            f"{c(GREEN, format_cost(session['cost'])):>19}"
        )
    print()

    # Cost hotspots
    hotspots = identify_hotspots(sessions)
    if hotspots:
        print(c(BOLD, "  Cost Hotspots"))
        print(c(DIM, "  " + "-" * 56))
        for hotspot in hotspots:
            print(f"  {c(RED, '!')} {hotspot}")
        print()

    # Recommendations
    recommendations = generate_recommendations(sessions)
    if recommendations:
        print(c(BOLD, "  Recommendations"))
        print(c(DIM, "  " + "-" * 56))
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Analyze Claude Code session data to find cost hotspots "
            "and optimization opportunities."
        ),
        epilog=(
            "Examples:\n"
            "  %(prog)s ~/.claude/projects/\n"
            "  %(prog)s ./sessions/ --top 10\n"
            "  %(prog)s ~/.claude/projects/ --sort tokens\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "directory",
        help="Directory containing Claude session files (JSON/JSONL)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        metavar="N",
        help="Number of top sessions to display (default: 5)",
    )
    parser.add_argument(
        "--sort",
        choices=["cost", "tokens", "turns"],
        default="cost",
        help="Sort sessions by: cost, tokens, or turns (default: cost)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    # Scan and parse
    files = scan_directory(args.directory)
    if not files:
        print(
            f"\n{c(YELLOW, '  No JSON/JSONL files found in:')} {args.directory}\n",
            file=sys.stderr,
        )
        sys.exit(1)

    sessions = []
    skipped = 0
    for file_path in files:
        session = extract_session_data(file_path)
        if session:
            sessions.append(session)
        else:
            skipped += 1

    if skipped > 0:
        print(
            c(DIM, f"  Skipped {skipped} file(s) with no recognizable session data."),
            file=sys.stderr,
        )

    # JSON output mode
    if args.json:
        result = {
            "sessions": sessions,
            "summary": {
                "total_sessions": len(sessions),
                "total_tokens": sum(s["total_tokens"] for s in sessions),
                "total_input_tokens": sum(s["input_tokens"] for s in sessions),
                "total_output_tokens": sum(s["output_tokens"] for s in sessions),
                "total_cost": sum(s["cost"] for s in sessions),
                "total_turns": sum(s["turns"] for s in sessions),
            },
            "hotspots": identify_hotspots(sessions),
            "recommendations": generate_recommendations(sessions),
        }
        print(json.dumps(result, indent=2, default=str))
        return

    # Terminal report
    print_summary(sessions, top_n=args.top, sort_by=args.sort)


if __name__ == "__main__":
    main()
