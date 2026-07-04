# ADR 0001 - Local-first with SQLite

## Status

Accepted

## Context

O projeto precisa ser simples, portavel e adequado para estudo e portfolio publico, com minimo atrito de setup.

## Decision

Adotar SQLite local como armazenamento padrao no MVP.

## Consequences

- Pro: setup rapido, sem infra externa.
- Pro: reforca privacidade por manter dados locais.
- Con: limita concorrencia e cenarios multiusuario.
