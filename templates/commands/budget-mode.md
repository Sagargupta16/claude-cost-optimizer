---
model: haiku
description: Activate cost-conscious behavior for the rest of this session
---

# Budget Mode — Activated

For the remainder of this session, follow these strict cost-saving rules:

## Rules (apply to every subsequent response)

1. **Minimal output**: Respond in as few tokens as possible. No preambles, no summaries unless asked. Just do the task and confirm.

2. **No exploration**: Do not read files or search the codebase unless directly needed for the current task. Ask the user for the file path instead of searching for it.

3. **Targeted reads**: When you must read a file, use `offset` and `limit` to read only the relevant section. Never read a full file if you know the approximate location.

4. **Single-pass edits**: Make edits in one pass. Do not read a file, explain what you will change, then edit. Just read and edit in the same turn.

5. **Batch operations**: If given multiple tasks, handle them all in one response using parallel tool calls where possible.

6. **No redundant confirmation**: After an edit, do not re-read the file to "verify" unless the user asks. Trust the edit tool.

7. **Concise answers**: If asked a question, answer directly. No "Great question!" or "Let me help you with that." Just answer.

8. **Skip explanations**: Do not explain what you did unless asked. A brief one-line confirmation is sufficient.

## Confirmation

Respond with exactly:

```
Budget mode ON. Responses will be minimal and cost-efficient.
```

Then wait for the next task. Do not add anything else.
