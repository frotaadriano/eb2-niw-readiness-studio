# Copilot Instructions for EB2-NIW Readiness Studio

This repository follows a local-first and spec-driven architecture.

## Architectural Guardrails

- Preserve local-first behavior: user data should remain local by default.
- Keep Flask + SQLite as the core stack.
- Use backend-rendered HTML/CSS (server-side rendering).
- Do not introduce an ORM in the initial implementation.
- Prefer direct SQL with explicit migrations/scripts.

## Product and Legal Boundaries

- Never provide legal or immigration advice.
- Never promise approval outcomes.
- Never compute real approval probabilities.
- Keep educational and organizational disclaimers visible in UI and docs.

## Security and Privacy Rules

- Never hardcode secrets, tokens, or credentials.
- Use environment variables for provider configuration.
- Never commit personal data, immigration documents, or sensitive evidence.
- Keep demo data fake/synthetic.

## Internationalization

- Preserve PT-BR and EN-US support.
- Add new UI copy through locale JSON files.
- Avoid hardcoded user-facing strings when translatable text is expected.

## Engineering Quality

- Add or update tests for critical behavior.
- Keep code simple, readable, and testable.
- Update documentation when behavior or architecture changes.
- Prefer explicit contracts and predictable error handling.
