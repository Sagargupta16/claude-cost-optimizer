# cost-mode

A Claude Code skill that saves 30-60% on costs through concise responses (40-70% output token reduction), smart model routing, and efficient workflow patterns.

## Install

**Claude Code (official plugin):**

```bash
/plugin marketplace add Sagargupta16/claude-cost-optimizer
/plugin install cost-mode@sagargupta16-claude-cost-optimizer
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

| Intensity | Output Token Reduction | Estimated Cost Savings | Best For |
|-----------|:---------------------:|:---------------------:|----------|
| lite | 20-40% | ~10-20% | Team-visible work, PRs, shared sessions |
| standard | 40-60% | ~20-35% | Daily development, solo coding |
| strict | 60-70% | ~30-45% | High-volume sessions, budget-constrained |

Output tokens cost 5x more than input tokens, so even moderate output reduction has significant cost impact. Combined with model routing and CLI suggestions, total savings reach 30-60%.

## License

MIT
