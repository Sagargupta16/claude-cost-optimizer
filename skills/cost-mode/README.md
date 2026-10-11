# cost-mode

A Claude Code skill that trims visible output, suggests cheaper models, and nudges efficient workflow patterns. It has not been benchmarked: measure it with `/usage` before and after.

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
/cost-mode strict     # Telegraphic, max brevity
/cost-mode off        # Resume normal behavior
```

## What It Does

- **Cuts filler**: No pleasantries, hedging, restating questions, or trailing summaries
- **Suggests cheaper models**: Recommends Haiku 5.5 (1/40 the Opus 5.5 rate up to 100K prompt tokens) for simple tasks, Sonnet 5.5 (half the rate) for standard work, Opus 5.5 over legacy Opus 5 (20% cheaper) and over Fable 5.1 for routine work, and lower effort on Opus 5.5 (its thinking can't be disabled, and thinking bills as output)
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
| lite | Not measured | Output cut x your output share | Team-visible work, PRs, shared sessions |
| standard | Not measured | Output cut x your output share | Daily development, solo coding |
| strict | Not measured | Output cut x your output share | High-volume sessions, budget-constrained |

Closest public measurements: on Anthropic's issue-triage agent, asking for a one-line final answer used 39% fewer output tokens than the two-line original and cost 14% less per run ($0.49 vs $0.57), while a memo-style answer cost $1.40, 2.8x the one-line, at the same accuracy within run-to-run noise ([Anthropic cost guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence)). caveman's README reports "Answer concisely." cutting output tokens 38% (6,983 to 4,334) on ten dev questions on Opus 5.5 ([its own run](https://github.com/JuliusBrussee/caveman), not verified here).

Output tokens cost 5x input tokens on every current model ([pricing](https://platform.claude.com/docs/en/about-claude/pricing)), so the saving is the output cut times the output share of your bill. In the token mix of Anthropic's own `/usage` example, priced at Opus 5.5 rates, output is 19% of the bill: a 40% output cut saves about 8%, a 60% cut about 12% (computed: the [costs page](https://code.claude.com/docs/en/costs) example of 1.2k input, 5.3k output, 940.0k cache-read and 50.0k cache-write tokens is $0.549 at Opus 5.5 rates with 5-minute writes, $0.106 of it output; 0.4 x 19.3% = 7.7%).

The 8% and 12% are arithmetic, not measurements: this repo has not run a controlled benchmark of cost-mode. Measure your own with `/usage` (or `npx ccusage`) before and after. Brevity cuts visible output only; thinking tokens also bill as output, and on Opus 5.5 lowering effort is what cuts those.

## Works Well With

Community tools that cover what a skill can't. Each claim is the project's own, not measured here.

- [ccusage](https://github.com/ccusage/ccusage) -- `npx ccusage` cost reports from local logs
- [Claude-Code-Usage-Monitor](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor) / [claudetop](https://github.com/liorwn/claudetop) -- real-time usage and cache monitors
- [rtk](https://github.com/rtk-ai/rtk) -- CLI proxy that compresses common dev-command output ("60-90%" on those commands; its README adds that this "is not the same as cutting your bill by 90%")
- [claude-mem](https://github.com/thedotmack/claude-mem) -- persistent compressed context across sessions
- [claude-code-router](https://github.com/musistudio/claude-code-router) -- routes requests across models
- [caveman](https://github.com/JuliusBrussee/caveman) -- brevity skill and proxy; its README reports output tokens on ten dev questions on Opus 5.5 falling 38% with "Answer concisely.", 41% with /caveman and 61% with /ultracave, while its rules add about 1,160 tokens and the bill effect is "not measured yet". Overlaps cost-mode's response rules, so pick one

## License

MIT
