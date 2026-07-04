# ADR 0003 - Pluggable AI Providers

## Status

Accepted

## Context

O projeto deve evitar lock-in e permitir operacao local (mock/ollama) e cloud (OpenAI/Azure OpenAI).

## Decision

Definir contrato unico de provider e implementar adaptadores por provedor.

## Consequences

- Pro: flexibilidade de custo, privacidade e disponibilidade.
- Pro: facilidade para testes com provider mock.
- Con: exige disciplina de contrato e tratamento uniforme de erros.
