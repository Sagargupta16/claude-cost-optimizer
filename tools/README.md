# Tools

CLI tools and utilities for measuring, tracking, and reducing Claude Code costs.

## Quick Reference

| Tool | Language | Purpose | Install |
|------|----------|---------|---------|
| [**claude-rate**](claude-rate/) | Python (stdlib only) | **Local Claude / AI setup rater** -- 7 categories, 0-100 score, A+ to F grade, copy-pasteable fixes, monthly-cost projection per model | `curl \| sh` one-shot; packaged for `uvx claude-rate` ([Releasing](#releasing)) |
| [Token Estimator](token-estimator/) | Python | Estimate token count and cost for files | `pip install tiktoken` |
| [Usage Analyzer](usage-analyzer/) | Python | Analyze session data for cost hotspots | stdlib only |
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

# Analyze usage data
python usage-analyzer/analyze.py ~/.claude/projects/

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

Each implementation of the cost math has its own suite, pinned to values worked out by hand from the posted rates (the README's Before vs After, the calculator default, the Haiku 5.5 100,000-token boundary). CI runs all three, plus `scripts/check-rate-values.py`, which compares every code copy of the rates against `claude-rate/rate.py`.

```bash
# from the repo root
python -m unittest discover -s tools/claude-rate/tests -v
python scripts/check-rate-values.py .
pnpm --dir tools/mcp-cost-server run build
pnpm --dir tools/mcp-cost-server test
cd site
npm test
```

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
