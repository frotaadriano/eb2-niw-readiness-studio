# Testing Instructions

## Framework

- Use pytest as the primary test framework.

## Baseline coverage goals

- Scoring logic and status mapping.
- Privacy and export filtering rules.
- i18n key parity and fallback behavior.
- DB initialization and minimal schema integrity.
- AI provider contract and error paths.

## Test principles

- Keep tests deterministic and local.
- Use fake/demo fixtures only.
- Do not call external AI APIs in default test suite.
- Separate fast unit tests from optional integration tests.
