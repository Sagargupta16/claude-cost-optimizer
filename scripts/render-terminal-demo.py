#!/usr/bin/env python3
"""Render the README's terminal capture from claude-rate's real output on this repo.

Runs `tools/claude-rate/rate.py .` from the repo root, keeps the grade, the seven
category bars and the current models' monthly estimates, and writes an animated
SVG (the command types itself, then the output prints line by line, on a loop):
docs/assets/terminal-demo.svg. Re-run it after a rate or rubric change, since the
numbers in the picture are the tool's own output at render time (the estimate also
moves with this repo's CLAUDE.md, so re-run after editing it too).

    python scripts/render-terminal-demo.py
"""

from __future__ import annotations

import argparse
import html
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets" / "terminal-demo.svg"
RATE = ROOT / "tools" / "claude-rate" / "rate.py"

COMMAND = "curl -sSL .../tools/claude-rate/rate.py | python3 - ."
# Current models only, so the picture stays short enough to read on a phone.
MODELS = ("Fable 5.2", "Opus 5.5", "Sonnet 5.5", "Haiku 5.5")

# 560 wide so the text stays readable once GitHub scales the image to a phone screen.
WIDTH = 560
PAD = 22
BAR_H = 34
LINE_H = 20
FONT = 14
# Advance per character on the prompt line. The command is drawn with textLength, so
# it spans exactly len * CHAR_W in every font and the typing cover stays in step.
CHAR_W = 8.4
CYCLE = 14.0  # seconds per loop

COLORS = {
    "bg": "#0d1117",
    "bar": "#161b22",
    "border": "#30363d",
    "text": "#c9d1d9",
    "dim": "#9ea7b3",
    "green": "#3fb950",
    "blue": "#58a6ff",
    "white": "#f0f6fc",
}

CATEGORY = re.compile(r"^  (?P<name>\S.*?)\s+\[(?P<bar>[#-]+)\]\s+(?P<score>\d+/\d+)")
TOTAL = re.compile(r"^Total: (?P<score>\d+/\d+)\s+\((?P<grade>[A-F][+-]?)\)")


def run_rate() -> list[str]:
    result = subprocess.run(
        [sys.executable, str(RATE), "."],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout.splitlines()


def pick_lines(raw: list[str]) -> list[list[tuple[str, str]]]:
    """Each output line as (text, colour) segments, in print order."""
    lines: list[list[tuple[str, str]]] = []
    for line in raw:
        if line.startswith("claude-rate --"):
            lines.append([(line, "white")])
        elif line.startswith("====="):
            lines.append([("=" * 52, "dim")])
        elif line.startswith("Project:"):
            lines.append([("Project: ", "dim"), ("claude-cost-optimizer", "text")])
        elif line.startswith("Verified against"):
            lines.append([(line, "dim")])
            lines.append([])
        elif m := CATEGORY.match(line):
            filled = m["bar"].count("#")
            empty = len(m["bar"]) - filled
            lines.append(
                [
                    (f"  {m['name']:<24}[", "text"),
                    ("#" * filled, "green"),
                    ("-" * empty, "dim"),
                    (f"]  {m['score']:>5}", "text"),
                ]
            )
        elif m := TOTAL.match(line):
            lines.append([])
            lines.append(
                [
                    ("Total: ", "white"),
                    (m["score"], "white"),
                    ("  (", "text"),
                    (m["grade"], "green"),
                    (")", "text"),
                ]
            )
        elif line.startswith("Estimated monthly cost"):
            lines.append([])
            lines.append(
                [
                    (
                        "Estimated monthly cost (30 turns x 3 sessions/day x 22 days)",
                        "dim",
                    )
                ]
            )
        elif any(line.startswith(f"  {name} ") for name in MODELS):
            lines.append([(line.rstrip(), "text")])
        elif line.startswith("Run with --fix"):
            lines.append([])
            lines.append([(line, "blue")])
    return lines


def keyframes(name: str, start: float) -> str:
    """Hidden until `start` seconds into the loop, then shown until the loop fades out."""
    on = start / CYCLE * 100
    return (
        f"@keyframes {name}{{0%,{on:.2f}%{{opacity:0}}{min(on + 0.6, 94):.2f}%,94%{{opacity:1}}"
        f"99%,100%{{opacity:0}}}}"
    )


def render(lines: list[list[tuple[str, str]]]) -> str:
    body_top = BAR_H + PAD
    prompt_y = body_top + FONT
    height = int(body_top + LINE_H * (len(lines) + 1) + PAD)
    type_start, type_end = 0.4, 2.4
    cover_w = len(COMMAND) * CHAR_W
    style = [
        f"text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace;"
        f"font-size:{FONT}px;white-space:pre}}",
        *(f".c-{k}{{fill:{v}}}" for k, v in COLORS.items()),
        f"@keyframes type{{0%,{type_start / CYCLE * 100:.2f}%{{transform:translateX(0)}}"
        f"{type_end / CYCLE * 100:.2f}%,100%{{transform:translateX({cover_w:.1f}px)}}}}",
        f".cover{{animation:type {CYCLE}s steps({len(COMMAND)}) infinite}}",
        "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}",
        ".cursor{animation:blink 1s step-end infinite}",
        keyframes("fade", 0) + f".prompt{{animation:fade {CYCLE}s linear infinite}}",
    ]
    rows = []
    t = type_end + 0.3
    for i, segments in enumerate(lines):
        if not segments:
            continue
        name = f"l{i}"
        style.append(
            keyframes(name, t) + f".{name}{{animation:{name} {CYCLE}s linear infinite}}"
        )
        y = prompt_y + LINE_H * (i + 1)
        spans = "".join(
            f'<tspan class="c-{c}">{html.escape(s)}</tspan>' for s, c in segments
        )
        rows.append(f'<text class="{name}" x="{PAD}" y="{y:.1f}">{spans}</text>')
        t += 0.12
    summary = " ".join("".join(s for s, _ in seg).strip() for seg in lines if seg)
    title = "claude-rate grading this repo in a terminal"
    desc = f"The command {COMMAND} runs and prints: {summary}"
    dots = "".join(
        f'<circle cx="{PAD + i * 18}" cy="{BAR_H / 2}" r="5.5" fill="{c}"/>'
        for i, c in enumerate(("#ff5f56", "#ffbd2e", "#27c93f"))
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" role="img" aria-labelledby="t d">
<title id="t">{html.escape(title)}</title>
<desc id="d">{html.escape(desc)}</desc>
<style>{"".join(style)}</style>
<defs><clipPath id="frame"><rect x="1" y="1" width="{WIDTH - 2}" height="{height - 2}" rx="9.5"/></clipPath></defs>
<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="10" fill="{COLORS["bg"]}" stroke="{COLORS["border"]}"/>
<path d="M0.5 {BAR_H}V10.5a10 10 0 0 1 10-10H{WIDTH - 10.5}a10 10 0 0 1 10 10V{BAR_H}Z" fill="{COLORS["bar"]}"/>
<line x1="0.5" y1="{BAR_H}" x2="{WIDTH - 0.5}" y2="{BAR_H}" stroke="{COLORS["border"]}"/>
{dots}
<text x="{WIDTH / 2}" y="{BAR_H / 2 + 4.5}" text-anchor="middle" class="c-dim" style="font-size:12px">claude-rate</text>
<g class="prompt">
<text x="{PAD}" y="{prompt_y:.1f}" class="c-green">$</text>
<text x="{PAD + 2 * CHAR_W:.1f}" y="{prompt_y:.1f}" class="c-text" textLength="{cover_w:.1f}" lengthAdjust="spacing">{html.escape(COMMAND)}</text>
<g clip-path="url(#frame)"><g class="cover"><rect x="{PAD + 2 * CHAR_W:.1f}" y="{prompt_y - FONT:.1f}" width="{cover_w + 4:.1f}" height="{LINE_H}" fill="{COLORS["bg"]}"/>
<rect class="cursor" x="{PAD + 2 * CHAR_W:.1f}" y="{prompt_y - FONT + 1:.1f}" width="8" height="{FONT + 3}" fill="{COLORS["text"]}"/></g></g>
</g>
{chr(10).join(rows)}
</svg>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out",
        type=Path,
        default=OUT,
        help=f"output SVG (default {OUT.relative_to(ROOT)})",
    )
    args = parser.parse_args()
    lines = pick_lines(run_rate())
    if not any(seg and seg[0][0] == "Total: " for seg in lines):
        print(
            "render-terminal-demo: no 'Total:' line in claude-rate's output",
            file=sys.stderr,
        )
        return 1
    args.out.write_text(render(lines), encoding="utf-8", newline="\n")
    print(f"wrote {args.out.relative_to(ROOT)} ({len([s for s in lines if s])} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
