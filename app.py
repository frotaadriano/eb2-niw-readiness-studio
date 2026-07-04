import hashlib
import json
import os
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from flask import Flask, g, redirect, render_template_string, request, url_for

load_dotenv()

BASE_DIR = Path(__file__).parent
DEFAULT_DB_PATH = str(BASE_DIR / "data" / "app.db")
DEFAULT_LOCALE = "pt-BR"
SUPPORTED_LOCALES = ("pt-BR", "en-US")


def load_locale(locale: str) -> dict[str, str]:
    locale_path = BASE_DIR / "locales" / f"{locale}.json"
    fallback_path = BASE_DIR / "locales" / f"{DEFAULT_LOCALE}.json"
    if locale_path.exists():
        return json.loads(locale_path.read_text(encoding="utf-8"))
    return json.loads(fallback_path.read_text(encoding="utf-8"))


def t(key: str, lang: str | None = None) -> str:
    catalog = load_locale(lang or DEFAULT_LOCALE)
    return catalog.get(key, key)


def ensure_data_dir() -> None:
    (BASE_DIR / "data").mkdir(parents=True, exist_ok=True)


def get_db() -> sqlite3.Connection:
    db_path = str(BASE_DIR / "data" / "app.db")
    if "db" not in g:
        init_db(db_path)
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db() -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _seed_initial_data(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
        ("language", DEFAULT_LOCALE),
    )

    assessment_questions = [
        ("Q_EXPERTISE", "assessment.question.expertise", 1),
        ("Q_IMPACT", "assessment.question.impact", 2),
        ("Q_LEADERSHIP", "assessment.question.leadership", 3),
        ("Q_PUBLICATIONS", "assessment.question.publications", 4),
        ("Q_RECOMMENDERS", "assessment.question.recommenders", 5),
    ]
    cursor.executemany(
        """
        INSERT OR IGNORE INTO assessment_questions (code, question_key, sort_order)
        VALUES (?, ?, ?)
        """,
        assessment_questions,
    )

    niw_prongs = [
        ("PRONG_1", "niw.prong.1.title", "niw.prong.1.description"),
        ("PRONG_2", "niw.prong.2.title", "niw.prong.2.description"),
        ("PRONG_3", "niw.prong.3.title", "niw.prong.3.description"),
    ]
    cursor.executemany(
        """
        INSERT OR IGNORE INTO niw_prongs (code, title_key, description_key)
        VALUES (?, ?, ?)
        """,
        niw_prongs,
    )

    roadmap_tasks = [
        ("TASK_BASELINE", "roadmap.task.baseline", "todo", 1),
        ("TASK_EVIDENCE", "roadmap.task.evidence", "todo", 2),
        ("TASK_ENDEAVOR", "roadmap.task.endeavor", "todo", 3),
        ("TASK_AUTHORITY", "roadmap.task.authority", "todo", 4),
    ]
    cursor.executemany(
        """
        INSERT OR IGNORE INTO roadmap_tasks (code, title_key, status, sort_order)
        VALUES (?, ?, ?, ?)
        """,
        roadmap_tasks,
    )

    cursor.execute(
        """
        INSERT OR IGNORE INTO proposed_endeavor (title, summary, impact)
        VALUES (?, ?, ?)
        """,
        (
            "AI Readiness and Knowledge Transfer for SMBs",
            "Fake demo endeavor focused on practical AI adoption and workforce enablement.",
            "Fake demo impact: improve productivity and public technical dissemination.",
        ),
    )

    cursor.execute(
        """
        INSERT OR IGNORE INTO github_projects (name, repo_url, summary, stars)
        VALUES (?, ?, ?, ?)
        """,
        (
            "niw-readiness-demo",
            "https://github.com/demo/niw-readiness-demo",
            "Fake portfolio project showing local-first evidence organization.",
            42,
        ),
    )

    linkedin_ideas = [
        (
            "From Local-First to Reliable AI Workflows",
            "Explain why local-first architecture helps privacy and reproducibility.",
        ),
        (
            "How I Documented NIW Evidence with Software Engineering",
            "Share a framework to map evidence to measurable impact and authority.",
        ),
        (
            "Pragmatic Career Roadmaps for Technical Leadership",
            "Present a weekly execution model to build authority and public artifacts.",
        ),
    ]
    cursor.executemany(
        """
        INSERT OR IGNORE INTO linkedin_content (title, idea)
        VALUES (?, ?)
        """,
        linkedin_ideas,
    )


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    ensure_data_dir()
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS profile (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                headline TEXT,
                target_domain TEXT,
                locale TEXT NOT NULL DEFAULT 'pt-BR',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS assessment_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                question_key TEXT NOT NULL,
                sort_order INTEGER NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS assessment_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER NOT NULL,
                answer INTEGER NOT NULL,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (question_id) REFERENCES assessment_questions(id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS niw_prongs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                title_key TEXT NOT NULL,
                description_key TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS evidences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER,
                niw_prong_code TEXT,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                impact_level INTEGER NOT NULL DEFAULT 1,
                is_private INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (profile_id) REFERENCES profile(id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS roadmap_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                title_key TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'todo',
                sort_order INTEGER NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS proposed_endeavor (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL UNIQUE,
                summary TEXT NOT NULL,
                impact TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS authority_plan (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel TEXT NOT NULL,
                objective TEXT NOT NULL,
                cadence TEXT,
                status TEXT NOT NULL DEFAULT 'planned'
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS github_projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                repo_url TEXT,
                summary TEXT,
                stars INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS linkedin_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL UNIQUE,
                idea TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS recommenders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                relationship TEXT,
                status TEXT NOT NULL DEFAULT 'prospect',
                notes TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_analysis_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                run_type TEXT NOT NULL,
                status TEXT NOT NULL,
                metadata_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        _seed_initial_data(conn)
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
    init_db()

    @app.teardown_appcontext
    def teardown_db(_exception: BaseException | None) -> None:
        close_db()

    def get_selected_language() -> str:
        query_lang = request.args.get("lang")
        if query_lang in SUPPORTED_LOCALES:
            return query_lang

        conn = get_db()
        row = conn.execute("SELECT value FROM settings WHERE key = ?", ("language",)).fetchone()
        db_lang = row["value"] if row else None
        if db_lang in SUPPORTED_LOCALES:
            return str(db_lang)
        return DEFAULT_LOCALE

    def render_page(lang: str, page_title: str, body_template: str, **context: Any) -> str:
        template = """
        <html>
          <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>{{ page_title }}</title>
            <style>
              :root {
                --bg: #f4f7fb;
                --surface: #ffffff;
                --text: #172033;
                --muted: #5a677f;
                --line: #d7dfec;
                --accent: #0b5f9c;
                --warn-bg: #fff3e9;
                --warn-border: #c56a18;
              }
              body {
                margin: 0;
                font-family: "Segoe UI", Tahoma, sans-serif;
                color: var(--text);
                background: radial-gradient(circle at top right, #ecf5ff, var(--bg) 45%);
              }
              .container {
                max-width: 980px;
                margin: 0 auto;
                padding: 1.25rem;
              }
              .menu {
                display: flex;
                gap: 0.75rem;
                margin-bottom: 1rem;
                flex-wrap: wrap;
              }
              .menu a {
                text-decoration: none;
                color: var(--accent);
                font-weight: 600;
              }
              .panel {
                background: var(--surface);
                border: 1px solid var(--line);
                border-radius: 14px;
                padding: 1rem;
                box-shadow: 0 8px 24px rgba(7, 31, 61, 0.07);
              }
              .disclaimer {
                margin-top: 1rem;
                border-left: 4px solid var(--warn-border);
                background: var(--warn-bg);
                padding: 0.8rem;
              }
              .cards {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 0.75rem;
                margin-top: 1rem;
              }
              .card {
                background: #fbfdff;
                border: 1px solid var(--line);
                border-radius: 12px;
                padding: 0.75rem;
              }
              .metric {
                font-size: 1.4rem;
                margin: 0.25rem 0;
              }
              .small {
                color: var(--muted);
              }
              .language {
                margin-left: auto;
              }
              @media (max-width: 620px) {
                .language {
                  margin-left: 0;
                }
              }
            </style>
          </head>
          <body>
            <main class="container">
              <nav class="menu">
                <a href="{{ url_for('index', lang=lang) }}">{{ t('nav.home', lang) }}</a>
                <a href="{{ url_for('settings', lang=lang) }}">{{ t('nav.settings', lang) }}</a>
                <a href="{{ url_for('about', lang=lang) }}">{{ t('nav.about', lang) }}</a>
                <span class="small language">{{ t('settings.current_language', lang) }}: {{ lang }}</span>
              </nav>
              <section class="panel">
                {{ body|safe }}
              </section>
            </main>
          </body>
        </html>
        """
        body = render_template_string(body_template, lang=lang, t=t, **context)
        return render_template_string(template, page_title=page_title, body=body, lang=lang, t=t, url_for=url_for)

    def dashboard_stats() -> dict[str, int]:
        conn = get_db()
        return {
            "assessment_questions": conn.execute("SELECT COUNT(*) FROM assessment_questions").fetchone()[0],
            "niw_prongs": conn.execute("SELECT COUNT(*) FROM niw_prongs").fetchone()[0],
            "roadmap_tasks": conn.execute("SELECT COUNT(*) FROM roadmap_tasks").fetchone()[0],
            "github_projects": conn.execute("SELECT COUNT(*) FROM github_projects").fetchone()[0],
            "linkedin_content": conn.execute("SELECT COUNT(*) FROM linkedin_content").fetchone()[0],
        }

    @app.route("/")
    def index() -> str:
        lang = get_selected_language()
        stats = dashboard_stats()
        body = """
        <h1>{{ t('app.title', lang) }}</h1>
        <p>{{ t('app.subtitle', lang) }}</p>
        <p><strong>{{ t('app.status', lang) }}</strong></p>
        <div class="disclaimer">{{ t('app.disclaimer', lang) }}</div>
        <div class="cards">
          <article class="card">
            <h3>{{ t('home.card.questions', lang) }}</h3>
            <p class="metric">{{ stats.assessment_questions }}</p>
            <p class="small">{{ t('home.card.questions_hint', lang) }}</p>
          </article>
          <article class="card">
            <h3>{{ t('home.card.prongs', lang) }}</h3>
            <p class="metric">{{ stats.niw_prongs }}</p>
            <p class="small">{{ t('home.card.prongs_hint', lang) }}</p>
          </article>
          <article class="card">
            <h3>{{ t('home.card.roadmap', lang) }}</h3>
            <p class="metric">{{ stats.roadmap_tasks }}</p>
            <p class="small">{{ t('home.card.roadmap_hint', lang) }}</p>
          </article>
          <article class="card">
            <h3>{{ t('home.card.github', lang) }}</h3>
            <p class="metric">{{ stats.github_projects }}</p>
            <p class="small">{{ t('home.card.github_hint', lang) }}</p>
          </article>
          <article class="card">
            <h3>{{ t('home.card.linkedin', lang) }}</h3>
            <p class="metric">{{ stats.linkedin_content }}</p>
            <p class="small">{{ t('home.card.linkedin_hint', lang) }}</p>
          </article>
        </div>
        """
        return render_page(lang, t("app.title", lang), body, stats=stats)

    @app.route("/settings", methods=["GET", "POST"])
    def settings() -> str:
        lang = get_selected_language()
        saved = False
        if request.method == "POST":
            selected_lang = request.form.get("lang", DEFAULT_LOCALE)
            if selected_lang not in SUPPORTED_LOCALES:
                selected_lang = DEFAULT_LOCALE
            conn = get_db()
            conn.execute(
                """
                INSERT INTO settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value=excluded.value,
                    updated_at=CURRENT_TIMESTAMP
                """,
                ("language", selected_lang),
            )
            conn.commit()
            return redirect(url_for("settings", lang=selected_lang, saved="1"))

        if request.args.get("saved") == "1":
            saved = True

        body = """
        <h1>{{ t('settings.title', lang) }}</h1>
        <p>{{ t('settings.subtitle', lang) }}</p>
        {% if saved %}
          <div class="disclaimer">{{ t('settings.saved', lang) }}</div>
        {% endif %}
        <form method="post" action="{{ url_for('settings', lang=lang) }}">
          <label for="lang"><strong>{{ t('settings.language_label', lang) }}</strong></label>
          <select id="lang" name="lang">
            <option value="pt-BR" {% if lang == 'pt-BR' %}selected{% endif %}>PT-BR</option>
            <option value="en-US" {% if lang == 'en-US' %}selected{% endif %}>EN-US</option>
          </select>
          <button type="submit">{{ t('settings.save', lang) }}</button>
        </form>
        """
        return render_page(lang, t("settings.title", lang), body, saved=saved)

    @app.route("/about")
    def about() -> str:
        lang = get_selected_language()
        body = """
        <h1>{{ t('about.title', lang) }}</h1>
        <p>{{ t('about.description', lang) }}</p>
        <div class="disclaimer">{{ t('app.disclaimer', lang) }}</div>
        """
        return render_page(lang, t("about.title", lang), body)

    @app.route("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "db": "ready", "mode": "local-first"}

    return app


if __name__ == "__main__":
    init_db()
    create_app().run(debug=True)
