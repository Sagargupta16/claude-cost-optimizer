# MERN Stack CLAUDE.md Template

<!-- ABOUT THIS TEMPLATE
  - ~95 lines of content (~680 tokens)
  - Optimized for MongoDB + Express + React + Node.js projects
  - Covers: server/client commands, API patterns, auth, Mongoose, React conventions
  - Copy everything below the "---" line into your project's CLAUDE.md
  - Replace all {PLACEHOLDER} values with your project specifics
  - Delete comment blocks before use to save tokens
-->

---

<!-- COPY BELOW THIS LINE INTO YOUR PROJECT'S CLAUDE.md -->

# {Project Name}

{One-sentence description of what this project does.}
Stack: MongoDB, Express {4.x}, React {18/19}, Node.js {20.x}, TypeScript
Package manager: {npm/pnpm} | Monorepo: {yes/no}

## Commands

```bash
# Server (Express API)
{cd server && npm run dev}         # Nodemon dev server (port 4000)
{cd server && npm run build}       # TypeScript compile
{cd server && npm test}            # Jest tests

# Client (React)
{cd client && npm run dev}         # Vite dev server (port 5173)
{cd client && npm run build}       # Production build
{cd client && npm test}            # Vitest tests

# Both (from root)
{npm run dev}                      # Concurrently start server + client
{npm run test:all}                 # Run all tests

# Database
{npm run db:seed}                  # Seed MongoDB with sample data
```

## Project Structure

```
server/
├── src/
│   ├── app.ts                # Express app setup, middleware
│   ├── server.ts             # Entry point, DB connection, listen
│   ├── config/               # Environment config, constants
│   ├── routes/               # Express routers (one per resource)
│   ├── controllers/          # Request handlers (called by routes)
│   ├── services/             # Business logic (called by controllers)
│   ├── models/               # Mongoose schemas and models
│   ├── middleware/            # Auth, validation, error handler
│   ├── types/                # Shared TypeScript types
│   └── utils/                # Helpers (logger, email, tokens)
│
client/
├── src/
│   ├── components/           # React components
│   │   ├── ui/               # Generic: Button, Modal, Input
│   │   └── features/         # Domain: UserProfile, PostCard
│   ├── pages/                # Route-level page components
│   ├── hooks/                # Custom React hooks
│   ├── services/             # API client functions (axios calls)
│   ├── stores/               # {Zustand/Context} state management
│   ├── types/                # Client TypeScript types
│   └── utils/                # Client helpers
```

## API Patterns (Express)

- RESTful: `GET/POST/PUT/PATCH/DELETE /api/v1/{resource}`
- Route -> Controller -> Service -> Model (strict layer separation)
- Validation: {Zod/Joi} schemas in middleware, validated before controller
- Error responses: `{ success: false, error: { code, message } }`
- Success responses: `{ success: true, data: {...}, meta?: {pagination} }`
- Pagination: `?page=1&limit=20` — default limit 20, max 100

```typescript
// Standard route pattern
router.get('/', validate(listUsersSchema), userController.list);
router.post('/', validate(createUserSchema), userController.create);
router.get('/:id', userController.getById);
router.patch('/:id', validate(updateUserSchema), userController.update);
router.delete('/:id', userController.delete);
```

## Auth Pattern

- Strategy: {JWT access + refresh tokens / session-based}
- Access token: short-lived ({15 min}), sent in `Authorization: Bearer <token>`
- Refresh token: long-lived ({7 days}), httpOnly cookie
- Middleware: `authMiddleware` verifies token, attaches `req.user`
- Password hashing: bcrypt with salt rounds {12}
- Protected routes: `router.use(authMiddleware)` on router group

## Mongoose Models

- Define schema and model in the same file in `server/src/models/`
- Use TypeScript interface for document type
- Timestamps: always enable `{ timestamps: true }`
- Indexes: define in schema for frequent query fields
- Virtuals for computed fields, pre-hooks for hashing/sanitization
- Never expose `__v` or sensitive fields — use `toJSON` transform

```typescript
// Standard Mongoose model
const userSchema = new Schema<IUser>({
  email: { type: String, required: true, unique: true, lowercase: true },
  password: { type: String, required: true, select: false },
  role: { type: String, enum: ['user', 'admin'], default: 'user' },
}, { timestamps: true });

userSchema.pre('save', async function() { /* hash password */ });
userSchema.methods.comparePassword = async function(candidate: string) { /* ... */ };
export const User = model<IUser>('User', userSchema);
```

## React Conventions (Client)

- Functional components with `const` arrow syntax, named exports
- API calls in `client/src/services/` via axios instance with interceptors
- Auth state in context/store — token refresh handled by axios interceptor
- Styling: {Tailwind CSS} utility classes
- Forms: {React Hook Form} + {Zod} for validation
- Routing: {React Router v6} with protected route wrapper

## Code Rules

- TypeScript strict mode on both server and client
- Named exports only (except Mongoose models)
- `interface` for object shapes, `type` for unions
- No `any` — use `unknown` and narrow
- Server logging via structured logger — no `console.log` in production

## Do Not

- Do not put business logic in controllers — delegate to services
- Do not query MongoDB directly in routes or controllers — use service/model layer
- Do not store JWT secrets or DB credentials in code — use env vars
- Do not install new dependencies without asking first
- Do not modify shared types without checking both server and client usage

<!-- END OF TEMPLATE
  Content: ~95 lines (~680 tokens)
  Overhead per 30-turn session: ~20,400 tokens (pre-cache)
  Optimized for: clear server/client separation, consistent API patterns -->
