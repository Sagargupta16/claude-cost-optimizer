# Django + Python CLAUDE.md Template

<!-- ABOUT THIS TEMPLATE
  - ~85 lines of content (~600 tokens)
  - Optimized for Django projects with DRF (optional) and pytest
  - Covers: manage.py commands, project layout, views, models, testing
  - Copy everything below the "---" line into your project's CLAUDE.md
  - Replace all {PLACEHOLDER} values with your project specifics
  - Delete comment blocks before use to save tokens
-->

---

<!-- COPY BELOW THIS LINE INTO YOUR PROJECT'S CLAUDE.md -->

# {Project Name}

{One-sentence description of what this project does.}
Stack: Python {3.11/3.12}, Django {5.x}, {Django REST Framework / none}, {PostgreSQL / SQLite}
Package manager: {uv / poetry / pip}

## Commands

```bash
# Environment
{uv sync}                                # Install dependencies
source .venv/bin/activate                 # Activate virtual env

# Development
python manage.py runserver               # Dev server (port 8000)
python manage.py shell_plus              # Enhanced Django shell (django-extensions)

# Database
python manage.py makemigrations          # Generate migration from model changes
python manage.py migrate                 # Apply migrations
python manage.py showmigrations          # List migration status

# Testing
pytest                                   # Run all tests (pytest-django)
pytest apps/{app}/tests/                 # Single app
pytest -k "test_name"                    # Single test by name
pytest --cov=apps                        # With coverage

# Code Quality
ruff check .                             # Linting
ruff format .                            # Formatting
mypy apps/                               # Type checking
```

## Project Structure

```
{project}/
├── settings/
│   ├── base.py              # Shared settings
│   ├── local.py             # Dev overrides (DEBUG=True)
│   └── production.py        # Production settings
├── urls.py                  # Root URL configuration
└── wsgi.py
apps/
├── {app_name}/
│   ├── models.py            # Django models (one model per concept)
│   ├── views.py             # Views or ViewSets (DRF)
│   ├── serializers.py       # DRF serializers (if API)
│   ├── urls.py              # App-level URL patterns
│   ├── admin.py             # Admin site registration
│   ├── services.py          # Business logic (keep views thin)
│   ├── selectors.py         # Complex queries (keep models thin)
│   └── tests/
│       ├── test_views.py
│       ├── test_models.py
│       └── factories.py     # Model factories (factory_boy)
templates/                   # Django templates (if server-rendered)
static/                      # Static files
```

## View Patterns

- Keep views thin -- delegate business logic to `services.py`
- Use class-based views for CRUD, function views for custom logic
- DRF: prefer `ModelViewSet` for standard CRUD, `APIView` for custom endpoints

```python
# DRF ViewSet pattern
from rest_framework import viewsets, status
from rest_framework.response import Response

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def perform_create(self, serializer):
        UserService.create_user(serializer.validated_data)
```

## Model Conventions

- One model per business concept -- split large models into separate files in `models/` dir
- Use `verbose_name` and `verbose_name_plural` in `Meta`
- Custom managers for complex querysets: `User.objects.active()`
- Always set `ordering` in `Meta` or queries -- never rely on implicit DB order
- Indexes: add `db_index=True` or `Meta.indexes` for fields used in filters/lookups

## Testing with pytest-django

- Use `pytest-django` with `@pytest.mark.django_db` for tests that hit the database
- Factories via `factory_boy` -- not fixtures or hardcoded dicts
- Test client: `client` fixture (Django test client) or `api_client` (DRF)
- Name tests: `test_{action}_{expected}` (e.g., `test_create_user_returns_201`)

## Code Rules

- Type hints on all function signatures
- `snake_case` for everything except classes (`PascalCase`)
- Settings from environment variables -- never hardcode secrets
- Async views only if the project already uses ASGI -- do not mix WSGI and async

## Do Not

- Do not put business logic in views or models -- use `services.py`
- Do not write raw SQL unless ORM cannot express the query
- Do not edit or squash migrations that have been applied to any environment
- Do not store secrets in settings files -- use env vars via `django-environ` or `pydantic-settings`
- Do not install new dependencies without asking first

<!-- END OF TEMPLATE
  Content: ~85 lines (~600 tokens)
  Overhead per 30-turn session: ~18,000 tokens (pre-cache)
  Optimized for: Django conventions, thin views, service layer pattern -->
