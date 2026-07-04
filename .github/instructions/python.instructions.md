# Python Implementation Instructions

## Scope

Guidelines for Python code in this project.

## Rules

- Use Python 3.12+.
- Prefer simple functions and small modules.
- Keep side effects isolated.
- Use type hints on public functions.
- Avoid premature abstractions.

## Data access

- Use sqlite3 directly.
- No ORM in the initial architecture.
- Keep SQL explicit and readable.

## Flask

- Render HTML from backend.
- Keep route handlers thin and delegate logic.
- Keep legal disclaimer visible on user-facing pages.

## AI integration

- Use provider interface contract from docs.
- Never hardcode provider credentials.
- Handle network/provider errors gracefully.
