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

ASSESSMENT_DIMENSIONS = [
    {
        "code": "Q_ACADEMIC",
        "category_key": "assessment.category.academic",
        "question_key": "assessment.question.academic",
        "weight": 5,
        "sort_order": 1,
    },
    {
        "code": "Q_EXPERIENCE",
        "category_key": "assessment.category.experience",
        "question_key": "assessment.question.experience",
        "weight": 5,
        "sort_order": 2,
    },
    {
        "code": "Q_SENIORITY",
        "category_key": "assessment.category.seniority",
        "question_key": "assessment.question.seniority",
        "weight": 4,
        "sort_order": 3,
    },
    {
        "code": "Q_STRATEGIC",
        "category_key": "assessment.category.strategic",
        "question_key": "assessment.question.strategic",
        "weight": 4,
        "sort_order": 4,
    },
    {
        "code": "Q_IMPACT_METRICS",
        "category_key": "assessment.category.impact_metrics",
        "question_key": "assessment.question.impact_metrics",
        "weight": 5,
        "sort_order": 5,
    },
    {
        "code": "Q_RECOGNITION",
        "category_key": "assessment.category.recognition",
        "question_key": "assessment.question.recognition",
        "weight": 4,
        "sort_order": 6,
    },
    {
        "code": "Q_PUBLICATIONS",
        "category_key": "assessment.category.publications",
        "question_key": "assessment.question.publications",
        "weight": 3,
        "sort_order": 7,
    },
    {
        "code": "Q_COMMUNITY",
        "category_key": "assessment.category.community",
        "question_key": "assessment.question.community",
        "weight": 3,
        "sort_order": 8,
    },
    {
        "code": "Q_RECOMMENDATION_LETTERS",
        "category_key": "assessment.category.recommendation_letters",
        "question_key": "assessment.question.recommendation_letters",
        "weight": 4,
        "sort_order": 9,
    },
    {
        "code": "Q_PUBLIC_PROJECTS",
        "category_key": "assessment.category.public_projects",
        "question_key": "assessment.question.public_projects",
        "weight": 3,
        "sort_order": 10,
    },
    {
        "code": "Q_CERTIFICATIONS",
        "category_key": "assessment.category.certifications",
        "question_key": "assessment.question.certifications",
        "weight": 2,
        "sort_order": 11,
    },
    {
        "code": "Q_ENDEAVOR",
        "category_key": "assessment.category.endeavor",
        "question_key": "assessment.question.endeavor",
        "weight": 5,
        "sort_order": 12,
    },
    {
        "code": "Q_DOCUMENTATION",
        "category_key": "assessment.category.documentation",
        "question_key": "assessment.question.documentation",
        "weight": 3,
        "sort_order": 13,
    },
]

EVIDENCE_TYPES = [
    "Diploma",
    "Historico academico",
    "Certificacao",
    "Carta de emprego",
    "Carta de recomendacao",
    "Projeto corporativo",
    "Metrica de impacto",
    "Artigo",
    "Palestra",
    "GitHub",
    "Reconhecimento",
    "Premio",
    "Publicacao",
    "Comunidade",
    "Remuneracao",
    "Curriculo",
    "LinkedIn",
    "Proposed endeavor",
    "Case study anonimizado",
    "Outro",
]

EVIDENCE_STATUS_OPTIONS = ["coletar", "em_revisao", "pronto", "fraco", "descartado"]
ROADMAP_HORIZON_OPTIONS = ["0_30", "30_90", "3_6", "6_12"]
ROADMAP_STATUS_OPTIONS = ["backlog", "in_progress", "completed", "blocked"]
ROADMAP_PRIORITY_OPTIONS = ["low", "medium", "high", "critical"]

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


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(row[1]) for row in rows}


def _ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
    if column_name in _table_columns(conn, table_name):
        return
    conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def _seed_initial_data(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
        ("language", DEFAULT_LOCALE),
    )

    assessment_questions = [
        (
            question["code"],
            question["category_key"],
            question["question_key"],
            int(question["weight"]),
            int(question["sort_order"]),
        )
        for question in ASSESSMENT_DIMENSIONS
    ]
    cursor.executemany(
        """
        INSERT OR IGNORE INTO assessment_questions (code, category_key, question_key, weight, sort_order)
        VALUES (?, ?, ?, ?, ?)
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

    niw_assessment_seed = [
        (
            "PRONG_1",
            0,
            "",
            "",
            "",
            "",
        ),
        (
            "PRONG_2",
            0,
            "",
            "",
            "",
            "",
        ),
        (
            "PRONG_3",
            0,
            "",
            "",
            "",
            "",
        ),
    ]
    cursor.executemany(
        """
        INSERT OR IGNORE INTO niw_prong_assessments
        (prong_code, score, observations, gaps, recommendations, suggested_tasks)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        niw_assessment_seed,
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
                category_key TEXT NOT NULL DEFAULT 'assessment.category.academic',
                question_key TEXT NOT NULL,
                weight INTEGER NOT NULL DEFAULT 1,
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
                score INTEGER NOT NULL DEFAULT 0,
                justification TEXT,
                status TEXT NOT NULL DEFAULT 'ausente',
                evidence_refs TEXT,
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
            CREATE TABLE IF NOT EXISTS roadmap_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                category TEXT,
                priority TEXT NOT NULL DEFAULT 'medium',
                horizon TEXT NOT NULL DEFAULT '30_90',
                status TEXT NOT NULL DEFAULT 'backlog',
                target_date TEXT,
                estimated_effort TEXT,
                estimated_impact TEXT,
                related_criteria TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
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

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS niw_prong_assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prong_code TEXT NOT NULL UNIQUE,
                score INTEGER NOT NULL DEFAULT 0,
                observations TEXT,
                gaps TEXT,
                recommendations TEXT,
                suggested_tasks TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (prong_code) REFERENCES niw_prongs(code)
            )
            """
        )

        _ensure_column(conn, "assessment_questions", "category_key", "TEXT NOT NULL DEFAULT 'assessment.category.academic'")
        _ensure_column(conn, "assessment_questions", "weight", "INTEGER NOT NULL DEFAULT 1")
        _ensure_column(conn, "assessment_answers", "score", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "assessment_answers", "justification", "TEXT")
        _ensure_column(conn, "assessment_answers", "status", "TEXT NOT NULL DEFAULT 'ausente'")
        _ensure_column(conn, "assessment_answers", "evidence_refs", "TEXT")
        _ensure_column(conn, "evidences", "evidence_type", "TEXT NOT NULL DEFAULT 'Outro'")
        _ensure_column(conn, "evidences", "link_or_path", "TEXT")
        _ensure_column(conn, "evidences", "evidence_date", "TEXT")
        _ensure_column(conn, "evidences", "relevance", "INTEGER NOT NULL DEFAULT 3")
        _ensure_column(conn, "evidences", "related_criteria", "TEXT")
        _ensure_column(conn, "evidences", "status", "TEXT NOT NULL DEFAULT 'coletar'")
        _ensure_column(conn, "evidences", "notes", "TEXT")
        _ensure_column(conn, "evidences", "can_send_to_ai", "INTEGER NOT NULL DEFAULT 0")

        _seed_initial_data(conn)
        conn.commit()
    finally:
        conn.close()


def score_to_status(score: int | None) -> str:
    if score is None or score == 0:
        return "ausente"
    if score <= 2:
        return "fraco"
    if score == 3:
        return "medio"
    return "forte"


def classify_readiness(score: int) -> str:
    bounded_score = max(0, min(100, score))
    if bounded_score <= 39:
        return "low"
    if bounded_score <= 59:
        return "initial"
    if bounded_score <= 74:
        return "moderate"
    if bounded_score <= 89:
        return "strong"
    return "robust"


def calculate_weighted_score(items: list[dict[str, Any]]) -> int:
    total_weight = sum(int(item.get("weight", 0)) for item in items)
    if total_weight <= 0:
        return 0

    weighted_points = 0.0
    for item in items:
        score = item.get("score")
        weight = int(item.get("weight", 0))
        if score is None:
            normalized = 0.0
        else:
            normalized = max(0.0, min(5.0, float(score))) / 5.0
        weighted_points += normalized * weight

    score_0_100 = (weighted_points / total_weight) * 100
    return int(round(score_0_100))


def calculate_eb2_scores(questions: list[dict[str, Any]]) -> dict[str, Any]:
    dimensions: dict[str, list[dict[str, Any]]] = {}
    for question in questions:
        category_key = str(question.get("category_key", "assessment.category.unknown"))
        dimensions.setdefault(category_key, []).append(question)

    dimension_scores: dict[str, int] = {}
    for category_key, items in dimensions.items():
        dimension_scores[category_key] = calculate_weighted_score(items)

    overall_score = calculate_weighted_score(questions)
    return {
        "overall_score": overall_score,
        "classification": classify_readiness(overall_score),
        "dimension_scores": dimension_scores,
        "answered_count": sum(1 for item in questions if item.get("score") is not None),
        "question_count": len(questions),
    }


def compute_readiness_score(
    evidences: list[dict[str, Any]],
    gaps: list[dict[str, Any]],
    completed_tasks: int,
) -> dict[str, Any]:
    # Kept for backwards compatibility with existing scripts/tests from previous phase.
    evidence_points = min(len(evidences) * 4, 40)
    high_impact_bonus = sum(2 for ev in evidences if int(ev.get("impact_level", 1)) >= 4)
    high_impact_bonus = min(high_impact_bonus, 20)
    completed_task_points = min(completed_tasks * 2, 20)
    open_critical_gaps = sum(1 for gap in gaps if gap.get("severity") == "critical" and gap.get("status") != "mitigated")
    penalty = min(open_critical_gaps * 10, 30)

    score = max(0, min(100, evidence_points + high_impact_bonus + completed_task_points - penalty))
    return {
        "score": score,
        "status": classify_readiness(score),
        "explanation": "Educational readiness indicator only. Not legal advice and not an approval prediction.",
    }


def filter_private_evidences(evidences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [ev for ev in evidences if not bool(ev.get("is_private", False))]


def filter_ai_allowed_evidences(evidences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        ev
        for ev in evidences
        if bool(ev.get("can_send_to_ai", False)) and not bool(ev.get("is_private", False))
    ]


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
                            table {
                                width: 100%;
                                border-collapse: collapse;
                            }
                            th, td {
                                border-bottom: 1px solid var(--line);
                                padding: 0.55rem;
                                text-align: left;
                                vertical-align: top;
                            }
                            input, select, textarea, button {
                                font: inherit;
                            }
                            input[type="text"], input[type="date"], select, textarea {
                                width: 100%;
                                box-sizing: border-box;
                                border: 1px solid var(--line);
                                border-radius: 8px;
                                padding: 0.45rem;
                                margin-top: 0.2rem;
                                margin-bottom: 0.55rem;
                                background: #fff;
                            }
                            button {
                                border: 1px solid #0f4f81;
                                color: #fff;
                                background: #0b5f9c;
                                border-radius: 8px;
                                padding: 0.4rem 0.75rem;
                                cursor: pointer;
                            }
                            .actions {
                                display: flex;
                                gap: 0.45rem;
                                flex-wrap: wrap;
                            }
                            .badge {
                                display: inline-block;
                                border-radius: 999px;
                                padding: 0.15rem 0.55rem;
                                font-size: 0.78rem;
                                font-weight: 600;
                                border: 1px solid transparent;
                            }
                            .badge.forte,
                            .badge.strong,
                            .badge.robust,
                            .badge.pronto,
                            .badge.completed,
                            .badge.done,
                            .badge.low {
                                background: #eaf8ee;
                                border-color: #2f8f4b;
                                color: #1f6a35;
                            }
                            .badge.medio,
                            .badge.medium,
                            .badge.moderate,
                            .badge.initial,
                            .badge.em_revisao,
                            .badge.in_progress,
                            .badge.backlog,
                            .badge.medium {
                                background: #fff5e8;
                                border-color: #c9791c;
                                color: #8b4a00;
                            }
                            .badge.fraco,
                            .badge.weak,
                            .badge.low,
                            .badge.ausente,
                            .badge.missing,
                            .badge.descartado,
                            .badge.blocked,
                            .badge.high,
                            .badge.critical {
                                background: #fdeced;
                                border-color: #c73d3d;
                                color: #8f1f28;
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
                <a href="{{ url_for('dashboard', lang=lang) }}">{{ t('nav.dashboard', lang) }}</a>
                <a href="{{ url_for('assessment', lang=lang) }}">{{ t('nav.assessment', lang) }}</a>
                <a href="{{ url_for('niw', lang=lang) }}">{{ t('nav.niw', lang) }}</a>
                <a href="{{ url_for('evidences', lang=lang) }}">{{ t('nav.evidences', lang) }}</a>
                <a href="{{ url_for('roadmap', lang=lang) }}">{{ t('nav.roadmap', lang) }}</a>
                <a href="{{ url_for('gaps', lang=lang) }}">{{ t('nav.gaps', lang) }}</a>
                <a href="{{ url_for('settings', lang=lang) }}">{{ t('nav.settings', lang) }}</a>
                <a href="{{ url_for('about', lang=lang) }}">{{ t('nav.about', lang) }}</a>
                <span class="small language">{{ t('settings.current_language', lang) }}: {{ lang }}</span>
              </nav>
              <section class="panel">
                {{ body|safe }}
              </section>
              <div class="disclaimer">{{ t('app.score_disclaimer', lang) }}</div>
            </main>
          </body>
        </html>
        """
        body = render_template_string(body_template, lang=lang, t=t, **context)
        return render_template_string(template, page_title=page_title, body=body, lang=lang, t=t, url_for=url_for)

    def dashboard_stats() -> dict[str, int]:
        conn = get_db()
        roadmap_count = conn.execute("SELECT COUNT(*) FROM roadmap_items").fetchone()[0]
        if roadmap_count == 0:
            roadmap_count = conn.execute("SELECT COUNT(*) FROM roadmap_tasks").fetchone()[0]
        return {
            "assessment_questions": conn.execute("SELECT COUNT(*) FROM assessment_questions").fetchone()[0],
            "niw_prongs": conn.execute("SELECT COUNT(*) FROM niw_prongs").fetchone()[0],
            "roadmap_tasks": roadmap_count,
            "github_projects": conn.execute("SELECT COUNT(*) FROM github_projects").fetchone()[0],
            "linkedin_content": conn.execute("SELECT COUNT(*) FROM linkedin_content").fetchone()[0],
        }

    def fetch_assessment_questions_with_answers() -> list[dict[str, Any]]:
        conn = get_db()
        rows = conn.execute(
            """
            SELECT
                q.id,
                q.code,
                q.category_key,
                q.question_key,
                q.weight,
                q.sort_order,
                a.score,
                a.justification,
                a.status,
                a.evidence_refs
            FROM assessment_questions q
            LEFT JOIN assessment_answers a ON a.question_id = q.id
            ORDER BY q.sort_order ASC
            """
        ).fetchall()

        return [
            {
                "id": row["id"],
                "code": row["code"],
                "category_key": row["category_key"],
                "question_key": row["question_key"],
                "weight": row["weight"],
                "score": row["score"],
                "justification": row["justification"] or "",
                "status": row["status"] or "ausente",
                "evidence_refs": row["evidence_refs"] or "",
            }
            for row in rows
        ]

    def upsert_assessment_answer(question_id: int, score: int | None, justification: str, evidence_refs: str) -> None:
        conn = get_db()
        normalized_score = 0 if score is None else max(0, min(5, score))
        status = score_to_status(score)
        conn.execute("DELETE FROM assessment_answers WHERE question_id = ?", (question_id,))
        conn.execute(
            """
            INSERT INTO assessment_answers (question_id, answer, notes, score, justification, status, evidence_refs)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                question_id,
                normalized_score,
                justification,
                normalized_score,
                justification,
                status,
                evidence_refs,
            ),
        )
        conn.commit()

    def fetch_niw_assessments() -> list[dict[str, Any]]:
        conn = get_db()
        rows = conn.execute(
            """
            SELECT
                p.code,
                p.title_key,
                p.description_key,
                a.score,
                a.observations,
                a.gaps,
                a.recommendations,
                a.suggested_tasks
            FROM niw_prongs p
            LEFT JOIN niw_prong_assessments a ON a.prong_code = p.code
            ORDER BY p.id ASC
            """
        ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            result.append(
                {
                    "code": row["code"],
                    "title_key": row["title_key"],
                    "description_key": row["description_key"],
                    "score": int(row["score"] or 0),
                    "observations": row["observations"] or "",
                    "gaps": row["gaps"] or "",
                    "recommendations": row["recommendations"] or "",
                    "suggested_tasks": row["suggested_tasks"] or "",
                }
            )
        return result

    def upsert_niw_assessment(
        prong_code: str,
        score: int,
        observations: str,
        gaps: str,
        recommendations: str,
        suggested_tasks: str,
    ) -> None:
        conn = get_db()
        bounded_score = max(0, min(100, score))
        conn.execute(
            """
            INSERT INTO niw_prong_assessments
            (prong_code, score, observations, gaps, recommendations, suggested_tasks, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(prong_code)
            DO UPDATE SET
                score=excluded.score,
                observations=excluded.observations,
                gaps=excluded.gaps,
                recommendations=excluded.recommendations,
                suggested_tasks=excluded.suggested_tasks,
                updated_at=CURRENT_TIMESTAMP
            """,
            (prong_code, bounded_score, observations, gaps, recommendations, suggested_tasks),
        )
        conn.commit()

    def fetch_evidence_list(status: str = "", category: str = "") -> list[dict[str, Any]]:
        conn = get_db()
        query = """
            SELECT
                id,
                title,
                evidence_type,
                category,
                description,
                link_or_path,
                evidence_date,
                relevance,
                related_criteria,
                status,
                notes,
                can_send_to_ai
            FROM evidences
            WHERE 1=1
        """
        params: list[Any] = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY COALESCE(evidence_date, '') DESC, id DESC"
        rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(row) for row in rows]

    def fetch_evidence_by_id(evidence_id: int) -> dict[str, Any] | None:
        conn = get_db()
        row = conn.execute(
            """
            SELECT
                id,
                title,
                evidence_type,
                category,
                description,
                link_or_path,
                evidence_date,
                relevance,
                related_criteria,
                status,
                notes,
                can_send_to_ai
            FROM evidences
            WHERE id = ?
            """,
            (evidence_id,),
        ).fetchone()
        return dict(row) if row else None

    def upsert_evidence(evidence_id: int | None, form_data: dict[str, str]) -> None:
        conn = get_db()
        payload = {
            "title": form_data.get("title", "").strip(),
            "evidence_type": form_data.get("evidence_type", "Outro").strip() or "Outro",
            "category": form_data.get("category", "").strip(),
            "description": form_data.get("description", "").strip(),
            "link_or_path": form_data.get("link_or_path", "").strip(),
            "evidence_date": form_data.get("evidence_date", "").strip(),
            "relevance": max(1, min(5, int(form_data.get("relevance", "3") or "3"))),
            "related_criteria": form_data.get("related_criteria", "").strip(),
            "status": form_data.get("status", "coletar").strip() or "coletar",
            "notes": form_data.get("notes", "").strip(),
            "can_send_to_ai": 1 if form_data.get("can_send_to_ai") == "on" else 0,
        }
        if payload["status"] not in EVIDENCE_STATUS_OPTIONS:
            payload["status"] = "coletar"
        if payload["evidence_type"] not in EVIDENCE_TYPES:
            payload["evidence_type"] = "Outro"

        if evidence_id is None:
            conn.execute(
                """
                INSERT INTO evidences
                (title, evidence_type, category, description, link_or_path, evidence_date, relevance, related_criteria, status, notes, can_send_to_ai, impact_level, is_private)
                VALUES (:title, :evidence_type, :category, :description, :link_or_path, :evidence_date, :relevance, :related_criteria, :status, :notes, :can_send_to_ai, :relevance, :is_private)
                """,
                {
                    **payload,
                    "is_private": 0 if payload["can_send_to_ai"] else 1,
                },
            )
        else:
            conn.execute(
                """
                UPDATE evidences
                SET title = :title,
                    evidence_type = :evidence_type,
                    category = :category,
                    description = :description,
                    link_or_path = :link_or_path,
                    evidence_date = :evidence_date,
                    relevance = :relevance,
                    related_criteria = :related_criteria,
                    status = :status,
                    notes = :notes,
                    can_send_to_ai = :can_send_to_ai,
                    impact_level = :relevance,
                    is_private = :is_private
                WHERE id = :id
                """,
                {
                    **payload,
                    "id": evidence_id,
                    "is_private": 0 if payload["can_send_to_ai"] else 1,
                },
            )
        conn.commit()

    def delete_evidence(evidence_id: int) -> None:
        conn = get_db()
        conn.execute("DELETE FROM evidences WHERE id = ?", (evidence_id,))
        conn.commit()

    def fetch_roadmap_items(status: str = "", category: str = "", horizon: str = "") -> list[dict[str, Any]]:
        conn = get_db()
        query = """
            SELECT
                id,
                title,
                description,
                category,
                priority,
                horizon,
                status,
                target_date,
                estimated_effort,
                estimated_impact,
                related_criteria
            FROM roadmap_items
            WHERE 1=1
        """
        params: list[Any] = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if category:
            query += " AND category = ?"
            params.append(category)
        if horizon:
            query += " AND horizon = ?"
            params.append(horizon)
        query += " ORDER BY CASE horizon WHEN '0_30' THEN 1 WHEN '30_90' THEN 2 WHEN '3_6' THEN 3 ELSE 4 END, COALESCE(target_date, ''), id"
        rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(row) for row in rows]

    def fetch_roadmap_item_by_id(item_id: int) -> dict[str, Any] | None:
        conn = get_db()
        row = conn.execute(
            """
            SELECT
                id,
                title,
                description,
                category,
                priority,
                horizon,
                status,
                target_date,
                estimated_effort,
                estimated_impact,
                related_criteria
            FROM roadmap_items
            WHERE id = ?
            """,
            (item_id,),
        ).fetchone()
        return dict(row) if row else None

    def upsert_roadmap_item(item_id: int | None, form_data: dict[str, str]) -> None:
        conn = get_db()
        payload = {
            "title": form_data.get("title", "").strip(),
            "description": form_data.get("description", "").strip(),
            "category": form_data.get("category", "").strip(),
            "priority": form_data.get("priority", "medium").strip() or "medium",
            "horizon": form_data.get("horizon", "30_90").strip() or "30_90",
            "status": form_data.get("status", "backlog").strip() or "backlog",
            "target_date": form_data.get("target_date", "").strip(),
            "estimated_effort": form_data.get("estimated_effort", "").strip(),
            "estimated_impact": form_data.get("estimated_impact", "").strip(),
            "related_criteria": form_data.get("related_criteria", "").strip(),
        }
        if payload["priority"] not in ROADMAP_PRIORITY_OPTIONS:
            payload["priority"] = "medium"
        if payload["horizon"] not in ROADMAP_HORIZON_OPTIONS:
            payload["horizon"] = "30_90"
        if payload["status"] not in ROADMAP_STATUS_OPTIONS:
            payload["status"] = "backlog"

        if item_id is None:
            conn.execute(
                """
                INSERT INTO roadmap_items
                (title, description, category, priority, horizon, status, target_date, estimated_effort, estimated_impact, related_criteria)
                VALUES (:title, :description, :category, :priority, :horizon, :status, :target_date, :estimated_effort, :estimated_impact, :related_criteria)
                """,
                payload,
            )
        else:
            conn.execute(
                """
                UPDATE roadmap_items
                SET title = :title,
                    description = :description,
                    category = :category,
                    priority = :priority,
                    horizon = :horizon,
                    status = :status,
                    target_date = :target_date,
                    estimated_effort = :estimated_effort,
                    estimated_impact = :estimated_impact,
                    related_criteria = :related_criteria,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
                """,
                {**payload, "id": item_id},
            )
        conn.commit()

    def delete_roadmap_item(item_id: int) -> None:
        conn = get_db()
        conn.execute("DELETE FROM roadmap_items WHERE id = ?", (item_id,))
        conn.commit()

    def build_gaps_summary() -> list[dict[str, str]]:
        conn = get_db()
        gaps_list: list[dict[str, str]] = []

        low_questions = conn.execute(
            """
            SELECT q.category_key, q.question_key, COALESCE(a.score, 0) AS score
            FROM assessment_questions q
            LEFT JOIN assessment_answers a ON a.question_id = q.id
            WHERE COALESCE(a.score, 0) <= 2
            ORDER BY q.sort_order
            """
        ).fetchall()
        for row in low_questions:
            gaps_list.append(
                {
                    "gap": f"assessment:{row['question_key']}",
                    "severity": "high" if int(row["score"]) <= 1 else "medium",
                    "related_criteria": str(row["category_key"]),
                    "missing_evidences": "score_low",
                    "suggested_task": "action.raise_assessment_score",
                    "priority": "high" if int(row["score"]) <= 1 else "medium",
                }
            )

        low_prongs = conn.execute(
            """
            SELECT p.title_key, p.code, COALESCE(a.score, 0) AS score
            FROM niw_prongs p
            LEFT JOIN niw_prong_assessments a ON a.prong_code = p.code
            WHERE COALESCE(a.score, 0) < 60
            ORDER BY p.id
            """
        ).fetchall()
        for row in low_prongs:
            gaps_list.append(
                {
                    "gap": f"niw:{row['title_key']}",
                    "severity": "high" if int(row["score"]) < 40 else "medium",
                    "related_criteria": str(row["code"]),
                    "missing_evidences": "niw_supporting_evidence",
                    "suggested_task": "action.raise_niw_prong",
                    "priority": "high",
                }
            )

        evidence_categories = {
            str(row[0])
            for row in conn.execute("SELECT DISTINCT TRIM(COALESCE(category, '')) FROM evidences WHERE TRIM(COALESCE(category, '')) <> ''")
        }
        expected_categories = {item["category_key"] for item in ASSESSMENT_DIMENSIONS}
        for missing_category in sorted(expected_categories - evidence_categories):
            gaps_list.append(
                {
                    "gap": "missing_category_evidence",
                    "severity": "medium",
                    "related_criteria": missing_category,
                    "missing_evidences": missing_category,
                    "suggested_task": "action.collect_category_evidence",
                    "priority": "medium",
                }
            )

        overdue_items = conn.execute(
            """
            SELECT title, related_criteria
            FROM roadmap_items
            WHERE target_date <> ''
              AND date(target_date) < date('now')
              AND status NOT IN ('completed')
            ORDER BY target_date
            """
        ).fetchall()
        for row in overdue_items:
            gaps_list.append(
                {
                    "gap": f"overdue:{row['title']}",
                    "severity": "high",
                    "related_criteria": row["related_criteria"] or "roadmap",
                    "missing_evidences": "timeline_delay",
                    "suggested_task": "action.replan_overdue_task",
                    "priority": "high",
                }
            )

        blocked_items = conn.execute(
            """
            SELECT title, related_criteria
            FROM roadmap_items
            WHERE status = 'blocked'
            ORDER BY id DESC
            """
        ).fetchall()
        for row in blocked_items:
            gaps_list.append(
                {
                    "gap": f"blocked:{row['title']}",
                    "severity": "critical",
                    "related_criteria": row["related_criteria"] or "roadmap",
                    "missing_evidences": "blocked_execution",
                    "suggested_task": "action.unblock_task",
                    "priority": "critical",
                }
            )

        return gaps_list

    def render_evidence_form(lang: str, data: dict[str, Any]) -> str:
        form_template = """
        <label>{{ t('evidence.field.title', lang) }}
            <input type="text" name="title" value="{{ data.title }}" required />
        </label>
        <label>{{ t('evidence.field.type', lang) }}
            <select name="evidence_type">
                {% for opt in type_options %}
                    <option value="{{ opt }}" {% if data.evidence_type == opt %}selected{% endif %}>{{ t('evidence.type.' ~ opt, lang) }}</option>
                {% endfor %}
            </select>
        </label>
        <label>{{ t('evidence.field.category', lang) }}
            <input type="text" name="category" value="{{ data.category }}" required />
        </label>
        <label>{{ t('evidence.field.description', lang) }}
            <textarea name="description" rows="3">{{ data.description }}</textarea>
        </label>
        <label>{{ t('evidence.field.link_or_path', lang) }}
            <input type="text" name="link_or_path" value="{{ data.link_or_path }}" />
        </label>
        <label>{{ t('evidence.field.date', lang) }}
            <input type="date" name="evidence_date" value="{{ data.evidence_date }}" />
        </label>
        <label>{{ t('evidence.field.relevance', lang) }}
            <select name="relevance">
                {% for opt in range(1, 6) %}
                    <option value="{{ opt }}" {% if data.relevance|int == opt %}selected{% endif %}>{{ opt }}</option>
                {% endfor %}
            </select>
        </label>
        <label>{{ t('evidence.field.related_criteria', lang) }}
            <input type="text" name="related_criteria" value="{{ data.related_criteria }}" />
        </label>
        <label>{{ t('evidence.field.status', lang) }}
            <select name="status">
                {% for opt in status_options %}
                    <option value="{{ opt }}" {% if data.status == opt %}selected{% endif %}>{{ t('evidence.status.' ~ opt, lang) }}</option>
                {% endfor %}
            </select>
        </label>
        <label>{{ t('evidence.field.notes', lang) }}
            <textarea name="notes" rows="3">{{ data.notes }}</textarea>
        </label>
        <label>
            <input type="checkbox" name="can_send_to_ai" {% if data.can_send_to_ai %}checked{% endif %} />
            {{ t('evidence.field.can_send_to_ai', lang) }}
        </label>
        """
        return render_template_string(
            form_template,
            lang=lang,
            t=t,
            data=data,
            type_options=EVIDENCE_TYPES,
            status_options=EVIDENCE_STATUS_OPTIONS,
        )

    def render_roadmap_form(lang: str, data: dict[str, Any]) -> str:
        form_template = """
        <label>{{ t('roadmap.field.title', lang) }}
            <input type="text" name="title" value="{{ data.title }}" required />
        </label>
        <label>{{ t('roadmap.field.description', lang) }}
            <textarea name="description" rows="3">{{ data.description }}</textarea>
        </label>
        <label>{{ t('roadmap.field.category', lang) }}
            <input type="text" name="category" value="{{ data.category }}" required />
        </label>
        <label>{{ t('roadmap.field.priority', lang) }}
            <select name="priority">
                {% for opt in priority_options %}
                    <option value="{{ opt }}" {% if data.priority == opt %}selected{% endif %}>{{ t('roadmap.priority.' ~ opt, lang) }}</option>
                {% endfor %}
            </select>
        </label>
        <label>{{ t('roadmap.field.horizon', lang) }}
            <select name="horizon">
                {% for opt in horizon_options %}
                    <option value="{{ opt }}" {% if data.horizon == opt %}selected{% endif %}>{{ t('roadmap.horizon.' ~ opt, lang) }}</option>
                {% endfor %}
            </select>
        </label>
        <label>{{ t('roadmap.field.status', lang) }}
            <select name="status">
                {% for opt in status_options %}
                    <option value="{{ opt }}" {% if data.status == opt %}selected{% endif %}>{{ t('roadmap.status.' ~ opt, lang) }}</option>
                {% endfor %}
            </select>
        </label>
        <label>{{ t('roadmap.field.target_date', lang) }}
            <input type="date" name="target_date" value="{{ data.target_date }}" />
        </label>
        <label>{{ t('roadmap.field.estimated_effort', lang) }}
            <input type="text" name="estimated_effort" value="{{ data.estimated_effort }}" />
        </label>
        <label>{{ t('roadmap.field.estimated_impact', lang) }}
            <input type="text" name="estimated_impact" value="{{ data.estimated_impact }}" />
        </label>
        <label>{{ t('roadmap.field.related_criteria', lang) }}
            <input type="text" name="related_criteria" value="{{ data.related_criteria }}" />
        </label>
        """
        return render_template_string(
            form_template,
            lang=lang,
            t=t,
            data=data,
            priority_options=ROADMAP_PRIORITY_OPTIONS,
            horizon_options=ROADMAP_HORIZON_OPTIONS,
            status_options=ROADMAP_STATUS_OPTIONS,
        )

    def build_dashboard_summary() -> dict[str, Any]:
        conn = get_db()
        assessment_questions = fetch_assessment_questions_with_answers()
        eb2_score = calculate_eb2_scores(assessment_questions)

        evidence_count = conn.execute("SELECT COUNT(*) FROM evidences").fetchone()[0]
        roadmap_total = conn.execute("SELECT COUNT(*) FROM roadmap_items").fetchone()[0]
        if roadmap_total == 0:
            roadmap_total = conn.execute("SELECT COUNT(*) FROM roadmap_tasks").fetchone()[0]
        tasks_completed = conn.execute(
            "SELECT COUNT(*) FROM roadmap_items WHERE status IN ('completed')"
        ).fetchone()[0]
        tasks_pending = roadmap_total - tasks_completed

        niw_assessments = fetch_niw_assessments()
        niw_score = int(round(sum(item["score"] for item in niw_assessments) / max(1, len(niw_assessments))))

        gap_count = len(build_gaps_summary())
        roadmap_progress = int(round((tasks_completed / max(1, roadmap_total)) * 100))

        alerts: list[str] = []
        if eb2_score["overall_score"] < 60:
            alerts.append("dashboard.alert.low_eb2")
        if niw_score < 60:
            alerts.append("dashboard.alert.low_niw")
        if evidence_count == 0:
            alerts.append("dashboard.alert.no_evidence")
        if tasks_pending > 0:
            alerts.append("dashboard.alert.pending_tasks")

        return {
            "eb2": eb2_score,
            "niw_score": niw_score,
            "classification": classify_readiness(eb2_score["overall_score"]),
            "evidence_count": evidence_count,
            "gap_count": gap_count,
            "tasks_pending": tasks_pending,
            "tasks_completed": tasks_completed,
            "roadmap_progress": roadmap_progress,
            "alerts": alerts,
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

    @app.route("/dashboard")
    def dashboard() -> str:
        lang = get_selected_language()
        summary = build_dashboard_summary()
        body = """
        <h1>{{ t('dashboard.title', lang) }}</h1>
        <p>{{ t('dashboard.subtitle', lang) }}</p>
        <div class="cards">
            <article class="card"><h3>{{ t('dashboard.card.overall_score', lang) }}</h3><p class="metric">{{ summary.eb2.overall_score }}</p></article>
            <article class="card">
                <h3>{{ t('dashboard.card.classification', lang) }}</h3>
                <p class="metric">
                    <span class="badge {{ summary.classification }}">{{ t('classification.' ~ summary.classification, lang) }}</span>
                </p>
            </article>
            <article class="card"><h3>{{ t('dashboard.card.evidences', lang) }}</h3><p class="metric">{{ summary.evidence_count }}</p></article>
            <article class="card"><h3>{{ t('dashboard.card.gaps', lang) }}</h3><p class="metric">{{ summary.gap_count }}</p></article>
            <article class="card"><h3>{{ t('dashboard.card.tasks_pending', lang) }}</h3><p class="metric">{{ summary.tasks_pending }}</p></article>
            <article class="card"><h3>{{ t('dashboard.card.tasks_completed', lang) }}</h3><p class="metric">{{ summary.tasks_completed }}</p></article>
            <article class="card"><h3>{{ t('dashboard.card.roadmap_progress', lang) }}</h3><p class="metric">{{ summary.roadmap_progress }}%</p></article>
            <article class="card"><h3>{{ t('dashboard.card.niw_score', lang) }}</h3><p class="metric">{{ summary.niw_score }}</p></article>
        </div>

        <h2>{{ t('dashboard.section.dimensions', lang) }}</h2>
        <div class="cards">
            {% for category_key, score in summary.eb2.dimension_scores.items() %}
                <article class="card">
                    <h3>{{ t(category_key, lang) }}</h3>
                    <p class="metric">{{ score }}</p>
                </article>
            {% endfor %}
        </div>

        <h2>{{ t('dashboard.section.alerts', lang) }}</h2>
        {% if summary.alerts %}
            <ul>
            {% for alert in summary.alerts %}
                <li>{{ t(alert, lang) }}</li>
            {% endfor %}
            </ul>
        {% else %}
            <p class="small">{{ t('dashboard.alert.none', lang) }}</p>
        {% endif %}
        """
        return render_page(lang, t("dashboard.title", lang), body, summary=summary)

    @app.route("/assessment", methods=["GET", "POST"])
    def assessment() -> str:
        lang = get_selected_language()
        saved = False
        if request.method == "POST":
            question_ids = request.form.getlist("question_id")
            for raw_id in question_ids:
                question_id = int(raw_id)
                score_value = request.form.get(f"score_{question_id}", "")
                score = int(score_value) if score_value.strip() else None
                justification = request.form.get(f"justification_{question_id}", "").strip()
                evidence_refs = request.form.get(f"evidence_refs_{question_id}", "").strip()
                upsert_assessment_answer(question_id, score, justification, evidence_refs)
            saved = True

        questions = fetch_assessment_questions_with_answers()
        score_data = calculate_eb2_scores(questions)
        body = """
        <h1>{{ t('assessment.title', lang) }}</h1>
        <p>{{ t('assessment.subtitle', lang) }}</p>
        {% if saved %}
        <div class="disclaimer">{{ t('assessment.saved', lang) }}</div>
        {% endif %}
        <form method="post" action="{{ url_for('assessment', lang=lang) }}">
            {% for question in questions %}
                <article class="card" style="margin-bottom: 0.75rem;">
                    <input type="hidden" name="question_id" value="{{ question.id }}" />
                    <p><strong>{{ t(question.category_key, lang) }}</strong> <span class="small">({{ t('assessment.weight', lang) }}: {{ question.weight }})</span></p>
                    <p>{{ t(question.question_key, lang) }}</p>
                    <label>{{ t('assessment.score', lang) }}
                        <select name="score_{{ question.id }}">
                            <option value="">-</option>
                            {% for value in range(0, 6) %}
                                <option value="{{ value }}" {% if question.score == value %}selected{% endif %}>{{ value }}</option>
                            {% endfor %}
                        </select>
                    </label>
                    <p><span class="small">{{ t('assessment.status', lang) }}:</span>
                        <span class="badge {{ question.status }}">{{ t('status.' ~ question.status, lang) }}</span>
                    </p>
                    <label>{{ t('assessment.justification', lang) }}<br />
                        <textarea name="justification_{{ question.id }}" rows="2" style="width: 100%;">{{ question.justification }}</textarea>
                    </label>
                    <label>{{ t('assessment.evidence_refs', lang) }}<br />
                        <input type="text" name="evidence_refs_{{ question.id }}" value="{{ question.evidence_refs }}" style="width: 100%;" />
                    </label>
                </article>
            {% endfor %}
            <button type="submit">{{ t('assessment.save', lang) }}</button>
        </form>

        <h2>{{ t('assessment.summary.title', lang) }}</h2>
        <p><strong>{{ t('dashboard.card.overall_score', lang) }}:</strong> {{ score_data.overall_score }}</p>
        <p><strong>{{ t('dashboard.card.classification', lang) }}:</strong> <span class="badge {{ score_data.classification }}">{{ t('classification.' ~ score_data.classification, lang) }}</span></p>
        """
        return render_page(lang, t("assessment.title", lang), body, questions=questions, score_data=score_data, saved=saved)

    @app.route("/niw", methods=["GET", "POST"])
    def niw() -> str:
        lang = get_selected_language()
        saved = False
        if request.method == "POST":
            prong_codes = request.form.getlist("prong_code")
            for code in prong_codes:
                score = int(request.form.get(f"score_{code}", "0") or "0")
                observations = request.form.get(f"observations_{code}", "").strip()
                gaps = request.form.get(f"gaps_{code}", "").strip()
                recommendations = request.form.get(f"recommendations_{code}", "").strip()
                suggested_tasks = request.form.get(f"tasks_{code}", "").strip()
                upsert_niw_assessment(code, score, observations, gaps, recommendations, suggested_tasks)
            saved = True

        prongs = fetch_niw_assessments()
        body = """
        <h1>{{ t('niw.title', lang) }}</h1>
        <p>{{ t('niw.subtitle', lang) }}</p>
        {% if saved %}
        <div class="disclaimer">{{ t('niw.saved', lang) }}</div>
        {% endif %}
        <form method="post" action="{{ url_for('niw', lang=lang) }}">
            {% for prong in prongs %}
                <article class="card" style="margin-bottom: 0.75rem;">
                    <input type="hidden" name="prong_code" value="{{ prong.code }}" />
                    <h3>{{ t(prong.title_key, lang) }}</h3>
                    <p class="small">{{ t(prong.description_key, lang) }}</p>
                    <label>{{ t('niw.field.score', lang) }}
                        <input type="number" min="0" max="100" name="score_{{ prong.code }}" value="{{ prong.score }}" />
                    </label>
                    <label>{{ t('niw.field.observations', lang) }}<br />
                        <textarea name="observations_{{ prong.code }}" rows="2" style="width: 100%;">{{ prong.observations }}</textarea>
                    </label>
                    <label>{{ t('niw.field.gaps', lang) }}<br />
                        <textarea name="gaps_{{ prong.code }}" rows="2" style="width: 100%;">{{ prong.gaps }}</textarea>
                    </label>
                    <label>{{ t('niw.field.recommendations', lang) }}<br />
                        <textarea name="recommendations_{{ prong.code }}" rows="2" style="width: 100%;">{{ prong.recommendations }}</textarea>
                    </label>
                    <label>{{ t('niw.field.tasks', lang) }}<br />
                        <textarea name="tasks_{{ prong.code }}" rows="2" style="width: 100%;">{{ prong.suggested_tasks }}</textarea>
                    </label>
                </article>
            {% endfor %}
            <button type="submit">{{ t('niw.save', lang) }}</button>
        </form>
        """
        return render_page(lang, t("niw.title", lang), body, prongs=prongs, saved=saved)

    @app.route("/evidences")
    def evidences() -> str:
        lang = get_selected_language()
        selected_status = request.args.get("status", "").strip()
        selected_category = request.args.get("category", "").strip()
        items = fetch_evidence_list(selected_status, selected_category)
        categories = sorted({str(item["category"]) for item in fetch_evidence_list() if str(item["category"]).strip()})
        body = """
        <h1>{{ t('evidences.title', lang) }}</h1>
        <p>{{ t('evidences.subtitle', lang) }}</p>
        <p class="small">{{ t('app.privacy_notice', lang) }}</p>
        <form method="get" action="{{ url_for('evidences') }}">
            <input type="hidden" name="lang" value="{{ lang }}" />
            <div class="cards">
                <article class="card">
                    <label>{{ t('filter.status', lang) }}
                        <select name="status">
                            <option value="">{{ t('filter.all', lang) }}</option>
                            {% for opt in statuses %}
                                <option value="{{ opt }}" {% if selected_status == opt %}selected{% endif %}>{{ t('evidence.status.' ~ opt, lang) }}</option>
                            {% endfor %}
                        </select>
                    </label>
                </article>
                <article class="card">
                    <label>{{ t('filter.category', lang) }}
                        <select name="category">
                            <option value="">{{ t('filter.all', lang) }}</option>
                            {% for cat in categories %}
                                <option value="{{ cat }}" {% if selected_category == cat %}selected{% endif %}>{{ cat }}</option>
                            {% endfor %}
                        </select>
                    </label>
                </article>
            </div>
            <button type="submit">{{ t('filter.apply', lang) }}</button>
            <a href="{{ url_for('evidence_new', lang=lang) }}">{{ t('evidences.new', lang) }}</a>
        </form>
        <table>
            <thead>
                <tr>
                    <th>{{ t('evidence.field.title', lang) }}</th>
                    <th>{{ t('evidence.field.type', lang) }}</th>
                    <th>{{ t('evidence.field.category', lang) }}</th>
                    <th>{{ t('evidence.field.status', lang) }}</th>
                    <th>{{ t('evidence.field.relevance', lang) }}</th>
                    <th>{{ t('evidence.field.can_send_to_ai', lang) }}</th>
                    <th>{{ t('common.actions', lang) }}</th>
                </tr>
            </thead>
            <tbody>
                {% for item in items %}
                    <tr>
                        <td>{{ item.title }}</td>
                        <td>{{ t('evidence.type.' ~ item.evidence_type, lang) }}</td>
                        <td>{{ item.category }}</td>
                        <td><span class="badge {{ item.status }}">{{ t('evidence.status.' ~ item.status, lang) }}</span></td>
                        <td>{{ item.relevance }}/5</td>
                        <td>{{ t('common.yes' if item.can_send_to_ai else 'common.no', lang) }}</td>
                        <td>
                            <div class="actions">
                                <a href="{{ url_for('evidence_edit', evidence_id=item.id, lang=lang) }}">{{ t('common.edit', lang) }}</a>
                                <form method="post" action="{{ url_for('evidence_delete', evidence_id=item.id, lang=lang) }}">
                                    <button type="submit">{{ t('common.delete', lang) }}</button>
                                </form>
                            </div>
                        </td>
                    </tr>
                {% endfor %}
            </tbody>
        </table>
        """
        return render_page(
            lang,
            t("evidences.title", lang),
            body,
            items=items,
            categories=categories,
            selected_status=selected_status,
            selected_category=selected_category,
            statuses=EVIDENCE_STATUS_OPTIONS,
        )

    @app.route("/evidences/new", methods=["GET", "POST"])
    def evidence_new() -> str:
        lang = get_selected_language()
        if request.method == "POST":
            upsert_evidence(None, dict(request.form))
            return redirect(url_for("evidences", lang=lang))

        form_data = {
            "title": "",
            "evidence_type": "Outro",
            "category": "",
            "description": "",
            "link_or_path": "",
            "evidence_date": "",
            "relevance": 3,
            "related_criteria": "",
            "status": "coletar",
            "notes": "",
            "can_send_to_ai": 0,
        }
        body = """
        <h1>{{ t('evidences.new', lang) }}</h1>
        <form method="post" action="{{ url_for('evidence_new', lang=lang) }}">
            {{ evidence_form|safe }}
            <button type="submit">{{ t('common.save', lang) }}</button>
        </form>
        """
        return render_page(
            lang,
            t("evidences.new", lang),
            body,
            evidence_form=render_evidence_form(lang, form_data),
        )

    @app.route("/evidences/<int:evidence_id>/edit", methods=["GET", "POST"])
    def evidence_edit(evidence_id: int) -> str:
        lang = get_selected_language()
        evidence = fetch_evidence_by_id(evidence_id)
        if not evidence:
            return redirect(url_for("evidences", lang=lang))
        if request.method == "POST":
            upsert_evidence(evidence_id, dict(request.form))
            return redirect(url_for("evidences", lang=lang))
        body = """
        <h1>{{ t('evidences.edit', lang) }}</h1>
        <form method="post" action="{{ url_for('evidence_edit', evidence_id=evidence.id, lang=lang) }}">
            {{ evidence_form|safe }}
            <button type="submit">{{ t('common.save', lang) }}</button>
        </form>
        """
        return render_page(
            lang,
            t("evidences.edit", lang),
            body,
            evidence=evidence,
            evidence_form=render_evidence_form(lang, evidence),
        )

    @app.route("/evidences/<int:evidence_id>/delete", methods=["POST"])
    def evidence_delete(evidence_id: int) -> Any:
        lang = get_selected_language()
        delete_evidence(evidence_id)
        return redirect(url_for("evidences", lang=lang))

    @app.route("/roadmap")
    def roadmap() -> str:
        lang = get_selected_language()
        selected_status = request.args.get("status", "").strip()
        selected_category = request.args.get("category", "").strip()
        selected_horizon = request.args.get("horizon", "").strip()
        items = fetch_roadmap_items(selected_status, selected_category, selected_horizon)
        categories = sorted({str(item["category"]) for item in fetch_roadmap_items() if str(item["category"]).strip()})
        body = """
        <h1>{{ t('roadmap.title', lang) }}</h1>
        <p>{{ t('roadmap.subtitle', lang) }}</p>
        <form method="get" action="{{ url_for('roadmap') }}">
            <input type="hidden" name="lang" value="{{ lang }}" />
            <div class="cards">
                <article class="card">
                    <label>{{ t('filter.status', lang) }}
                        <select name="status">
                            <option value="">{{ t('filter.all', lang) }}</option>
                            {% for opt in status_options %}
                                <option value="{{ opt }}" {% if selected_status == opt %}selected{% endif %}>{{ t('roadmap.status.' ~ opt, lang) }}</option>
                            {% endfor %}
                        </select>
                    </label>
                </article>
                <article class="card">
                    <label>{{ t('filter.category', lang) }}
                        <select name="category">
                            <option value="">{{ t('filter.all', lang) }}</option>
                            {% for cat in categories %}
                                <option value="{{ cat }}" {% if selected_category == cat %}selected{% endif %}>{{ cat }}</option>
                            {% endfor %}
                        </select>
                    </label>
                </article>
                <article class="card">
                    <label>{{ t('filter.horizon', lang) }}
                        <select name="horizon">
                            <option value="">{{ t('filter.all', lang) }}</option>
                            {% for opt in horizon_options %}
                                <option value="{{ opt }}" {% if selected_horizon == opt %}selected{% endif %}>{{ t('roadmap.horizon.' ~ opt, lang) }}</option>
                            {% endfor %}
                        </select>
                    </label>
                </article>
            </div>
            <button type="submit">{{ t('filter.apply', lang) }}</button>
            <a href="{{ url_for('roadmap_new', lang=lang) }}">{{ t('roadmap.new', lang) }}</a>
        </form>

        {% for horizon in horizon_options %}
            <h2>{{ t('roadmap.horizon.' ~ horizon, lang) }}</h2>
            <table>
                <thead>
                    <tr>
                        <th>{{ t('roadmap.field.title', lang) }}</th>
                        <th>{{ t('roadmap.field.priority', lang) }}</th>
                        <th>{{ t('roadmap.field.status', lang) }}</th>
                        <th>{{ t('roadmap.field.target_date', lang) }}</th>
                        <th>{{ t('common.actions', lang) }}</th>
                    </tr>
                </thead>
                <tbody>
                    {% for item in items if item.horizon == horizon %}
                        <tr>
                            <td>{{ item.title }}<br /><span class="small">{{ item.category }}</span></td>
                            <td><span class="badge {{ item.priority }}">{{ t('roadmap.priority.' ~ item.priority, lang) }}</span></td>
                            <td><span class="badge {{ item.status }}">{{ t('roadmap.status.' ~ item.status, lang) }}</span></td>
                            <td>{{ item.target_date or '-' }}</td>
                            <td>
                                <div class="actions">
                                    <a href="{{ url_for('roadmap_edit', item_id=item.id, lang=lang) }}">{{ t('common.edit', lang) }}</a>
                                    <form method="post" action="{{ url_for('roadmap_delete', item_id=item.id, lang=lang) }}">
                                        <button type="submit">{{ t('common.delete', lang) }}</button>
                                    </form>
                                </div>
                            </td>
                        </tr>
                    {% endfor %}
                </tbody>
            </table>
        {% endfor %}
        """
        return render_page(
            lang,
            t("roadmap.title", lang),
            body,
            items=items,
            categories=categories,
            selected_status=selected_status,
            selected_category=selected_category,
            selected_horizon=selected_horizon,
            status_options=ROADMAP_STATUS_OPTIONS,
            horizon_options=ROADMAP_HORIZON_OPTIONS,
        )

    @app.route("/roadmap/new", methods=["GET", "POST"])
    def roadmap_new() -> str:
        lang = get_selected_language()
        if request.method == "POST":
            upsert_roadmap_item(None, dict(request.form))
            return redirect(url_for("roadmap", lang=lang))

        form_data = {
            "title": "",
            "description": "",
            "category": "",
            "priority": "medium",
            "horizon": "30_90",
            "status": "backlog",
            "target_date": "",
            "estimated_effort": "",
            "estimated_impact": "",
            "related_criteria": "",
        }
        body = """
        <h1>{{ t('roadmap.new', lang) }}</h1>
        <form method="post" action="{{ url_for('roadmap_new', lang=lang) }}">
            {{ roadmap_form|safe }}
            <button type="submit">{{ t('common.save', lang) }}</button>
        </form>
        """
        return render_page(lang, t("roadmap.new", lang), body, roadmap_form=render_roadmap_form(lang, form_data))

    @app.route("/roadmap/<int:item_id>/edit", methods=["GET", "POST"])
    def roadmap_edit(item_id: int) -> str:
        lang = get_selected_language()
        item = fetch_roadmap_item_by_id(item_id)
        if not item:
            return redirect(url_for("roadmap", lang=lang))
        if request.method == "POST":
            upsert_roadmap_item(item_id, dict(request.form))
            return redirect(url_for("roadmap", lang=lang))

        body = """
        <h1>{{ t('roadmap.edit', lang) }}</h1>
        <form method="post" action="{{ url_for('roadmap_edit', item_id=item.id, lang=lang) }}">
            {{ roadmap_form|safe }}
            <button type="submit">{{ t('common.save', lang) }}</button>
        </form>
        """
        return render_page(lang, t("roadmap.edit", lang), body, item=item, roadmap_form=render_roadmap_form(lang, item))

    @app.route("/roadmap/<int:item_id>/delete", methods=["POST"])
    def roadmap_delete(item_id: int) -> Any:
        lang = get_selected_language()
        delete_roadmap_item(item_id)
        return redirect(url_for("roadmap", lang=lang))

    @app.route("/gaps")
    def gaps() -> str:
        lang = get_selected_language()
        items = build_gaps_summary()
        body = """
        <h1>{{ t('gaps.title', lang) }}</h1>
        <p>{{ t('gaps.subtitle', lang) }}</p>
        <table>
            <thead>
                <tr>
                    <th>{{ t('gaps.field.gap', lang) }}</th>
                    <th>{{ t('gaps.field.severity', lang) }}</th>
                    <th>{{ t('gaps.field.related_criteria', lang) }}</th>
                    <th>{{ t('gaps.field.missing_evidences', lang) }}</th>
                    <th>{{ t('gaps.field.suggested_task', lang) }}</th>
                    <th>{{ t('gaps.field.priority', lang) }}</th>
                </tr>
            </thead>
            <tbody>
                {% for item in items %}
                    <tr>
                        <td>{{ t(item.gap, lang) if item.gap in locale_keys else item.gap }}</td>
                        <td><span class="badge {{ item.severity }}">{{ t('severity.' ~ item.severity, lang) }}</span></td>
                        <td>{{ t(item.related_criteria, lang) if item.related_criteria in locale_keys else item.related_criteria }}</td>
                        <td>{{ t(item.missing_evidences, lang) if item.missing_evidences in locale_keys else item.missing_evidences }}</td>
                        <td>{{ t(item.suggested_task, lang) if item.suggested_task in locale_keys else item.suggested_task }}</td>
                        <td><span class="badge {{ item.priority }}">{{ t('roadmap.priority.' ~ item.priority, lang) }}</span></td>
                    </tr>
                {% endfor %}
            </tbody>
        </table>
        """
        return render_page(
            lang,
            t("gaps.title", lang),
            body,
            items=items,
            locale_keys=set(load_locale(lang).keys()),
        )

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
