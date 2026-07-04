# 04 - Implementation Plan

## Ordem de implementacao

1. Estrutura de projeto, docs e harness de testes.
2. Banco SQLite e script de seed/reset demo.
3. Dashboard basico e assessment local.
4. CRUD de evidencias, gaps e tarefas.
5. Proposed endeavor e exportacao inicial.
6. i18n completo PT-BR/EN-US.
7. Providers de IA plugaveis e regras de privacidade.
8. Harden de testes, CI e polish de portfolio.

## Dependencias

- Python 3.12+
- Flask
- pytest
- sqlite3 (stdlib)
- requests (para futuros providers HTTP)
- python-dotenv

## Riscos

- Escopo crescer alem do MVP devido a complexidade de dominio.
- Confusao entre ferramenta educacional e aconselhamento juridico.
- Risco de uso incorreto de dados sensiveis em repo publico.
- Dependencia de providers externos para analises online.

## Decisoes tecnicas

- Monolito Flask inicial para reduzir atrito.
- Sem ORM no inicio para previsibilidade e simplicidade.
- Contrato de provider para IA em camada separada.
- Local-first como padrao de privacidade e custo.

## Checkpoints

1. Checkpoint A: estrutura + docs + CI verde.
2. Checkpoint B: schema SQLite + seed demo + testes DB.
3. Checkpoint C: assessment e dashboard com disclaimers.
4. Checkpoint D: fluxo de evidencias/gaps/roadmap funcional.
5. Checkpoint E: i18n validado por testes.
6. Checkpoint F: providers + filtros de privacidade validados.
7. Checkpoint G: README final e narrativa de portfolio consolidada.
8. Checkpoint H: polish final com docs coerentes e orientacao de portfolio publico.
