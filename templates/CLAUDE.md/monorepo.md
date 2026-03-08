# Monorepo CLAUDE.md Template

<!-- ABOUT THIS TEMPLATE
  - ~120 lines of actual content (~850 tokens) for the ROOT CLAUDE.md
  - Optimized for multi-package workspaces (Turborepo, Nx, pnpm workspaces, etc.)
  - Includes guidance on structuring BOTH root-level and package-level CLAUDE.md files
  - Key principle: root CLAUDE.md has shared conventions, package CLAUDE.md files have specifics
  - This prevents duplicating context across packages (which would multiply token costs)
  - Copy everything below the "---" line into your project's root CLAUDE.md
  - Then create per-package CLAUDE.md files using the package template at the bottom
  - Replace all {PLACEHOLDER} values with your project specifics
  - Delete all <!-- comment --> blocks before use to save tokens

  MONOREPO CONTEXT STRATEGY:
  Claude Code loads CLAUDE.md from the current working directory AND parent directories.
  In a monorepo, this means if you are working in packages/web/, Claude loads:
    1. /CLAUDE.md (root — shared conventions)
    2. /packages/web/CLAUDE.md (package-specific)

  This is powerful but dangerous for costs: if both files are large, you pay for
  both on every turn. The strategy below keeps the root file focused on shared rules
  and each package file focused on package-specific details.
-->

---

<!-- ============================================================
     ROOT CLAUDE.md — Copy this into your monorepo root
     ============================================================ -->

# {Project Name} Monorepo

{One-sentence description. Example: "SaaS platform with web app, marketing site, API server, and shared component library."}

Monorepo tool: {Turborepo} | Package manager: {pnpm} | Node: {20.x}

## Workspace Structure

```
packages/
├── web/              # Main web application ({Next.js 14})
├── api/              # API server ({Express + tRPC})
├── ui/               # Shared component library ({React + Tailwind})
├── config/           # Shared configs (ESLint, TypeScript, Tailwind)
└── types/            # Shared TypeScript types and Zod schemas
```

## Root Commands

```bash
# Run across all packages
{pnpm build}                     # Build all packages (topological order)
{pnpm test}                      # Test all packages
{pnpm lint}                      # Lint all packages
{pnpm typecheck}                 # Type-check all packages

# Run for a specific package
{pnpm --filter web dev}          # Dev server for web
{pnpm --filter api dev}          # Dev server for api
{pnpm --filter ui storybook}     # Storybook for ui library
{pnpm --filter web test}         # Tests for web only
{pnpm --filter api test}         # Tests for api only

# Dependency management
{pnpm add -D {pkg} --filter web} # Add dev dependency to web package
{pnpm add {pkg} -w}              # Add dependency to workspace root
```

## Shared Code Conventions

These rules apply across ALL packages. Package-specific rules are in each package's own CLAUDE.md.

### TypeScript
- Strict mode in all packages — base config is in `packages/config/tsconfig.base.json`
- Named exports only — no default exports
- `interface` for object shapes, `type` for unions/intersections
- Shared types go in `packages/types/` — do not duplicate type definitions across packages

### Naming
- Files: `kebab-case.ts` for utils, `PascalCase.tsx` for components
- Variables/functions: `camelCase`
- Types/interfaces: `PascalCase`
- Constants: `SCREAMING_SNAKE_CASE`

### Testing
- Framework: {Vitest} (all packages use the same runner)
- Pattern: AAA (Arrange / Act / Assert), `describe`/`it` blocks
- Test files: colocated as `{name}.test.ts` or in `__tests__/` directory
- Shared test utilities: `packages/config/test-utils.ts`

### Import Rules
- Packages import each other via workspace protocol: `import { Button } from '@{scope}/ui'`
- Never use relative imports to reach into another package (e.g., `../../packages/ui/src/`)
- Internal package imports use path aliases: `@/components/`, `@/lib/`, `@/types/`

## Dependency Graph

```
web ──→ ui, types, config
api ──→ types, config
ui  ──→ types, config
types ──→ config
config ──→ (none)
```

Build order follows this graph. Do not introduce circular dependencies between packages.

## Shared Infrastructure

- CI: GitHub Actions — runs `turbo build test lint typecheck` on PRs
- Deploy: `web` → {Vercel}, `api` → {Railway}, `ui` → {Chromatic} (Storybook)
- Env vars: each package has its own `.env.example` — root `.env` is for shared vars only

## Do Not

- Do not duplicate types across packages — add shared types to `packages/types/`
- Do not import across packages using relative paths — use workspace protocol
- Do not add dependencies to the root `package.json` unless they are workspace-level tools
- Do not edit `packages/config/` without considering the impact on all packages
- Do not install dependencies without asking first


<!-- ============================================================
     PACKAGE-LEVEL CLAUDE.md — Copy this into each package directory
     (e.g., packages/web/CLAUDE.md, packages/api/CLAUDE.md)
     Keep each package CLAUDE.md under 40 lines to control total context size.
     ============================================================ -->

<!-- EXAMPLE: packages/web/CLAUDE.md -->

<!--
# {scope}/web

Next.js 14 App Router application. Main user-facing web app.

## Commands

```bash
pnpm dev          # Dev server on port 3000
pnpm build        # Production build
pnpm test         # Run tests
pnpm test:e2e     # Playwright E2E tests
```

## Structure

```
app/                  # Next.js App Router (pages, layouts, API routes)
src/
├── components/       # Page-specific components
├── hooks/            # Web-specific hooks (useAuth, useToast)
├── lib/              # Web-specific utilities
└── stores/           # Client-side Zustand stores
```

## Web-Specific Rules

- Server Components by default — add `'use client'` only when needed
- Use components from `@{scope}/ui` — do not create new primitives in this package
- Data fetching: server components use tRPC server caller, client components use tRPC React hooks
- Styling: Tailwind only — no CSS modules or styled-components
- Auth: use `useAuth()` hook for client, `getServerSession()` for server components

## Do Not

- Do not create generic UI components here — add them to `@{scope}/ui` instead
- Do not define types that are used by other packages — add them to `@{scope}/types`
-->


<!-- ============================================================
     EXAMPLE: packages/api/CLAUDE.md
     ============================================================ -->

<!--
# {scope}/api

Express + tRPC API server. Handles all backend logic, database access, and external integrations.

## Commands

```bash
pnpm dev            # Dev server on port 4000 with hot reload
pnpm build          # Compile TypeScript
pnpm test           # Run tests
pnpm db:migrate     # Run Prisma migrations
pnpm db:seed        # Seed dev data
```

## Structure

```
src/
├── routers/        # tRPC routers (one per domain: users, projects, billing)
├── services/       # Business logic layer
├── repositories/   # Data access layer (Prisma, Redis)
├── middleware/      # Auth, rate-limiting, logging
└── lib/            # API-specific utilities (email, stripe, s3)
prisma/
├── schema.prisma   # Database schema
└── migrations/     # Do not edit after creation
```

## API-Specific Rules

- All routes use tRPC — no raw Express route handlers
- Input validation: Zod schemas inline in router procedures
- Auth: `.protectedProcedure()` for authenticated, `.adminProcedure()` for admin
- Errors: throw `TRPCError` with proper codes — never return error objects
- Database: Prisma client only — no raw SQL except via `$queryRaw` with tagged templates

## Do Not

- Do not return Prisma models directly — map to response DTOs
- Do not edit migration files after they have been applied
-->


<!-- ============================================================
     COST ANALYSIS: Monorepo CLAUDE.md Strategy
     ============================================================

  When working in packages/web/:
    Root CLAUDE.md:    ~850 tokens (shared conventions)
    Package CLAUDE.md: ~280 tokens (web-specific)
    Total per turn:    ~1,130 tokens

  Compare to a single monolithic CLAUDE.md with everything:
    Monolithic:        ~2,800 tokens per turn (all packages' details loaded always)

  Savings per 30-turn session: (2,800 - 1,130) x 30 = 50,100 tokens
  At Sonnet 4 rates: ~$0.15 saved per session

  More importantly, Claude gets ONLY the relevant context for the package
  it is working in, which improves output quality and reduces follow-up turns.
-->
