# EB2-NIW Readiness Studio

[PT-BR](#pt-br) | [EN-US](#en-us)

## PT-BR

Aplicação web local-first para organização de prontidão EB-2/NIW, construída com Python, Flask, SQLite e HTML/CSS renderizado no backend.

### Aviso importante

Este projeto e educacional e organizacional.
Nao fornece aconselhamento juridico ou imigratorio.
Nao promete aprovacao.
Nao calcula chance real de aprovacao.

### Objetivo

- Estruturar evidencias profissionais, lacunas e roadmap de evolucao.
- Apoiar organizacao de autoridade tecnica, publicacoes e projetos publicos.
- Permitir analises assistidas por IA com arquitetura plugavel.
- Demonstrar boas praticas de engenharia para portfolio tecnico publico.

### Stack base

- Python 3.11+
- Flask
- SQLite (local-first)
- Pytest
- i18n PT-BR/EN-US por arquivos JSON

### Como executar

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Acesse: http://127.0.0.1:5000

Ao iniciar com `python app.py`, o banco SQLite local e criado automaticamente em `data/app.db` com schema inicial e seed idempotente da Fase 1.

### Como rodar testes

```bash
pytest -q
```

### Estrutura

- `docs/`: especificacao, arquitetura, plano e ADRs.
- `tests/`: harness inicial com regras criticas.
- `scripts/`: utilitarios de smoke test, reset e export demo.
- `locales/`: internacionalizacao PT-BR e EN-US.

### Status atual

Fases 2, 3 e 4 implementadas: dashboard/assessment, gestao operacional e modulos de narrativa/autoridade.

- Rotas: `/dashboard`, `/assessment`, `/niw`, `/evidences`, `/roadmap`, `/gaps`, `/proposed-endeavor`, `/authority`, `/github-projects`, `/linkedin-content`, `/recommenders`, `/report/export`.
- CRUD de evidencias com tipo, categoria, relevancia, criterio relacionado, status e flag de envio para IA.
- CRUD de tarefas de roadmap com horizonte, prioridade, status, data alvo, esforco e impacto.
- Modulo Proposed Endeavor Builder com versao curta/longa, relevancia, impacto esperado e status.
- Modulo de Autoridade Tecnica com plano de artigos, talks, comunidades e evidencias publicas.
- CRUD de projetos GitHub, conteudos LinkedIn e recomendadores com badges de status.
- Exportacao de relatorio organizacional JSON com filtro automatico de evidencias privadas.
- Consolidacao automatica de gaps com recomendacoes de acao.

### Privacidade e dados

- Use apenas dados fake/demo neste repositorio publico.
- Nao versione dados pessoais, documentos reais ou segredos.
- Nao hardcode API keys; use variaveis de ambiente.

---

## EN-US

Local-first web application to organize EB-2/NIW readiness using Python, Flask, SQLite, and backend-rendered HTML/CSS.

### Important notice

This project is educational and organizational.
It does not provide legal or immigration advice.
It does not promise approval.
It does not compute real approval odds.

### Goal

- Organize professional evidence, gaps, and roadmap tasks.
- Support technical authority, publications, and public project planning.
- Enable AI-assisted analysis through a pluggable provider architecture.
- Serve as a public software engineering portfolio project.

### Core stack

- Python 3.12+
- Flask
- SQLite (local-first)
- Pytest
- PT-BR/EN-US i18n from JSON files

### Run locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open: http://127.0.0.1:5000

### Run tests

```bash
pytest -q
```

### Privacy and public repo rules

- Use fake/demo data only.
- Never commit real personal data or immigration documents.
- Never hardcode secrets; rely on environment variables.

### Current status

Phases 2, 3, and 4 implemented: readiness dashboard/assessments plus operational and authority-building modules.

- Routes: `/dashboard`, `/assessment`, `/niw`, `/evidences`, `/roadmap`, `/gaps`, `/proposed-endeavor`, `/authority`, `/github-projects`, `/linkedin-content`, `/recommenders`, `/report/export`.
- EB-2 assessment with weighted questions (0-5), justification, status badge, and optional evidence references.
- NIW assessment for the 3 prongs with score, observations, gaps, practical recommendations, and suggested tasks.
- Evidence CRUD with metadata fields, status, and AI sharing privacy flag.
- Roadmap CRUD with horizon, priority, status, target date, estimated effort, and estimated impact.
- Proposed endeavor builder with short/long narrative, relevance, expected impact, and status.
- Technical authority plan plus CRUD for GitHub projects, LinkedIn content, and recommenders.
- Organizational JSON report export with automatic private evidence filtering.
- Automatic gaps consolidation with actionable recommendations.
- Educational scoring engine with 0-100 dimension scores, 0-100 overall score, and readiness classification bands.
- Persistent legal/organizational disclaimers across user-facing pages.
