---
description: Write a 40-line handoff to .claude/handoff.md and print it, before /clear or a long break
---

# Handoff

Write a short handoff so a fresh session (after `/clear`, or a new one) can pick this work up without the old conversation. Run it while the prompt cache is still warm: once the cache has expired, this turn re-sends the whole conversation at the cache-write rate before it writes anything.

## Instructions

1. Overwrite `.claude/handoff.md` in the project root with at most 40 lines, under these headings:
   - **Goal**: one or two lines.
   - **Done**: what is finished, with the proof (the command run and what it showed).
   - **Next**: the next concrete steps, in order.
   - **Files touched**: paths only, one per line, no contents.
   - **Open questions**: anything undecided or waiting on the user.
   - **Commands to re-run**: the exact commands that show the current state (tests, build, a server).

   Write facts, not instructions to a future assistant. No secrets, tokens or credentials, and no pasted file contents.
2. Run `git check-ignore -q .claude/handoff.md`. If the file is not ignored, say so and suggest adding `.claude/handoff.md` to `.gitignore`, so it is never committed. The optional loader hook (`hooks/handoff-loader.sh`) only reads an ignored, untracked file.
3. Print the same notes in chat inside one code block, so they can be pasted into a new session when no hook loads them.

Reply with that code block and one line naming the file. Nothing else.
