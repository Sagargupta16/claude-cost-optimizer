# Guide 02: Context Optimization

> Every token in your input is a token you pay for. This guide covers practical strategies to reduce input tokens without sacrificing Claude's ability to help you. No combined measurement exists for them; the measured ones: with caching on, Anthropic's input trimming (image resizing plus tool search) took a further 26% off a short run and 21% off a long one ([cost-optimization guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence)), and reading a CSV through code execution instead of the prompt cut a request 79% in Anthropic's [cost-optimization cookbook](https://platform.claude.com/cookbook/cost-optimization-cost-optimization).

---

## Table of Contents

- [Why Input Tokens Matter](#why-input-tokens-matter)
- [CLAUDE.md: The Line Budget](#claudemd-the-line-budget)
- [Before and After: CLAUDE.md Optimization](#before-and-after-claudemd-optimization)
- [Read Deny Rules: Stop Reading Junk](#read-deny-rules-stop-reading-junk)
- [File Read Strategies](#file-read-strategies)
- [Using /compact to Reset Context](#using-compact-to-reset-context)
- [Subagents: Isolating Context-Heavy Work](#subagents-isolating-context-heavy-work)
- [Writing Concise Prompts](#writing-concise-prompts)
- [Memory Files vs Inline Instructions](#memory-files-vs-inline-instructions)
- [Putting It All Together](#putting-it-all-together)

---

## Why Input Tokens Matter

Input tokens are the tokens sent *to* Claude on each turn. They include everything: the system prompt, your CLAUDE.md, the full conversation history, tool results, and your current message.

The critical insight is that **input tokens are cumulative and recurring**. Unlike output tokens (which are generated once), input tokens include all previous conversation history -- so they grow with every turn and you pay for them repeatedly.

```
Turn  1 input:   4,500 tokens   (system + CLAUDE.md + your message)
Turn 10 input:  35,000 tokens   (all of the above + 9 turns of history)
Turn 30 input: 100,000 tokens   (all of the above + 29 turns of history)
```

Every token you can keep out of the input -- by trimming CLAUDE.md, ignoring irrelevant files, avoiding unnecessary file reads, and compacting history -- saves you money on *every subsequent turn*.

The math is straightforward: remove 1,000 tokens of recurring input, and over a 30-turn session you send 30,000 fewer input tokens. Claude Code writes those tokens to the cache once (1.25x input) and reads them on the other 29 turns, so on Sonnet 4.6 the cut saves 1,000 x ($3.75 + 29 x $0.30) / 1M = $0.012 per session, $1.37 a month at 5 sessions a day for 22 days; on Opus 5.5 ($5 write, $0.20 read) it is $0.011 and $1.19 ([formula](01-understanding-costs.md#claudemd-cost-over-a-session)). Every pause longer than the cache TTL adds one more write of the whole prefix, so the cut is worth more on sessions with breaks. Each cut in this guide adds to that.

---

## CLAUDE.md: The Line Budget

### Why Every Line Costs You Money

Your project's `CLAUDE.md` file is loaded in its entirety as part of the input on **every single turn**. It does not matter whether the current turn is about database schemas or CSS styling -- the whole file is always there.

This makes CLAUDE.md the highest-leverage optimization target because:

1. It affects **every turn** in **every session**
2. It is under your direct control
3. Many CLAUDE.md files carry content Claude rarely needs; Anthropic's target is under 200 lines per file

### What Actually Loads (No Character Cap)

Claude Code does not truncate CLAUDE.md, and there is no per-file or total character cap. What loads, per Anthropic's memory docs:

- **In full, at launch**: every CLAUDE.md and CLAUDE.local.md in the directory hierarchy above your working directory.
- **On demand**: CLAUDE.md files in subdirectories load when Claude reads files there. Rules in `.claude/rules/` with `paths:` frontmatter load when Claude reads a matching file. Skills load when invoked.
- **Every turn, even unused**: each skill's description in the skill listing ("Every skill in the skill listing adds to your context on every turn, whether or not Claude ever uses it"; `description` plus `when_to_use` is cut at 1,536 characters). Run `/skill-doctor` (Claude Code v2.1.252+) to see what each skill costs and how often it is used; it flags skills that have never been invoked and says where to turn them off ([skills docs](https://code.claude.com/docs/en/skills)).
- **The one real truncation**: auto memory. Only the first 200 lines or 25KB of `MEMORY.md`, whichever comes first, load at session start.

Anthropic's size guidance, verbatim: "target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence." So the reason to stay small is token cost in every session plus adherence, not a cutoff. `@path` imports help organize a long file, but imported files still load at launch, so they do not reduce tokens.

What this means in practice:

| Scenario | Loads at Launch | Loads on Demand | Risk |
|----------|:--------------:|:------------:|------|
| Single project, one CLAUDE.md | Root CLAUDE.md, in full | -- | Low while it stays under 200 lines |
| Monorepo with root + 2 workspace CLAUDE.md files | Root file, plus the workspace file if you launch from inside that workspace | Workspace files when Claude reads files there | Every loaded file adds tokens to every turn |
| Nested dirs with parent CLAUDE.md files (e.g., `~/CLAUDE.md` + `~/code/CLAUDE.md` + project) | Every file above your working directory, in full | Subdirectory files | Parent files add tokens to every session in every child project |

**For monorepos**: keep the root file to what every workspace needs, and put workspace rules in that workspace's CLAUDE.md or in path-scoped `.claude/rules/` files so they load only when Claude touches that code.

### The 150-Line Budget (Approximate Guideline)

Anthropic's target is under **200 lines** per CLAUDE.md file; this guide aims for about **150 lines** to leave headroom. Nothing is cut off past either number -- every extra line just costs tokens on every turn. Here is the cost breakdown by size:

| CLAUDE.md Size | Tokens Per Turn | 30-Turn Session, Warm Cache (Sonnet 4.6) | 30-Turn Session, Warm Cache (Opus 5.5) | 30-Turn Session, No Cache (Sonnet 4.6) | Monthly, Warm Cache (Opus 5.5, 110 sessions) |
|:--------------:|:---------------:|:----------------------------------------:|:--------------------------------------:|:--------------------------------------:|:--------------------------------------------:|
| 50 lines | ~350 | $0.0044 | $0.0038 | $0.03 | $0.42 |
| 100 lines | ~700 | $0.0087 | $0.0076 | $0.06 | $0.83 |
| **150 lines** | **~1,050** | **$0.013** | **$0.011** | **$0.09** | **$1.25** |
| 300 lines | ~2,100 | $0.026 | $0.023 | $0.19 | $2.49 |
| 500 lines | ~3,500 | $0.044 | $0.038 | $0.32 | $4.16 |

> Computed with Claude Code's prefix caching ([Guide 01 formula](01-understanding-costs.md#claudemd-cost-over-a-session)): the file is written to the cache once and read on the other 29 turns, so a session costs tokens x (write + 29 x read). Sonnet 4.6: $3.75 + 29 x $0.30 = $12.45 per 1M tokens; Opus 5.5: $5 + 29 x $0.20 = $10.80, which puts Opus 5.5 below Sonnet 4.6 here because its cache reads cost 0.05x. "No cache" is 30 x $3 = $90 per 1M, every turn at full input price. Each pause longer than the cache TTL adds one re-write: 3,500 tokens x $5/1M = $0.0175 on Opus 5.5 for a 500-line file.

**On legacy Opus 5** ($6.25 write, $0.50 read) the warm-cache cost is 1.9x the Opus 5.5 column: a 500-line CLAUDE.md costs $4.16/month on Opus 5.5 and $7.99 on legacy Opus 5 across 110 sessions. **Opus 5.5 adds about 30% on top** because its tokenizer (the same one shipped with Opus 4.7 and used by every Opus since) produces more tokens for the same text ([Anthropic pricing page](https://platform.claude.com/docs/en/about-claude/pricing)).

One caching caveat that depends on size: a `cache_control` block is silently ignored -- no error, no discount -- if the prefix it marks is shorter than the model's minimum cacheable prompt. That floor is **512 tokens on Opus 5.5, Opus 5, Sonnet 5.5 and Haiku 5.5**, down from 1,024 on Opus 4.8, 2,048 on Opus 4.7, and 4,096 on Opus 4.6. Sonnet 5 and Sonnet 4.6 sit at 1,024; legacy Haiku 4.5 at 4,096. Practical effect: a ~100-line CLAUDE.md (~700 tokens) that was too short to cache on Opus 4.8, Sonnet 5 or Haiku 4.5 does cache on Opus 5.5, Opus 5, Sonnet 5.5 and Haiku 5.5, while a 50-line one (~350 tokens) still caches on none of them.

### What Belongs in CLAUDE.md

Include only information Claude needs on **most turns**:

| Include | Why |
|---------|-----|
| Tech stack (language, framework, versions) | Affects every code suggestion |
| Build/test/lint commands | Claude runs these frequently |
| Project structure overview (10 lines max) | Helps Claude find files |
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
| Workflow-specific instructions (PR reviews, DB migrations) | Only relevant when running that workflow | A skill, which loads on demand |
| Commented-out alternatives | Adds tokens for no active benefit | Delete them |
| Aspirational rules not yet enforced | Confuses Claude | Add when enforced |

### The "Every Line" Audit

Go through your CLAUDE.md and ask for each line: **"Does Claude need this on EVERY turn?"**

- If yes, keep it.
- If "only sometimes," move it to a skill, a path-scoped `.claude/rules/` file, a nested CLAUDE.md, or a custom command.
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
- Alice (Tech Lead) -- alice@acme.com
- Bob (Frontend) -- bob@acme.com
- Carol (Backend) -- carol@acme.com
- Dave (DevOps) -- dave@acme.com

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
- No `any` types allowed -- use `unknown` if type is truly unknown
- Prefer `const` over `let`, never use `var`
- Use early returns to reduce nesting
- Maximum function length: 50 lines
- Maximum file length: 300 lines
- Use descriptive variable names (no single-letter variables except in loops)
- All functions must have JSDoc comments
- All exported functions must have unit tests
- Use absolute imports with path aliases (@client/, @server/, @shared/)
- Handle all errors explicitly -- no empty catch blocks
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
- Controller functions should be thin -- delegate to services
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
- npm run dev -- Start development server (Vite + Express)
- npm run build -- Production build
- npm test -- Run unit tests
- npm run test:e2e -- Run Playwright e2e tests
- npm run lint -- ESLint + Prettier check
- npm run lint:fix -- Auto-fix linting issues
- npm run type-check -- TypeScript type checking
- npm run db:migrate -- Run Prisma migrations
- npm run db:seed -- Seed database with test data
- npm run db:studio -- Open Prisma Studio
- npm run storybook -- Open Storybook
- npm run analyze -- Bundle size analysis

## API Endpoints (Current)
- POST /api/auth/login -- User login
- POST /api/auth/register -- User registration
- GET /api/products -- List products (paginated)
- GET /api/products/:id -- Product detail
- POST /api/cart -- Add to cart
- GET /api/cart -- Get cart
- PUT /api/cart/:itemId -- Update cart item
- DELETE /api/cart/:itemId -- Remove from cart
- POST /api/orders -- Create order
- GET /api/orders -- List user orders
- GET /api/orders/:id -- Order detail
- GET /api/admin/dashboard -- Admin dashboard stats
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

**Token count: ~2,660 tokens per turn. Over 30 turns with prefix caching: ~$0.014 (Sonnet 5.5) / ~$0.029 (Opus 5.5)**

### After: 62 Lines (Optimized)

```markdown
# MyApp -- E-commerce Platform

Tech: TypeScript strict, React 18, Redux Toolkit, Tailwind, Vite 5
Backend: Node 20, Express, PostgreSQL 16 + Prisma, Redis, RabbitMQ
Auth: Passport.js + JWT | Search: Elasticsearch | Hosting: AWS ECS

## Commands
- `npm run dev` -- Dev server (Vite + Express)
- `npm run build` -- Production build
- `npm test` -- Unit tests (Vitest + RTL)
- `npm run test:e2e` -- E2E tests (Playwright)
- `npm run lint:fix` -- ESLint + Prettier autofix
- `npm run type-check` -- TypeScript checks
- `npm run db:migrate` -- Prisma migrations

## Structure
- `src/client/` -- React frontend (components/, hooks/, store/, services/)
- `src/server/` -- Express backend (routes/, controllers/, models/, services/)
- `src/shared/` -- Shared types and constants

## Code Rules
- No `any` -- use `unknown` if needed
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

**Token count: ~434 tokens per turn. Over 30 turns with prefix caching: ~$0.0023 (Sonnet 5.5) / ~$0.0047 (Opus 5.5)**

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
| 30-turn Sonnet 5.5 cost | $0.014 | $0.0023 | **$0.012 saved/session** |
| 30-turn Opus 5.5 cost | $0.029 | $0.0047 | **$0.024 saved/session** |
| Monthly Opus 5.5 cost (110 sessions) | $3.16 | $0.52 | **$2.64 saved/month** |

> Costs use Claude Code's prefix caching ([Guide 01](01-understanding-costs.md#key-formulas)): the file is written once at the 5-minute cache-write rate and read on the other 29 turns, tokens x (write + 29 x read): $2.50 + 29 x $0.10 = $5.40 per 1M on Sonnet 5.5, $5 + 29 x $0.20 = $10.80 on Opus 5.5. For example, 2,660 x $10.80 / 1M = $0.029.

---

## Read Deny Rules: Stop Reading Junk

> `.claudeignore` is not a Claude Code feature. It appears nowhere in Claude Code's documentation, and Claude Code does not read it. If you created one from an earlier version of this guide, convert it with the rule [below](#converting-an-existing-claudeignore).

### What Read Deny Rules Do

The documented way to keep Claude's file tools out of paths is `permissions.deny` with `Read(...)` rules in `.claude/settings.json`. Read deny rules apply to Claude's built-in file tools, to the file commands Claude Code recognizes in Bash (`cat`, `head`, `tail`, `sed`, `tee`), and to redirection targets.

Patterns use gitignore syntax:

- `./path` is relative to the project, `//path` is absolute from the filesystem root, `~/path` is your home directory
- `*` matches within one path segment, `**` across directories
- A bare filename matches at any depth: `Read(.env)` equals `Read(**/.env)`
- A pattern starting with `!` is a negation that carves paths out of earlier rules in the same file

### Why It Matters

Dependency folders, build output and lock files add tokens to your context but provide no value, and a file Claude reads stays in history for every remaining turn. Deny rules take those paths off the table. Scoped rules such as `Read(./dist/**)` do not change which tools Claude sees, so adding them does not invalidate the prompt cache.

### Recommended Read Deny Rules

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

Extend it for your stack with the same patterns, for example `Read(./vendor/**)`, `Read(./.next/**)`, `Read(./target/**)`, `Read(*.map)`, `Read(*.pem)`, and one rule per lock file you have: `Read(pnpm-lock.yaml)`, `Read(yarn.lock)`, `Read(poetry.lock)`, `Read(Cargo.lock)`, `Read(uv.lock)`.

### Converting an Existing `.claudeignore`

| Ignore-file line | Read rule |
|------------------|-----------|
| `dir/` (e.g. `node_modules/`) | `Read(./node_modules/**)` |
| A path with a `/` elsewhere (e.g. `.vscode/settings.json`, `/config/local.json`) | `Read(./.vscode/settings.json)`, `Read(./config/local.json)` (strip a leading `/`) |
| A bare name or glob with no `/` (e.g. `.env`, `*.min.js`) | `Read(.env)`, `Read(*.min.js)` (matches at any depth) |
| Blank lines, `#` comments, `!` negations | Skip |

### Measuring the Impact

There is no published measurement of what Read deny rules save. The effect depends on how often Claude would otherwise open those files. To gauge your exposure, count what sits in the paths you deny, and run `/context` in a session to see what is consuming space:

```bash
# Count every file in the project
find . -type f | wc -l

# Count how many are in node_modules alone
find ./node_modules -type f 2>/dev/null | wc -l

# A typical React project: 30,000+ files in node_modules vs ~200 source files
```

---

## File Read Strategies

### The Problem with Full File Reads

When Claude uses the Read tool on a file, the entire file content becomes part of the conversation history. A 500-line file is approximately 5,000 tokens -- and those tokens persist for every remaining turn.

```
Reading a 500-line file on turn 5 of a 30-turn session (Sonnet 4.6):
= 5,000 tokens written to the cache once, then read on the 25 later turns
= 5,000 x $3.75/1M + 125,000 x $0.30/1M
= $0.019 + $0.038 = $0.056 with a warm cache
  ($0.050 on Opus 5.5; $0.375 if all 125,000 re-reads billed at the uncached $3/1M)
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
Fix the null pointer in src/services/userService.ts -- the getUserById function around line 45
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
Read lines 120-180 of src/models/Order.ts -- that's the calculateTotal method
```

**4. Let Claude search instead of read**

For finding patterns across files, Grep is much cheaper than reading entire files:

```
Search for all uses of deprecated_function across the src/ directory
```

Grep returns only the matching lines: a 20-match search is about 200 tokens at this guide's 10 tokens per line, against about 5,000 for a full read of one 500-line file.

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

**6. Use code intelligence instead of grep-then-read**

Anthropic's costs page notes that code intelligence plugins replace grep-then-read-many-files with one go-to-definition call. If a plugin exists for your language, it is the cheapest way for Claude to find a symbol.

**7. Run code over data files instead of reading them**

Ask Claude to write and run a short script (`python`, `jq`, `awk`) over a CSV, log or JSON file rather than reading it into the conversation. Anthropic measured the API version of this: 25 aggregate questions over a 1,862-row CSV, answered through code execution on the uploaded file, were 25/25 correct for $0.40; with the CSV pasted into the prompt, 6/25 correct for $5.01. Code execution cost 92% less (1 - $0.40 / $5.01) and got every answer right ([cost-optimization guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence)).

### File Read Cost Reference

| File Size | Tokens | Cost to Add It (one cache write, Sonnet 4.6) | 30-Turn Carry Cost (Sonnet 4.6) | 30-Turn Carry Cost (Opus 5.5) |
|:---------:|:------:|:--------------------------------------------:|:-------------------------------:|:-----------------------------:|
| 50 lines | ~500 | $0.0019 | ~$0.0064 | ~$0.0055 |
| 100 lines | ~1,000 | $0.0038 | ~$0.013 | ~$0.011 |
| 300 lines | ~3,000 | $0.011 | ~$0.038 | ~$0.033 |
| 500 lines | ~5,000 | $0.019 | ~$0.064 | ~$0.055 |
| 1,000 lines | ~10,000 | $0.038 | ~$0.128 | ~$0.110 |
| 2,000 lines | ~20,000 | $0.075 | ~$0.255 | ~$0.220 |

> "Cost to add it" is one 5-minute cache write ($3.75/MTok on Sonnet 4.6). "30-turn carry cost" is that write plus a cache read on each of the next 30 turns: tokens x ($3.75 + 30 x $0.30) / 1M on Sonnet 4.6, tokens x ($5 + 30 x $0.20) / 1M on Opus 5.5. A pause longer than the cache TTL adds a full re-write of the whole context, this file included.

### Keep Tool Output Small

File reads are not the only tool results that pile up in history:

- **Filter verbose output with a hook.** Hooks can preprocess output before Claude sees it. Anthropic's example is a PreToolUse hook that filters test output down to failures, which cuts tens of thousands of tokens to hundreds.
- **Prefer CLI tools to MCP servers where one exists** (`gh`, `aws`, `gcloud`, `sentry-cli`). They add no per-tool listing. MCP tool search is on by default, so only tool names and server instructions enter context until Claude uses a specific tool; full schemas load up front only when tool search is off (`ENABLE_TOOL_SEARCH=false`, a custom `ANTHROPIC_BASE_URL`, or models older than the Claude 4.5 generation on Google Cloud). Disable unused servers with `/mcp`.
- **Watch MCP output size.** Claude Code warns when an MCP tool result exceeds 10,000 tokens and caps it at 25,000 by default (`MAX_MCP_OUTPUT_TOKENS`).

---

## Using /compact to Reset Context

### What /compact Does

The `/compact` command tells Claude Code to summarize the entire conversation history into a condensed form. This replaces the full history with a much shorter summary, dramatically reducing input tokens for all subsequent turns.

```
Before /compact:
  Conversation history: 80,000 tokens (40 turns of detailed exchanges)

After /compact:
  Conversation summary: ~7,500 tokens (key decisions and context preserved;
                        an illustrative size, it depends on the session)

Savings: 72,500 tokens of input per turn going forward (80,000 - 7,500)
         (with a warm cache those were cache reads: $0.0145 per turn on Opus 5.5)
```

Claude Code also compacts on its own when the context nears the window: at about 967K tokens by default on 1M-window models. `/autocompact` sets that point anywhere from 100K to 1M and is saved per model since v2.1.288, and subagents get their own `autoCompactWindow` since v2.1.296 ([model-config page](https://code.claude.com/docs/en/model-config), [changelog](https://code.claude.com/docs/en/changelog)). On Haiku 5.5 the lowest setting, 100K, sits right at its price line ($0.10/$0.50 up to 100K prompt tokens, $0.50/$2.50 above).

### When to Use /compact

| Signal | Action |
|--------|--------|
| Session exceeds 20 turns | Run `/compact` |
| `/usage` shows input tokens > 60K per turn | Run `/compact` |
| Claude seems slow to respond | Context may be large -- run `/compact` |
| You are switching to a different area of the codebase | Run `/compact` (or start a new session) |
| Claude is "forgetting" earlier instructions | Context may have been auto-compacted (older history summarized) -- restate key context, or `/compact` with instructions on what to keep |

### When NOT to Use /compact

| Signal | Why Not |
|--------|---------|
| You are in the middle of a multi-step operation | Claude needs the detailed history to continue correctly |
| You just referenced specific code from earlier turns | The summary may not preserve exact code details |
| Session is under 10 turns | Not enough history to justify the cost of compacting |

### The /compact Trade-Off

`/compact` is not free:

1. **It costs tokens to generate the summary** -- Claude produces output tokens for the summary (an output cost). While the cache is warm, the summarization request reads the prefix from cache, so it costs a fraction of the context size; after a break longer than the cache TTL it reprocesses the full history uncached
2. **It rebuilds the conversation layer of the cache** -- the summary replaces the history, so that part needs to be re-cached
3. **It loses detail** -- the summary is lossy; specific code snippets and exact phrasings may be lost

Two cheaper alternatives: `/clear` costs nothing when you no longer need the old context, and `/rewind` returns to an already-cached prefix when you want to back out of a wrong turn.

The rule of thumb: **with a warm cache, `/compact` pays for itself only over many later turns**, because the history it removes was already billing at the cache-read rate. Computed on Opus 5.5 for 80,000 tokens of history compacted to a 7,500-token summary: the summary request costs $0.17 (80K cache read x $0.20/1M plus 7,500 output tokens x $20/1M), re-caching the summary $0.04 (7,500 x $5/1M), and each later turn then reads 72,500 fewer cached tokens, $0.0145 less. Break-even is after about 14 turns, the same on Sonnet 5.5 (every rate halves) and about 8 on Sonnet 4.6, whose cache reads cost 0.1x. So compact to keep Claude focused and to stay under a price line such as Haiku 5.5's 100K, not to cut per-turn cost on a short remainder.

What Anthropic measured: on a long triage run, pruning stale tool results at task boundaries saved 39% and compaction 32%; on a 20-issue run neither saved anything and context editing cost 74% more ([cost-optimization guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence)). In the [cost-optimization cookbook](https://platform.claude.com/cookbook/cost-optimization-cost-optimization) loop, context editing cut 12%, compaction 16%, jagged pruning 29% and moving the work into a subagent 78%.

### Custom Compact Prompts

You can provide a focus hint when compacting:

```
/compact Focus on the authentication refactor -- keep all decisions about JWT token structure and middleware changes.
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

When a subagent completes, only its **final result** is added to your main conversation. Not the files it read, not the searches it ran -- just the answer ("only the relevant summary returns", per Claude Code's [sub-agents docs](https://code.claude.com/docs/en/sub-agents)). No published figure gives typical sizes; the saving is whatever the subagent read minus the summary it returns.

### Best Use Cases for Subagents

| Task | Why Subagent | Main-Context Tokens Kept Out (example) |
|------|-------------|:--------------------------------------:|
| Searching codebase for patterns | Grep results stay in subagent | 2,000 for 200 matching lines |
| Reading multiple files for analysis | File contents stay in subagent | 25,000 for five 500-line files |
| Generating boilerplate | Output stays in subagent until summarized | 3,000 for a 300-line draft |
| Running and interpreting test output | Verbose test output stays in subagent | 10,000 for 1,000 lines of output |
| Exploring unfamiliar code | Discovery reads stay in subagent | 30,000 for ten 300-line files |

> Computed at this guide's 10 tokens per line; the examples are illustrative. Each token kept out would otherwise be read from cache on every later main-context turn ($0.20/1M on Opus 5.5) and re-written after any cache miss ($5/1M), minus the summary the subagent returns. The subagent still bills its own requests, so it saves money only when it reads far more than it returns, ideally on a cheaper model.

### How to Trigger Subagent Usage

Claude Code automatically uses subagents for certain complex tasks, but you can encourage it:

```
Search the entire src/ directory for all usages of the deprecated
calculateTotal function, and give me a summary of which files need updating.
Don't read the full files -- just tell me file names and line numbers.
```

By asking for a summary, you signal Claude to delegate the heavy search to a subagent and return only the distilled result.

For simple subagent tasks, set `model: haiku` in the subagent definition, as Anthropic's costs page suggests. On the Anthropic API that alias is Haiku 5.5 (Claude Code v2.1.293+), priced at $0.10/$0.50 per 1M up to 100K prompt tokens and $0.50/$2.50 above, so a subagent that returns file names and line numbers instead of reading whole files stays in the cheap tier. On Bedrock, Google Cloud, Microsoft Foundry and Claude Platform on AWS the alias still means legacy Haiku 4.5. Do not assume delegation picks Haiku for you: the built-in Explore subagent uses the main conversation's model ([sub-agents docs](https://code.claude.com/docs/en/sub-agents)).

### When Subagents Are Not Worth It

- **Very short tasks** -- The overhead of spawning a subagent (separate context initialization) may cost more than just doing it inline for simple lookups
- **Tasks requiring tight interaction** -- If the subagent's result determines your next 5 prompts, the back-and-forth negates the isolation benefit
- **Already-small context** -- If your main context is under 20K tokens, isolation savings are minimal
- **Agent teams by default** -- Anthropic's costs page says agent teams use about 7x the tokens of a standard session when teammates run in plan mode

---

## Writing Concise Prompts

### Why Prompt Length Matters

Your prompts are small (every example below is under 100 tokens) next to system prompts and history. But concise prompts have a second-order benefit: **they produce shorter conversations**, which means less history accumulation.

A vague prompt leads to clarification questions, false starts, and iteration -- each adding to history. A precise prompt often gets the right result in one turn.

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
Fix the null reference crash in src/middleware/auth.ts -- req.user is
undefined when the JWT token is expired. Add a null check before line 23.
```

The bad prompt will trigger Claude to: search for auth files, read multiple files, ask clarifying questions, and guess at the issue -- costing several turns (4 in the cost figure below). The good prompt leads to a 1-turn fix.

**Computed cost difference: $0.058 (4 turns) vs $0.028 (1 turn) on Sonnet 5.5 for the same outcome**, from a fresh session at this repo's calculator defaults with cache-aware billing. Most of the 1-turn cost is the first cache write of the 9,200-token prompt; each extra turn adds about $0.01.

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

The good prompt is actually fewer tokens *and* more specific. Claude can implement it in fewer turns because there is no ambiguity (illustrative; no published measurement).

### Prompt Conciseness Rules

1. **Name exact files and paths** -- "in `src/services/auth.ts`" not "in the auth service"
2. **Reference line numbers when possible** -- "around line 45" saves a file search
3. **Specify the expected pattern** -- "return `{ error, code }` format" not "handle errors properly"
4. **Batch related changes** -- one prompt for 5 related edits beats 5 separate prompts
5. **Skip pleasantries** -- "Fix X" not "Hey, could you possibly help me fix X?"
6. **Use structured formats** -- bullet points and specs are more token-efficient than prose

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

Each repetition costs about 22 tokens of input (the 56-character first example at about 2.5 characters per token on the current tokenizer, per Anthropic's [models overview](https://platform.claude.com/docs/en/about-claude/models/overview)). Across 5 sessions a day, that is about 110 wasted tokens per instruction per day. Not huge individually, but these add up across many such habits.

### The Solution: Put It in CLAUDE.md Once

```markdown
## Code Rules
- Single quotes in TypeScript
- Error handling: throw new AppError(message, statusCode)
- Run `npm test` after changes
```

Three lines in CLAUDE.md (~21 tokens) that are loaded once per turn via cache, replacing about 61 tokens of repeated ad-hoc instructions each time you would have typed all three (153 characters / 2.5).

### When to Use CLAUDE.md vs Separate Files

| Instruction Type | Where | Why |
|-----------------|-------|-----|
| Universal rules (applies to every task) | CLAUDE.md | Loaded every turn, always available |
| Module-specific patterns | Nested CLAUDE.md in that directory | Only loaded when working in that area |
| Rules for one file type or path | `.claude/rules/` file with `paths:` frontmatter | Only loaded when Claude reads a matching file |
| Workflow-specific instructions (PR reviews, DB migrations) | Skill | Loads on demand |
| Rare/specialized workflows | Skill or custom slash command | Only loaded when explicitly invoked |
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

> **Important**: There is no shared character budget and nothing is truncated. What you pay is tokens: once `src/client/CLAUDE.md` loads, its tokens sit in context alongside the root file. Keep each file lean -- Anthropic's target is under 200 lines per CLAUDE.md file.

**Example: moving frontend rules to `src/client/CLAUDE.md`**

Root CLAUDE.md (before): 150 lines including 40 lines of React-specific rules
Root CLAUDE.md (after): 110 lines
`src/client/CLAUDE.md`: 40 lines of React rules -- only loaded during frontend work

Savings: 40 fewer lines in root CLAUDE.md = ~280 fewer tokens on every non-frontend turn.

### Custom Slash Commands for Specialized Workflows

For workflows you run occasionally (deploying, database migrations, performance audits), keep the instructions out of CLAUDE.md. Anthropic's costs page recommends moving workflow-specific instructions into skills, which load on demand. A custom command does the same job for a checklist you trigger yourself:

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

Invoke with `/deploy` when needed. This keeps the checklist out of CLAUDE.md and only loads it when you explicitly ask.

---

## Putting It All Together

### The Context Optimization Checklist

Apply these in order of impact:

- [ ] **Audit CLAUDE.md** -- target under 200 lines per file (Anthropic's guidance); move workflow instructions to skills and area-specific rules to path-scoped `.claude/rules/` or nested CLAUDE.md files
- [ ] **Add Read deny rules** -- copy the `permissions.deny` block from this guide into `.claude/settings.json` and customize
- [ ] **Set budget caps** -- `claude -p --max-budget-usd 5 "..."` on scripted runs (print mode only), and a budget hook such as [hooks/budget-tracker.sh](../hooks/budget-tracker.sh) for interactive sessions
- [ ] **Use `/compact` after 20 turns** -- or sooner if `/usage` shows high input token counts
- [ ] **Reference specific files and lines** in prompts -- avoid triggering full-file reads
- [ ] **Batch related changes** into single prompts -- fewer turns = less history growth
- [ ] **Use subagents for search-heavy tasks** -- keep search results out of main context
- [ ] **Filter verbose tool output** -- e.g. a PreToolUse hook that keeps only failing tests
- [ ] **Move domain rules to nested CLAUDE.md files** -- reduce root file size
- [ ] **Create commands for rare workflows** -- deploy, migrate, audit procedures
- [ ] **Start new sessions for new tasks** -- do not carry stale context

### Expected Savings When Fully Applied

| Strategy | Savings (source) | Effort to Implement |
|----------|:----------------:|:-------------------:|
| CLAUDE.md under 150 lines | About 3% of a 30-turn session (500 to 150 lines, derived: $0.769 vs $0.742 per Opus 5.5 session, cache-aware calculator defaults) | One-time, 15 minutes |
| Read deny rules configured | Not measured (no published figure; depends on how often Claude would open those files) | One-time, 2 minutes |
| /compact usage | 32% (Anthropic long triage run; nothing on short loops) | Ongoing habit |
| Precise file references | 1 - lines read / file length per read (50 of 2,000 lines: 97.5% fewer tokens for that read) | Ongoing habit |
| Subagent delegation | No Claude Code figure (cookbook loop: 78%) | Ongoing habit |
| Concise prompts | No published figure (Anthropic: vague requests "trigger broad scanning") | Ongoing habit |
| Nested CLAUDE.md + commands | No published figure (nested files and path-scoped rules load only when Claude reads files there) | One-time, 15 minutes |
| New sessions for new tasks | About 23% for an 80-turn day split into eight sessions (derived: $2.51 vs $1.93 on Opus 5.5); `/clear` itself costs nothing | Ongoing habit |
| **Combined** | **Not measured combined** | |

Each figure applies to its own slice of spend, so they do not simply add, and no one has published a combined measurement. Sources: the [cost-optimization guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence) (compaction), the [cost-optimization cookbook](https://platform.claude.com/cookbook/cost-optimization-cost-optimization) (subagent loop), and Claude Code's [costs page](https://code.claude.com/docs/en/costs) and [prompt-caching page](https://code.claude.com/docs/en/prompt-caching). Price your own before and after with `/usage`.

---

*Next: [Guide 03 - Model Selection](03-model-selection.md) -- when to use Opus vs Sonnet vs Haiku, with a decision tree and cost comparisons for every task type.*
