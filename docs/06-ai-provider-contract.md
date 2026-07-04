# 06 - AI Provider Contract

## Interface comum de providers

Todos os providers devem implementar uma interface comum:

- `name() -> str`
- `analyze(prompt: str, context: dict | None = None) -> dict`
- `healthcheck() -> dict`

Resposta padrao de `analyze`:

```json
{
  "provider": "mock",
  "status": "ok",
  "analysis": "texto",
  "tokens_used": 0,
  "model": "mock-v1"
}
```

## MockProvider

- Sempre disponivel para desenvolvimento local/offline.
- Nao realiza chamadas de rede.
- Retorna analise sintetica deterministicamente.

## OpenAIProvider

- Usa endpoint oficial OpenAI.
- Requer chave por variavel de ambiente.
- Deve aplicar timeout e tratamento de erro de rede.

## AzureOpenAIProvider

- Usa endpoint Azure OpenAI.
- Requer endpoint, deployment e chave configurados por ambiente.
- Deve registrar metadados minimos de latencia/erro.

## OllamaProvider

- Usa instancia local/remota de Ollama por HTTP.
- Requer modelo configurado.
- Suporta cenario local sem cloud.

## Variaveis de ambiente

- `AI_PROVIDER=mock|openai|azure_openai|ollama`
- `OPENAI_API_KEY=`
- `OPENAI_MODEL=`
- `AZURE_OPENAI_API_KEY=`
- `AZURE_OPENAI_ENDPOINT=`
- `AZURE_OPENAI_DEPLOYMENT=`
- `OLLAMA_BASE_URL=`
- `OLLAMA_MODEL=`

## Regras de privacidade

- Evidencias marcadas com `is_private=true` nao podem ser enviadas para providers externos.
- Campos sensiveis devem ser removidos ou mascarados antes de qualquer envio.
- O modo `mock` pode operar com dados completos apenas localmente.
- O app deve preferir minimizar o contexto enviado mesmo em providers externos.

## Tratamento de erro

- Erros de provider devem retornar estrutura padrao:
  - `status=error`
  - `error_code`
  - `error_message`
  - `retryable` (boolean)
- Falha de provider nao deve quebrar o fluxo principal da aplicacao.

## Logs de analise

- Registrar apenas metadados essenciais:
  - provider
  - timestamp
  - hash do prompt
  - status
  - latencia aproximada
- Evitar persistencia de texto sensivel em logs.

## Regra critica

Nao enviar para providers externos evidencias marcadas como privadas.
