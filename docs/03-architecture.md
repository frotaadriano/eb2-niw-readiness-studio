# 03 - Architecture

## Visao geral

Arquitetura web monolitica leve, local-first, com Flask para HTTP/renderizacao, SQLite para persistencia local e camada de servicos Python para regras de negocio.

## Decisao local-first

- Dados ficam locais por padrao.
- Fluxo essencial funciona offline com provider mock.
- Exportacoes sao geradas localmente.

## Flask

- Responsavel por rotas HTTP e HTML/CSS renderizado no backend.
- Sem dependencia inicial de frontend SPA.
- Rotas devem exibir disclaimer visivel.

## SQLite

- Banco local simples e portavel.
- Sem ORM inicialmente para manter controle explicito sobre SQL.
- Scripts dedicados para init/reset demo.

## i18n

- Dicionarios JSON em `locales/pt-BR.json` e `locales/en-US.json`.
- Selecao por query param, sessao ou configuracao.
- Fallback para EN-US quando locale/chave nao existir.

## AI Providers

- Contrato comum para multiplos providers:
  - MockProvider
  - OpenAIProvider
  - AzureOpenAIProvider
  - OllamaProvider
- Aplicacao escolhe provider por variavel de ambiente.
- Politica de privacidade bloqueia envio de evidencias privadas.

## Exportacoes

- Relatorios em JSON/TXT/HTML (fases futuras), iniciando por JSON demo.
- Export deve incluir disclaimer legal.
- Export deve excluir itens marcados como privados.

## Seguranca

- Sem secrets no codigo ou repo.
- Uso de `.env` local e `.env.example` versionado.
- Validacoes de entrada e sanitizacao basica em formulários.

## Privacidade

- Repositorio publico com dados fake/demo.
- Regras de nao envio externo para conteudo privado.
- Logs de IA com minimizacao de dados (metadados sempre que possivel).

## Limitacoes

- Nao substitui avaliacao juridica especializada.
- Scoring e educacional e nao preditivo.
- Modo local-first nao elimina riscos se usuario optar por provider externo.

## Evolucao futura

- Separar modulos por camadas (domain/application/infrastructure).
- Migracoes SQL versionadas.
- Exportadores adicionais (PDF/Markdown).
- Observabilidade local e trilha de auditoria ampliada.
