# ADR 0002 - Flask with Backend-rendered HTML/CSS

## Status

Accepted

## Context

O MVP exige velocidade de entrega, baixa complexidade e facilidade de manutencao.

## Decision

Usar Flask com HTML/CSS renderizado no backend, sem SPA no inicio.

## Consequences

- Pro: curva de aprendizado menor e stack enxuta.
- Pro: menos superficie para bugs de sincronizacao frontend/backend.
- Con: interacoes ricas podem demandar evolucao futura.
