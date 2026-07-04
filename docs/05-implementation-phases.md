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

## Fase 4: proposed endeavor e relatorios

- Estruturar campos para proposed endeavor.
- Implementar exportacao de relatorio organizacional.
- Garantir filtro de conteudo privado.

## Fase 5: i18n PT-BR/EN-US

- Expandir cobertura de traducoes para UI principal.
- Garantir fallback e paridade de chaves.
- Cobrir i18n com testes.

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
