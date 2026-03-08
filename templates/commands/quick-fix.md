---
model: sonnet
description: Minimal-token bug fix — direct fix with no exploration
---

# Quick Fix

Apply a targeted bug fix with minimal token usage. No exploration, no discussion — just fix.

## Process

1. **Identify**: The user has described a bug or pointed to a specific file/line. If the file path is provided, read only the relevant section (use `offset`/`limit` if possible).

2. **Fix**: Apply the edit immediately. Do not:
   - Explain the root cause in detail
   - Show "before and after" comparisons
   - Suggest related improvements
   - Refactor surrounding code
   - Read other files "for context"

3. **Verify** (only if a test command is known): Run the relevant test in one command. If no test file is obvious, skip this step.

4. **Report**: Respond with a single line describing the fix:

```
Fixed: {what was wrong} in {file path}
```

## Rules

- ONE file edit per bug. If the fix truly requires multiple files, do them all in parallel in one turn.
- Do NOT read the entire file — read only the area around the reported issue.
- Do NOT suggest follow-up improvements or "while we're here" changes.
- Do NOT explain the fix unless the user asks "why."
- If the bug description is ambiguous, ask ONE clarifying question — do not guess.

## Example

User: "The login button doesn't submit the form — it's in src/components/LoginForm.tsx around line 45"

Good response:
```
[Reads lines 40-55 of LoginForm.tsx]
[Edits: changed type="button" to type="submit" on line 47]
Fixed: button type was "button" instead of "submit" in src/components/LoginForm.tsx
```

Bad response:
```
Let me take a look at the LoginForm component to understand the issue...
[Reads entire file]
I can see the problem! The button on line 47 has type="button" which prevents
form submission. This is a common issue in React forms because...
[Long explanation]
[Edit]
I've fixed the issue. The button was using type="button" instead of type="submit".
You might also want to consider adding form validation...
```
