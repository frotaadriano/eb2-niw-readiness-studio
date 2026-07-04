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

- Python 3.12+
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

### Como rodar testes

```bash
pytest -q
```

### Estrutura

- `docs/`: especificacao, arquitetura, plano e ADRs.
- `tests/`: harness inicial com regras criticas.
- `scripts/`: utilitarios de smoke test, reset e export demo.
- `locales/`: internacionalizacao PT-BR e EN-US.

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

Foundation created: specs, architecture docs, test harness, CI, i18n, and initial app skeleton.
