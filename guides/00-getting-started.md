# Getting Started in 5 Minutes

Go from zero to optimized Claude Code setup in 5 steps. No tools to install -- just file edits.

---

## Step 1: Deny reads of junk paths (1 minute)

Add `permissions.deny` rules to `.claude/settings.json` in your project root. `Read(...)` rules keep Claude's file tools out of files that waste tokens, and also apply to the file commands Claude Code recognizes in Bash (`cat`, `head`, `tail`, `sed`, `tee`).

```json
{
  "permissions": {
    "deny": [
      "Read(./node_modules/**)",
      "Read(./dist/**)",
      "Read(./build/**)",
      "Read(./coverage/**)",
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(*.min.js)",
      "Read(./package-lock.json)"
    ]
  }
}
```

Adapt to your stack. Patterns use gitignore syntax: `./path` is relative to the project, `*` matches within one path segment, `**` across directories, and a bare filename such as `Read(.env)` matches at any depth.

> `.claudeignore` is not a Claude Code feature: it appears nowhere in Claude Code's documentation and Claude Code does not read it. If you made one, convert each line: `dir/` becomes `Read(./dir/**)`, a line with a `/` elsewhere becomes `Read(./line)` (strip a leading `/`), and a bare name or glob becomes `Read(line)`. Skip blank lines, `#` comments and `!` negations.

**Savings: no published measurement.** The effect depends on how often Claude would otherwise open those files. Scoped rules like `Read(./dist/**)` do not change which tools Claude sees, so they do not invalidate the prompt cache.

---

## Step 2: Create or trim your `CLAUDE.md` (2 minutes)

If you don't have a `CLAUDE.md`, create one at your project root. If you do, check its size:

```bash
wc -l CLAUDE.md
# Anthropic's guidance: under 200 lines
```

Keep it focused:
- Project purpose (1-2 sentences)
- Tech stack
- How to build/test/run
- Code conventions that aren't obvious from the code
- Common commands

**What to cut**: verbose explanations, full API docs, things Claude can figure out from the code.

There is no character cap: CLAUDE.md files in the directories above your working directory load in full at launch. Anthropic's guidance is to "target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence." Every line costs tokens in every session, so move situational content somewhere that loads on demand:
- **Skills** for workflow-specific instructions (PR reviews, DB migrations)
- **Path-scoped rules** in `.claude/rules/` (with `paths:` frontmatter) or a **subdirectory CLAUDE.md** for rules that apply to one part of the tree; both load when Claude reads a matching file

`@path` imports help you organize a long file, but imported files still load at launch, so they do not cut tokens.

Grab a template: [minimal](../templates/CLAUDE.md/minimal.md) | [standard](../templates/CLAUDE.md/standard.md) | [by stack](../templates/CLAUDE.md/by-stack/)

**Savings: 10-20%** from a lean CLAUDE.md that loads every turn.

---

## Step 3: Use the right model for the task (0 minutes)

You don't need Opus for everything. Quick rule:

| Task | Model | Why |
|------|-------|-----|
| Architecture, complex refactors | Opus 5.5 | Anthropic's recommended start for most workloads |
| Feature implementation, debugging | Sonnet 5.5 | Good balance, 2x cheaper than Opus 5.5 |
| Tests, docs, formatting, renames | Haiku 5.5 | Fastest, 40x cheaper per token than Opus 5.5 while the prompt stays under 100K tokens |

Haiku 5.5 is priced by prompt length: $0.10/$0.50 per 1M up to 100K prompt tokens, $0.50/$2.50 above (cache reads and writes count toward the 100K), so keep its prompts short. `/model haiku` selects Haiku 5.5 on the Anthropic API (Claude Code v2.1.293+); on Bedrock, Google Cloud, Microsoft Foundry and Claude Platform on AWS it still means legacy Haiku 4.5 ($1/$5).

Switch models mid-session:

```
/model haiku
# do simple tasks
/model opus
# back to complex work
```

**Opus 5.5 caveat** (released 2026-09-22, $4/$20, 20% below Opus 5's $5/$25): adaptive thinking is **always on** -- `thinking: {type: "disabled"}` returns a 400, so effort is the only control. Default effort is `medium` (Opus 5 defaulted to `high`), and reasoning tokens bill as output at $20/1M. Code that disabled thinking on Opus 5 now pays for thinking it did not pay for before, so re-baseline cost after migrating and lower it with `/effort`. `max_tokens` caps thinking plus text together, so a small cap can be spent on thinking before the answer is written. Details in [Guide 01](01-understanding-costs.md#token-pricing).

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

Exit plan mode with `/plan` again when you're ready to code. You can also press Shift+Tab to cycle into plan mode.

**Savings: 15-25%** from reduced iterative turns.

---

## Step 5: Start fresh sessions often (0 minutes)

Every turn, Claude resends the entire conversation history. By turn 30, you're paying for 30x the accumulated context.

Best practice:
- **Start a new session** when switching tasks
- **Use subagents** for isolated searches (`/agent` or let Claude spawn them)
- **Compact** long sessions with `/compact` to summarize history. While the prompt cache is warm the summary request reads from cache, so it costs a fraction of the context size; after a break longer than the cache TTL it reprocesses the full history uncached
- **Clear** with `/clear` when the old context is no longer needed -- it costs nothing

A 50-turn session costs 3-5x more per turn than a 10-turn session doing the same work.

**Savings: 20-40%** from shorter, focused sessions.

---

## Verify your setup

Run [claude-rate](../tools/claude-rate/) to check your score locally and get:
- Cost-efficiency grade (A+ to F)
- Estimated monthly cost per model
- Specific recommendations

```bash
curl -sSL https://raw.githubusercontent.com/Sagargupta16/claude-cost-optimizer/main/tools/claude-rate/install.sh | sh -s -- .
```

Or use the legacy CLI:

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
