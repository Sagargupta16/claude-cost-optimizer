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
  Opus 4.6         $0.0062           $5.00
  Sonnet 4.6       $0.0037           $3.00
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
  Opus 4.6         $0.2225       $0.0045
  Sonnet 4.6       $0.1335       $0.0027
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
| `--model MODEL` | Show cost for one model: `opus`, `sonnet`, or `haiku` | `--model haiku` |
| `--json` | Output results as JSON | `--json` |

## Pricing

The estimator uses current Claude API pricing (as of March 2026):

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Cache Hit (per 1M tokens) |
|-------|:---------------------:|:----------------------:|:-------------------------:|
| Opus 4.6 | $5.00 | $25.00 | $0.50 |
| Sonnet 4.6 | $3.00 | $15.00 | $0.30 |
| Haiku 4.5 | $1.00 | $5.00 | $0.10 |

Batch API pricing is 50% off the standard rates above.

## Tips

- **CLAUDE.md audit**: Run `estimate.py CLAUDE.md --per-turn 50` regularly. If the per-turn cost feels high, trim your CLAUDE.md.
- **Compare before/after**: Estimate tokens before and after optimizing a file to see the difference.
- **Batch check**: Use a shell loop to estimate all files in a directory:
  ```bash
  for f in src/*.py; do python tools/token-estimator/estimate.py "$f"; done
  ```

## Accuracy Note

This tool uses OpenAI's `cl100k_base` tokenizer as an approximation. Claude uses a different tokenizer internally, so counts may differ by 5-15%. For cost planning purposes, this is accurate enough to make informed decisions.
