# Measurement method

The rules every measured number in this repo follows. It was written on 2026-11-03, before any run, and a run
that breaks a rule here is not published as a result.

Status: **no measured cost-mode result exists yet.** The harness is built
([cost-mode-eval](cost-mode-eval/README.md)); each run costs real money and starts only when the maintainer
approves the run count and the cost cap. Until data is committed next to this file, every "not measured" claim
in this repo stays as written.

## What counts as measured

| Label | Meaning | Example in this repo |
|-------|---------|----------------------|
| **Measured** | A run under this method, with raw data committed beside the table | none yet |
| **Computed** | Arithmetic on posted rates and stated token counts, formula shown | the estimate files in this folder |
| **Claimed** | Another project's number, attributed to it, with how it was taken | the caveman figures below |

The task, model, context-size and leaderboard files in this folder were written before this method and were not
run under it: read them as estimates and community submissions.

## Declared before any run

Changing any row after seeing data is a method change and is reported as one.

| Item | Declared |
|------|----------|
| Question | Against a plain `Answer concisely.` prompt on the same model, does cost-mode lower the cost per passed task, and does it hold quality? |
| Model | One run set per model, model id pinned. The first set is Opus 5.5. Another model is another set, never merged |
| Effort | `medium`, identical in every arm (the default for Opus 5.5) |
| Claude Code | One exact version, recorded in the data. The runner refuses to start on any other and stops if the version changes mid-run |
| Tools | `Read`, `Edit`, `Write`, `Grep`, `Glob` in every arm. No Bash, so every pass/fail check runs after the session |
| Cases | 8 (explain a function, fix a seeded failing test, rename across files, review a diff, structured JSON, a short factual answer, a security question, a model-routing question) |
| **n** | **5 reps per arm and case, so 40 runs per arm per model.** Fewer completed reps in any arm and case makes the whole table a pilot |
| Arms | `none`, `concise` (control), `concise-b` (noise), `costmode-lite`, `costmode-standard`, `costmode-strict`. Optional: `costmode-installed` |
| Runs | 6 arms x 8 cases x 5 reps = 240 per model set |
| Order | Randomized blocks (one block is a case and rep with every arm shuffled), seed 20261103, so stopping early at the cap leaves every arm with the same cases |
| Interval | 95% percentile bootstrap, 5,000 resamples inside each case, seed 20261103 |
| Spend | A per-run budget (`--max-budget-usd`, default $0.60) and a batch cap on summed `total_cost_usd`, both stated to the maintainer with the run count before the run |

### The arms

| Arm | What the model gets | Why it exists |
|-----|---------------------|---------------|
| `none` | Nothing extra | The verbose default. Shows what brevity alone buys, not what cost-mode buys |
| `concise` | The line `Answer concisely.` appended to the system prompt | **The control.** A realistic terse baseline, not a verbose strawman. Every change is measured against it |
| `concise-b` | The same line, a separate arm | **The noise arm.** Control against control sizes run-to-run variation. A cost-mode effect smaller than this arm's interval is not an effect |
| `costmode-lite`, `-standard`, `-strict` | The body of [SKILL.md](../skills/cost-mode/SKILL.md) plus a line naming the level, appended to the system prompt | The skill is active by construction, so this measures its rules and its input cost, not whether it triggers |
| `costmode-installed` | The plugin loaded with `--plugin-dir`, no forcing | Optional. Measures how often the skill fires on its own, which the skill ties to wording about budget, cost, tokens or spending. Reported as an activated rate, from `Skill` tool use in the transcript |

Sampling parameters cannot be set on the 5.5 models, so the variation is real and the answer to it is repeated
runs and the noise arm, not a seed.

## What is recorded per run

Billed output tokens (thinking included: `usage.output_tokens` covers it), fresh input, cache read, cache write,
every request's usage block from the session transcript, turns, tools used, whether the skill fired, the checks
and the verdict, and Claude Code's `total_cost_usd`. Reply text, working paths and session ids stay in the local
`raw/` folder and are not in the committed JSON.

## A pass is decided outside the session

No judge model. Each case carries graders that the harness runs after the session ends: a regex on the reply, a
regex on the files, the project's unit tests, a strict JSON parse, a check that a tool was used. A run passes only
when every grader passes and the session did not end in an error (budget cap, API error, timeout).

A saving counts only on runs that pass. A cheap run that fails the check is not a saving, and an arm that fails
more is charged for it: **cost per passed task** is everything the arm spent, failed runs included, divided by its
passes.

## Cost

- **Billed output** is the output-token count the API reports, thinking included. Opus 5.5's adaptive thinking is
  always on and Sonnet 5.5's is on by default, and thinking bills as output, so brevity rules do not shrink that part
  and the numbers show it.
- **List price** re-prices every request with [rate.py](../tools/claude-rate/rate.py) from the rates in
  [pricing-data.md](../docs/pricing-data.md): fresh input, cache read at the model's own cache-read rate, cache
  write at the 5-minute or 1-hour rate, output. Haiku 5.5 is priced per request by that request's prompt length, so
  it is priced from the transcript's requests, never from run totals. Without a transcript its cost column falls
  back to the client estimate and says so.
- **Client estimate** is `total_cost_usd` from Claude Code. It is computed on the client, it is an estimate and not
  a bill, and it is printed beside the list price, never instead of it.
- A cache read is never derived as `input * 0.1`: the rate is read from the model's own field.

## Statistics

- **Median with min and max as separate columns**, never a range written as `x-y%`. The output columns use passed
  runs only; the cost columns use every run.
- **Change against the control** is the percent change of the arm's statistic over the control's, with the
  bootstrap interval's low and high bounds as separate columns. A change whose interval spans zero is reported as
  within noise. So is a change inside the noise arm's own interval.
- **Quality gate**: an exact McNemar test (`math.comb`, two-sided) on matched case and rep pairs, counting
  regressions (control passes, arm fails) and improvements. **With fewer than 5 discordant pairs the gate is
  labelled "not powered"**, because the test cannot see a quality loss at that size. Easy cases pass in every arm,
  so expect this label; it means quality is untested, not that quality is fine.
- No multiplicity correction. Three levels and two outcomes are tested, so a single interval that excludes zero is
  weak evidence on its own.

## Break-even

Cost-mode adds text that is written to the cache on turn one and read on every later turn. It repays that only if
the output it removes is worth more:

```
output tokens to save per run = injected tokens x (5-minute write rate + (turns - 1) x cache read rate) / output rate
```

Every rate comes from rate.py `MODELS`, per model and, for Haiku 5.5, per tier. Injected tokens are measured as the
first request's prompt size minus the control's, per case. The summary prints the break-even for each model and
the net dollars per run for the model that was run.

## Publication rules

1. Publish every arm, including the ones that lose, cost more, fail the gate or sit inside the noise.
2. No monthly or yearly extrapolation. A run set says what happened in these 8 cases on this model and version.
3. No vague ranges. Each number is measured under this method, computed with the formula shown, or another
   project's claim labelled as such.
4. A pilot is labelled a pilot in the same sentence as its number.
5. Raw JSON goes in beside every table, with working paths and session ids removed.
6. A claim in another file changes only from committed data, and says the model, effort, Claude Code version and
   date the data was taken.

## What the numbers do not show

- The cases are short and synthetic, in a bare session: no CLAUDE.md, no hooks, no memory. A real session is longer
  and its bill is mostly input and cache reads, which an output-style rule cannot touch. The share of your own
  bill that is output is what bounds any saving; `rate.py --usage` (claude-rate 0.4.0 or later) prints that ceiling.
- Cache state at the start of a run varies, so cache read and write differ run to run. This is why cost columns are
  medians with min and max.
- The forced arms do not test the trigger. `costmode-installed` is the only arm that does.
- Pass checks are regexes and unit tests. They catch a wrong answer or a broken edit, not a worse explanation.

## Prior art, and how it is used

Methods borrowed, with what each source's own page supports:

- **JayPokale/Chisle** (MIT): its [rerun write-up](https://github.com/JayPokale/Chisle/blob/HEAD/benchmarks/results/2026-10-12-tools-off-rerun.md)
  publishes arms that lose and results that are not significant, reports a bootstrap interval for each arm, counts
  billed output as including reasoning, and pins the model and Claude Code version.
- **thedotmack/claude-mem** (Apache-2.0): its [read-gate eval](https://github.com/thedotmack/claude-mem/blob/HEAD/tests/evals/read-gate/README.md)
  grades only with `regex` and `tool_used` graders, so no judge model is called, caps spend with `--max-cost-usd`, and
  takes per-run token counts from kept traces.
- **anthropics/claude-cookbooks** (MIT): its [cost optimization notebook](https://github.com/anthropics/claude-cookbooks/blob/HEAD/cost_optimization/cost_optimization.ipynb)
  says to measure cost per completed task, run each configuration more than once, and read cost and pass rate together.

Another project's measured claim, labelled as its own: **JuliusBrussee/caveman** (Apache-2.0). Its
[README](https://github.com/JuliusBrussee/caveman/blob/HEAD/README.md) and
[HONEST-NUMBERS.md](https://github.com/JuliusBrussee/caveman/blob/HEAD/docs/HONEST-NUMBERS.md) (read 2026-11-03)
report that, against an `Answer concisely.` control, caveman -3%, ultracave -35% and megacave -9% at the median.
That is 10 prompts with one run each, output length counted with a tiktoken o200k approximation (not billed
tokens), on claude-opus-5-5, measured on the 3.1.0 rules and not re-run after 3.2.0. The same page lists cases where
caveman lost. It is a claim about output length from one run per prompt; this method asks for repeats, billed
tokens and cost.

`claude plugin eval` can cross-check the plugin-versus-no-plugin pair; see the
[eval README](cost-mode-eval/README.md#optional-cross-check-with-claude-plugin-eval). It is not the harness,
because its baseline arm has no terse control and no noise arm.
