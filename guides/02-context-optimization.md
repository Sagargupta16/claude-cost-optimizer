# Guide 02: Context Optimization

> Every token in your input is a token you pay for. This guide covers practical strategies to reduce input tokens without sacrificing Claude's ability to help you. Applied together, these techniques can reduce input costs by 30-50%.

---

## Table of Contents

- [Why Input Tokens Matter](#why-input-tokens-matter)
- [CLAUDE.md: The Line Budget](#claudemd-the-line-budget)
- [Before and After: CLAUDE.md Optimization](#before-and-after-claudemd-optimization)
- [.claudeignore: Stop Indexing Junk](#claudeignore-stop-indexing-junk)
- [File Read Strategies](#file-read-strategies)
- [Using /compact to Reset Context](#using-compact-to-reset-context)
- [Subagents: Isolating Context-Heavy Work](#subagents-isolating-context-heavy-work)
- [Writing Concise Prompts](#writing-concise-prompts)
- [Memory Files vs Inline Instructions](#memory-files-vs-inline-instructions)
- [Putting It All Together](#putting-it-all-together)

---

## Why Input Tokens Matter

Input tokens are the tokens sent *to* Claude on each turn. They include everything: the system prompt, your CLAUDE.md, the full conversation history, tool results, and your current message.

The critical insight is that **input tokens are cumulative and recurring**. Unlike output tokens (which are generated once), input tokens include all previous conversation history — so they grow with every turn and you pay for them repeatedly.

```
Turn  1 input:   4,500 tokens   (system + CLAUDE.md + your message)
Turn 10 input:  35,000 tokens   (all of the above + 9 turns of history)
Turn 30 input: 100,000 tokens   (all of the above + 29 turns of history)
```

Every token you can keep out of the input — by trimming CLAUDE.md, ignoring irrelevant files, avoiding unnecessary file reads, and compacting history — saves you money on *every subsequent turn*.

The math is straightforward: remove 1,000 tokens of recurring input, and over a 30-turn session you save 30,000 input tokens. At Sonnet pricing with 80% cache rate, that is about $0.03 per session. Do that across 5 sessions a day for a month, and it adds up to $3.30 from just that one cut. Now multiply by the 10-20 cuts this guide will show you.

---

## CLAUDE.md: The Line Budget

### Why Every Line Costs You Money

Your project's `CLAUDE.md` file is loaded in its entirety as part of the input on **every single turn**. It does not matter whether the current turn is about database schemas or CSS styling — the whole file is always there.

This makes CLAUDE.md the highest-leverage optimization target because:

1. It affects **every turn** in **every session**
2. It is under your direct control
3. Most CLAUDE.md files contain 2-3x more content than Claude actually needs

### The 150-Line Budget

We recommend keeping CLAUDE.md under **150 lines**. Here is why:

| CLAUDE.md Size | Tokens Per Turn | Cost Per Turn (Sonnet) | 30-Turn Session Cost | Monthly (110 sessions) |
|:--------------:|:---------------:|:---------------------:|:--------------------:|:---------------------:|
| 50 lines | ~350 | $0.001 | $0.03 | $3.30 |
| 100 lines | ~700 | $0.002 | $0.06 | $6.60 |
| **150 lines** | **~1,050** | **$0.003** | **$0.09** | **$9.90** |
| 300 lines | ~2,100 | $0.006 | $0.18 | $19.80 |
| 500 lines | ~3,500 | $0.011 | $0.33 | $36.30 |

> The cost column assumes a blended rate with 80% cache hits. Actual savings from trimming are about 20% of the raw difference (since most of these tokens get cached), but the cache is not free — cached tokens still cost 10% of full price.

**On Opus 4**, multiply these numbers by 5x. A 500-line CLAUDE.md on Opus costs about $181.50/month just for the CLAUDE.md itself across 110 sessions.

### What Belongs in CLAUDE.md

Include only information Claude needs on **most turns**:

| Include | Why |
|---------|-----|
| Tech stack (language, framework, versions) | Affects every code suggestion |
| Build/test/lint commands | Claude runs these frequently |
| Project structure overview (5-10 lines max) | Helps Claude find files |
| Critical coding conventions | Prevents repeated corrections |
| Error handling patterns | Applies to most code written |

### What Does NOT Belong in CLAUDE.md

| Exclude | Why | Where to Put It Instead |
|---------|-----|------------------------|
| Detailed API documentation | Only relevant for API tasks | Separate docs file, reference as needed |
| Full directory tree | Stale quickly, Claude can use `ls`/`Glob` | Let Claude explore dynamically |
| Lengthy code examples | Takes many tokens for situational use | Nearby files in the codebase |
| Team member names/roles | Irrelevant to coding | Project wiki |
| Changelog/history | Never needed for code generation | CHANGELOG.md |
| Deployment procedures | Only relevant during deploy | docs/deployment.md |
| Commented-out alternatives | Adds tokens for no active benefit | Delete them |
| Aspirational rules not yet enforced | Confuses Claude | Add when enforced |

### The "Every Line" Audit

Go through your CLAUDE.md and ask for each line: **"Does Claude need this on EVERY turn?"**

- If yes, keep it.
- If "only sometimes," move it to a separate file or a custom command.
- If "rarely," delete it.

---

## Before and After: CLAUDE.md Optimization

### Before: 380 Lines (Bloated)

```markdown
# MyApp Project

## Overview
MyApp is an e-commerce platform built with React and Node.js. It was started in 2023
by the engineering team at Acme Corp. The platform serves over 10,000 customers
and processes approximately $2M in transactions monthly. We migrated from a legacy
PHP application in Q3 2023 and have been iterating on the platform since then.

## Team
- Alice (Tech Lead) — alice@acme.com
- Bob (Frontend) — bob@acme.com
- Carol (Backend) — carol@acme.com
- Dave (DevOps) — dave@acme.com

## Tech Stack
- Frontend: React 18.2.0 with TypeScript 5.3
- State Management: Redux Toolkit 2.0
- Styling: Tailwind CSS 3.4 with custom design system
- Build Tool: Vite 5.0
- Backend: Node.js 20 LTS with Express 4.18
- Database: PostgreSQL 16 with Prisma ORM 5.7
- Cache: Redis 7.2
- Message Queue: RabbitMQ 3.12
- Search: Elasticsearch 8.11
- Authentication: Passport.js with JWT
- API Documentation: Swagger/OpenAPI 3.0
- Monitoring: Datadog APM + custom dashboards
- CI/CD: GitHub Actions
- Hosting: AWS (ECS Fargate + RDS + ElastiCache)
- CDN: CloudFront

## Directory Structure
```
src/
├── client/
│   ├── components/
│   │   ├── atoms/
│   │   │   ├── Button/
│   │   │   ├── Input/
│   │   │   ├── Text/
│   │   │   ├── Icon/
│   │   │   └── Badge/
│   │   ├── molecules/
│   │   │   ├── SearchBar/
│   │   │   ├── ProductCard/
│   │   │   ├── CartItem/
│   │   │   └── NavLink/
│   │   ├── organisms/
│   │   │   ├── Header/
│   │   │   ├── Footer/
│   │   │   ├── ProductGrid/
│   │   │   ├── ShoppingCart/
│   │   │   └── CheckoutForm/
│   │   └── pages/
│   │       ├── Home/
│   │       ├── ProductDetail/
│   │       ├── Cart/
│   │       ├── Checkout/
│   │       ├── Account/
│   │       └── Admin/
│   ├── hooks/
│   ├── store/
│   │   ├── slices/
│   │   └── middleware/
│   ├── services/
│   ├── utils/
│   └── types/
├── server/
│   ├── routes/
│   ├── controllers/
│   ├── models/
│   ├── middleware/
│   ├── services/
│   └── utils/
└── shared/
    ├── types/
    └── constants/
```

## Coding Conventions

### General Rules
- Use TypeScript strict mode everywhere
- No `any` types allowed — use `unknown` if type is truly unknown
- Prefer `const` over `let`, never use `var`
- Use early returns to reduce nesting
- Maximum function length: 50 lines
- Maximum file length: 300 lines
- Use descriptive variable names (no single-letter variables except in loops)
- All functions must have JSDoc comments
- All exported functions must have unit tests
- Use absolute imports with path aliases (@client/, @server/, @shared/)
- Handle all errors explicitly — no empty catch blocks
- Log errors with structured logging (winston)
- Use enums for fixed sets of values
- Prefer composition over inheritance
- Use dependency injection where possible

### React Conventions
- Functional components only (no class components)
- Use custom hooks for shared logic
- Props interfaces must be exported and named ComponentNameProps
- Use React.memo for expensive renders
- Lazy load routes with React.lazy
- Use Suspense with fallback components
- Event handlers should be prefixed with "handle" (handleClick, handleSubmit)
- Use controlled forms with react-hook-form
- Use zod for form validation
- Separate business logic from UI components
- Use error boundaries for each route

### Backend Conventions
- All routes must have input validation using zod
- Use middleware for auth, logging, error handling
- Controller functions should be thin — delegate to services
- Services contain business logic
- Models define database schema and relationships
- Use transactions for multi-table operations
- Return consistent error responses: { error: string, code: number }
- Rate limit all public endpoints
- Use pagination for list endpoints (limit/offset)

### Database Conventions
- Use Prisma migrations for all schema changes
- Name tables in snake_case plural (user_accounts, order_items)
- Name columns in snake_case (created_at, updated_by)
- Always include created_at and updated_at timestamps
- Use UUIDs for primary keys
- Add indexes for frequently queried columns
- Use soft deletes (deleted_at) instead of hard deletes

### Testing
- Unit tests: Vitest + React Testing Library
- E2E tests: Playwright
- Minimum 80% code coverage
- Test file naming: *.test.ts or *.test.tsx
- Use factories for test data (src/test/factories/)
- Mock external services in tests
- Integration tests for API routes
- Run tests: npm test (unit), npm run test:e2e (e2e)
- Run specific test: npm test -- --grep "test name"

### Git Conventions
- Branch naming: feature/TICKET-123-description, fix/TICKET-456-description
- Commit messages: type(scope): description (conventional commits)
- Squash merge to main
- Require PR reviews from at least one team member
- Run CI checks before merge

## Build Commands
- npm run dev — Start development server (Vite + Express)
- npm run build — Production build
- npm test — Run unit tests
- npm run test:e2e — Run Playwright e2e tests
- npm run lint — ESLint + Prettier check
- npm run lint:fix — Auto-fix linting issues
- npm run type-check — TypeScript type checking
- npm run db:migrate — Run Prisma migrations
- npm run db:seed — Seed database with test data
- npm run db:studio — Open Prisma Studio
- npm run storybook — Open Storybook
- npm run analyze — Bundle size analysis

## API Endpoints (Current)
- POST /api/auth/login — User login
- POST /api/auth/register — User registration
- GET /api/products — List products (paginated)
- GET /api/products/:id — Product detail
- POST /api/cart — Add to cart
- GET /api/cart — Get cart
- PUT /api/cart/:itemId — Update cart item
- DELETE /api/cart/:itemId — Remove from cart
- POST /api/orders — Create order
- GET /api/orders — List user orders
- GET /api/orders/:id — Order detail
- GET /api/admin/dashboard — Admin dashboard stats
- ... (20 more endpoints)

## Recent Changes
- 2024-01-15: Migrated from Redux to Redux Toolkit
- 2024-01-10: Added Elasticsearch for product search
- 2024-01-05: Upgraded to Node 20 LTS
- 2023-12-20: Added Playwright E2E tests
- 2023-12-15: Implemented real-time notifications with WebSockets

## Known Issues
- Cart total calculation sometimes rounds incorrectly (TICKET-789)
- Search indexing can lag by up to 30 seconds (TICKET-823)
- Admin dashboard slow with >10k orders (TICKET-856)

## Deployment
### Staging
1. Push to staging branch
2. GitHub Actions runs tests
3. Builds Docker image
4. Deploys to ECS Fargate staging cluster
5. Runs smoke tests

### Production
1. Create PR from staging to main
2. Require 2 approvals
3. Merge triggers production pipeline
4. Blue-green deployment via ECS
5. Automatic rollback on health check failure
6. Post-deploy: verify monitoring dashboards
```

**Token count: ~2,660 tokens per turn. Over 30 turns with 80% caching: ~$0.048 (Sonnet) / ~$0.240 (Opus)**

### After: 62 Lines (Optimized)

```markdown
# MyApp — E-commerce Platform

Tech: TypeScript strict, React 18, Redux Toolkit, Tailwind, Vite 5
Backend: Node 20, Express, PostgreSQL 16 + Prisma, Redis, RabbitMQ
Auth: Passport.js + JWT | Search: Elasticsearch | Hosting: AWS ECS

## Commands
- `npm run dev` — Dev server (Vite + Express)
- `npm run build` — Production build
- `npm test` — Unit tests (Vitest + RTL)
- `npm run test:e2e` — E2E tests (Playwright)
- `npm run lint:fix` — ESLint + Prettier autofix
- `npm run type-check` — TypeScript checks
- `npm run db:migrate` — Prisma migrations

## Structure
- `src/client/` — React frontend (components/, hooks/, store/, services/)
- `src/server/` — Express backend (routes/, controllers/, models/, services/)
- `src/shared/` — Shared types and constants

## Code Rules
- No `any` — use `unknown` if needed
- Functional components only, use custom hooks for shared logic
- Props: export interface ComponentNameProps
- Early returns, max 50-line functions, max 300-line files
- Use @client/, @server/, @shared/ path aliases
- Controlled forms: react-hook-form + zod validation
- All routes: zod input validation, consistent { error, code } responses
- Thin controllers → services for business logic
- Use transactions for multi-table operations
- Soft deletes (deleted_at), UUIDs for PKs, snake_case tables/columns
- All exported functions need unit tests, 80% coverage minimum

## Tests
- Unit: `npm test -- --grep "name"` | E2E: `npm run test:e2e`
- Test data factories in `src/test/factories/`
- Mock external services in tests

## Git
- Branches: feature/TICKET-123-desc, fix/TICKET-456-desc
- Commits: type(scope): description (conventional commits)
- Squash merge, 1+ review required
```

**Token count: ~434 tokens per turn. Over 30 turns with 80% caching: ~$0.008 (Sonnet) / ~$0.039 (Opus)**

### What Was Cut and Why

| Removed Content | Lines Saved | Reason |
|-----------------|:-----------:|--------|
| Company overview and team info | 12 lines | Irrelevant to code generation |
| Full directory tree | 40 lines | Claude can explore with `ls`/`Glob`; trees go stale |
| Detailed component breakdown | 8 lines | Structure summary is sufficient |
| API endpoint listing | 20 lines | Claude can read route files directly |
| Deployment procedures | 15 lines | Only needed during deploys (use a custom command) |
| Recent changes / changelog | 6 lines | Not needed for writing code |
| Known issues | 4 lines | Reference tickets when relevant, not every turn |
| Monitoring/CDN/CI details | 5 lines | Only relevant for infra tasks |
| Redundant/verbose phrasing | ~50 lines | Compressed into terse, high-density format |
| Storybook, bundle analysis commands | 2 lines | Rarely used, not needed every turn |

### Savings Summary

| Metric | Before | After | Improvement |
|--------|:------:|:-----:|:-----------:|
| Lines | 380 | 62 | **84% fewer** |
| Tokens per turn | ~2,660 | ~434 | **84% fewer** |
| 30-turn Sonnet cost | $0.048 | $0.008 | **$0.040 saved/session** |
| 30-turn Opus cost | $0.240 | $0.039 | **$0.201 saved/session** |
| Monthly Opus cost (110 sessions) | $26.40 | $4.29 | **$22.11 saved/month** |

---

## .claudeignore: Stop Indexing Junk

### What .claudeignore Does

When Claude Code searches your project (via Glob or Grep), it can discover and read files that add tokens to your context but provide no value. The `.claudeignore` file (placed at your project root) tells Claude Code to skip these paths entirely.

This works the same way as `.gitignore` — same glob pattern syntax.

### Why It Matters

Without `.claudeignore`, a Glob search for `**/*.js` in a Node.js project might return thousands of results from `node_modules/`. Even if Claude does not read them all, the search results themselves consume tokens, and Claude may waste turns exploring irrelevant files.

### Recommended .claudeignore

```gitignore
# Dependencies — thousands of files Claude never needs to read
node_modules/
vendor/
bower_components/
.pnpm-store/

# Build output — generated files, not source code
dist/
build/
out/
.next/
.nuxt/
.svelte-kit/
.vercel/
.netlify/
target/
bin/
obj/

# Lock files — huge, machine-generated, not useful for Claude
package-lock.json
yarn.lock
pnpm-lock.yaml
Gemfile.lock
poetry.lock
composer.lock
Cargo.lock
go.sum

# Generated / compiled assets
*.min.js
*.min.css
*.bundle.js
*.chunk.js
*.map
*.d.ts

# Test artifacts
coverage/
.nyc_output/
test-results/
playwright-report/
__snapshots__/

# Caches
.cache/
.parcel-cache/
.eslintcache
.tsbuildinfo
*.pyc
__pycache__/
.pytest_cache/

# Version control internals
.git/

# Environment and secrets
.env
.env.*
*.pem
*.key

# IDE files (usually not needed)
.idea/
.vscode/settings.json
*.swp
*.swo

# Large data files
*.sqlite
*.db
*.sql.gz
*.csv
*.parquet

# OS files
.DS_Store
Thumbs.db
desktop.ini

# Logs
*.log
logs/
```

### Measuring the Impact

You can estimate how much `.claudeignore` saves by checking what Claude would otherwise find:

```bash
# Count how many files Claude would index without .claudeignore
find . -type f | wc -l

# Count how many are in node_modules alone
find ./node_modules -type f 2>/dev/null | wc -l

# A typical React project: 30,000+ files in node_modules vs ~200 source files
```

In a project with `node_modules/` containing 30,000 files, a single Glob search returning even 100 results from dependencies adds ~500-2,000 tokens of useless context per search. Over a 30-turn session with multiple searches, this adds up to 5,000-20,000 wasted tokens.

---

## File Read Strategies

### The Problem with Full File Reads

When Claude uses the Read tool on a file, the entire file content becomes part of the conversation history. A 500-line file is approximately 5,000 tokens — and those tokens persist for every remaining turn.

```
Reading a 500-line file on turn 5 of a 30-turn session:
= 5,000 tokens x 25 remaining turns
= 125,000 extra input tokens
= $0.375 on Sonnet (uncached) or ~$0.075 (with 80% caching)
```

Reading three large files carelessly can add more cost than your entire CLAUDE.md.

### Strategies to Minimize File Read Costs

**1. Point Claude to specific locations**

Instead of:
```
Look at the user service and fix the bug
```

Use:
```
Fix the null pointer in src/services/userService.ts — the getUserById function around line 45
```

Claude will read only the relevant section instead of the entire file.

**2. Reference functions by name**

```
Read the processPayment function in src/services/paymentService.ts
```

Claude can use Grep to find the function and read only the surrounding lines rather than the full file.

**3. Use line ranges for large files**

If you know where the relevant code is, tell Claude:

```
Read lines 120-180 of src/models/Order.ts — that's the calculateTotal method
```

**4. Let Claude search instead of read**

For finding patterns across files, Grep is much cheaper than reading entire files:

```
Search for all uses of deprecated_function across the src/ directory
```

Grep results are typically 50-200 tokens vs 2,000-10,000 for full file reads.

**5. Avoid "read and understand" prompts for large files**

Instead of:
```
Read src/config/routes.ts and tell me about the route structure
```

Use:
```
What routes are defined in src/config/routes.ts? Just list the paths and HTTP methods.
```

This signals Claude to scan efficiently rather than ingest the whole file into a detailed analysis.

### File Read Cost Reference

| File Size | Tokens | Per-Turn Cost (Sonnet) | 30-Turn Carry Cost |
|:---------:|:------:|:---------------------:|:------------------:|
| 50 lines | ~500 | $0.0015 | ~$0.009 |
| 100 lines | ~1,000 | $0.003 | ~$0.018 |
| 300 lines | ~3,000 | $0.009 | ~$0.054 |
| 500 lines | ~5,000 | $0.015 | ~$0.090 |
| 1,000 lines | ~10,000 | $0.030 | ~$0.180 |
| 2,000 lines | ~20,000 | $0.060 | ~$0.360 |

> "30-turn carry cost" = the total extra input cost of having that file in history for the remaining 30 turns at blended cache rate. Actual cost is lower with higher cache rates but these are useful upper-bound estimates.

---

## Using /compact to Reset Context

### What /compact Does

The `/compact` command tells Claude Code to summarize the entire conversation history into a condensed form. This replaces the full history with a much shorter summary, dramatically reducing input tokens for all subsequent turns.

```
Before /compact:
  Conversation history: 80,000 tokens (40 turns of detailed exchanges)

After /compact:
  Conversation summary: ~5,000-10,000 tokens (key decisions and context preserved)

Savings: 70,000-75,000 tokens of input per turn going forward
```

### When to Use /compact

| Signal | Action |
|--------|--------|
| Session exceeds 20 turns | Run `/compact` |
| `/usage` shows input tokens > 60K per turn | Run `/compact` |
| Claude seems slow to respond | Context may be large — run `/compact` |
| You are switching to a different area of the codebase | Run `/compact` (or start a new session) |
| Claude is "forgetting" earlier instructions | Context may be truncating — `/compact` + restate key context |

### When NOT to Use /compact

| Signal | Why Not |
|--------|---------|
| You are in the middle of a multi-step operation | Claude needs the detailed history to continue correctly |
| You just referenced specific code from earlier turns | The summary may not preserve exact code details |
| Session is under 10 turns | Not enough history to justify the cost of compacting |

### The /compact Trade-Off

`/compact` is not free:

1. **It costs tokens to generate the summary** — Claude produces output tokens for the summary (an output cost)
2. **It breaks the prompt cache** — the conversation structure changes, so cached content needs to be re-cached
3. **It loses detail** — the summary is lossy; specific code snippets and exact phrasings may be lost

The rule of thumb: **`/compact` pays for itself after 3-5 turns** following the compaction. If you have fewer turns left, it may not be worth it. If you have 10+ turns left, it is almost always worth it.

### Custom Compact Prompts

You can provide a focus hint when compacting:

```
/compact Focus on the authentication refactor — keep all decisions about JWT token structure and middleware changes.
```

This helps Claude prioritize what to preserve in the summary, reducing the risk of losing important context.

---

## Subagents: Isolating Context-Heavy Work

### How Subagents Save Tokens

When Claude Code spawns a subagent (via the Task tool), that subagent gets its own isolated context window. The key cost benefit: **the subagent's detailed work does not pollute your main conversation history**.

```
Without subagents:
  Main context: system + CLAUDE.md + history + [5 large file reads] + [50 grep results]
  Every subsequent turn carries those file reads and grep results

With subagents:
  Subagent context: system + CLAUDE.md + [5 large file reads] + [50 grep results]
  Main context: system + CLAUDE.md + history + [subagent's summary result]
  The detailed file contents stay in the subagent, not your main thread
```

### What Comes Back to Main Context

When a subagent completes, only its **final result** is added to your main conversation. Not the files it read, not the searches it ran — just the answer. This is typically 100-500 tokens vs the 10,000-50,000 tokens the subagent consumed internally.

### Best Use Cases for Subagents

| Task | Why Subagent | Token Savings |
|------|-------------|:------------:|
| Searching codebase for patterns | Grep results stay in subagent | 2,000-10,000 |
| Reading multiple files for analysis | File contents stay in subagent | 5,000-30,000 |
| Generating boilerplate | Output stays in subagent until summarized | 1,000-5,000 |
| Running and interpreting test output | Verbose test output stays in subagent | 3,000-15,000 |
| Exploring unfamiliar code | Discovery reads stay in subagent | 5,000-20,000 |

### How to Trigger Subagent Usage

Claude Code automatically uses subagents for certain complex tasks, but you can encourage it:

```
Search the entire src/ directory for all usages of the deprecated
calculateTotal function, and give me a summary of which files need updating.
Don't read the full files — just tell me file names and line numbers.
```

By asking for a summary, you signal Claude to delegate the heavy search to a subagent and return only the distilled result.

### When Subagents Are Not Worth It

- **Very short tasks** — The overhead of spawning a subagent (separate context initialization) may cost more than just doing it inline for simple lookups
- **Tasks requiring tight interaction** — If the subagent's result determines your next 5 prompts, the back-and-forth negates the isolation benefit
- **Already-small context** — If your main context is under 20K tokens, isolation savings are minimal

---

## Writing Concise Prompts

### Why Prompt Length Matters

Your prompts are typically 20-200 tokens, which seems small compared to system prompts and history. But concise prompts have a second-order benefit: **they produce shorter conversations**, which means less history accumulation.

A vague prompt leads to clarification questions, false starts, and iteration — each adding to history. A precise prompt often gets the right result in one turn.

### Bad vs Good Prompts (With Token Impact)

**Example 1: Bug Fix**

Bad (47 tokens):
```
Hey Claude, so I've been having this issue where the app crashes sometimes
when users try to log in. I think it might be related to the auth middleware
but I'm not sure. Can you take a look and see what might be going on?
```

Good (28 tokens):
```
Fix the null reference crash in src/middleware/auth.ts — req.user is
undefined when the JWT token is expired. Add a null check before line 23.
```

The bad prompt will trigger Claude to: search for auth files, read multiple files, ask clarifying questions, and guess at the issue — costing 3-5 turns. The good prompt leads to a 1-turn fix.

**Estimated cost difference: $0.08 vs $0.02 (Sonnet) for the same outcome.**

**Example 2: New Feature**

Bad (62 tokens):
```
I need a new endpoint for the admin panel. It should let admins search through
user accounts with various filters. We need to be able to filter by name,
email, role, and registration date. It should support pagination too.
Also make sure it has proper authentication. Oh and add tests.
```

Good (51 tokens):
```
Add GET /api/admin/users endpoint in src/server/routes/admin.ts:
- Query params: name, email, role, registered_after, registered_before, page, limit
- Require admin role (use existing adminAuth middleware)
- Return paginated { users, total, page, limit }
- Add tests in src/server/routes/__tests__/admin.test.ts
```

The good prompt is actually fewer tokens *and* more specific. Claude can implement it in 1-2 turns instead of 3-5 because there is no ambiguity.

### Prompt Conciseness Rules

1. **Name exact files and paths** — "in `src/services/auth.ts`" not "in the auth service"
2. **Reference line numbers when possible** — "around line 45" saves a file search
3. **Specify the expected pattern** — "return `{ error, code }` format" not "handle errors properly"
4. **Batch related changes** — one prompt for 5 related edits beats 5 separate prompts
5. **Skip pleasantries** — "Fix X" not "Hey, could you possibly help me fix X?"
6. **Use structured formats** — bullet points and specs are more token-efficient than prose

---

## Memory Files vs Inline Instructions

### The Problem with Repeating Yourself

If you find yourself typing the same instruction across multiple sessions:

```
Remember to always use single quotes in TypeScript files
```
```
Make sure to add error handling with our standard AppError class
```
```
Run npm test after making changes
```

Each repetition costs ~15-30 tokens of input. Across 5 sessions a day, that is 75-150 wasted tokens per instruction per day. Not huge individually, but these add up when you have 10+ such habits.

### The Solution: Put It in CLAUDE.md Once

```markdown
## Code Rules
- Single quotes in TypeScript
- Error handling: throw new AppError(message, statusCode)
- Run `npm test` after changes
```

Three lines in CLAUDE.md (~21 tokens) that are loaded once per turn via cache, replacing 30+ tokens of repeated ad-hoc instructions.

### When to Use CLAUDE.md vs Separate Files

| Instruction Type | Where | Why |
|-----------------|-------|-----|
| Universal rules (applies to every task) | CLAUDE.md | Loaded every turn, always available |
| Module-specific patterns | Nested CLAUDE.md in that directory | Only loaded when working in that area |
| Rare/specialized workflows | Custom slash command | Only loaded when explicitly invoked |
| One-off task context | Your prompt | Does not persist beyond this session |

### Nested CLAUDE.md Files

Claude Code supports `CLAUDE.md` files in subdirectories. These are loaded **only when Claude is working with files in that directory or below**:

```
project/
├── CLAUDE.md                 ← Always loaded (keep this lean)
├── src/
│   ├── client/
│   │   └── CLAUDE.md         ← Loaded only for frontend work
│   └── server/
│       └── CLAUDE.md         ← Loaded only for backend work
└── infrastructure/
    └── CLAUDE.md             ← Loaded only for infra work
```

This lets you move domain-specific instructions out of the root CLAUDE.md (reducing its size) while still having them available when relevant.

**Example: moving frontend rules to `src/client/CLAUDE.md`**

Root CLAUDE.md (before): 150 lines including 40 lines of React-specific rules
Root CLAUDE.md (after): 110 lines
`src/client/CLAUDE.md`: 40 lines of React rules — only loaded during frontend work

Savings: 40 fewer lines in root CLAUDE.md = ~280 fewer tokens on every non-frontend turn.

### Custom Slash Commands for Specialized Workflows

For workflows you run occasionally (deploying, database migrations, performance audits), create custom commands instead of putting instructions in CLAUDE.md:

```
.claude/commands/deploy.md:
---
Run the deployment checklist:
1. Run npm test and ensure all pass
2. Run npm run build and check for errors
3. Check that .env.production has all required variables
4. Run npm run db:migrate -- --dry-run to preview migrations
5. Report status of each step
---
```

Invoke with `/deploy` when needed. This keeps 20+ lines out of CLAUDE.md and only loads them when you explicitly ask.

---

## Putting It All Together

### The Context Optimization Checklist

Apply these in order of impact:

- [ ] **Audit CLAUDE.md** — cut to under 150 lines, move extras to nested files or commands
- [ ] **Create `.claudeignore`** — copy the recommended file from this guide and customize
- [ ] **Set budget caps** — `claude --max-budget-usd 5` as your default launch command
- [ ] **Use `/compact` after 20 turns** — or sooner if `/usage` shows high input token counts
- [ ] **Reference specific files and lines** in prompts — avoid triggering full-file reads
- [ ] **Batch related changes** into single prompts — fewer turns = less history growth
- [ ] **Use subagents for search-heavy tasks** — keep search results out of main context
- [ ] **Move domain rules to nested CLAUDE.md files** — reduce root file size
- [ ] **Create commands for rare workflows** — deploy, migrate, audit procedures
- [ ] **Start new sessions for new tasks** — do not carry stale context

### Expected Savings When Fully Applied

| Strategy | Savings on Input | Effort to Implement |
|----------|:----------------:|:-------------------:|
| CLAUDE.md under 150 lines | 10-20% | One-time, 15 minutes |
| .claudeignore configured | 5-15% | One-time, 2 minutes |
| /compact usage | 10-20% per long session | Ongoing habit |
| Precise file references | 5-15% | Ongoing habit |
| Subagent delegation | 10-25% on search-heavy sessions | Ongoing habit |
| Concise prompts | 5-10% | Ongoing habit |
| Nested CLAUDE.md + commands | 5-10% | One-time, 15 minutes |
| New sessions for new tasks | 10-20% | Ongoing habit |
| **Combined** | **30-50% reduction** | |

These percentages compound. A developer who was spending $15/day on Sonnet can realistically drop to $7-10/day by applying all of these strategies — saving $110-176/month.

---

*Next: [Guide 03 - Model Selection](03-model-selection.md) — when to use Opus vs Sonnet vs Haiku, with a decision tree and cost comparisons for every task type.*
