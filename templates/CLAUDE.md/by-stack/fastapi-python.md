# FastAPI + Python CLAUDE.md Template

<!-- ABOUT THIS TEMPLATE
  - ~90 lines of content (~640 tokens)
  - Optimized for FastAPI + Python projects
  - Covers: venv/poetry, endpoint patterns, Pydantic, DB, pytest
  - Copy everything below the "---" line into your project's CLAUDE.md
  - Replace all {PLACEHOLDER} values with your project specifics
  - Delete comment blocks before use to save tokens
-->

---

<!-- COPY BELOW THIS LINE INTO YOUR PROJECT'S CLAUDE.md -->

# {Project Name}

{One-sentence description of what this project does.}
Stack: Python {3.11/3.12}, FastAPI, {SQLAlchemy/Tortoise ORM}, {PostgreSQL/SQLite}
Package manager: {poetry / uv / pip}

## Commands

```bash
# Environment setup
{poetry install}                      # Install dependencies
{poetry shell}                        # Activate virtual env
# OR: source .venv/bin/activate       # If using venv directly

# Development
{uvicorn app.main:app --reload}       # Dev server (port 8000)
# Docs at http://localhost:8000/docs  # Swagger UI (auto-generated)

# Testing
{poetry run pytest}                   # Run all tests
{poetry run pytest tests/path.py}     # Single file
{poetry run pytest -k "test_name"}    # Single test by name
{poetry run pytest --cov=app}         # With coverage

# Code Quality
{poetry run ruff check .}            # Linting (Ruff)
{poetry run ruff format .}           # Formatting
{poetry run mypy app/}               # Type checking
```

## Project Structure

```
app/
├── main.py               # FastAPI app instance, startup, middleware
├── config.py             # Settings via pydantic-settings (env vars)
├── dependencies.py       # Shared FastAPI dependencies (get_db, get_user)
├── routers/              # Route modules (one per domain)
│   ├── users.py
│   └── items.py
├── models/               # SQLAlchemy/ORM models (DB tables)
├── schemas/              # Pydantic models (request/response shapes)
├── services/             # Business logic (called by routers)
├── repositories/         # Database queries (called by services)
└── utils/                # Pure helpers
migrations/               # Alembic migration files
tests/
├── conftest.py           # Fixtures (test client, test DB, factories)
├── test_users.py         # Tests mirror router structure
└── factories/            # Test data factories
```

## Endpoint Patterns

- Routers in `app/routers/`, included in `main.py` with prefix
- Use dependency injection for DB sessions, auth, pagination
- Return Pydantic `response_model` — never return ORM objects directly
- Status codes: 201 for creation, 204 for deletion, 200 for everything else

```python
# Standard endpoint pattern
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.user import UserCreate, UserResponse
from app.services.user_service import UserService
from app.dependencies import get_db

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(data: UserCreate, db=Depends(get_db)):
    return await UserService(db).create(data)

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db=Depends(get_db)):
    user = await UserService(db).get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

## Pydantic Models (Schemas)

- `{Name}Create` — request body for creation (no id)
- `{Name}Update` — partial update fields (all Optional)
- `{Name}Response` — API response shape (includes id, timestamps)
- `{Name}Base` — shared fields inherited by Create/Response
- Use `model_config = ConfigDict(from_attributes=True)` for ORM conversion

## Database Patterns

- ORM: {SQLAlchemy 2.0 async / Tortoise ORM}
- Session: injected via `Depends(get_db)` — never create sessions manually
- Migrations: {Alembic} — auto-generate with `alembic revision --autogenerate -m "description"`
- Queries go in `app/repositories/` — routers and services never write raw SQL
- Transactions: use `async with db.begin():` for multi-step operations

## Testing with pytest

- Test client: `httpx.AsyncClient` with `app` (or `TestClient` for sync)
- Fixtures in `conftest.py`: test DB, authenticated client, sample data
- Use factories for test data — not hardcoded dicts
- Mock external services with `unittest.mock.patch` or `pytest-mock`
- Name tests: `test_{action}_{expected_result}` (e.g., `test_create_user_returns_201`)

## Code Rules

- Type hints on all function signatures — enforce with mypy
- `snake_case` for functions/variables, `PascalCase` for classes
- No `*` imports — explicit imports only
- Async endpoints by default unless calling sync-only libraries
- Logging via `structlog` or stdlib `logging` — no `print()` in app code

## Do Not

- Do not put business logic in routers — delegate to services
- Do not return ORM model instances from endpoints — use Pydantic schemas
- Do not edit Alembic migration files after they have been applied
- Do not store secrets in code — use environment variables via `app/config.py`
- Do not install new dependencies without asking first

<!-- END OF TEMPLATE
  Content: ~90 lines (~640 tokens)
  Overhead per 30-turn session: ~19,200 tokens (pre-cache)
  Optimized for: correct FastAPI patterns, clear layer separation -->
