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

8. Proposed Endeavor
- Narrativa estruturada de area, problema, impacto e relevancia.

9. AuthorityPlan
- Plano de evolucao para autoridade tecnica.

10. GitHubProject
- Projeto publico com problema, tecnologia, impacto e evidencias.

11. LinkedInContent
- Ideias e publicacoes planejadas para portfolio e autoridade.

12. Recommender
- Contato de recomendador com relacao, independencia e forca potencial da carta.

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

### Proposed Endeavor
- id, area, problem_to_solve, impacted_sector, technologies, relevance, experience_evidence, expected_impact, broader_importance, short_version, long_version, status

### AuthorityPlan
- id, channel, objective, cadence, status, main_theme, target_communities, planned_articles, planned_talks, planned_github_repos, events, people_recommenders, public_evidence

### GitHubProject
- id, name, summary, solved_problem, technologies, repo_url, status, potential_impact, generated_evidence, related_articles, related_criteria

### LinkedInContent
- id, title, content_type, theme, status, planned_date, published_link, related_evidence, objective

### Recommender
- id, name, relationship, organization, role_title, email, letter_strength, independence, validation_area, status, notes

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
- Profile 1:N Proposed Endeavor
- Profile 1:N AuthorityPlan
- Profile 1:N GitHubProject
- Profile 1:N LinkedInContent
- Profile 1:N Recommender

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
