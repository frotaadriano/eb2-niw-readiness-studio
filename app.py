import hashlib
import json
import os
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from flask import Flask, request

load_dotenv()

BASE_DIR = Path(__file__).parent
DEFAULT_DB_PATH = str(BASE_DIR / "data" / "studio.db")
DEFAULT_LOCALE = "en-US"


def load_locale(locale: str) -> dict[str, str]:
    locale_path = BASE_DIR / "locales" / f"{locale}.json"
    fallback_path = BASE_DIR / "locales" / "en-US.json"

    if locale_path.exists():
        return json.loads(locale_path.read_text(encoding="utf-8"))

    return json.loads(fallback_path.read_text(encoding="utf-8"))


def t(locale: str, key: str) -> str:
    catalog = load_locale(locale)
    return catalog.get(key, key)


def ensure_data_dir() -> None:
    (BASE_DIR / "data").mkdir(parents=True, exist_ok=True)


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    ensure_data_dir()
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                headline TEXT,
                target_domain TEXT,
                locale TEXT NOT NULL DEFAULT 'en-US',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS evidences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                impact_level INTEGER NOT NULL DEFAULT 1,
                is_private INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (profile_id) REFERENCES profiles(id)
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def compute_readiness_score(
    evidences: list[dict[str, Any]],
    gaps: list[dict[str, Any]],
    completed_tasks: int,
) -> dict[str, Any]:
    evidence_points = min(len(evidences) * 4, 40)
    high_impact_bonus = sum(2 for ev in evidences if int(ev.get("impact_level", 1)) >= 4)
    high_impact_bonus = min(high_impact_bonus, 20)
    completed_task_points = min(completed_tasks * 2, 20)
    open_critical_gaps = sum(1 for gap in gaps if gap.get("severity") == "critical" and gap.get("status") != "mitigated")
    penalty = min(open_critical_gaps * 10, 30)

    score = max(0, min(100, evidence_points + high_impact_bonus + completed_task_points - penalty))

    if score >= 75:
        status = "structured"
    elif score >= 45:
        status = "in_progress"
    else:
        status = "early_stage"

    return {
        "score": score,
        "status": status,
        "explanation": "Educational readiness indicator only. Not legal advice and not an approval prediction.",
    }


def filter_private_evidences(evidences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [ev for ev in evidences if not bool(ev.get("is_private", False))]


def build_export_payload(profile: dict[str, Any], evidences: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "disclaimer": "Educational and organizational only. Not legal or immigration advice.",
        "profile": profile,
        "evidences": filter_private_evidences(evidences),
    }


class ProviderConfigError(RuntimeError):
    pass


class BaseAIProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def analyze(self, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        raise NotImplementedError

    def healthcheck(self) -> dict[str, Any]:
        return {"provider": self.provider_name, "status": "ok"}


class MockProvider(BaseAIProvider):
    @property
    def provider_name(self) -> str:
        return "mock"

    def analyze(self, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12]
        return {
            "provider": self.provider_name,
            "status": "ok",
            "model": "mock-v1",
            "analysis": f"Mock analysis generated for prompt hash {digest}.",
            "tokens_used": 0,
        }


class OpenAIProvider(BaseAIProvider):
    @property
    def provider_name(self) -> str:
        return "openai"

    def analyze(self, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        if not os.getenv("OPENAI_API_KEY"):
            raise ProviderConfigError("OPENAI_API_KEY is not configured")
        return {
            "provider": self.provider_name,
            "status": "error",
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "analysis": "Provider stub: integration pending.",
            "tokens_used": 0,
        }


class AzureOpenAIProvider(BaseAIProvider):
    @property
    def provider_name(self) -> str:
        return "azure_openai"

    def analyze(self, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        required_vars = ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT"]
        missing = [name for name in required_vars if not os.getenv(name)]
        if missing:
            raise ProviderConfigError(f"Missing Azure OpenAI settings: {', '.join(missing)}")
        return {
            "provider": self.provider_name,
            "status": "error",
            "model": os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            "analysis": "Provider stub: integration pending.",
            "tokens_used": 0,
        }


class OllamaProvider(BaseAIProvider):
    @property
    def provider_name(self) -> str:
        return "ollama"

    def analyze(self, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        if not os.getenv("OLLAMA_BASE_URL"):
            raise ProviderConfigError("OLLAMA_BASE_URL is not configured")
        return {
            "provider": self.provider_name,
            "status": "error",
            "model": os.getenv("OLLAMA_MODEL", "llama3"),
            "analysis": "Provider stub: integration pending.",
            "tokens_used": 0,
        }


def get_ai_provider(provider_name: str | None = None) -> BaseAIProvider:
    selected = (provider_name or os.getenv("AI_PROVIDER", "mock")).strip().lower()
    providers: dict[str, type[BaseAIProvider]] = {
        "mock": MockProvider,
        "openai": OpenAIProvider,
        "azure_openai": AzureOpenAIProvider,
        "ollama": OllamaProvider,
    }
    if selected not in providers:
        raise ValueError(f"Unsupported provider: {selected}")
    return providers[selected]()


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/")
    def index() -> str:
        locale = request.args.get("lang", DEFAULT_LOCALE)
        title = t(locale, "app.title")
        subtitle = t(locale, "app.subtitle")
        disclaimer = t(locale, "app.disclaimer")
        privacy = t(locale, "app.privacy_notice")
        status_text = t(locale, "app.status")

        return f"""
        <html>
          <head>
            <meta charset=\"utf-8\" />
            <title>{title}</title>
            <style>
              body {{
                font-family: 'Segoe UI', sans-serif;
                margin: 2rem auto;
                max-width: 980px;
                background: linear-gradient(120deg, #f6f9fc 0%, #edf3ff 100%);
                color: #1d2433;
              }}
              .card {{
                background: white;
                border-radius: 14px;
                padding: 1.5rem;
                box-shadow: 0 8px 20px rgba(21, 35, 65, 0.08);
              }}
              .tag {{
                display: inline-block;
                background: #e6f1ff;
                color: #0b3f75;
                padding: 0.2rem 0.6rem;
                border-radius: 999px;
                font-size: 0.85rem;
              }}
              .warn {{
                margin-top: 1rem;
                padding: 0.8rem;
                border-left: 4px solid #b04a00;
                background: #fff3e9;
              }}
            </style>
          </head>
          <body>
            <div class=\"card\">
              <span class=\"tag\">Local-First MVP Foundation</span>
              <h1>{title}</h1>
              <p>{subtitle}</p>
              <p><strong>{status_text}</strong></p>
              <div class=\"warn\">{disclaimer}</div>
              <div class=\"warn\">{privacy}</div>
            </div>
          </body>
        </html>
        """

    @app.route("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


if __name__ == "__main__":
    init_db()
    create_app().run(debug=True)
