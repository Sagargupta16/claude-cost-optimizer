# cost-mode

A Claude Code skill that reduces token usage by 40-70% through concise responses, smart model routing, and efficient workflow patterns.

## Install

```bash
npx skills add Sagargupta16/claude-cost-optimizer
```

Or clone and reference locally in your Claude Code settings.

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
- **Suggests cheaper models**: Recommends Haiku for simple tasks, Sonnet for standard work
- **Suggests CLI tools**: Points to `prettier`, `eslint --fix`, `git` instead of burning LLM tokens on deterministic tasks
- **Session awareness**: Reminds you to `/compact` after 20+ turns, start fresh sessions for new tasks
- **Minimal code gen**: Diffs over rewrites, no obvious comments, no speculative error handling

## What It Keeps

- Full technical accuracy
- All code blocks unchanged
- Security warnings at full clarity
- Destructive operation confirmations
- Detailed explanations when you explicitly ask

## Savings

| Intensity | Output Token Reduction | Best For |
|-----------|:---------------------:|----------|
| lite | 20-40% | Team-visible work, PRs, shared sessions |
| standard | 40-60% | Daily development, solo coding |
| strict | 60-70% | High-volume sessions, budget-constrained |

## License

MIT
