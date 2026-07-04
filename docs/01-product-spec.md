# 01 - Product Spec

## Personas

1. Profissional Tecnico em Transicao Internacional
- Quer organizar historico e evidencias sem depender de planilhas dispersas.

2. Pesquisador(a) ou Especialista de Dominio
- Possui producao tecnica, mas precisa transformar em narrativa estruturada.

3. Mentor(a) de Carreira Tecnica
- Usa ferramenta para guiar aconselhamento organizacional (nao juridico).

## Jornadas do usuario

1. Onboarding local
- Usuario inicia app local, escolhe idioma e cria perfil demo.

2. Mapeamento de evidencias
- Usuario cadastra evidencias por categoria, origem e impacto.

3. Diagnostico organizacional
- Usuario visualiza gaps e score educacional interno.

4. Planejamento
- Usuario transforma gaps em tarefas com prioridade e prazo.

5. Relatorio
- Usuario exporta snapshot com disclaimer e itens nao privados.

## Funcionalidades

- Dashboard local de prontidao.
- Cadastro e classificacao de evidencias.
- Registro de gaps e tarefas de roadmap.
- Estrutura de proposed endeavor e contribuicoes publicas.
- Exportacao de relatorio organizacional.
- Camada de IA plugavel com provider mock para modo offline.
- Internacionalizacao PT-BR e EN-US.
- Narrativa de portfolio tecnico com privacidade e limites de uso publico.

## Requisitos funcionais

- RF-01: Persistir dados em SQLite local.
- RF-02: Permitir CRUD de evidencias, gaps e tarefas.
- RF-03: Calcular score educacional interno (nao juridico).
- RF-04: Permitir marcar evidencias como privadas.
- RF-05: Bloquear exportacao/envio externo de evidencia privada.
- RF-06: Permitir selecao de idioma PT-BR/EN-US.
- RF-07: Exibir disclaimers legal/privacidade em telas e exportacoes.
- RF-08: Definir provider de IA por configuracao de ambiente.
- RF-09: Exibir orientacao de portfolio e limites de uso publico.

## Requisitos nao funcionais

- RNF-01: Execucao local-first sem dependencia de cloud para fluxo basico.
- RNF-02: Codigo legivel, simples e coberto por testes criticos.
- RNF-03: Sem secrets hardcoded.
- RNF-04: Suporte a reprodutibilidade em ambiente CI (pytest).
- RNF-05: Documentacao recuperavel para contexto de copilots.

## Criterios de aceite

- CA-01: App sobe localmente com Flask e SQLite.
- CA-02: Testes de scoring, i18n, db, providers e privacidade passam.
- CA-03: README e docs explicam limites legais de forma clara.
- CA-04: Export nao inclui evidencias privadas.
- CA-05: PT-BR e EN-US disponiveis com paridade minima de chaves.

## Escopo do MVP

- Estrutura de dados inicial.
- Dashboard e assessment basico.
- Evidencias, gaps e roadmap.
- Exportacao simples de relatorio.
- Provider Mock funcional.
- Contratos para OpenAI, Azure OpenAI e Ollama.

## Escopo futuro

- Versionamento de snapshots de evolucao.
- Modo multi-perfil local.
- Painel de analytics de progresso temporal.
- Integrações opcionais com calendarios e trackers.
- Templates de narrativa tecnica para artigos e talks.
