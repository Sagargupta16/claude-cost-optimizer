# Comprehensive CLAUDE.md Template

<!-- ABOUT THIS TEMPLATE
  - ~150 lines of actual content (~1,050 tokens)
  - Full-featured configuration for team projects
  - Best for: teams of 3+, projects with complex architecture, onboarding new team members
  - Includes: architecture overview, API patterns, deployment, team conventions
  - Trade-off: higher per-turn cost, but fewer convention violations and better first-pass quality
  - Copy everything below the "---" line into your project's CLAUDE.md
  - Replace all {PLACEHOLDER} values with your project specifics
  - Delete all <!-- comment --> blocks before use to save tokens
-->

---

<!-- COPY BELOW THIS LINE INTO YOUR PROJECT'S CLAUDE.md -->

# {Project Name}

{One-sentence description. Example: "Multi-tenant project management platform with real-time collaboration."}

Stack: {TypeScript, Next.js 14 (App Router), Tailwind CSS, tRPC, Prisma, PostgreSQL, Redis}
Node: {20.x} | Package manager: {pnpm} | Runtime: {Node.js}

## Commands

```bash
# Development
{pnpm dev}                    # Start Next.js dev server (port 3000)
{pnpm db:studio}              # Open Prisma Studio (port 5555)
{pnpm storybook}              # Start Storybook (port 6006)

# Building & Checking
{pnpm build}                  # Production build
{pnpm typecheck}              # TypeScript check
{pnpm lint}                   # ESLint + Prettier check
{pnpm lint:fix}               # Auto-fix lint issues

# Testing
{pnpm test}                   # All unit tests (Vitest)
{pnpm test:watch}             # Watch mode
{pnpm test -- path/to/file}   # Single file
{pnpm test:integration}       # Integration tests (needs running DB)
{pnpm test:e2e}               # Playwright E2E tests
{pnpm test:coverage}          # Coverage report

# Database
{pnpm db:migrate}             # Run pending migrations
{pnpm db:migrate:create}      # Create new migration
{pnpm db:seed}                # Seed development data
{pnpm db:reset}               # Reset DB and re-seed (DESTRUCTIVE)
```

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                   Next.js App                    │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │  Pages/   │  │  API/    │  │  Middleware    │  │
│  │  Layouts  │  │  tRPC    │  │  (auth, rbac) │  │
│  └────┬─────┘  └────┬─────┘  └───────┬───────┘  │
│       │              │                │          │
│  ┌────┴──────────────┴────────────────┴───────┐  │
│  │              Service Layer                  │  │
│  │  (business logic, validation, orchestration)│  │
│  └────────────────────┬───────────────────────┘  │
│                       │                          │
│  ┌────────────────────┴───────────────────────┐  │
│  │              Data Layer                     │  │
│  │  ┌─────────┐  ┌────────┐  ┌─────────────┐  │  │
│  │  │ Prisma  │  │ Redis  │  │ External APIs│  │  │
│  │  │ (PG)    │  │ (cache)│  │ (Stripe,etc) │  │  │
│  │  └─────────┘  └────────┘  └─────────────┘  │  │
│  └─────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

Data flow: Page/API -> Service -> Repository/Cache/External API
Auth flow: Request -> Middleware (JWT verify) -> RBAC check -> Handler

## Project Structure

```
app/                        # Next.js App Router pages and layouts
├── (auth)/                 # Auth route group (login, register, forgot-password)
├── (dashboard)/            # Authenticated dashboard routes
│   ├── projects/           # Project management pages
│   ├── settings/           # User and org settings
│   └── layout.tsx          # Dashboard shell (sidebar, header)
├── api/trpc/[trpc]/        # tRPC API handler
└── layout.tsx              # Root layout (providers, fonts, metadata)
src/
├── components/
│   ├── ui/                 # Design system primitives (Button, Dialog, Table)
│   └── features/           # Feature components (ProjectBoard, MemberList)
├── hooks/                  # Custom hooks (useAuth, useRBAC, useDebounce)
├── server/
│   ├── routers/            # tRPC routers (projects, users, billing)
│   ├── services/           # Business logic (ProjectService, BillingService)
│   ├── repositories/       # Data access (Prisma queries, Redis cache)
│   └── middleware/         # tRPC middleware (auth, logging, rate-limit)
├── lib/                    # Shared utilities (auth, validation, formatting)
├── types/                  # Shared TypeScript types
└── stores/                 # Client-side state (Zustand)
prisma/
├── schema.prisma           # Database schema
├── migrations/             # Migration files (do not edit after creation)
└── seed.ts                 # Development seed data
```

## Code Style

### TypeScript
- Strict mode, no `any` without `// eslint-disable-next-line` and justification comment
- `interface` for object shapes, `type` for unions/intersections/mapped types
- Named exports only — no default exports anywhere
- Components: `export const ComponentName = () => {}` (const arrow functions)
- Use `as const` objects instead of TypeScript enums
- Zod schemas for all external data validation (API inputs, env vars, form data)

### React / Next.js
- Server Components by default — add `'use client'` only when needed (hooks, events, browser APIs)
- Props interface named `{ComponentName}Props`, defined above the component
- Colocate related files: `Button.tsx`, `Button.test.tsx`, `Button.stories.tsx` in same directory
- Data fetching: server components use `fetch` or Prisma directly; client components use tRPC hooks
- Error boundaries at route segment level using `error.tsx` files

### Naming Conventions
- Files: `kebab-case.ts` for utils/lib, `PascalCase.tsx` for components, `camelCase.ts` for hooks
- Variables/functions: `camelCase`
- Types/interfaces/components: `PascalCase`
- Constants/env vars: `SCREAMING_SNAKE_CASE`
- Database columns: `snake_case` (Prisma maps to camelCase in code)
- API routes: `/api/v1/kebab-case-resource`

## Testing Conventions

- Unit: Vitest, AAA pattern, `describe`/`it` blocks
- Integration: Vitest + test database, transactions rolled back after each test
- E2E: Playwright, page object model pattern
- Mocking: `vi.mock()` for modules, `vi.fn()` for functions, MSW for API mocks
- Test data: factory functions in `tests/factories/` — never raw object literals
- Naming: `it('should {expected behavior} when {condition}')`
- Coverage target: 85%+ for services, 70%+ for components, 90%+ for utils

## API Patterns (tRPC)

- Routers in `src/server/routers/` — one file per resource domain
- Input validation: Zod schemas defined inline or imported from `src/types/schemas/`
- Procedures: `query` for reads, `mutation` for writes
- Error handling: throw `TRPCError` with appropriate code (NOT_FOUND, FORBIDDEN, BAD_REQUEST)
- Auth: use `.protectedProcedure()` for authenticated routes, `.adminProcedure()` for admin-only
- Pagination: cursor-based using `{ cursor, limit }` input, returns `{ items, nextCursor }`

## Database Conventions

- Schema changes: create migration with `{pnpm db:migrate:create}`, never edit existing migrations
- Relations: always define both sides of a relation in the Prisma schema
- Soft deletes: use `deletedAt DateTime?` column, filter in repository layer
- Indexes: add indexes for any column used in WHERE clauses or JOINs
- Seeding: `prisma/seed.ts` creates a consistent dev dataset — keep it idempotent

## Deployment

- Environment: {Vercel} (app) + {Supabase} (PostgreSQL) + {Upstash} (Redis)
- Branches: `main` (production), `staging` (preview), feature branches (preview deploys)
- CI: GitHub Actions runs `typecheck`, `lint`, `test`, `build` on every PR
- Env vars: see `.env.example` — production values are in Vercel dashboard
- Database migrations run automatically on deploy via `postbuild` script

## Team Conventions

- PRs require 1 approval before merge
- Commit messages: conventional commits (`feat:`, `fix:`, `chore:`, `docs:`)
- Branch naming: `{type}/{ticket-id}-{short-description}` (e.g., `feat/PROJ-123-add-teams`)
- Feature flags: use `src/lib/feature-flags.ts` — do not use environment variables for flags
- Logging: use `src/lib/logger.ts` (structured JSON logs) — never `console.log` in production code

## Do Not

- Do not edit files in `src/generated/` or `prisma/migrations/` (after creation)
- Do not install dependencies without asking — check if an existing util covers the use case
- Do not commit `.env` files, API keys, or any credentials
- Do not use `console.log` — use the structured logger
- Do not add client-side state for data that can be a server component
- Do not write raw SQL — use Prisma client; if a complex query is needed, use `$queryRaw` with a tagged template
- Do not modify CI/CD workflows without discussing with the team lead

<!-- END OF TEMPLATE
  Actual content: ~150 lines (~1,050 tokens)
  Estimated overhead per 30-turn session: ~31,500 tokens (pre-cache)
  Justified for teams: prevents convention divergence across multiple developers
  Review quarterly and trim sections that Claude consistently gets right without guidance -->
