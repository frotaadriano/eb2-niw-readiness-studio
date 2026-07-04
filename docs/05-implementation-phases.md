# 05 - Implementation Phases

## Fase 0: estrutura, specs e harness

- Criar estrutura de diretorios e arquivos base.
- Definir docs spec-driven e ADRs.
- Configurar pytest e workflow de CI.

## Fase 1: banco SQLite e seed

- Definir schema inicial.
- Criar scripts de init/reset com dados demo.
- Validar constraints basicas em testes.

## Fase 2: dashboard e assessment

- Implementar pagina inicial com resumo de prontidao.
- Implementar scoring educacional inicial.
- Exibir disclaimers de forma persistente.

Status (implementado):

- Rotas entregues: `/dashboard`, `/assessment` e `/niw`.
- Assessment EB-2 por categoria com peso, nota 0-5, justificativa, status e evidencias associadas opcionais.
- Assessment NIW para 3 pilares com score, observacoes, gaps, recomendacoes e tarefas sugeridas.
- Score por dimensao (0-100), score geral (0-100) e classificacao educacional.
- Dashboard com cards de score, classificacao, evidencias, gaps, tarefas e alertas principais.
- Disclaimer de score exibido de forma persistente nas telas.

## Fase 3: evidencias e roadmap

- CRUD de evidencias.
- CRUD de gaps.
- CRUD de tarefas e acompanhamento de status.

Status (implementado):

- Rotas entregues: `/evidences`, `/evidences/new`, `/evidences/<id>/edit`, `/evidences/<id>/delete`, `/roadmap`, `/roadmap/new`, `/roadmap/<id>/edit`, `/roadmap/<id>/delete` e `/gaps`.
- Gestao de evidencias com campos completos de metadados, status e controle de privacidade para envio a IA (`can_send_to_ai`).
- Roadmap por horizonte (0-30, 30-90, 3-6, 6-12 meses) com prioridade, status, data alvo e criterio relacionado.
- Gaps automaticos consolidados a partir de assessment baixo, pilares NIW baixos, categorias sem evidencias, tarefas atrasadas e itens bloqueados.
- Filtros simples por status/categoria/horizonte e badges visuais nas telas operacionais.

## Fase 4: proposed endeavor e relatorios

- Estruturar campos para proposed endeavor.
- Implementar exportacao de relatorio organizacional.
- Garantir filtro de conteudo privado.

Status (implementado):

- Rotas entregues: `/proposed-endeavor`, `/proposed-endeavor/new`, `/proposed-endeavor/<id>/edit`, `/proposed-endeavor/<id>/delete`, `/authority`, `/authority/new`, `/authority/<id>/edit`, `/authority/<id>/delete`, `/github-projects`, `/github-projects/new`, `/github-projects/<id>/edit`, `/github-projects/<id>/delete`, `/linkedin-content`, `/linkedin-content/new`, `/linkedin-content/<id>/edit`, `/linkedin-content/<id>/delete`, `/recommenders`, `/recommenders/new`, `/recommenders/<id>/edit` e `/recommenders/<id>/delete`.
- Proposed Endeavor Builder com campos completos de narrativa curta/longa, impacto, relevancia e status.
- Autoridade tecnica com plano de evolucao, comunidades, artigos, talks, repositorios e evidencias publicas.
- Projetos GitHub com problema resolvido, status, impacto, evidencias e criterio relacionado.
- Conteudo LinkedIn com tipo, objetivo, planejamento e vinculo com evidencias.
- Recomendadores com relacao profissional, independencia, forca potencial da carta e status.
- Seed demo atualizado com exemplo default de proposed endeavor, projeto exemplo do proprio studio e ideias de conteudo LinkedIn.
- Exportacao de relatorio organizacional em JSON local pela rota `/report/export` (com opcao de download).
- Filtro de privacidade aplicado na exportacao: evidencias privadas nao sao incluidas no payload exportado.

## Fase 5: i18n PT-BR/EN-US

- Expandir cobertura de traducoes para UI principal.
- Garantir fallback e paridade de chaves.
- Cobrir i18n com testes.

Status (implementado):

- Fallback de locale configurado para `en-US` quando a lingua solicitada nao existe.
- Paridade de chaves validada entre `locales/pt-BR.json` e `locales/en-US.json`.
- Cobertura de testes para fallback, paridade de chaves e renderizacao da UI principal em EN-US.

## Fase 6: AI providers Mock, OpenAI, Azure OpenAI e Ollama

- Consolidar interface comum.
- Implementar providers com tratamento de erro consistente.
- Aplicar politica de nao envio de evidencias privadas.

## Fase 7: testes, exportacoes e README

- Consolidar suite de testes criticos e cenarios de regressao.
- Expandir exportadores e validacoes de payload.
- Refinar README bilíngue e exemplos de uso.

## Fase 8: polish de portfolio

- Melhorar UX e narrativa visual do projeto.
- Adicionar screenshots e walkthrough tecnico.
- Publicar artigos tecnicos com aprendizados.
