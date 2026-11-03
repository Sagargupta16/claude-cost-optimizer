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
- **Workflow levers**: Hooks that filter noisy test output to failures, compact command flags (`git diff --stat`), a search-before-read ladder by intent (locate, understand, modify, debug; unmeasured habits), `model: haiku` subagents for simple delegated work, `permissions.deny` `Read(...)` rules for build output and lock files
- **Effort per task**: the routing table names a thinking-effort level for each task type, mapped from Anthropic's per-level table (`low` for a rename, `medium` for a scoped feature, `high` for a bug fix, `max` for a security audit)
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

Closest public measurements: on Anthropic's issue-triage agent, asking for a one-line final answer used 39% fewer output tokens than the two-line original and cost 13% less per run (from the unrounded means; the chart's rounded $0.49 vs $0.57 give 14%; read 2026-11-01), while a memo-style answer cost $1.40, 2.8x the one-line, at the same accuracy within run-to-run noise ([Anthropic cost guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence)). caveman's README reports "Answer concisely." cutting output tokens 38% (6,983 to 4,334) on ten dev questions on Opus 5.5 ([its own run](https://github.com/JuliusBrussee/caveman), not verified here).

Output tokens cost 5x input tokens on every current model ([pricing](https://platform.claude.com/docs/en/about-claude/pricing)), so the saving is the output cut times the output share of your bill. In the token mix of Anthropic's own `/usage` example, priced at Opus 5.5 rates, output is 19% of the bill: a 40% output cut saves about 8%, a 60% cut about 12% (computed: the [costs page](https://code.claude.com/docs/en/costs) example of 1.2k input, 5.3k output, 940.0k cache-read and 50.0k cache-write tokens is $0.549 at Opus 5.5 rates with 5-minute writes, $0.106 of it output; 0.4 x 19.3% = 7.7%).

The 8% and 12% are arithmetic, not measurements: this repo has not run a controlled benchmark of cost-mode. Measure your own with `/usage` (or `npx ccusage`) before and after. Brevity cuts visible output only; thinking tokens also bill as output, and on Opus 5.5 lowering effort is what cuts those.

## When cost-mode saves nothing

The output-share arithmetic above is a ceiling. The real saving can be smaller, or below zero:

- **Your output share is small.** `claude-rate --usage` (claude-rate 0.4.0 or later) prints the output share of your list-price spend from your own transcripts. Brevity saves at most that share times the output cut.
- **Terse rules can raise reasoning, which bills as output.** In Chisle's own run (a competing brevity skill; Haiku 4.5, single-turn, tools off, 26 cells per arm), reasoning tokens rose to 164% of the bare model with caveman's rules, 483% with ponytail's and 218% with Chisle's. Its billed-output intervals for caveman and Chisle reach 100%, so the run shows the reasoning rise, not a significant cost rise ([its 2026-10-12 rerun](https://github.com/JayPokale/Chisle/blob/HEAD/benchmarks/results/2026-10-12-tools-off-rerun.md), read 2026-11-03).
- **A large output cut can leave the total flat.** caveman's [honest-numbers page](https://github.com/JuliusBrussee/caveman/blob/HEAD/docs/HONEST-NUMBERS.md) reports LemonCrow's A/B: 300 runs per arm on Opus 4.8, with the July 2026 caveman SKILL.md (before its 3.x rewrite) as the only extra instruction, gave 44.1% less billed output, 0.06% higher total cost and 1,532 more cached-context tokens per run (read 2026-11-03). caveman calls such runs evidence about the approach, not about its current file. Both this run and Chisle's used legacy models, not a 5.5 model.
- **You pay per request, not per token.** On agents billed by request or credit, such as GitHub Copilot's premium requests, a shorter answer is the same request (caveman's honest-numbers page, issue #506, read 2026-11-03).
- **Code and JSON barely shrink.** cost-mode keeps code blocks, error messages and exact values unchanged by rule, so a reply that is mostly code or JSON leaves little prose to drop. No measured figure.
- **The skill is input too.** Once invoked, this SKILL.md (11,259 characters as committed, with LF line endings, measured 2026-11-03; about 4,504 tokens at 2.5 characters per token) stays in the conversation. On Opus 5.5 it is one 5-minute cache write, then a cache read each later turn: 4,504 x $5/M = $0.0225 once, 4,504 x $0.20/M = $0.0009 a turn, $0.049 over a 30-turn session (computed: $0.02252 + 29 x $0.0009008 = $0.04864; the 1-hour write a subscription's main conversation uses is $8/M, $0.036). Against the 500 output tokens a turn of the [README's worked example](../../README.md#before-vs-after), $0.30 of output a session (30 x 500 x $20/M), brevity pays for its own load only above a 16% output cut (computed: $0.04864 / $0.30 = 16.2%). Its frontmatter description is in context every turn whether or not you invoke it.

## Works Well With

Community tools that cover what a skill can't. Each claim is the project's own, not measured here.

- [ccusage](https://github.com/ccusage/ccusage) -- `npx ccusage` cost reports from local logs
- Real-time monitoring: this repo's [claude-rate](../../tools/claude-rate/) 0.4.0 or later has `--statusline` (cache time left, what a cold re-cache would add at list price, context fill and 5-hour/7-day pace in Claude Code's status line) and `--burn` (a live spend view in a terminal). Community alternatives: [ccstatusline](https://github.com/sirmalloc/ccstatusline), [Claude-Code-Usage-Monitor](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor) (no push since 2026-07-05) and [claudetop](https://github.com/liorwn/claudetop)
- [rtk](https://github.com/rtk-ai/rtk) -- CLI proxy that compresses common dev-command output ("60-90%" on those commands in its GitHub description, "up to 90% smaller" in its README, which adds that this "is not the same as cutting your bill by the same amount"; read 2026-11-01)
- [claude-mem](https://github.com/thedotmack/claude-mem) -- persistent compressed context across sessions, now for Claude Code and several other agents
- [claude-code-router](https://github.com/musistudio/claude-code-router) -- local control plane that routes Claude Code and other agent CLIs across models
- [caveman](https://github.com/JuliusBrussee/caveman) -- caveman 4.0: a brevity voice skill plus input compression, per-ask model and effort routing and reusable scripts. Its [honest-numbers page](https://github.com/JuliusBrussee/caveman/blob/HEAD/docs/HONEST-NUMBERS.md) measures against a plain "Answer concisely." control, which its README calls the real baseline: /caveman cuts output 3%, /ultracave 35% and /megacave 9% at the median (ten dev questions on Opus 5.5, one run, output tokens only, a tiktoken approximation, on its 3.1.0 rules, not re-run since), and it lists the cut against default verbose replies as "Not published" (read 2026-11-03). Its README adds that the rules cost about 1,160 tokens of input. Its CLI sends usage telemetry by default (`caveman telemetry off` or `DO_NOT_TRACK=1` turns it off; read 2026-11-01). Overlaps cost-mode's response rules, so pick one

## License

MIT
