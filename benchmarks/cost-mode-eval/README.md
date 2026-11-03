# cost-mode-eval

A harness for the first measured benchmark of the cost-mode skill. It follows [METHOD.md](../METHOD.md), which
declares the arms, the cases, n, the statistics and the publication rules before any run.

**Nothing has been run and no results are committed.** Every run is a real model call that costs money, so the
runner refuses to call anything without `--yes`, `--max-cost-usd` and `--cli-version`, and the maintainer approves
each run count and cap first. The cost-mode "not measured" claims elsewhere in this repo stay as they are until data
is committed here.

## Files

| Path | What it is |
|------|------------|
| `run.py` | The runner: `claude --bare -p --output-format json` for every arm, case and rep, with the model, effort and Claude Code version pinned |
| `summarize.py` | Prints the tables from a `results.json`: pass rate, output tokens, cache, list-price cost, change against the control with a bootstrap interval, the McNemar quality gate, per-case medians, a per-model break-even |
| `evalkit.py` | What both share: arms, case loading, graders, transcript reading, loading rate.py |
| `evals/<case>/` | One case: `prompt.md`, `case.json` (metadata and graders), and an optional `fixture/` copied into a throwaway folder per run |
| `results/` | Local run output. Gitignored |
| `data/` | Where a reviewed `results.json` is committed. Does not exist until the first measured run |

## Run it

1. See the plan. This starts no process, calls nothing and writes no results:

   ```
   python benchmarks/cost-mode-eval/run.py --dry-run
   ```

   It prints the model, effort, arms, cases, the run count (6 arms x 8 cases x 5 reps = 240) and the worst case at
   the per-run budget. Quote the run count and your `--max-cost-usd` when you ask for approval. The worst case is a
   ceiling (runs x per-run budget), not an estimate: no cost has been measured yet.

2. Credentials. `--bare` never reads a login or the keychain. Export `ANTHROPIC_API_KEY`, or the provider's own
   variables (for Bedrock, `CLAUDE_CODE_USE_BEDROCK=1` plus AWS credentials, and pass `--model-id` with the
   Bedrock model id).

3. A cheap pilot first (one rep, 48 runs, labelled a pilot by `summarize.py`):

   ```
   python benchmarks/cost-mode-eval/run.py --yes --max-cost-usd 10 --cli-version 2.1.312 --reps 1
   ```

   `--cli-version` must equal `claude --version`; the runner stops if it differs, and again if it changes during
   the run.

4. The declared run: leave `--reps` at its default of 5. Then:

   ```
   python benchmarks/cost-mode-eval/summarize.py benchmarks/cost-mode-eval/results/<run>/results.json
   ```

The runner stops after the first run if claude printed no JSON, the result had no usage, or no session transcript
was found under `cfg/projects`. Those are the assumptions about the CLI's output that this harness could not check
without spending money, and every later run depends on them. It also stops before a run that could take the batch
past `--max-cost-usd`, and after three errors in a row. `--resume --out <folder>` continues a stopped run.

### Flags

| Flag | Meaning |
|------|---------|
| `--dry-run` | Print the plan, the run count and the cost cap; call nothing |
| `--yes`, `--max-cost-usd N`, `--cli-version V` | All three are required for a real run |
| `--model KEY` | `opus-5-5` (default), `sonnet-5-5` or `haiku-5-5`, the rate.py `MODELS` key. One model per invocation |
| `--model-id ID` | The id for `claude --model` when the platform's differs from the API id |
| `--effort LEVEL` | `medium` by default, identical in every arm |
| `--arms`, `--cases` | Comma lists. Default: the six arms and all eight cases |
| `--reps N` | Reps per arm and case. Default 5, the n declared in METHOD.md |
| `--per-run-usd` | `--max-budget-usd` for each run. Default 0.60 |
| `--claude-arg=--flag` | Extra flag for every run, such as `--claude-arg=--settings`. Recorded in the manifest |
| `--keep-work` | Keep each run's temp working folder to inspect an edit |

## Arms

| Arm | Role |
|-----|------|
| `none` | Nothing appended |
| `concise` | Appends `Answer concisely.` The control |
| `concise-b` | Identical to `concise`; the noise arm |
| `costmode-lite`, `costmode-standard`, `costmode-strict` | The body of `skills/cost-mode/SKILL.md` plus the level, appended to the system prompt through `--append-system-prompt-file`. The skill is active by construction |
| `costmode-installed` | Not in the default set. Loads the repo root as a plugin with `--plugin-dir` and forces nothing, so it measures how often the skill fires. The case prompts mostly lack the budget and cost wording its description triggers on, so expect a low activated rate |

## Cases

All eight use the same tools in every arm: `Read`, `Edit`, `Write`, `Grep`, `Glob`. There is no Bash, so the
"run the tests" step is a check the harness runs after the session, with the Python that runs `run.py`. Those
checks execute the model's edited fixture files on your machine, in a throwaway temp folder.

| Case | Category | Checked by |
|------|----------|------------|
| `explain-function` | explain | file opened; reply names the refill and the capacity cap; reply says 0 means allowed and a positive value is a wait |
| `fix-failing-test` | code | unit tests pass after the session; the test file still holds its original assertion; a file was edited |
| `rename-across-files` | code | unit tests pass; the old name is gone from every `.py` and `.md` file; the new definition exists; unrelated code is untouched |
| `review-diff` | review | diff opened; reply finds the empty-list division and the mutable default argument |
| `structured-json` | structured | the whole reply parses as the requested object with the right values |
| `short-factual` | factual | reply says 429 |
| `security-question` | security | reply names XSS and recommends an HttpOnly cookie. Marked `expect_gain: false`: cost-mode switches itself off for security, so no saving is expected |
| `model-routing` | routing | reply names Opus and a cheaper model or tool for the rename |

Regex graders catch a missing fact, not a worse explanation. Add a case by creating `evals/<id>/` with `prompt.md`
and `case.json`; a grader is one of:

| Type | Fields | Passes when |
|------|--------|-------------|
| `regex` | `pattern`, `flags` (`i`, `s`, `m`), `match` (default true) | the reply matches (or, with `match: false`, does not) |
| `file_regex` | `glob`, `pattern`, `match` | any file under the working folder matching `glob` contains the pattern (with `match: false`, none does) |
| `command` | `argv` (a leading `python` means the running interpreter), `timeout` | the command exits 0 |
| `json_keys` | `require` (key to `string`, `number`, `boolean`, `array`, `object`), `equals` | the reply, with one optional code fence, parses as an object that satisfies both |
| `tool_used` | `tools` (any of), `match` | the transcript shows one of the tools used (or none, with `match: false`) |

## What is stored

`results/<utc time>-<model>/` holds:

- `results.json`: the manifest (model, effort, Claude Code version, seed, arm text hashes, case hashes, the caps), the
  status, and one record per run. A record has the verdict and each check, tokens, per-request usage, tools used,
  whether the skill fired and Claude Code's `total_cost_usd`. It has no reply text, working paths or session ids, so
  it can be committed once reviewed.
- `raw/`: each run's stdout and stderr. Local only.
- `cfg/`: the `CLAUDE_CONFIG_DIR` used, which holds the session transcripts. Local only.
- `append/`: the exact text each arm appended.

To publish a measured result: copy `results.json` to `data/<date>-<model>.json`, commit the `summarize.py` tables
beside it, run the repo's consistency checks (`scripts/check-pricing-sync.py`, `check-rate-values.py`,
`check-links.py`), and only then change a claim elsewhere, following the publication rules in METHOD.md.

## Optional cross-check with claude plugin eval

Claude Code ships `claude plugin eval`, which runs eval cases against a plugin and can add a no-plugin baseline arm
(`--ablation with-without`). Treat it as a second opinion on the plugin-versus-no-plugin pair only: it has no
terse-control arm and no noise arm, and the cases here use this folder's own `case.json` format, not its
`prompt.md` plus `graders/` layout. Run `claude plugin eval --help` first to confirm the flags on your version, and
note that the command can be switched off server-side. Point it at the repo root, which is the Claude plugin;
`plugins/cost-mode` is the Codex copy.

## Limits

Cases are short and synthetic and run in a bare session, so a saving here is an effect on output in that setting,
not on a real session's bill. n is 40 runs per arm per model, so intervals are wide; "within noise" and "not
powered" are expected results. See "What the numbers do not show" in [METHOD.md](../METHOD.md).
