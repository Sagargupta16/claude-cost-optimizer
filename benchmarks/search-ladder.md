# Compact Flags: Character Counts on This Repo

> **Evidence: measured on one repository, deterministic, not a session saving.** The table counts the characters git prints at one pinned commit of this repo, with and without a compact flag, using [scripts/measure-compact-flags.py](../scripts/measure-compact-flags.py). What a command costs inside a session depends on what Claude does with its output next, so no row here is a saving on your bill.

Many commands have a compact form that prints a summary instead of everything: `git diff --stat` instead of the whole patch, `git log --oneline` instead of full commit messages. The habit is to ask for the compact form first and fetch detail only where the task needs it. The search side of the same habit (search narrowly, then read the part you need) is in [Guide 02](../guides/02-context-optimization.md); it has no measurement here.

## How It Is Counted

- **Exact characters are the primary number.** The script runs both forms of each command with git's output pinned (no colour, pager, signatures or decorations, myers diff, 7-character abbreviations, medium log format, `COLUMNS=80`), so a user's own git config does not change the counts.
- **Estimated tokens** use this repo's convention for the current tokenizer: characters / 4 x 1.3, the factor `tools/claude-rate/rate.py` applies to Opus 4.7 and later models. [Guide 01](../guides/01-understanding-costs.md)'s "about 2.5 characters per token" gives about 23% more tokens for the same text (computed: (4 / 1.3) / 2.5 = 1.23).
- **Claude Code's inline cap decides what a long output costs.** A valid Bash result stays inline up to about 30,000 characters; past that Claude receives a file path plus a preview of up to the first 2,000 characters, and reads or searches the file when it needs the rest. A failing command gets about 10,000 characters inline, as a head-and-tail excerpt with no file path. The `bashOutputMaxChars` setting (v2.1.261+, up to 128,000) moves the inline ceiling ([tools reference](https://code.claude.com/docs/en/tools-reference), read 2026-11-03). For a row whose full output is over 30,000 characters the script computes no saving.

## Results

Commit `8e337f0df6fcfa720d6c0b8d6a535f6edb163ca8`, git 2.55.0.windows.3, run 2026-11-03. Output of `python scripts/measure-compact-flags.py`:

| Command pair | Full chars | Compact chars | Full est. tokens | Compact est. tokens | Note |
|---|--:|--:|--:|--:|---|
| `git diff 8e337f0~1 8e337f0` vs `--stat` | 124,148 | 367 | 40,349 | 120 | full output is over the 30,000-char inline cap: Claude gets a file path plus a 2,000-char preview, and the cost depends on what it reads next, so no saving is computed |
| `git log -20 8e337f0` vs `--oneline` | 23,373 | 1,603 | 7,597 | 521 | compact form is 21,770 chars (93.1%) shorter; both under the cap |
| `git show 8e337f0` vs `--stat` | 124,351 | 570 | 40,415 | 186 | full output is over the 30,000-char inline cap: Claude gets a file path plus a 2,000-char preview, and the cost depends on what it reads next, so no saving is computed |
| `git status` vs `git status --short` | not measured | not measured | - | - | output depends on the working tree, not a commit |
| `gh pr view` vs `gh pr view --json <fields>` | not measured | not measured | - | - | needs network and GitHub auth |
| `gh run view --log` vs `--log-failed` | not measured | not measured | - | - | needs network and GitHub auth |
| `docker ps` vs `docker ps --format` | not measured | not measured | - | - | needs a Docker daemon |
| `kubectl get` vs `-o name` / custom columns | not measured | not measured | - | - | needs a cluster |
| `aws ...` vs `--query ... --output text` | not measured | not measured | - | - | needs AWS credentials and resources |
| `pytest` vs `pytest -q --tb=short` | not measured | not measured | - | - | this repo's Python tests use unittest |
| `jest` vs `jest --silent` | not measured | not measured | - | - | this repo's site tests use vitest |

## Reading the Rows

- **`git log -20` is the clean row.** Both forms fit inline, so the compact form puts 21,770 fewer characters into the conversation, about 7,076 fewer estimated tokens (computed: 7,597 - 521), every one of which later requests then re-read from cache.
- **The `git diff` and `git show` rows cross the cap.** The full patch (124,148 characters) never arrives inline: Claude gets a path and a 2,000-character preview, and what it costs depends on how much of the file Claude reads afterwards. `--stat` tells Claude which files changed, not how; when the task needs the change itself, a scoped `git diff <base> <head> -- <path>` is the narrow read.
- **The unmeasured rows are habits, not numbers.** `gh`, `docker`, `kubectl` and `aws` need services this repo cannot run offline, and the test runners are not the ones this repo uses. No figure is published for them.

## Reproduce

```bash
python scripts/measure-compact-flags.py              # the pinned commit above
python scripts/measure-compact-flags.py --sha HEAD   # any other commit
```

Standard library only, offline, and read-only; it needs a clone that contains the commit (a shallow clone may not). Another git version can print slightly different text and so slightly different counts.

The baseline-versus-compact comparison on one repository follows the shape of the benchmark in [TrNgTien/vfs](https://github.com/TrNgTien/vfs/blob/HEAD/pkg/bench/bench.go) (MIT), which estimates tokens as bytes / 4; the x1.3 factor and the inline-cap handling are this repo's.
