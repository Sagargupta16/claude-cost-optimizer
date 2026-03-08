# React + Vite CLAUDE.md Template

<!-- ABOUT THIS TEMPLATE
  - ~90 lines of content (~650 tokens)
  - Optimized for React 18/19 + Vite + Tailwind CSS projects
  - Covers: dev/build/test commands, component patterns, state, routing, conventions
  - Copy everything below the "---" line into your project's CLAUDE.md
  - Replace all {PLACEHOLDER} values with your project specifics
  - Delete comment blocks before use to save tokens
-->

---

<!-- COPY BELOW THIS LINE INTO YOUR PROJECT'S CLAUDE.md -->

# {Project Name}

{One-sentence description of what this project does.}
Stack: React {18/19}, Vite {5.x}, TypeScript, Tailwind CSS {3.x/4.x}
Node: {20.x} | Package manager: {pnpm}

## Commands

```bash
# Development
{pnpm dev}                # Vite dev server (port 5173)

# Building
{pnpm build}              # TypeScript check + Vite production build
{pnpm preview}            # Preview production build locally

# Testing
{pnpm test}               # Vitest watch mode
{pnpm test:run}           # Vitest single run (CI)
{pnpm test -- src/path/to/file.test.tsx}  # Single file

# Code Quality
{pnpm lint}               # ESLint
{pnpm lint:fix}           # ESLint auto-fix
{pnpm typecheck}          # tsc --noEmit
```

## Project Structure

```
src/
├── components/           # Reusable UI components (PascalCase dirs)
│   ├── ui/               # Primitives: Button, Input, Modal, Card
│   └── features/         # Domain components: UserCard, InvoiceTable
├── pages/                # Route-level components (one per route)
├── hooks/                # Custom hooks (useAuth, useDebounce)
├── stores/               # {Zustand/Jotai} state stores
├── services/             # API calls and business logic
├── types/                # Shared TypeScript types
├── utils/                # Pure helper functions
├── lib/                  # Third-party config wrappers (axios, dayjs)
└── assets/               # Static assets (images, fonts)
```

## Component Patterns

- Functional components only with `const` arrow syntax
- Props interface above component, named `{ComponentName}Props`
- Co-locate component, styles, tests, and types in one directory when complex
- Use `React.lazy()` for route-level code splitting

```tsx
// Standard component pattern
export interface ButtonProps {
  variant?: 'primary' | 'secondary';
  children: React.ReactNode;
  onClick?: () => void;
}

export const Button = ({ variant = 'primary', children, onClick }: ButtonProps) => {
  return (
    <button className={cn('btn', `btn-${variant}`)} onClick={onClick}>
      {children}
    </button>
  );
};
```

## State Management

- Local UI state: `useState` / `useReducer`
- Shared client state: {Zustand} stores in `src/stores/`
- Server state: {TanStack Query} for API data fetching and caching
- Form state: {React Hook Form} + {Zod} validation
- URL state: search params via {React Router} `useSearchParams`

## Routing

- Router: {React Router v6} with `createBrowserRouter`
- Routes defined in `src/routes.tsx` (or `src/router/`)
- Lazy-loaded route components for bundle splitting
- Protected routes via `<AuthGuard>` wrapper component
- Layout routes for shared headers/sidebars

## Styling (Tailwind CSS)

- Utility-first — use Tailwind classes directly in JSX
- No inline `style` props or CSS-in-JS
- Custom design tokens in `tailwind.config.{js/ts}`
- Use `cn()` utility (clsx + tailwind-merge) for conditional classes
- Responsive: mobile-first with `sm:`, `md:`, `lg:` breakpoints

## Code Rules

- Named exports only — no default exports
- `interface` for object shapes, `type` for unions/intersections
- No `any` — use `unknown` and narrow with type guards
- Files: `kebab-case.ts` for utils, `PascalCase.tsx` for components
- Tests: `{name}.test.tsx` co-located or in `tests/` mirror

## Do Not

- Do not use class components
- Do not import from `src/` using relative paths deeper than two levels — use `@/` alias
- Do not add global CSS — use Tailwind utilities or component-scoped styles
- Do not install new dependencies without asking first
- Do not modify `vite.config.ts` without discussing impact on build

<!-- END OF TEMPLATE
  Content: ~90 lines (~650 tokens)
  Overhead per 30-turn session: ~19,500 tokens (pre-cache)
  Optimized for: fast component work, clear conventions, minimal ambiguity -->
