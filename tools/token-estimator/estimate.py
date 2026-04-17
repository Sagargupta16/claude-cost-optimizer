#!/usr/bin/env python3
"""
Token Estimator for Claude Code

Estimates token count for a file or text input and calculates
cost across Claude models (Opus, Sonnet, Haiku).

Usage:
    python estimate.py path/to/file.py
    echo "some text" | python estimate.py -
    python estimate.py path/to/CLAUDE.md --per-turn 50
    python estimate.py path/to/file.py --model opus
"""

import argparse
import sys
import os

try:
    import tiktoken
except ImportError:
    print(
        "Error: tiktoken is required. Install it with:\n"
        "  pip install tiktoken",
        file=sys.stderr,
    )
    sys.exit(1)


# Claude model pricing per 1M tokens (as of April 2026)
# NOTE: 1M context on Opus 4.7/4.6/Sonnet 4.6 is now billed at standard rates
# (no long-context premium). The old "2x over 200K" pricing only applied to
# Opus 4.1 and older.
MODEL_PRICING = {
    "opus": {
        "input": 5.00,
        "output": 25.00,
        "cache_hit": 0.50,
        "name": "Opus 4.7",
        "note": "New tokenizer may use up to 35% more tokens than Opus 4.6.",
    },
    "opus_4_6": {
        "input": 5.00,
        "output": 25.00,
        "cache_hit": 0.50,
        "name": "Opus 4.6 (legacy)",
    },
    "sonnet": {"input": 3.00, "output": 15.00, "cache_hit": 0.30, "name": "Sonnet 4.6"},
    "haiku": {"input": 1.00, "output": 5.00, "cache_hit": 0.10, "name": "Haiku 4.5"},
    "fast_mode": {
        "input": 30.00,
        "output": 150.00,
        "cache_hit": None,
        "name": "Opus 4.6 (Fast Mode)",
        "note": "Research preview. 6x standard Opus rates. Opus 4.6 only. Not available with Batch API.",
    },
    "mythos": {
        "input": 25.00,
        "output": 125.00,
        "cache_hit": 2.50,
        "name": "Mythos Preview",
        "note": (
            "Invite-only via Project Glasswing (defensive cybersecurity research). "
            "Not available for general development. Listed for reference only."
        ),
    },
}

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


def count_tokens(text: str) -> int:
    """Count tokens using cl100k_base encoding (closest approximation for Claude)."""
    encoder = tiktoken.get_encoding("cl100k_base")
    return len(encoder.encode(text))


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


def calculate_cost(token_count: int, model: str, direction: str = "input") -> float:
    """Calculate cost for a given token count and model."""
    price_per_million = MODEL_PRICING[model][direction]
    return (token_count / 1_000_000) * price_per_million


def read_input(source: str) -> str:
    """Read text from a file path or stdin."""
    if source == "-":
        if sys.stdin.isatty():
            print(
                f"{c(DIM, 'Reading from stdin (Ctrl+D to finish)...')}",
                file=sys.stderr,
            )
        return sys.stdin.read()

    path = os.path.expanduser(source)
    if not os.path.exists(path):
        print(f"{c(RED, 'Error:')} File not found: {path}", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(path):
        print(f"{c(RED, 'Error:')} Not a file: {path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(path, "r", encoding="latin-1") as f:
                return f.read()
        except Exception as e:
            print(
                f"{c(RED, 'Error:')} Could not read file: {e}",
                file=sys.stderr,
            )
            sys.exit(1)
    except PermissionError:
        print(
            f"{c(RED, 'Error:')} Permission denied: {path}",
            file=sys.stderr,
        )
        sys.exit(1)
    except OSError as e:
        print(f"{c(RED, 'Error:')} {e}", file=sys.stderr)
        sys.exit(1)


def print_header(source: str, token_count: int, line_count: int, char_count: int):
    """Print the summary header."""
    print()
    print(c(BOLD, "  Token Estimate"))
    print(c(DIM, "  " + "-" * 50))

    label = "stdin" if source == "-" else os.path.basename(source)
    print(f"  Source:     {c(CYAN, label)}")
    print(f"  Lines:      {format_number(line_count)}")
    print(f"  Characters: {format_number(char_count)}")
    print(f"  Tokens:     {c(BOLD, format_number(token_count))}")
    print()


def print_cost_table(token_count: int, model_filter: str | None = None):
    """Print per-model cost table for a single pass."""
    models = (
        {model_filter: MODEL_PRICING[model_filter]}
        if model_filter
        else MODEL_PRICING
    )

    print(c(BOLD, "  Cost Estimate (single input pass)"))
    print(c(DIM, "  " + "-" * 50))
    print(
        f"  {'Model':<14} {'Input Cost':>12} {'$/1M tokens':>14}"
    )
    print(f"  {'':.<14} {'':.<12} {'':.<14}")

    for key, info in models.items():
        cost = calculate_cost(token_count, key, "input")
        price_label = "${:.2f}".format(info["input"])
        print(
            f"  {info['name']:<14} {c(GREEN, format_cost(cost)):>22} "
            f"{c(DIM, price_label):>23}"
        )
    print()


def print_per_turn_table(
    token_count: int, turns: int, model_filter: str | None = None
):
    """Print cost projection over N turns."""
    models = (
        {model_filter: MODEL_PRICING[model_filter]}
        if model_filter
        else MODEL_PRICING
    )

    total_tokens = token_count * turns

    print(c(BOLD, f"  Per-Turn Projection ({turns} turns)"))
    print(c(DIM, "  " + "-" * 50))
    print(
        f"  Tokens per turn:  {format_number(token_count)}"
    )
    print(
        f"  Total tokens:     {c(BOLD, format_number(total_tokens))}"
    )
    print()
    print(
        f"  {'Model':<14} {'Total Cost':>12} {'Per Turn':>12}"
    )
    print(f"  {'':.<14} {'':.<12} {'':.<12}")

    for key, info in models.items():
        total_cost = calculate_cost(total_tokens, key, "input")
        per_turn_cost = calculate_cost(token_count, key, "input")
        print(
            f"  {info['name']:<14} "
            f"{c(YELLOW, format_cost(total_cost)):>22} "
            f"{c(DIM, format_cost(per_turn_cost)):>21}"
        )

    print()
    print(
        c(
            DIM,
            "  Note: This estimates input cost only. CLAUDE.md and system prompt\n"
            "  are loaded as input on every turn, making this a recurring cost.",
        )
    )
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Estimate token count and Claude API cost for a file or text.",
        epilog=(
            "Examples:\n"
            "  %(prog)s CLAUDE.md\n"
            "  %(prog)s CLAUDE.md --per-turn 50\n"
            "  %(prog)s src/app.py --model haiku\n"
            '  echo "Hello world" | %(prog)s -\n'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "source",
        help='File path to analyze, or "-" to read from stdin',
    )
    parser.add_argument(
        "--per-turn",
        type=int,
        metavar="N",
        help="Project cost over N conversation turns (useful for CLAUDE.md analysis)",
    )
    parser.add_argument(
        "--model",
        choices=list(MODEL_PRICING.keys()),
        default=None,
        help=(
            "Show cost for a specific model only (default: show all). "
            "Use 'opus_4_6' for legacy Opus 4.6 pricing. "
            "Use 'fast_mode' for Fast Mode pricing (Opus 4.6, 6x rates)."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    # Validate --per-turn
    if args.per_turn is not None and args.per_turn < 1:
        parser.error("--per-turn must be a positive integer")

    # Read and count
    text = read_input(args.source)
    token_count = count_tokens(text)
    line_count = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
    char_count = len(text)

    # JSON output mode
    if args.json:
        import json

        result = {
            "source": args.source,
            "tokens": token_count,
            "lines": line_count,
            "characters": char_count,
            "costs": {},
        }
        models = (
            {args.model: MODEL_PRICING[args.model]}
            if args.model
            else MODEL_PRICING
        )
        for key, info in models.items():
            entry = {
                "model": info["name"],
                "input_cost": calculate_cost(token_count, key, "input"),
            }
            if args.per_turn:
                entry["per_turn_tokens"] = token_count
                entry["total_tokens"] = token_count * args.per_turn
                entry["total_cost"] = calculate_cost(
                    token_count * args.per_turn, key, "input"
                )
                entry["turns"] = args.per_turn
            result["costs"][key] = entry
        print(json.dumps(result, indent=2))
        return

    # Terminal output
    print_header(args.source, token_count, line_count, char_count)
    print_cost_table(token_count, model_filter=args.model)

    if args.per_turn:
        print_per_turn_table(token_count, args.per_turn, model_filter=args.model)


if __name__ == "__main__":
    main()
