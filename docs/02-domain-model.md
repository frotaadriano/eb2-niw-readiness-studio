# 02 - Domain Model

## Entidades principais

1. Profile
- Representa o resumo profissional do usuario.

2. Evidence
- Item de evidencia associado ao profile.

3. Gap
- Lacuna identificada no processo de prontidao.

4. RoadmapTask
- Tarefa acionavel para reduzir um gap.

5. Publication
- Publicacao, artigo, paper, post tecnico.

6. PublicProject
- Projeto publico (GitHub, blog, demo).

7. AnalysisLog
- Registro de analises assistidas por IA.

## Campos essenciais

### Profile
- id, full_name, headline, target_domain, locale, created_at, updated_at

### Evidence
- id, profile_id, category, title, description, source_url, impact_level, is_private, created_at

### Gap
- id, profile_id, gap_type, title, description, severity, status, created_at

### RoadmapTask
- id, profile_id, gap_id, title, description, priority, status, due_date, created_at

### Publication
- id, profile_id, title, venue, publication_date, url, visibility_level

### PublicProject
- id, profile_id, name, repo_url, summary, tags, status

### AnalysisLog
- id, profile_id, provider_name, prompt_hash, output_summary, privacy_mode, created_at

## Relacionamentos

- Profile 1:N Evidence
- Profile 1:N Gap
- Profile 1:N RoadmapTask
- Gap 1:N RoadmapTask
- Profile 1:N Publication
- Profile 1:N PublicProject
- Profile 1:N AnalysisLog

## Regras de scoring (educacional)

- Score base entre 0 e 100.
- Blocos de contribuicao:
  - evidencias completas e verificaveis;
  - projetos/publicacoes publicas;
  - gaps mitigados por tarefas concluidas;
  - consistencia de narrativa tecnica.
- Penalizacoes por gaps criticos em aberto.
- Score nao representa chance real de aprovacao.

## Status possiveis

- Gap.status: open, in_progress, mitigated, blocked
- RoadmapTask.status: todo, doing, done, blocked
- PublicProject.status: idea, building, published, archived

## Taxonomia de evidencias

- leadership
- innovation
- impact_metrics
- publications
- patents
- media_mentions
- judging_or_reviewing
- open_source
- talks_and_events
- awards
- recommendation_support

## Taxonomia de gaps

- evidence_quality
- evidence_quantity
- publication_depth
- public_visibility
- leadership_proof
- impact_clarity
- endeavor_alignment
- documentation_consistency

## Taxonomia de tarefas

- write_article
- ship_public_project
- collect_metrics
- request_peer_review
- prepare_talk
- improve_repo_readme
- create_case_study
- update_impact_dashboard
