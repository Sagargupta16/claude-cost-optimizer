# Rust CLAUDE.md Template

<!-- ABOUT THIS TEMPLATE
  - ~80 lines of content (~570 tokens)
  - Optimized for Rust projects using Cargo
  - Covers: cargo commands, project layout, error handling, testing
  - Copy everything below the "---" line into your project's CLAUDE.md
  - Replace all {PLACEHOLDER} values with your project specifics
  - Delete comment blocks before use to save tokens
-->

---

<!-- COPY BELOW THIS LINE INTO YOUR PROJECT'S CLAUDE.md -->

# {Project Name}

{One-sentence description of what this project does.}
Stack: Rust {stable / 1.78+}, {Actix-web / Axum / Tokio / none}, {SQLx / Diesel / none}
Build: Cargo

## Commands

```bash
# Development
cargo run                        # Run the binary
cargo run -- --flag value        # Run with arguments
cargo watch -x run               # Auto-rebuild on changes (cargo-watch)

# Building
cargo build                      # Debug build
cargo build --release            # Optimized release build

# Testing
cargo test                       # Run all tests
cargo test module_name           # Tests in a specific module
cargo test test_func_name        # Single test by name
cargo test -- --nocapture        # Show println! output in tests

# Code Quality
cargo clippy -- -D warnings      # Lint (treat warnings as errors)
cargo fmt                        # Format all code (rustfmt)
cargo fmt -- --check             # Check formatting without changes
cargo doc --open                 # Generate and open docs
```

## Project Structure

```
src/
├── main.rs                  # Entrypoint (binary) or lib.rs (library)
├── config.rs                # Configuration (env vars, files)
├── error.rs                 # Custom error types and From impls
├── handlers/                # HTTP handlers / request handlers
│   └── mod.rs
├── models/                  # Domain structs and data types
│   └── mod.rs
├── db/                      # Database access layer
│   └── mod.rs
├── services/                # Business logic
│   └── mod.rs
└── utils/                   # Shared helpers
tests/                       # Integration tests (separate from unit tests)
```

## Error Handling

- Define a crate-level `AppError` enum in `src/error.rs`
- Implement `From<T>` for common error types (sqlx, io, serde) so `?` works
- Use `thiserror` for library errors, `anyhow` for application errors (match existing choice)
- Never `.unwrap()` in production code -- use `?` or explicit error handling

```rust
// Standard error pattern
#[derive(Debug, thiserror::Error)]
pub enum AppError {
    #[error("not found: {0}")]
    NotFound(String),
    #[error("database error: {0}")]
    Database(#[from] sqlx::Error),
    #[error("internal error: {0}")]
    Internal(String),
}
```

## Patterns

- Prefer borrowing (`&str`, `&[T]`) over owned types in function parameters
- Use `impl Trait` for return types when the concrete type is complex
- Async: use `async fn` + `tokio` runtime -- match existing async runtime choice
- Builder pattern for complex struct construction
- Newtype pattern (`struct UserId(Uuid)`) for type safety on IDs

## Testing Patterns

- Unit tests: `#[cfg(test)] mod tests` at the bottom of each source file
- Integration tests: `tests/` directory, each file is a separate test binary
- Use `#[tokio::test]` for async tests
- Test helpers in `tests/common/mod.rs`
- Fixtures: build test data with helper functions, not hardcoded literals

## Code Rules

- `cargo fmt` is non-negotiable -- all code must be formatted
- `cargo clippy` must pass with no warnings
- All public items get `///` doc comments
- Use `snake_case` for functions/variables, `PascalCase` for types, `SCREAMING_SNAKE` for constants
- Prefer `&str` over `String` in function signatures unless ownership is needed

## Do Not

- Do not use `.unwrap()` or `.expect()` in non-test code
- Do not use `unsafe` without a `// SAFETY:` comment explaining why it is sound
- Do not add dependencies without asking first -- check if std covers the need
- Do not manually edit `Cargo.lock` -- let Cargo manage it
- Do not suppress Clippy warnings without justification

<!-- END OF TEMPLATE
  Content: ~80 lines (~570 tokens)
  Overhead per 30-turn session: ~17,100 tokens (pre-cache)
  Optimized for: idiomatic Rust, strict correctness, standard Cargo workflow -->
