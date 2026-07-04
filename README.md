# EB2-NIW Readiness Studio

Local-first, spec-driven Flask app for organizing EB-2/NIW readiness evidence, gaps, roadmap tasks, and portfolio narratives without turning the project into legal advice.

[PT-BR](#pt-br) | [EN-US](#en-us)

## PT-BR

### O que este projeto e

EB2-NIW Readiness Studio e uma aplicacao web local-first para organizacao educacional e organizacional de prontidao EB-2/NIW. O foco e estruturar evidencias, lacunas, tarefas e narrativa tecnica com privacidade por padrao e providers de IA plugaveis.

### Objetivo

- Organizar evidencias profissionais, gaps e roadmap de evolucao.
- Apoiar o planejamento de autoridade tecnica, projetos publicos e conteudo para portfolio.
- Permitir analises assistidas por IA com contrato comum para Mock, OpenAI, Azure OpenAI e Ollama.
- Demonstrar uma arquitetura simples, testavel e pronta para portfolio tecnico publico.

### Disclaimer juridico e de privacidade

Este projeto e educacional e organizacional.
Nao e aconselhamento juridico.
Nao e aconselhamento imigratorio.
Nao substitui advogado.
Nao promete aprovacao.
Nao estima chance real de aprovacao.
O score e apenas organizacional.
Use apenas dados fake/demo em publico e nao use evidencias sensiveis em demos abertas.

### Principais funcionalidades

- Dashboard com resumo de prontidao, score educacional e alertas.
- Assessment EB-2 por dimensao com nota, justificativa, status e evidencias opcionais.
- Assessment NIW para os 3 pilares com score e plano de acao.
- CRUD de evidencias, gaps e roadmap com filtros e badges de status.
- Proposed Endeavor, Autoridade Tecnica, Projetos GitHub, Conteudo LinkedIn e Recomendadores.
- Exportacao de relatorio organizacional local com filtro de evidencias privadas.
- i18n PT-BR/EN-US com fallback para EN-US.

### Arquitetura

- Flask com HTML renderizado no backend.
- SQLite local como persistencia principal.
- SQL direto sem ORM.
- Providers de IA em camada de abstracao simples.
- Docs spec-driven e ADRs para as decisoes principais.
- Test harness com pytest e scripts de smoke/reset/export.

### Stack

- Python 3.12+
- Flask
- SQLite
- Pytest
- python-dotenv
- requests

### Providers de IA

- MockProvider: modo offline, deterministico e seguro para demo local.
- OpenAIProvider: integracao via API key e modelo configurado por ambiente.
- AzureOpenAIProvider: integracao via endpoint, deployment e chave por ambiente.
- OllamaProvider: integracao local ou remota via HTTP.

### i18n PT-BR/EN-US

- Traducoes em `locales/pt-BR.json` e `locales/en-US.json`.
- Paridade de chaves mantida como regra de projeto.
- Fallback para `en-US` quando o locale solicitado nao existir.

### Spec-driven development

O repositorio foi organizado a partir de contexto, especificacao, modelo de dominio, arquitetura, plano e fases. As decisoes ficam documentadas para facilitar manutencao, revisao e uso com assistentes de codigo.

### Test harness

O projeto inclui testes para i18n, banco, scoring, contratos de IA, privacidade e exportacao. Scripts auxiliares validam smoke test, reset de banco demo e exportacao de relatorio.

### Instalacao

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Execucao

```bash
python app.py
```

Abra: http://127.0.0.1:5000

O banco SQLite local e criado automaticamente em `data/app.db` quando a aplicacao sobe. Para demo publica, mantenha os dados fake e privados fora do repositorio.

### Testes

```bash
pytest -q
python scripts/smoke_test.py
python scripts/reset_demo_db.py
python scripts/export_demo_report.py
```

### Uso com MockProvider

Defina `AI_PROVIDER=mock` no `.env` e execute a aplicacao localmente. Esse modo nao faz chamadas externas e e o recomendado para demo e desenvolvimento offline.

### Uso com OpenAI

Configure `AI_PROVIDER=openai`, `OPENAI_API_KEY` e `OPENAI_MODEL` no `.env`. Revise o conteudo antes de enviar para qualquer provider externo e nao envie evidencias privadas.

### Uso com Azure OpenAI

Configure `AI_PROVIDER=azure_openai`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` e `AZURE_OPENAI_DEPLOYMENT` no `.env`. Preserve a mesma regra de privacidade para demos e experimentos.

### Uso com Ollama

Configure `AI_PROVIDER=ollama`, `OLLAMA_BASE_URL` e `OLLAMA_MODEL`. Esse modo permite um fluxo local ou self-hosted sem depender de nuvem publica.

### Roadmap futuro

- Versionamento de snapshots de evolucao.
- Modo multi-perfil local.
- Exportacoes adicionais e relatorios mais ricos.
- Melhorias de UX e narrativa de portfolio.
- Integracoes opcionais com calendarios e trackers.

### Portfolio Value

Este projeto demonstra Python, Flask, SQLite, arquitetura local-first, abstracao de providers de IA, integracao com OpenAI/Azure OpenAI/Ollama, i18n, spec-driven development, privacy-by-design, harness de testes, workflows estruturados de assessment e geracao de exportacoes/relatorios.

### What this project is not

- Nao e aconselhamento juridico.
- Nao substitui advogado.
- Nao calcula chance real de aprovacao.
- Nao garante aprovacao.
- Nao deve armazenar dados sensiveis em repositorio publico.
- Nao deve ser usado como unica base de decisao.



### Estrutura

- `docs/`: contexto, especificacao, dominio, arquitetura, plano, fases, contratos e posicionamento.
- `tests/`: suite de regressao para comportamento critico.
- `scripts/`: utilitarios de smoke test, reset de banco e export demo.
- `locales/`: internacionalizacao PT-BR e EN-US.

---

## EN-US

### What this project is

EB2-NIW Readiness Studio is a local-first web application for educational and organizational EB-2/NIW readiness planning. It helps structure evidence, gaps, roadmap tasks, and technical storytelling with privacy by default and pluggable AI providers.

### Goal

- Organize professional evidence, gaps, and roadmap tasks.
- Support technical authority planning, public projects, and portfolio content.
- Enable AI-assisted analysis through a common contract for Mock, OpenAI, Azure OpenAI, and Ollama.
- Demonstrate a simple, testable architecture suitable for a public technical portfolio.

### Legal and privacy disclaimer

This project is educational and organizational.
It is not legal advice.
It is not immigration advice.
It does not replace an attorney.
It does not promise approval.
It does not estimate real approval odds.
The score is organizational only.
Use fake/demo data in public and avoid sensitive evidence in open demos.

### Main features

- Readiness dashboard with educational score and alerts.
- EB-2 assessment by dimension with score, justification, status, and optional evidence links.
- NIW assessment for the 3 prongs with score and action planning.
- CRUD for evidences, gaps, and roadmap tasks with filters and status badges.
- Proposed Endeavor, Technical Authority, GitHub Projects, LinkedIn Content, and Recommenders.
- Local organizational report export with private-evidence filtering.
- PT-BR/EN-US i18n with EN-US fallback.

### Architecture

- Flask with backend-rendered HTML.
- Local SQLite persistence.
- Direct SQL without an ORM.
- Lightweight abstraction for AI providers.
- Spec-driven docs and ADRs for key decisions.
- Test harness with pytest plus smoke/reset/export scripts.

### Stack

- Python 3.12+
- Flask
- SQLite
- Pytest
- python-dotenv
- requests

### AI providers

- MockProvider: offline, deterministic, safe for local demo.
- OpenAIProvider: API key and model configured through environment.
- AzureOpenAIProvider: endpoint, deployment, and key configured through environment.
- OllamaProvider: local or remote HTTP-based integration.

### PT-BR/EN-US i18n

- Translations live in `locales/pt-BR.json` and `locales/en-US.json`.
- Key parity is part of the project rules.
- Fallback to `en-US` when the requested locale does not exist.

### Spec-driven development

The repository was organized from context, product spec, domain model, architecture, implementation plan, and implementation phases. Decisions are documented to keep maintenance and collaboration predictable.

### Test harness

The project includes tests for i18n, database behavior, scoring, AI provider contracts, privacy, and exports. Helper scripts validate smoke tests, demo database reset, and report export.

### Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Run

```bash
python app.py
```

Open: http://127.0.0.1:5000

The local SQLite database is created automatically in `data/app.db` when the app starts. For public demos, keep only fake data and avoid sensitive records in the repository.

### Test

```bash
pytest -q
python scripts/smoke_test.py
python scripts/reset_demo_db.py
python scripts/export_demo_report.py
```

### Using MockProvider

Set `AI_PROVIDER=mock` in `.env` and run locally. This mode performs no external calls and is the recommended option for offline development and public demos.

### Using OpenAI

Set `AI_PROVIDER=openai`, `OPENAI_API_KEY`, and `OPENAI_MODEL` in `.env`. Review the prompt payload before sending anything to an external provider and keep private evidence out of the request.

### Using Azure OpenAI

Set `AI_PROVIDER=azure_openai`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, and `AZURE_OPENAI_DEPLOYMENT` in `.env`. Apply the same privacy rules for demos and experiments.

### Using Ollama

Set `AI_PROVIDER=ollama`, `OLLAMA_BASE_URL`, and `OLLAMA_MODEL`. This supports a local or self-hosted workflow without depending on public cloud services.

### Future roadmap

- Versioned readiness snapshots.
- Multi-profile local mode.
- Richer reports and exports.
- UX and portfolio narrative improvements.
- Optional calendar and tracker integrations.

### Portfolio Value

This project demonstrates Python, Flask, SQLite, local-first architecture, AI provider abstraction, OpenAI/Azure OpenAI/Ollama integration, i18n, spec-driven development, privacy-by-design, a test harness, structured assessment workflows, and report generation.

### What this project is not

- It is not legal advice.
- It does not replace an attorney.
- It does not compute real approval odds.
- It does not guarantee approval.
- It should not store sensitive data in a public repository.
- It should not be used as the only basis for decisions.

### Structure

- `docs/`: context, spec, domain, architecture, plan, phases, contracts, and positioning.
- `tests/`: regression suite for critical behavior.
- `scripts/`: smoke test, demo DB reset, and demo report export helpers.
- `locales/`: PT-BR and EN-US translations.
