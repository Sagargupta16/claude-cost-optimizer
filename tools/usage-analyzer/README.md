# Usage Analyzer (retired)

This tool is retired. Use [claude-rate](../claude-rate/) `--usage` (claude-rate 0.4.0 or later) instead: it reads the same local transcripts and answers the same questions.

## Why it was retired

`analyze.py` read `usage` and `content` from the top level of each transcript record. Current Claude Code transcripts nest both under `message`, so the analyzer found no sessions in them and reported $0. A path fix alone would not have been enough: Claude Code streams one record per content block, each carrying the same message id and usage, so a naive sum counts a response several times.

claude-rate reads the nested fields, keeps each message id once at its final usage snapshot, and prices every request the way Claude Code caches (cache reads, 5-minute and 1-hour writes, the Haiku 5.5 prompt-length tier, Fast Mode).

Running `python tools/usage-analyzer/analyze.py` now prints a pointer to claude-rate and exits with status 1, so a script that still calls it fails loudly instead of reading an empty report.

## What replaces each report

| usage-analyzer | claude-rate |
|---|---|
| Overview: total tokens and cost | `rate.py --usage`: requests, sessions and list-price spend per model |
| Top sessions (`--top`, `--sort cost`) | `rate.py --usage --by session`: every session, subagent requests rolled into the session that started them, with active minutes, output share and p90 prompt |
| Spend per project | `rate.py --usage --by project`: worktree folders count toward their repo |
| Spend over time | `rate.py --usage --by day,week` |
| Expensive model overuse | `rate.py --usage --what-if haiku,sonnet`: your recorded tokens repriced on other models, labelled modeled, quality not tested |
| `--json` | `rate.py --usage --json`: the views sit under `usage.facts.by.<view>` |

```bash
python tools/claude-rate/rate.py --usage --by session
python tools/claude-rate/rate.py --usage 30 --by project,day --json
```

The [claude-rate README](../claude-rate/README.md) lists every `--usage` flag.

## The pricing table

`analyze.py` keeps its `MODEL_PRICING` table until the release that deletes this folder, because `scripts/check-rate-values.py` checks it against the other copies of the rates. It no longer prices anything. claude-rate's `MODELS` table prices your usage, and [docs/pricing-data.md](../../docs/pricing-data.md) is the source of truth for the rates.
