# Tools

CLI tools and utilities for measuring, tracking, and reducing Claude Code costs.

## Quick Reference

| Tool | Language | Purpose | Install |
|------|----------|---------|---------|
| [**claude-rate**](claude-rate/) | Python (stdlib only) | **Local Claude / AI setup rater** -- 7 categories, 0-100 score, A+ to F grade, copy-pasteable fixes, monthly-cost projection per model. `--user` grades `~/.claude`; `--usage` prices your local transcripts (cache breaks, spend by class, session and agent type; `--by`, `--what-if`, `--tools`). From 0.4.0 it also runs live: `--statusline` for Claude Code's status line, `--burn` in a terminal, and `--transcript` and `--hook cache-guard` for the hooks | `curl \| sh` one-shot; packaged for `uvx claude-rate` ([Releasing](#releasing)) |
| [Token Estimator](token-estimator/) | Python | Estimate token count and cost for files; counts on the 4.7+ tokenizer are scaled by each model's `tokenizer_overhead` (1.3), a copy of claude-rate's | `pip install tiktoken` |
| [Usage Analyzer](usage-analyzer/) | Python | Retired: it prints a pointer and exits 1. Use `claude-rate --usage --by session` | -- |
| [Badge Generator](badge-generator/) | Python | Grade project config (A+ to F) -- precursor to claude-rate, 4-category | stdlib only |
| [MCP Cost Server](mcp-cost-server/) | TypeScript | In-session cost estimation via MCP | `pnpm install` |
| [VS Code Extension](vscode-extension/) | TypeScript | Status bar token/cost display | `npm install` |
| [/optimize Command](optimize-command/) | Markdown | Claude Code custom command for auditing | Copy to `.claude/commands/` |
| [GitHub Action](actions/claude-cost-audit/) | Python | CI cost audit for PRs | Use in workflow YAML |

## Running Python Tools

All Python tools require Python 3.10+. The token estimator needs `tiktoken`:

```bash
pip install -r ../requirements.txt
```

The other Python tools use stdlib only -- no install needed.

```bash
# Rate the entire project's Claude/AI setup (recommended starting point)
python claude-rate/rate.py .
# Or with no clone and no install (PowerShell: irm https://raw.githubusercontent.com/Sagargupta16/claude-cost-optimizer/main/tools/claude-rate/rate.py | python - .):
curl -sSL https://raw.githubusercontent.com/Sagargupta16/claude-cost-optimizer/main/tools/claude-rate/rate.py | python3 - .

# Estimate tokens for a file
python token-estimator/estimate.py path/to/file.py

# Price your local Claude Code transcripts, per session (replaces usage-analyzer)
python claude-rate/rate.py . --usage --by session

# Grade a project (legacy, 4-category)
python badge-generator/generate.py /path/to/project
```

## Running TypeScript Tools

```bash
# MCP Cost Server
cd mcp-cost-server
pnpm install
pnpm run build

# VS Code Extension
cd vscode-extension
npm install
npm run compile
```

## Tests

Each implementation of the cost math has its own suite, pinned to values worked out by hand from the posted rates (the README's Before vs After, the calculator default, the Haiku 5.5 100,000-token boundary). claude-rate's has six files: `test_rate.py` (billing, session estimate, model ids, `--user`), `test_a1.py`, `test_a2.py` and `test_a3.py` (the `--usage` reports, `--by`, `--what-if`, pace and history, `--tools`), `test_b1.py` (project findings, detected Read deny rules, `--max-context-tokens`) and `test_c.py` (`--statusline`, `--transcript`, `--hook cache-guard`). CI runs every suite, plus `scripts/check-rate-values.py`, which compares every code copy of the rates against `claude-rate/rate.py`, the `scripts/tests` suite and the output-trim fixture check.

```bash
# from the repo root
python -m unittest discover -s tools/claude-rate/tests -v
python -m unittest discover -s scripts/tests -v
python scripts/check-rate-values.py .
python scripts/eval-output-filter.py --strict
pnpm --dir tools/mcp-cost-server run build
pnpm --dir tools/mcp-cost-server test
cd site
npm test
```

## Repo scripts

The consistency checks and measurements in [`../scripts/`](../scripts/):

| Script | What it does | Runs |
|--------|--------------|------|
| `check-pricing-sync.py` | Reads the pricing stamps and retirement wording in every file and compares each stamp with the date in `rate.py` | CI, every pull request |
| `check-rate-values.py` | Compares every rate value in the code copies with `rate.py` | CI, every pull request |
| `check-links.py` | Checks every relative link and heading anchor in the markdown | CI, every pull request |
| [`check-live-pricing.py`](../scripts/check-live-pricing.py) | Fetches Anthropic's pricing page and compares its model and Fast Mode tables with `rate.py`: a changed rate, a model the page no longer lists, a new model `rate.py` does not carry. `--file` reads a saved copy, `--markdown` prints the table for an issue | Weekly and by hand: [`pricing-drift.yml`](../.github/workflows/pricing-drift.yml) opens or updates one "Live pricing drift" issue on drift or a changed page layout (`gh workflow run pricing-drift.yml`) |
| [`eval-output-filter.py`](../scripts/eval-output-filter.py) | Replays the captured runner output in `benchmarks/filter-fixtures/` through the opt-in output-trim hook; `--strict` fails on a dropped needed string, any growth or a trimmed control | CI, every pull request |
| [`measure-compact-flags.py`](../scripts/measure-compact-flags.py) | Counts the characters git prints with and without its compact flags at a pinned commit, for [`benchmarks/search-ladder.md`](../benchmarks/search-ladder.md) | By hand |
| `capture-screenshots.py` | The README screenshots and the site's social preview | By hand |

## Releasing

`claude-rate` and the MCP cost server are packaged for their registries but not published yet. [`release-tools.yml`](../.github/workflows/release-tools.yml) publishes on a tag, with OIDC trusted publishing and no stored tokens:

| Tag | Publishes | Version must match |
|-----|-----------|--------------------|
| `claude-rate-v<version>` | PyPI `claude-rate` (`uvx claude-rate .`) and npm `@sagargupta16/claude-rate` | `claude-rate/pyproject.toml`, `claude-rate/package.json`, `--version` in `rate.py` |
| `mcp-cost-server-v<version>` | npm `@sagargupta16/mcp-cost-server` and the MCP Registry as `io.github.Sagargupta16/cost-estimator` | `mcp-cost-server/package.json`, both versions in `mcp-cost-server/server.json`, the Server version in `mcp-cost-server/src/index.ts` |

One-time setup before the first tag, per registry:

1. **PyPI:** pypi.org, Your projects, Publishing, "Add a new pending publisher": project `claude-rate`, owner `Sagargupta16`, repository `claude-cost-optimizer`, workflow `release-tools.yml`, environment `release`.
2. **npm:** a package must exist before trusted publishing can be configured, so publish `0.2.0` / `1.0.0` once by hand (`npm publish --access public` in each tool folder), then on npmjs.com open the package, Settings, Trusted Publisher, GitHub Actions: `Sagargupta16` / `claude-cost-optimizer` / `release-tools.yml` / environment `release`. The tags `claude-rate-v0.2.0` and `mcp-cost-server-v1.0.0` still work after this: the npm step skips a version that is already on npm, so the first tag publishes `claude-rate` to PyPI and the server to the MCP Registry. The PyPI step uses `skip-existing`, so a failed run can be re-run from the top.
3. **MCP Registry:** nothing to configure; `mcp-publisher login github-oidc` proves the `io.github.Sagargupta16/` namespace from the workflow's own token.

## Web Tools

Browser-based versions are built in [../site/](../site/) and live on the [deployed site](https://sagargupta.online/claude-cost-optimizer/): the [Repo Analyzer](https://sagargupta.online/claude-cost-optimizer/analyzer/), [Cost Calculator](https://sagargupta.online/claude-cost-optimizer/calculator/) and [Badge Checker](https://sagargupta.online/claude-cost-optimizer/badge/). Use `claude-rate` for private or uncommitted repos, which the web analyzer cannot read.
