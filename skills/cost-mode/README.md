# cost-mode

A Claude Code skill that saves 30-60% on costs through concise responses (40-70% output token reduction), smart model routing, and efficient workflow patterns.

## Install

**Claude Code (official plugin):**

```bash
/plugin marketplace add Sagargupta16/claude-cost-optimizer
/plugin install cost-mode@claude-cost-optimizer
```

**Multi-agent (Cursor, Cline, Codex, etc.):**

```bash
npx skills add Sagargupta16/claude-cost-optimizer
```

## Usage

Once installed, activate with:

```
/cost-mode            # Toggle on (standard intensity)
/cost-mode lite       # Professional brevity, full sentences
/cost-mode standard   # Concise fragments, skip filler (default)
/cost-mode strict     # Telegraphic, max savings
/cost-mode off        # Resume normal behavior
```

## What It Does

- **Cuts filler**: No pleasantries, hedging, restating questions, or trailing summaries
- **Suggests cheaper models**: Recommends Haiku 4.5 (1/4 the Opus 5.5 rate) for simple tasks, Sonnet 5 (half the rate) for standard work, Opus 5.5 over legacy Opus 5 (20% cheaper) and over Fable 5.1 for routine work, and lower effort on Opus 5.5 (its thinking can't be disabled, and thinking bills as output)
- **Suggests CLI tools**: Points to `prettier`, `eslint --fix`, `git` instead of burning LLM tokens on deterministic tasks, and to `gh`/`aws` over the matching MCP server
- **Session awareness**: `/clear` between unrelated tasks, `/compact` at natural breaks while the prompt cache is warm, `/rewind` off a wrong path, and no mid-task model switches (each rebuilds the cache)
- **Workflow levers**: Hooks that filter noisy test output to failures, `model: haiku` subagents for simple delegated work, `permissions.deny` `Read(...)` rules for build output and lock files
- **Minimal code gen**: Diffs over rewrites, no obvious comments, no speculative error handling

## What It Keeps

- Full technical accuracy
- All code blocks unchanged
- Security warnings at full clarity
- Destructive operation confirmations
- Detailed explanations when you explicitly ask

## Savings

| Intensity | Output Token Reduction | Estimated Cost Savings | Best For |
|-----------|:---------------------:|:---------------------:|----------|
| lite | 20-40% | ~10-20% | Team-visible work, PRs, shared sessions |
| standard | 40-60% | ~20-35% | Daily development, solo coding |
| strict | 60-70% | ~30-45% | High-volume sessions, budget-constrained |

Output tokens cost 5x more than input tokens, so even moderate output reduction has significant cost impact. Combined with model routing and CLI suggestions, total savings are estimated at 30-60%.

These figures are estimates: this repo has not run a controlled benchmark of cost-mode. Measure your own with `/usage` (or `npx ccusage`) before and after. Brevity cuts visible output only; thinking tokens also bill as output, and on Opus 5.5 lowering effort is what cuts those.

## Works Well With

Community tools that cover what a skill can't. Each claim is the project's own, not measured here.

- [ccusage](https://github.com/ccusage/ccusage) -- `npx ccusage` cost reports from local logs
- [Claude-Code-Usage-Monitor](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor) / [claudetop](https://github.com/liorwn/claudetop) -- real-time usage and cache monitors
- [rtk](https://github.com/rtk-ai/rtk) -- CLI proxy that compresses common dev-command output ("60-90%" on those commands)
- [claude-mem](https://github.com/thedotmack/claude-mem) -- persistent compressed context across sessions
- [claude-code-router](https://github.com/musistudio/claude-code-router) -- routes requests across models
- [caveman](https://github.com/JuliusBrussee/caveman) -- brevity skill and proxy ("cuts 65% of tokens"); overlaps cost-mode's response rules, so pick one

## License

MIT
