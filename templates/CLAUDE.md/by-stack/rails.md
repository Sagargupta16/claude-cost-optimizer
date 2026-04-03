# Ruby on Rails CLAUDE.md Template

<!-- ABOUT THIS TEMPLATE
  - ~80 lines of content (~570 tokens)
  - Optimized for Rails 7+ projects with RSpec
  - Covers: rails commands, project layout, conventions, testing
  - Copy everything below the "---" line into your project's CLAUDE.md
  - Replace all {PLACEHOLDER} values with your project specifics
  - Delete comment blocks before use to save tokens
-->

---

<!-- COPY BELOW THIS LINE INTO YOUR PROJECT'S CLAUDE.md -->

# {Project Name}

{One-sentence description of what this project does.}
Stack: Ruby {3.2/3.3}, Rails {7.x/8.x}, {PostgreSQL / SQLite}, {Hotwire / React / API-only}
Package manager: Bundler

## Commands

```bash
# Setup
bundle install                           # Install gems
bin/rails db:setup                       # Create DB, load schema, seed

# Development
bin/rails server                         # Dev server (port 3000)
bin/rails console                        # Rails console (IRB)
bin/rails routes                         # List all routes

# Database
bin/rails db:migrate                     # Run pending migrations
bin/rails db:rollback                    # Undo last migration
bin/rails db:seed                        # Load seed data
bin/rails generate migration AddFieldToTable field:type  # Generate migration

# Testing
bundle exec rspec                        # Run all tests
bundle exec rspec spec/models/           # Single directory
bundle exec rspec spec/models/user_spec.rb        # Single file
bundle exec rspec spec/models/user_spec.rb:42     # Single test (by line)

# Code Quality
bundle exec rubocop                      # Linting
bundle exec rubocop -a                   # Auto-fix safe corrections
```

## Project Structure

```
app/
├── controllers/             # Thin controllers -- delegate to services
│   └── api/v1/              # API versioning (if API)
├── models/                  # ActiveRecord models and validations
├── views/                   # ERB/Haml templates (or jbuilder for JSON)
├── services/                # Business logic (app/services/)
├── serializers/             # JSON serializers (ActiveModel or Blueprinter)
├── jobs/                    # Background jobs (Sidekiq / Solid Queue)
├── mailers/                 # Email delivery
└── helpers/                 # View helpers
config/
├── routes.rb                # Route definitions
├── database.yml             # DB config (per-environment)
└── initializers/            # Boot-time configuration
db/
├── migrate/                 # Migration files (timestamped)
├── schema.rb                # Auto-generated schema snapshot
└── seeds.rb                 # Seed data
spec/                        # RSpec tests mirror app/ structure
```

## Conventions

- Fat models, skinny controllers -- but extract to services when models get large
- RESTful routes: prefer `resources` and nested `resources` in `routes.rb`
- Strong parameters in controllers: `params.require(:user).permit(:name, :email)`
- Callbacks: use sparingly and only for model-level concerns (not business logic)
- Scopes for reusable queries: `scope :active, -> { where(active: true) }`

```ruby
# Standard controller pattern
class Api::V1::UsersController < ApplicationController
  def create
    result = UserService.new.create(user_params)
    if result.success?
      render json: UserSerializer.new(result.user), status: :created
    else
      render json: { errors: result.errors }, status: :unprocessable_entity
    end
  end

  private

  def user_params
    params.require(:user).permit(:name, :email, :role)
  end
end
```

## Testing with RSpec

- Use `FactoryBot` for test data -- not fixtures
- Request specs for API endpoints, model specs for validations/scopes
- `let` and `let!` for test setup, `before` blocks for shared state
- Use `shared_examples` for common behavior across specs
- Name tests: `describe "#method"` and `it "does expected thing"`

## Code Rules

- `snake_case` for methods/variables, `PascalCase` for classes, `SCREAMING_SNAKE` for constants
- Rubocop must pass -- follow the project's `.rubocop.yml`
- No `puts` or `p` in app code -- use `Rails.logger`
- Secrets via `credentials.yml.enc` or environment variables -- never in source

## Do Not

- Do not put business logic in controllers -- extract to services
- Do not skip validations with `save(validate: false)` unless explicitly justified
- Do not edit old migrations -- create a new migration instead
- Do not use `update_column` / `update_columns` unless you intentionally want to skip callbacks
- Do not install new gems without asking first

<!-- END OF TEMPLATE
  Content: ~80 lines (~570 tokens)
  Overhead per 30-turn session: ~17,100 tokens (pre-cache)
  Optimized for: Rails conventions, service layer pattern, RSpec workflow -->
