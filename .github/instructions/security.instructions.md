# Security Instructions

## Secret handling

- Never commit `.env` or real credentials.
- Keep `.env.example` as the only tracked environment template.
- Read secrets from environment variables.

## Data handling

- Treat evidence data as potentially sensitive.
- Keep real personal/immigration records out of public repository.
- Use fake/demo fixtures for tests and examples.

## AI providers

- Do not send private evidence to external providers.
- Gate outbound payloads with privacy filters.
- Log only metadata required for debugging.

## Legal safety

- Do not generate legal advice.
- Keep non-legal disclaimer visible in app and exported reports.
