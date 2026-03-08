# Minimal CLAUDE.md Template

<!-- ABOUT THIS TEMPLATE
  - Under 50 lines of actual content (~320 tokens)
  - Designed for maximum cost savings — every line earns its place
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
  COST: ~20 tokens. Saves 1-2 clarification turns (~2,000+ tokens). -->
{One-sentence description of what this project does.}
{Language/framework}: {e.g., TypeScript, React 18, Node 20, PostgreSQL}

## Commands

<!-- SECTION: Essential commands
  WHY: Prevents Claude from guessing or reading package.json to find scripts.
  COST: ~40 tokens. Saves a file read (~250 tokens) + potential wrong guess. -->
- Build: `{npm run build}`
- Test all: `{npm test}`
- Test single: `{npm test -- path/to/file.test.ts}`
- Lint: `{npm run lint}`
- Dev server: `{npm run dev}`

## Structure

<!-- SECTION: Key directories only — not a full tree
  WHY: Helps Claude find files without running Glob on every task.
  COST: ~30 tokens. Saves 1-3 Glob calls (~500-1,500 tokens in results). -->
- `src/components/` — React components
- `src/services/` — Business logic
- `src/types/` — Shared TypeScript types
- `tests/` — Test files mirror src/ structure

## Code Rules

<!-- SECTION: Only rules Claude would otherwise get wrong
  WHY: Prevents the most common convention violations that cause follow-up turns.
  COST: ~50 tokens. Saves 1-2 revision turns (~3,000-6,000 tokens).
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
  COST: ~20 tokens. Can save an entire wasted session. -->
- Do not modify files in `src/generated/` — these are auto-generated
- Do not install new dependencies without asking first
- Do not change the database schema without discussing migration strategy

<!-- END OF TEMPLATE — This file should be under 50 lines of content.
  Total estimated tokens: ~320
  Over a 30-turn session: ~9,600 tokens of CLAUDE.md overhead (pre-cache)
  Compare to a 300-line CLAUDE.md: ~63,000 tokens of overhead
  Savings: ~53,400 tokens per session = ~$0.16/session (Sonnet 4) -->
