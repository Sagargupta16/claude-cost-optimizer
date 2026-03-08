---
model: haiku
description: Check and report current session cost and usage patterns
---

# Cost Check

Analyze the current session and report on cost efficiency. Be concise — this command should itself be cheap.

## Instructions

1. **Session summary**: Count how many turns have occurred so far in this conversation. Note the approximate scope of work done.

2. **Token usage estimate**: Based on the conversation length and complexity, estimate:
   - Approximate input tokens consumed (including CLAUDE.md overhead per turn)
   - Approximate output tokens generated
   - Which model has been used (Haiku/Sonnet/Opus)

3. **Cost patterns identified**: Flag any of these wasteful patterns if they occurred:
   - Full file reads when partial reads would suffice
   - Multiple search passes for the same information
   - Verbose explanations where concise answers were appropriate
   - Unnecessary exploration before making targeted edits
   - Reading files that were not ultimately used

4. **Recommendations**: Suggest 1-3 specific actions to reduce cost for the remainder of this session. Examples:
   - "Switch to Haiku for the remaining simple edits"
   - "Use Grep with specific patterns instead of reading full files"
   - "Batch remaining edits into fewer turns"

## Output Format

```
SESSION COST REPORT
-------------------
Turns so far:     {n}
Model used:       {model}
Est. input tokens: ~{n}k
Est. output tokens: ~{n}k
Est. session cost: ~${n.nn}

PATTERNS FOUND:
- {pattern 1}
- {pattern 2}

RECOMMENDATIONS:
1. {recommendation}
2. {recommendation}
```

Keep the report under 20 lines. Do not elaborate beyond what is shown above.
