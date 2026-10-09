# Token Estimator

Estimate how many tokens a file or text will consume when sent to Claude, and calculate the associated cost across models.

This uses the `cl100k_base` encoding from [tiktoken](https://github.com/openai/tiktoken) as an approximation for Claude's tokenizer. Actual Claude token counts may differ slightly, but this provides a reliable estimate for cost planning.

## Installation

```bash
pip install tiktoken
```

No other dependencies are required. Python 3.10+ recommended.

## Usage

### Basic: Estimate tokens for a file

```bash
python tools/token-estimator/estimate.py path/to/file.py
```

Output:

```
  Token Estimate
  --------------------------------------------------
  Source:     file.py
  Lines:      142
  Characters: 4,831
  Tokens:     1,247

  Cost Estimate (single input pass)
  --------------------------------------------------
  Model          Input Cost    $/1M tokens
  ..............  ............  ..............
  Opus 5.5         $0.0050           $4.00
  Sonnet 5.5       $0.0025           $2.00
  Haiku 5.5        $0.0001           $0.10
```

### Analyze CLAUDE.md cost over a session

The `--per-turn` flag projects cost over N conversation turns. This is essential for understanding the true cost of your CLAUDE.md file, since it loads on every single turn.

```bash
python tools/token-estimator/estimate.py CLAUDE.md --per-turn 50
```

Output includes a projection table:

```
  Per-Turn Projection (50 turns)
  --------------------------------------------------
  Tokens per turn:  890
  Total tokens:     44,500

  Model          Total Cost     Per Turn
  ..............  ............  ............
  Opus 5.5         $0.178        $0.0036
  Sonnet 5.5       $0.089        $0.0018
  Haiku 5.5       $0.0044        $0.0001
```

On Haiku 5.5 the price tier comes from the tokens per turn (one request), not the session total: 890 tokens is under 100,000, so all 50 turns are priced at $0.10/1M. A single file or turn over 100,000 tokens is priced at $0.50/1M, and its `$/1M tokens` column shows that rate.

### Filter to a specific model

```bash
python tools/token-estimator/estimate.py src/app.py --model haiku
```

### Read from stdin

```bash
echo "Hello, Claude" | python tools/token-estimator/estimate.py -
cat CLAUDE.md | python tools/token-estimator/estimate.py -
```

### JSON output

```bash
python tools/token-estimator/estimate.py CLAUDE.md --json
python tools/token-estimator/estimate.py CLAUDE.md --per-turn 50 --json
```

## Flags Reference

| Flag | Description | Example |
|------|-------------|---------|
| `source` | File path to analyze, or `-` for stdin | `estimate.py CLAUDE.md` |
| `--per-turn N` | Project cost over N conversation turns | `--per-turn 50` |
| `--model MODEL` | Show cost for one model: `fable` (Fable 5.1), `fable_5`, `opus` (Opus 5.5), `opus_5`, `opus_4_8`, `opus_4_7`, `opus_4_6`, `sonnet` (Sonnet 5.5), `sonnet_5`, `sonnet_4_6`, `haiku` (Haiku 5.5), `haiku_4_5` (legacy Haiku 4.5), `fast_mode` (Opus 5.5 Fast), `fast_mode_opus_5` (Opus 5 / 4.8 Fast), `mythos` (Mythos 5.1) | `--model haiku` |
| `--json` | Output results as JSON | `--json` |

File reads are contained to the current directory tree or your home directory; paths outside both are refused.

## Pricing

The estimator uses current Claude API pricing (as of 2026-10-09):

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Cache Hit (per 1M tokens) |
|-------|:---------------------:|:----------------------:|:-------------------------:|
| Fable 5.1 (alias: `fable`) | $10.00 | $50.00 | **$0.25** |
| Fable 5 (alias: `fable_5`) | $10.00 | $50.00 | $1.00 |
| Mythos 5.1 (alias: `mythos`, verified organizations only) | $10.00 | $50.00 | **$0.25** |
| Opus 5.5 (alias: `opus`) | $4.00 | $20.00 | **$0.20** |
| Opus 5 (alias: `opus_5`, legacy) | $5.00 | $25.00 | $0.50 |
| Opus 4.8 (alias: `opus_4_8`, legacy) | $5.00 | $25.00 | $0.50 |
| Opus 4.7 (alias: `opus_4_7`, legacy) | $5.00 | $25.00 | $0.50 |
| Opus 4.6 (alias: `opus_4_6`, legacy) | $5.00 | $25.00 | $0.50 |
| Sonnet 5.5 (alias: `sonnet`) | $2.00 | $10.00 | **$0.10** |
| Sonnet 5 (alias: `sonnet_5`, legacy) | $2.00 | $10.00 | $0.20 |
| Sonnet 4.6 (alias: `sonnet_4_6`, legacy) | $3.00 | $15.00 | $0.30 |
| Haiku 5.5 (alias: `haiku`), prompt <= 100K tokens | $0.10 | $0.50 | $0.01 |
| Haiku 5.5 (alias: `haiku`), prompt > 100K tokens | $0.50 | $2.50 | $0.05 |
| Haiku 4.5 (alias: `haiku_4_5`, legacy) | $1.00 | $5.00 | $0.10 |
| Opus 5.5 Fast Mode (alias: `fast_mode`) | $8.00 | $40.00 | n/a |
| Opus 5 / 4.8 Fast Mode (alias: `fast_mode_opus_5`) | $10.00 | $50.00 | n/a |

Cache hits have three multipliers: 0.1x base input by default, 0.025x on Fable 5.1 and Mythos 5.1, and 0.05x on Opus 5.5 and Sonnet 5.5 (95% off).

Batch API pricing is 50% off the standard rates above (Opus 5.5 batch: $2/$10; legacy Opus 5 batch: $2.50/$12.50; Fable 5 batch: $5/$25; Haiku 5.5 batch: $0.05/$0.25 up to 100K prompt tokens, $0.25/$1.25 above).

Sonnet 5 is $2/$10 permanently -- the launch rate was labelled introductory through 2026-08-31, but Anthropic made it standard and cancelled the increase to $3/$15. Sonnet 5.5 (released 2026-09-28) launched at the same $2/$10 and moved Sonnet 5 to legacy.

> **Haiku 5.5 note.** Haiku 5.5 (released 2026-10-07) is the first model priced by prompt length: $0.10/$0.50 up to 100K prompt tokens, $0.50/$2.50 above. Anthropic prices each request on its own, and the prompt length counts cache reads and writes, so a 100,001-token prompt pays 5x the input rate of a 100,000-token one. This tool picks the tier from one request's tokens (with `--per-turn`, the tokens per turn). Haiku 5.5 counts ~30% more tokens than Haiku 4.5 for the same text, so treat a count near 100K as over the line. Minimum cacheable prompt is 512 tokens (Haiku 4.5: 4,096).

> **Sonnet 5.5 note.** Sonnet 5.5 has the same input and output price and tokenizer as Sonnet 5, so this tool's input-cost numbers are identical for both; its cache read is half Sonnet 5's ($0.10 vs $0.20 since 2026-10-07). Its minimum cacheable prompt drops to 512 tokens (Sonnet 5: 1,024). Adaptive thinking is on by default, reasoning bills as output, and effort levels are recalibrated, so re-baseline your real output bill after migrating.

> **Opus 5.5 note.** Opus 5.5 costs 20% less per token than Opus 5, but adaptive thinking is always on (it cannot be disabled) and reasoning tokens bill as output. Effort defaults to `medium` (Opus 5 defaulted to `high`), so a request that omits effort thinks less than it did on Opus 5 -- but code that disabled thinking on Opus 5 now pays for thinking tokens it did not pay for before. This tool measures input tokens, so its numbers are unaffected; re-baseline your real output bill after migrating.

## Tips

- **CLAUDE.md audit**: Run `estimate.py CLAUDE.md --per-turn 50` regularly. If the per-turn cost feels high, trim your CLAUDE.md.
- **Compare before/after**: Estimate tokens before and after optimizing a file to see the difference.
- **Batch check**: Use a shell loop to estimate all files in a directory:
  ```bash
  for f in src/*.py; do python tools/token-estimator/estimate.py "$f"; done
  ```

## Accuracy Note

This tool uses OpenAI's `cl100k_base` tokenizer as an approximation. Claude uses a different tokenizer internally, so counts may differ. Note that the newer tokenizer (Opus 4.7 and later, including Opus 4.8, Opus 5, and Opus 5.5, plus Fable 5, Sonnet 5.5, Sonnet 5, and Sonnet 4.6) may use up to 35% more tokens for the same text, so treat these estimates as a lower bound for those models. Haiku 5.5 uses it too (~30% more tokens than Haiku 4.5), which matters most near its 100K price threshold. Opus 5.5 shares that tokenizer exactly, so token counts need no re-baselining when moving from Opus 4.7, 4.8, or 5. For cost planning purposes, this is accurate enough to make informed decisions.
