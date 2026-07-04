import pytest

from app import (
    AzureOpenAIProvider,
    MockProvider,
    OllamaProvider,
    OpenAIProvider,
    analyze_with_provider,
    get_ai_provider,
    sanitize_ai_context,
)


def test_mock_provider_returns_analysis() -> None:
    provider = MockProvider()
    result = provider.analyze("test", {"foo": "bar"})
    assert result["provider"] == "mock"
    assert result["status"] == "ok"
    assert result["model"] == "mock-v1"
    assert result["context_items"] == 1


def test_factory_returns_mock_by_default() -> None:
    provider = get_ai_provider("mock")
    assert provider.provider_name == "mock"
    assert provider.name() == "mock"


def test_openai_provider_returns_error_when_key_missing(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = get_ai_provider("openai")
    result = provider.analyze("hello", {"evidences": [{"id": 1, "can_send_to_ai": True, "is_private": False}, {"id": 2, "can_send_to_ai": True, "is_private": True}]})
    assert result["status"] == "error"
    assert result["error_code"] == "missing_configuration"


def test_sanitize_ai_context_blocks_private_fields() -> None:
    sanitized = sanitize_ai_context(
        {
            "email": "private@example.com",
            "evidences": [
                {"id": 1, "can_send_to_ai": True, "is_private": False},
                {"id": 2, "can_send_to_ai": True, "is_private": True},
            ],
        },
        allow_private=False,
    )
    assert sanitized["email"] == "[redacted]"
    assert [item["id"] for item in sanitized["evidences"]] == [1]


def test_analyze_with_provider_records_run(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    monkeypatch.setattr("app.DEFAULT_DB_PATH", str(tmp_path / "ai.db"))

    def fake_post(*args, **kwargs):
        class FakeResponse:
            status_code = 200

            def json(self):
                return {
                    "choices": [{"message": {"content": "analysis ok"}}],
                    "usage": {"total_tokens": 9},
                }

        return FakeResponse()

    monkeypatch.setattr("app.requests.post", fake_post)
    result = analyze_with_provider("prompt", {"evidences": [{"id": 1, "can_send_to_ai": True, "is_private": False}]}, "openai")
    assert result["status"] == "ok"
    assert result["analysis"] == "analysis ok"


def test_ollama_provider_healthcheck_reports_missing_config(monkeypatch) -> None:
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    provider = OllamaProvider()
    health = provider.healthcheck()
    assert health["status"] == "error"


def test_azure_provider_returns_error_when_config_missing(monkeypatch) -> None:
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT", raising=False)
    provider = AzureOpenAIProvider()
    result = provider.analyze("hello")
    assert result["status"] == "error"
    assert result["error_code"] == "missing_configuration"


def test_invalid_provider_raises() -> None:
    with pytest.raises(ValueError):
        get_ai_provider("invalid-provider")
