#!/usr/bin/env python3
"""
Claude Code Usage Analyzer (retired)

This tool read usage and content from the top level of each transcript record.
Current Claude Code transcripts nest both under `message`, so it found no
sessions in them. Its job moved to claude-rate, which prices every request from
the same local transcripts, cache-aware and counted once per message id:

    python tools/claude-rate/rate.py --usage --by session

Running this script prints that pointer and exits with status 1. The pricing
table below stays until the release that deletes this file, because
scripts/check-rate-values.py checks it against the other copies of the rates.
"""

import sys

# Claude model pricing per 1M tokens (verified 2026-11-10; Fable 5.2 released 2026-11-09)
# "fable" = Fable 5.2 (most capable, 2x Opus 5.5); "fable-5.1" = legacy Fable 5.1 at
# $10/$50; "opus" = Opus 5.5, the
# recommended default Opus at $4/$20 (20% below Opus 5); "opus-5" and
# "opus-4.8"/"opus-4.7"/"opus-4.6" = legacy at $5/$25. Opus 5.5 runs adaptive
# thinking ALWAYS ON (it cannot be disabled; effort defaults to medium), and Opus 5
# runs it ON by default; either way reasoning tokens bill at the normal output rate.
# "sonnet" = Sonnet 5.5 at $2/$10; "sonnet-5" = legacy Sonnet 5 at the same rate.
# The 4.7+ tokenizer (also used by Opus 4.8, Opus 5, Opus 5.5, Fable 5, Fable 5.1, Fable 5.2, Sonnet 5.5,
# Sonnet 5 and Haiku 5.5; not Sonnet 4.6) produces about 30% more tokens for the same
# source text (https://platform.claude.com/docs/en/about-claude/pricing).
# cache_hit has three multipliers: 0.1x input by default, 0.025x on Fable 5.2 /
# Mythos 5.2 ($0.20/MTok) and Fable 5.1 / Mythos 5.1 ($0.25/MTok), and 0.05x on Opus 5.5 ($0.20/MTok) and Sonnet 5.5
# ($0.10/MTok since 2026-10-07). Read the rate from this table; never compute
# input * 0.1.
# "haiku" = Haiku 5.5, priced by prompt length: "long_prompt" holds the rates for a
# request whose prompt (input plus cache reads and writes) is over "threshold".
# "haiku-4.5" = legacy Haiku 4.5.
# Pricing keys, as scripts/check-rate-values.py maps them to the canonical rows.
FABLE = "fable"
FABLE_5_1 = "fable-5.1"
FABLE_5 = "fable-5"
OPUS = "opus"
OPUS_5 = "opus-5"
OPUS_4_8 = "opus-4.8"
OPUS_4_7 = "opus-4.7"
OPUS_4_6 = "opus-4.6"
OPUS_4_5 = "opus-4.5"
# Opus 4.1 and Opus 4 share the old $15/$75 tier. Both are retired on the Claude
# API but still served on Bedrock and Google Cloud, so their logs still appear.
OPUS_4_1 = "opus-4.1"
SONNET = "sonnet"
SONNET_5 = "sonnet-5"
SONNET_4_6 = "sonnet-4.6"
SONNET_4_5 = "sonnet-4.5"
HAIKU = "haiku"
HAIKU_4_5 = "haiku-4.5"

MODEL_PRICING = {
    FABLE: {"input": 8.00, "output": 40.00, "cache_hit": 0.20},
    FABLE_5_1: {"input": 10.00, "output": 50.00, "cache_hit": 0.25},
    FABLE_5: {"input": 10.00, "output": 50.00, "cache_hit": 1.00},
    OPUS: {"input": 4.00, "output": 20.00, "cache_hit": 0.20},
    OPUS_5: {"input": 5.00, "output": 25.00, "cache_hit": 0.50},
    OPUS_4_8: {"input": 5.00, "output": 25.00, "cache_hit": 0.50},
    OPUS_4_7: {"input": 5.00, "output": 25.00, "cache_hit": 0.50},
    OPUS_4_6: {"input": 5.00, "output": 25.00, "cache_hit": 0.50},
    OPUS_4_5: {"input": 5.00, "output": 25.00, "cache_hit": 0.50},
    OPUS_4_1: {"input": 15.00, "output": 75.00, "cache_hit": 1.50},
    SONNET: {"input": 2.00, "output": 10.00, "cache_hit": 0.10},
    SONNET_5: {"input": 2.00, "output": 10.00, "cache_hit": 0.20},
    SONNET_4_6: {"input": 3.00, "output": 15.00, "cache_hit": 0.30},
    SONNET_4_5: {"input": 3.00, "output": 15.00, "cache_hit": 0.30},
    HAIKU: {
        "input": 0.10,
        "output": 0.50,
        "cache_hit": 0.01,
        "long_prompt": {"threshold": 100_000, "input": 0.50, "output": 2.50, "cache_hit": 0.05},
    },
    HAIKU_4_5: {"input": 1.00, "output": 5.00, "cache_hit": 0.10},
}

POINTER = """\
usage-analyzer is retired: it read a transcript layout Claude Code no longer writes,
so it found no sessions. claude-rate (0.4.0 or later) reports the same from your
local transcripts, per session, project, day, skill or MCP server:

    python tools/claude-rate/rate.py --usage --by session
    python tools/claude-rate/rate.py --usage 30 --by project,day --json

See tools/claude-rate/README.md for every --usage flag.
"""


def main() -> None:
    """Print where the analysis moved, then exit 1 so scripts notice."""
    print(POINTER, file=sys.stderr, end="")
    sys.exit(1)


if __name__ == "__main__":
    main()
