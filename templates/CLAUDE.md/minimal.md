# Minimal CLAUDE.md Template

<!-- ABOUT THIS TEMPLATE
  - 25 lines of actual content, 1,009 characters as written: about 400 tokens on the
    current tokenizer (2.5 characters per token, Anthropic's models overview), about 250
    on pre-4.7 models (4 per token)
  - Designed for maximum cost savings -- every line earns its place
  - Best for: solo developers, small projects, budget-conscious usage
  - Trade-off: Claude may need more follow-up turns for project-specific conventions
  - Copy everything below the "---" line into your project's CLAUDE.md
  - Replace all {PLACEHOLDER} values with your project specifics
  - Delete these comment blocks before use (they add unnecessary tokens)
-->

---

<!-- COPY BELOW THIS LINE INTO YOUR PROJECT'S CLAUDE.md -->

# {Project Name}

<!-- SECTION: Project overview (2-3 lines max)
  WHY: Tells Claude what it's working on so it doesn't waste turns asking.
  COST: 140 characters, about 56 tokens. Saves the clarification turns it answers in
  advance; no published figure says how many. Each avoided turn saves a cache read of the
  whole context plus that turn's output. -->
{One-sentence description of what this project does.}
{Language/framework}: {e.g., TypeScript, React 18, Node 20, PostgreSQL}

## Commands

<!-- SECTION: Essential commands
  WHY: Prevents Claude from guessing or reading package.json to find scripts.
  COST: 165 characters, about 66 tokens. Saves reading package.json (or a wrong guess)
  to find scripts; that read stays in context for the rest of the session. -->
- Build: `{npm run build}`
- Test all: `{npm test}`
- Test single: `{npm test -- path/to/file.test.ts}`
- Lint: `{npm run lint}`
- Dev server: `{npm run dev}`

## Structure

<!-- SECTION: Key directories only -- not a full tree
  WHY: Helps Claude find files without running Glob on every task.
  COST: 173 characters, about 69 tokens. Saves the Glob or ls calls it answers in
  advance; no published figure says how many. -->
- `src/components/` -- React components
- `src/services/` -- Business logic
- `src/types/` -- Shared TypeScript types
- `tests/` -- Test files mirror src/ structure

## Code Rules

<!-- SECTION: Only rules Claude would otherwise get wrong
  WHY: Prevents the most common convention violations that cause follow-up turns.
  COST: 326 characters, about 130 tokens. Saves the revision turns these rules prevent;
  no published figure says how many.
  TIP: Add rules here ONLY after Claude gets something wrong twice. -->
- Use named exports, not default exports
- Prefer `interface` over `type` for object shapes
- Error handling: throw typed errors from `src/types/errors.ts`
- Tests: use `describe`/`it` blocks, AAA pattern (Arrange/Act/Assert)
- {Add your most-violated convention here}
- {Add your second most-violated convention here}

## Do Not

<!-- SECTION: Hard guardrails
  WHY: Prevents costly mistakes that require multi-turn rollbacks.
  COST: 205 characters, about 82 tokens. Can save a multi-turn rollback; no published
  figure says how often. -->
- Do not modify files in `src/generated/` -- these are auto-generated
- Do not install new dependencies without asking first
- Do not change the database schema without discussing migration strategy

<!-- END OF TEMPLATE -- This file should be under 50 lines of content.
  Total: 25 content lines, 1,009 characters as written: about 400 tokens (2.5 characters
  per token on the current tokenizer; about 250 on pre-4.7 models at 4)
  Over a 30-turn session: about 12,100 tokens of CLAUDE.md sent (pre-cache, 400 x 30)
  Compare to a 300-line CLAUDE.md at the same density (40 characters a line): about
  4,840 tokens, 145,300 sent over 30 turns
  Difference: about 4,440 tokens per request, 133,200 per session = $0.27/session if nothing
  were cached (Sonnet 5.5, $2/1M input)
  With Claude Code's prompt caching (warm cache) that is about $0.02: the 4,440 extra tokens
  are written once at $2.50/1M (1.25x) and read 29 times at $0.10/1M (0.05x) -->
