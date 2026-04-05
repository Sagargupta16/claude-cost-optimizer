# Getting Started in 5 Minutes

Go from zero to optimized Claude Code setup in 5 steps. No tools to install -- just file edits.

---

## Step 1: Create a `.claudeignore` (1 minute)

Create a `.claudeignore` file in your project root. This stops Claude from reading files that waste tokens.

```
# Build outputs
dist/
build/
out/
.next/
target/

# Dependencies
node_modules/
vendor/
.venv/
__pycache__/

# Lock files
package-lock.json
pnpm-lock.yaml
yarn.lock
poetry.lock
Cargo.lock

# Generated
*.min.js
*.map
*.d.ts
coverage/
```

Adapt to your stack. The goal: exclude anything Claude doesn't need to read.

**Savings: 5-15%** from reduced file read tokens.

---

## Step 2: Create or trim your `CLAUDE.md` (2 minutes)

If you don't have a `CLAUDE.md`, create one at your project root. If you do, check its size:

```bash
wc -c CLAUDE.md
# Should be under 4,000 characters
```

Keep it focused:
- Project purpose (1-2 sentences)
- Tech stack
- How to build/test/run
- Code conventions that aren't obvious from the code
- Common commands

**What to cut**: verbose explanations, full API docs, things Claude can figure out from the code.

Hard limits:
- **4,000 characters per file** (content beyond this is silently truncated)
- **12,000 characters total** across all instruction files

Grab a template: [minimal](../templates/CLAUDE.md/minimal.md) | [standard](../templates/CLAUDE.md/standard.md) | [by stack](../templates/CLAUDE.md/by-stack/)

**Savings: 10-20%** from a lean CLAUDE.md that loads every turn.

---

## Step 3: Use the right model for the task (0 minutes)

You don't need Opus for everything. Quick rule:

| Task | Model | Why |
|------|-------|-----|
| Architecture, complex refactors | Opus 4.6 | Needs deep reasoning |
| Feature implementation, debugging | Sonnet 4.6 | Good balance |
| Tests, docs, formatting, renames | Haiku 4.5 | Fast, 5x cheaper than Opus |

Switch models mid-session:

```
/model haiku
# do simple tasks
/model opus
# back to complex work
```

**Savings: 20-40%** by matching model to task complexity.

---

## Step 4: Use Plan Mode before coding (0 minutes)

Before asking Claude to implement something complex, type:

```
/plan
```

This makes Claude think through the approach before writing code. The result:
- Fewer wasted turns from wrong approaches
- Less back-and-forth correction
- Smaller conversation history (the biggest cost driver in long sessions)

Exit plan mode with `/plan` again when you're ready to code.

**Savings: 15-25%** from reduced iterative turns.

---

## Step 5: Start fresh sessions often (0 minutes)

Every turn, Claude resends the entire conversation history. By turn 30, you're paying for 30x the accumulated context.

Best practice:
- **Start a new session** when switching tasks
- **Use subagents** for isolated searches (`/agent` or let Claude spawn them)
- **Compact** long sessions with `/compact` to summarize history

A 50-turn session costs 3-5x more per turn than a 10-turn session doing the same work.

**Savings: 20-40%** from shorter, focused sessions.

---

## Verify your setup

Run the [Repo Analyzer](https://sagargupta16.github.io/claude-cost-optimizer/analyzer) to check your score. Paste your GitHub repo URL and get:
- Cost-efficiency grade (A+ to F)
- Estimated monthly cost per model
- Specific recommendations

Or use the CLI:

```bash
python tools/badge-generator/generate.py /path/to/your/project
```

---

## What's next

| Want to... | Read |
|-----------|------|
| Understand the full billing model | [Guide 01: Understanding Costs](01-understanding-costs.md) |
| Optimize context deeply | [Guide 02: Context Optimization](02-context-optimization.md) |
| Skip the LLM for simple tasks | [Guide 10: Three-Tier Task Routing](10-task-routing.md) |
| Learn about prompt caching | [Guide 08: Prompt Caching](08-prompt-caching.md) |
| Choose the right subscription | [Guide 09: Subscription Value](09-subscription-value.md) |
| See all strategies on one page | [Cheatsheet](../cheatsheet.md) |

---

**Total time: ~5 minutes. Expected savings: 30-60%.**
