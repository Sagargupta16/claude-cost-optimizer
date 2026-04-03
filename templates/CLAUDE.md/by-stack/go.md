# Go CLAUDE.md Template

<!-- ABOUT THIS TEMPLATE
  - ~80 lines of content (~560 tokens)
  - Optimized for Go projects using standard library and modules
  - Covers: build/test/lint commands, project layout, common patterns
  - Copy everything below the "---" line into your project's CLAUDE.md
  - Replace all {PLACEHOLDER} values with your project specifics
  - Delete comment blocks before use to save tokens
-->

---

<!-- COPY BELOW THIS LINE INTO YOUR PROJECT'S CLAUDE.md -->

# {Project Name}

{One-sentence description of what this project does.}
Stack: Go {1.22/1.23}, {net/http / Chi / Gin / Echo}, {PostgreSQL / SQLite / none}
Build: go modules

## Commands

```bash
# Development
go run ./cmd/{app}/...           # Run the application
{air}                            # Live reload (if using cosmtrek/air)

# Building
go build -o bin/{app} ./cmd/{app}/...   # Build binary
go vet ./...                            # Static analysis

# Testing
go test ./...                    # Run all tests
go test ./path/to/pkg/...       # Single package
go test -run TestFuncName ./...  # Single test by name
go test -race ./...              # Race condition detection
go test -cover ./...             # With coverage

# Code Quality
golangci-lint run                # Linting (golangci-lint)
gofmt -w .                      # Format all files
```

## Project Structure

```
cmd/
└── {app}/
    └── main.go              # Entrypoint - minimal, wires dependencies
internal/
├── config/                  # Config loading (env vars, files)
├── handler/                 # HTTP handlers (or "controller")
├── middleware/               # HTTP middleware (auth, logging, CORS)
├── model/                   # Domain types and structs
├── repository/              # Database access layer
├── service/                 # Business logic
└── {pkg}/                   # Other internal packages
pkg/                         # Public library code (if any)
migrations/                  # SQL migration files
```

## Patterns

- Accept interfaces, return structs
- Use constructor functions: `func NewUserService(repo UserRepository) *UserService`
- Errors: return `error` as the last return value, wrap with `fmt.Errorf("context: %w", err)`
- Context: pass `context.Context` as the first parameter to functions that do I/O
- Dependency injection via constructor params -- no global state, no `init()` side effects

```go
// Standard handler pattern
func (h *UserHandler) GetUser(w http.ResponseWriter, r *http.Request) {
    id := r.PathValue("id") // Go 1.22+ net/http
    user, err := h.service.GetByID(r.Context(), id)
    if err != nil {
        http.Error(w, "not found", http.StatusNotFound)
        return
    }
    json.NewEncoder(w).Encode(user)
}
```

## Testing Patterns

- Table-driven tests with `t.Run()` subtests
- Use `testify/assert` or standard `t.Errorf` -- match existing test style
- Test files: `{name}_test.go` in the same package
- Mocks: interfaces + manual mock structs (or `gomock` / `testify/mock` if already in use)
- Integration tests behind build tag: `//go:build integration`

## Code Rules

- `gofmt` is non-negotiable -- all code must be formatted
- Exported names get doc comments: `// UserService handles user operations.`
- No `panic` in library/service code -- return errors
- No unused imports or variables (compiler enforces this)
- Prefer standard library over third-party when feasible

## Do Not

- Do not use global mutable state or `init()` for side effects
- Do not ignore errors with `_ = someFunc()` unless explicitly justified
- Do not add dependencies without asking first -- check if stdlib covers the need
- Do not use `interface{}` / `any` when a concrete type or generic will do
- Do not modify `go.mod` / `go.sum` manually -- use `go get` and `go mod tidy`

<!-- END OF TEMPLATE
  Content: ~80 lines (~560 tokens)
  Overhead per 30-turn session: ~16,800 tokens (pre-cache)
  Optimized for: idiomatic Go, clear project layout, standard tooling -->
