import pytest

from app import MockProvider, ProviderConfigError, get_ai_provider


def test_mock_provider_returns_analysis() -> None:
    provider = MockProvider()
    result = provider.analyze("test")
    assert result["provider"] == "mock"
    assert result["status"] == "ok"


def test_factory_returns_mock_by_default() -> None:
    provider = get_ai_provider("mock")
    assert provider.provider_name == "mock"


def test_openai_provider_requires_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = get_ai_provider("openai")
    with pytest.raises(ProviderConfigError):
        provider.analyze("hello")


def test_invalid_provider_raises() -> None:
    with pytest.raises(ValueError):
        get_ai_provider("invalid-provider")
