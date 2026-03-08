# Next.js App Router CLAUDE.md Template

<!-- ABOUT THIS TEMPLATE
  - ~95 lines of content (~680 tokens)
  - Optimized for Next.js 14+ with App Router
  - Covers: dev commands, server/client components, data fetching, routing, middleware
  - Copy everything below the "---" line into your project's CLAUDE.md
  - Replace all {PLACEHOLDER} values with your project specifics
  - Delete comment blocks before use to save tokens
-->

---

<!-- COPY BELOW THIS LINE INTO YOUR PROJECT'S CLAUDE.md -->

# {Project Name}

{One-sentence description of what this project does.}
Stack: Next.js {14/15}, React {18/19}, TypeScript, Tailwind CSS
Node: {20.x} | Package manager: {pnpm}

## Commands

```bash
# Development
{pnpm dev}                # Next.js dev server (port 3000)

# Building
{pnpm build}              # Production build
{pnpm start}              # Run production build locally

# Testing
{pnpm test}               # Vitest unit tests
{pnpm test:e2e}           # Playwright E2E
{pnpm test -- path/to/file.test.ts}  # Single test file

# Code Quality
{pnpm lint}               # next lint (ESLint)
{pnpm typecheck}          # tsc --noEmit
```

## Project Structure

```
app/
├── (auth)/               # Route group — shared auth layout
│   ├── login/page.tsx
│   └── register/page.tsx
├── (dashboard)/          # Route group — shared dashboard layout
│   ├── layout.tsx
│   └── settings/page.tsx
├── api/                  # Route Handlers (API endpoints)
│   └── users/route.ts
├── layout.tsx            # Root layout
├── page.tsx              # Home page
└── error.tsx             # Error boundary
src/
├── components/           # Shared components
│   ├── ui/               # Primitives (Button, Input, Modal)
│   └── features/         # Domain components
├── lib/                  # Utilities, DB client, auth config
├── actions/              # Server Actions
├── types/                # Shared TypeScript types
└── hooks/                # Client-side custom hooks
```

## Server vs Client Components

**Default is Server Component.** Only add `'use client'` when you need:
- `useState`, `useEffect`, `useReducer`, or other React hooks
- Browser APIs (`window`, `localStorage`, `IntersectionObserver`)
- Event handlers (`onClick`, `onChange`, `onSubmit`)
- Class components or libraries that use them

Rules:
- Keep `'use client'` boundary as low in the tree as possible
- Server Components can import Client Components (not vice versa)
- Pass server data to client components via props, not by importing server code
- Never put `'use client'` on layout or page files unless truly required

## Data Fetching Patterns

- **Server Components**: `async` component with direct `fetch()` or DB queries
- **Server Actions**: `'use server'` functions in `src/actions/` for mutations
- **Route Handlers**: `app/api/*/route.ts` for webhook/external API endpoints
- **Client fetching**: {TanStack Query / SWR} only when real-time updates needed

```tsx
// Server Component data fetching (preferred)
export default async function UsersPage() {
  const users = await db.user.findMany();
  return <UserList users={users} />;
}

// Server Action for mutations
'use server';
export async function createUser(formData: FormData) {
  await db.user.create({ data: { name: formData.get('name') as string } });
  revalidatePath('/users');
}
```

## Routing Conventions

- `page.tsx` — route UI (required to make a route accessible)
- `layout.tsx` — shared UI wrapping child routes (persists across navigation)
- `loading.tsx` — Suspense fallback for the route segment
- `error.tsx` — error boundary for the route segment
- `not-found.tsx` — 404 UI for the segment
- Route groups `(name)/` for organization without affecting URL
- Dynamic routes: `[id]/`, catch-all: `[...slug]/`, optional: `[[...slug]]/`
- Parallel routes `@slot/` and intercepting routes `(.)path/` used sparingly

## Middleware

- File: `middleware.ts` at project root (or `src/middleware.ts`)
- Runs on Edge Runtime — no Node.js APIs (no `fs`, no native modules)
- Used for: auth redirects, locale detection, request rewriting
- Keep logic minimal — delegate heavy work to route handlers

## Code Rules

- Named exports for components, default export only for `page.tsx` / `layout.tsx`
- `interface` for props, `type` for unions
- Styling: Tailwind utility classes, `cn()` helper for conditionals
- No `any` types — use `unknown` + type narrowing
- Files: `kebab-case.ts` for utils, `PascalCase.tsx` only for component-only files

## Do Not

- Do not use `getServerSideProps` / `getStaticProps` — those are Pages Router (legacy)
- Do not put `'use client'` on files that don't need interactivity
- Do not call Server Actions from Server Components — use them in forms or Client Components
- Do not install new dependencies without asking first
- Do not modify `next.config.{js/mjs}` without discussing impact

<!-- END OF TEMPLATE
  Content: ~95 lines (~680 tokens)
  Overhead per 30-turn session: ~20,400 tokens (pre-cache)
  Optimized for: correct server/client boundaries, modern App Router patterns -->
