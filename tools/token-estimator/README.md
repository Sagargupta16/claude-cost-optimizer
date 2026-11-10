# Token Estimator

Estimate how many tokens a file or text will consume when sent to Claude, and calculate the associated cost across models.

This counts with the `cl100k_base` encoding from [tiktoken](https://github.com/openai/tiktoken), which is not Claude's tokenizer, then scales the count by 1.3 for the models on the Claude 4.7 and later tokenizer, because Anthropic says that tokenizer produces approximately 30% more tokens for the same text (see [Accuracy Note](#accuracy-note)). Both numbers are estimates for cost planning, not Claude token counts.

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

Output for this tool's own source file (`estimate.py`), abridged to four of the fifteen rows, measured 2026-11-03; your file's numbers will differ:

```
  Token Estimate
  --------------------------------------------------
  Source:      estimate.py
  Lines:       560
  Characters:  20,374
  cl100k:      5,761
  4.7+ models: ~7,489 (cl100k x 1.3, estimate)

  Cost Estimate (single input pass)
  --------------------------------------------------
  Model                       Tokens   Input Cost    $/1M tokens
  ........................ ......... ............ ..............
  Opus 5.5                     7,489       $0.030          $4.00
  Opus 4.6 (legacy)            5,761       $0.029          $5.00
  Sonnet 5.5                   7,489       $0.015          $2.00
  Haiku 5.5                    7,489      $0.0007          $0.10
```

Each row is priced on its own model's count: the models on the 4.7+ tokenizer (Opus 5.5, Sonnet 5.5, Haiku 5.5 and the rest) on `round(cl100k x 1.3)`, and Opus 4.6, Sonnet 4.6 and Haiku 4.5 on the raw cl100k count.

### Analyze CLAUDE.md cost over a session

The `--per-turn` flag projects cost over N conversation turns. This is essential for understanding the true cost of your CLAUDE.md file, since it loads on every single turn.

```bash
python tools/token-estimator/estimate.py CLAUDE.md --per-turn 50
```

Output includes a projection table (this repository's `CLAUDE.md`, 76 lines, 5,288 characters, 1,445 cl100k tokens, abridged to four rows, measured 2026-11-03):

```
  Per-Turn Projection (50 turns)
  --------------------------------------------------
  Model                     Tokens/turn   Total Cost     Per Turn
  ........................ ............ ............ ............
  Opus 5.5                        1,878       $0.376      $0.0075
  Opus 4.6 (legacy)               1,445       $0.361      $0.0072
  Sonnet 5.5                      1,878       $0.188      $0.0038
  Haiku 5.5                       1,878      $0.0094      $0.0002
```

On Haiku 5.5 the price tier comes from the tokens per turn (one request, on the scaled count), not the session total: 1,878 tokens is under 100,000, so all 50 turns are priced at $0.10/1M. A single file or turn over 100,000 scaled tokens is priced at $0.50/1M, and its `$/1M tokens` column shows that rate.

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

`tokens` at the top level is the raw cl100k count, labelled by `tokens_basis`. Each entry under `costs` has its own `tokens` (the count scaled for that model's tokenizer) and a `basis` of `cl100k` or `cl100k x 1.3 (estimate)`; with `--per-turn`, its `per_turn_tokens` and `total_tokens` use that scaled count too.

## Flags Reference

| Flag | Description | Example |
|------|-------------|---------|
| `source` | File path to analyze, or `-` for stdin | `estimate.py CLAUDE.md` |
| `--per-turn N` | Project cost over N conversation turns | `--per-turn 50` |
| `--model MODEL` | Show cost for one model: `fable` (Fable 5.2), `fable_5_1` (legacy Fable 5.1), `fable_5`, `opus` (Opus 5.5), `opus_5`, `opus_4_8`, `opus_4_7`, `opus_4_6`, `sonnet` (Sonnet 5.5), `sonnet_5`, `sonnet_4_6`, `haiku` (Haiku 5.5), `haiku_4_5` (legacy Haiku 4.5), `fast_mode` (Opus 5.5 Fast), `fast_mode_fable` (Fable 5.2 Fast), `fast_mode_opus_5` (Opus 5 / 4.8 Fast), `mythos` (Mythos 5.2), `mythos_5_1` (legacy Mythos 5.1) | `--model haiku` |
| `--json` | Output results as JSON | `--json` |

File reads are contained to the current directory tree or your home directory; paths outside both are refused.

## Pricing

The estimator uses current Claude API pricing (as of 2026-11-10):

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Cache Hit (per 1M tokens) |
|-------|:---------------------:|:----------------------:|:-------------------------:|
| Fable 5.2 (alias: `fable`) | $8.00 | $40.00 | **$0.20** |
| Fable 5.1 (alias: `fable_5_1`, legacy) | $10.00 | $50.00 | $0.25 |
| Fable 5 (alias: `fable_5`) | $10.00 | $50.00 | $1.00 |
| Mythos 5.2 (alias: `mythos`, verified organizations only) | $8.00 | $40.00 | **$0.20** |
| Mythos 5.1 (alias: `mythos_5_1`, legacy, verified organizations only) | $10.00 | $50.00 | $0.25 |
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
| Fable 5.2 Fast Mode (alias: `fast_mode_fable`) | $16.00 | $80.00 | n/a |
| Opus 5 / 4.8 Fast Mode (alias: `fast_mode_opus_5`) | $10.00 | $50.00 | n/a |

Cache hits have three multipliers: 0.1x base input by default, 0.025x on Fable 5.2, Mythos 5.2, Fable 5.1 and Mythos 5.1, and 0.05x on Opus 5.5 and Sonnet 5.5 (95% off).

Batch API pricing is 50% off the standard rates above (Opus 5.5 batch: $2/$10; legacy Opus 5 batch: $2.50/$12.50; Fable 5.2 batch: $4/$20; Fable 5 batch: $5/$25; Haiku 5.5 batch: $0.05/$0.25 up to 100K prompt tokens, $0.25/$1.25 above).

Fast Mode is Fable 5.2, Mythos 5.2, Opus 5.5, Opus 5 and Opus 4.8 only. Fable 5.2 (released 2026-11-09) and Opus 5.5 (since 2026-10-15) have it generally available with no beta header, at a flat 2x their own base rate (Fable 5.2: $16/$80); Opus 5 and Opus 4.8 are a research preview that needs the `fast-mode-2026-02-01` beta header, and Opus 4.8's fast mode is deprecated and removed on 2026-11-30 ([fast mode](https://platform.claude.com/docs/en/build-with-claude/fast-mode), read 2026-11-10). The Cache Hit column is n/a because this tool does not price cache reads at fast mode rates; Anthropic stacks the caching multipliers on top of fast mode pricing.

Sonnet 5 is $2/$10 permanently -- the launch rate was labelled introductory through 2026-08-31, but Anthropic made it standard and cancelled the increase to $3/$15. Sonnet 5.5 (released 2026-09-28) launched at the same $2/$10 and moved Sonnet 5 to legacy.

> **Haiku 5.5 note.** Haiku 5.5 (released 2026-10-07) is the first model priced by prompt length: $0.10/$0.50 up to 100K prompt tokens, $0.50/$2.50 above. Anthropic prices each request on its own, and the prompt length counts cache reads and writes, so a 100,001-token prompt pays 5x the input rate of a 100,000-token one. This tool picks the tier from one request's tokens (with `--per-turn`, the tokens per turn). Haiku 5.5 counts ~30% more tokens than Haiku 4.5 for the same text, so the tier test uses the scaled count (cl100k x 1.3, an estimate): a text of 80,001 cl100k tokens is ~104,001 scaled tokens and is priced at $0.50/1M, so treat a count near 100K as borderline. Minimum cacheable prompt is 512 tokens (Haiku 4.5: 4,096).

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

This tool counts with OpenAI's `cl100k_base` tokenizer, which is not Claude's, so every count is an estimate. Anthropic's [pricing page](https://platform.claude.com/docs/en/about-claude/pricing) says Claude 4.7 and later models use a newer tokenizer that produces approximately 30% more tokens for the same text, that the exact increase depends on the content, and that Claude Sonnet 4.6 and earlier models use the previous tokenizer ([token counting](https://platform.claude.com/docs/en/build-with-claude/token-counting) lists the Fable and Mythos models). So the cost tables price Fable 5.2, Fable 5.1, Fable 5, Mythos 5.2, Mythos 5.1, Opus 5.5, Opus 5, Opus 4.8, Opus 4.7, Sonnet 5.5, Sonnet 5, Haiku 5.5 and both Fast Mode rows on `round(cl100k x 1.3)`, and Opus 4.6, Sonnet 4.6 and Haiku 4.5 on the raw cl100k count. The factor is each model's `tokenizer_overhead`, a copy of the one in `claude-rate` that `scripts/check-rate-values.py` keeps equal.

1.3 is the pricing page's ratio between the two Claude tokenizers applied to a count from a third tokenizer, so it is a planning estimate, not a measurement of your file. As a cross-check, Anthropic's [models overview](https://platform.claude.com/docs/en/about-claude/models/overview) puts 1M tokens at roughly 2.5M Unicode characters on the current tokenizer, about 2.5 characters per token. By that rule this repository's `CLAUDE.md` (5,288 characters) is 2,115 tokens, against 1,878 from 1,445 x 1.3 (both computed 2026-11-03), so on text-heavy files the character rule gives the larger figure. On Haiku 5.5 the gap matters most near its 100K price threshold. Opus 5.5 shares the 4.7+ tokenizer, so token counts need no re-baselining when moving from Opus 4.7, 4.8, or 5.
