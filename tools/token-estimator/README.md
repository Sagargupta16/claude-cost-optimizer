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
  Opus 5           $0.0062           $5.00
  Sonnet 5         $0.0037           $3.00
  Haiku 4.5        $0.0012           $1.00
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
  Opus 5           $0.2225       $0.0045
  Sonnet 5         $0.1335       $0.0027
  Haiku 4.5        $0.0445       $0.0009
```

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
| `--model MODEL` | Show cost for one model: `fable` (Fable 5), `opus` (Opus 5), `opus_4_8`, `opus_4_7`, `opus_4_6`, `sonnet` (Sonnet 5), `sonnet_4_6`, `haiku`, `fast_mode`, `mythos` (Mythos 5) | `--model haiku` |
| `--json` | Output results as JSON | `--json` |

File reads are contained to the current directory tree or your home directory; paths outside both are refused.

## Pricing

The estimator uses current Claude API pricing (as of 2026-07-25):

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Cache Hit (per 1M tokens) |
|-------|:---------------------:|:----------------------:|:-------------------------:|
| Fable 5 (alias: `fable`) | $10.00 | $50.00 | $1.00 |
| Mythos 5 (alias: `mythos`, Glasswing only) | $10.00 | $50.00 | $1.00 |
| Opus 5 (alias: `opus`) | $5.00 | $25.00 | $0.50 |
| Opus 4.8 (alias: `opus_4_8`, legacy) | $5.00 | $25.00 | $0.50 |
| Opus 4.7 (alias: `opus_4_7`, legacy) | $5.00 | $25.00 | $0.50 |
| Opus 4.6 (alias: `opus_4_6`, legacy) | $5.00 | $25.00 | $0.50 |
| Sonnet 5 (alias: `sonnet`) | $3.00 | $15.00 | $0.30 |
| Sonnet 4.6 (alias: `sonnet_4_6`, legacy) | $3.00 | $15.00 | $0.30 |
| Haiku 4.5 | $1.00 | $5.00 | $0.10 |
| Opus 5 / 4.8 Fast Mode (alias: `fast_mode`) | $10.00 | $50.00 | n/a |

Batch API pricing is 50% off the standard rates above (Opus 5 batch: $2.50/$12.50; Fable 5 batch: $5/$25).

Sonnet 5 also has an introductory rate of $2/$10 through 2026-08-31. The table above uses the standard rate so that projections stay valid past that date.

> **Opus 5 note.** Opus 5 costs the same per token as Opus 4.8, but thinking is on by default and reasoning tokens bill as output. This tool measures input tokens, so its numbers are unaffected -- but your real output bill on Opus 5 will run higher than the same workload on Opus 4.8 until you lower `output_config.effort`.

## Tips

- **CLAUDE.md audit**: Run `estimate.py CLAUDE.md --per-turn 50` regularly. If the per-turn cost feels high, trim your CLAUDE.md.
- **Compare before/after**: Estimate tokens before and after optimizing a file to see the difference.
- **Batch check**: Use a shell loop to estimate all files in a directory:
  ```bash
  for f in src/*.py; do python tools/token-estimator/estimate.py "$f"; done
  ```

## Accuracy Note

This tool uses OpenAI's `cl100k_base` tokenizer as an approximation. Claude uses a different tokenizer internally, so counts may differ. Note that the newer tokenizer (Opus 4.7 and later, including Opus 4.8 and Opus 5, plus Fable 5, Sonnet 5, and Sonnet 4.6) may use up to 35% more tokens for the same text, so treat these estimates as a lower bound for those models. Opus 5 shares that tokenizer exactly, so nothing needs re-baselining when moving from Opus 4.7 or 4.8. For cost planning purposes, this is accurate enough to make informed decisions.
