import hashlib
import json
import os
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from dotenv import load_dotenv
from flask import Flask, g, redirect, render_template_string, request, url_for
import requests

load_dotenv()

BASE_DIR = Path(__file__).parent
DEFAULT_DB_PATH = str(BASE_DIR / "data" / "app.db")
DEFAULT_LOCALE = "pt-BR"
FALLBACK_LOCALE = "en-US"
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

ENDEAVOR_STATUS_OPTIONS = ["draft", "in_review", "ready"]
AUTHORITY_STATUS_OPTIONS = ["planned", "in_progress", "active", "recognized"]
GITHUB_PROJECT_STATUS_OPTIONS = ["idea", "building", "published", "maintenance"]
LINKEDIN_CONTENT_TYPE_OPTIONS = ["short_post", "article", "carousel", "tutorial", "case_study", "technical_reflection"]
LINKEDIN_CONTENT_STATUS_OPTIONS = ["draft", "planned", "published"]
LINKEDIN_CONTENT_OBJECTIVE_OPTIONS = ["authority", "community", "education", "portfolio", "networking"]
RECOMMENDER_STRENGTH_OPTIONS = ["low", "medium", "high"]
RECOMMENDER_INDEPENDENCE_OPTIONS = ["independent", "partially_independent", "direct_manager", "peer"]
RECOMMENDER_STATUS_OPTIONS = ["prospect", "contacted", "confirmed", "declined"]

def load_locale(locale: str) -> dict[str, str]:
    locale_path = BASE_DIR / "locales" / f"{locale}.json"
    fallback_path = BASE_DIR / "locales" / f"{FALLBACK_LOCALE}.json"
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

    default_endeavor = (
        "Arquiteturas seguras e governadas de agentes de IA generativa",
        "Desenvolvimento e disseminacao de arquiteturas seguras, governadas e escalaveis de agentes de IA generativa para acelerar a transformacao digital de empresas, aumentar produtividade, reduzir riscos operacionais e melhorar a adocao responsavel de IA em setores estrategicos.",
        "Apoiar a adocao responsavel de IA em ambientes corporativos e setores estrategicos por meio de boas praticas tecnicas replicaveis.",
        "arquitetura de agentes de IA generativa",
        "Aceleracao de transformacao digital com governanca e seguranca para agentes de IA generativa.",
        "Desenvolvimento e disseminacao de arquiteturas seguras, governadas e escalaveis de agentes de IA generativa para acelerar a transformacao digital de empresas, aumentar produtividade, reduzir riscos operacionais e melhorar a adocao responsavel de IA em setores estrategicos.",
        "ready",
    )
    cursor.execute(
        """
        INSERT OR IGNORE INTO proposed_endeavor
        (title, summary, impact, area, short_version, long_version, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        default_endeavor,
    )

    cursor.execute(
        """
        INSERT OR IGNORE INTO github_projects
        (name, summary, solved_problem, technologies, repo_url, status, potential_impact, generated_evidence, related_articles, related_criteria, stars)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "EB2-NIW Readiness Studio",
            "Ferramenta local-first para auto-organizacao de evidencias, gaps e roadmap de prontidao EB-2/NIW.",
            "Baixa rastreabilidade de evidencias e lacunas para planejamento tecnico-profissional.",
            "Python, Flask, SQLite, i18n PT-BR/EN-US",
            "https://github.com/demo/eb2-niw-readiness-studio",
            "published",
            "Organizacao disciplinada de evidencias e melhoria da narrativa tecnica publica.",
            "Arquitetura documentada, testes criticos, roteiro de evolucao e compliance de privacidade.",
            "Como construir um tracker local-first para prontidao profissional",
            "assessment.category.public_projects",
            42,
        ),
    )

    cursor.execute(
        """
        INSERT OR IGNORE INTO authority_plan
        (channel, objective, cadence, status, main_theme, target_communities, planned_articles, planned_talks, planned_github_repos, events, people_recommenders, public_evidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "LinkedIn + GitHub + Comunidades tecnicas",
            "Consolidar autoridade tecnica em IA generativa aplicada com foco em governanca, seguranca e impacto.",
            "quinzenal",
            "planned",
            "Arquiteturas governadas para agentes de IA generativa",
            "Comunidades de arquitetura, engenharia de dados e lideranca tecnica",
            "Serie sobre governanca de IA, observabilidade e seguranca",
            "Talks em meetups e eventos tecnicos",
            "Demos locais-first para organizacao de evidencias",
            "Meetups de engenharia e AI Summit comunitario",
            "Mentores tecnicos e lideres de times parceiros",
            "Repositorios publicos, artigos, talks e estudos de caso sinteticos",
        ),
    )

    linkedin_ideas = [
        (
            "Como organizar um roadmap tecnico para fortalecer um perfil EB-2/NIW",
            "Tema base para roadmap tecnico com foco em evidencia publica.",
        ),
        (
            "Por que evidencias publicas importam para profissionais de tecnologia",
            "Conectar autoridade tecnica e impacto comprovavel.",
        ),
        (
            "Construindo uma ferramenta local-first com Python, SQLite e IA plugavel",
            "Arquitetura pragmatica para dados sensiveis em ambientes locais.",
        ),
        (
            "Como agentes de IA podem apoiar assessments profissionais sem substituir especialistas",
            "Explicar limites e uso responsavel de IA em contexto educacional.",
        ),
        (
            "OpenAI, Azure OpenAI e Ollama: criando uma arquitetura simples de providers plugaveis",
            "Comparativo de contrato unico para providers de IA.",
        ),
        (
            "De arquiteto de solucoes a autoridade tecnica: como transformar experiencia em evidencia publica",
            "Narrativa de carreira com artefatos verificaveis.",
        ),
        (
            "Como documentar impacto tecnico em projetos corporativos de IA generativa",
            "Template de impacto para portfolio tecnico.",
        ),
        (
            "O que aprendi criando um readiness tracker para carreira internacional",
            "Licoes tecnicas e de produto do projeto.",
        ),
    ]
    cursor.executemany(
        """
        INSERT OR IGNORE INTO linkedin_content (title, idea, content_type, status, objective)
        VALUES (?, ?, 'short_post', 'planned', 'authority')
        """,
        linkedin_ideas,
    )

    cursor.execute(
        """
        INSERT OR IGNORE INTO recommenders
        (name, relationship, organization, role_title, email, letter_strength, independence, validation_area, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "Recomendador Demo",
            "Mentoria tecnica",
            "Empresa Exemplo",
            "Gerente de Engenharia",
            "",
            "medium",
            "independent",
            "Lideranca tecnica e impacto em IA aplicada",
            "prospect",
            "Contato ficticio para demonstracao. Nao usar dados reais em repositorio publico.",
        ),
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
                area TEXT,
                problem_to_solve TEXT,
                impacted_sector TEXT,
                technologies TEXT,
                relevance TEXT,
                experience_evidence TEXT,
                expected_impact TEXT,
                broader_importance TEXT,
                short_version TEXT,
                long_version TEXT,
                status TEXT NOT NULL DEFAULT 'draft',
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
                status TEXT NOT NULL DEFAULT 'planned',
                main_theme TEXT,
                target_communities TEXT,
                planned_articles TEXT,
                planned_talks TEXT,
                planned_github_repos TEXT,
                events TEXT,
                people_recommenders TEXT,
                public_evidence TEXT
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
                solved_problem TEXT,
                technologies TEXT,
                status TEXT NOT NULL DEFAULT 'idea',
                potential_impact TEXT,
                generated_evidence TEXT,
                related_articles TEXT,
                related_criteria TEXT,
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
                content_type TEXT NOT NULL DEFAULT 'short_post',
                theme TEXT,
                planned_date TEXT,
                published_link TEXT,
                related_evidence TEXT,
                objective TEXT NOT NULL DEFAULT 'authority',
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
                notes TEXT,
                organization TEXT,
                role_title TEXT,
                email TEXT,
                letter_strength TEXT NOT NULL DEFAULT 'medium',
                independence TEXT NOT NULL DEFAULT 'independent',
                validation_area TEXT
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

        _ensure_column(conn, "proposed_endeavor", "area", "TEXT")
        _ensure_column(conn, "proposed_endeavor", "problem_to_solve", "TEXT")
        _ensure_column(conn, "proposed_endeavor", "impacted_sector", "TEXT")
        _ensure_column(conn, "proposed_endeavor", "technologies", "TEXT")
        _ensure_column(conn, "proposed_endeavor", "relevance", "TEXT")
        _ensure_column(conn, "proposed_endeavor", "experience_evidence", "TEXT")
        _ensure_column(conn, "proposed_endeavor", "expected_impact", "TEXT")
        _ensure_column(conn, "proposed_endeavor", "broader_importance", "TEXT")
        _ensure_column(conn, "proposed_endeavor", "short_version", "TEXT")
        _ensure_column(conn, "proposed_endeavor", "long_version", "TEXT")
        _ensure_column(conn, "proposed_endeavor", "status", "TEXT NOT NULL DEFAULT 'draft'")

        _ensure_column(conn, "authority_plan", "main_theme", "TEXT")
        _ensure_column(conn, "authority_plan", "target_communities", "TEXT")
        _ensure_column(conn, "authority_plan", "planned_articles", "TEXT")
        _ensure_column(conn, "authority_plan", "planned_talks", "TEXT")
        _ensure_column(conn, "authority_plan", "planned_github_repos", "TEXT")
        _ensure_column(conn, "authority_plan", "events", "TEXT")
        _ensure_column(conn, "authority_plan", "people_recommenders", "TEXT")
        _ensure_column(conn, "authority_plan", "public_evidence", "TEXT")

        _ensure_column(conn, "github_projects", "solved_problem", "TEXT")
        _ensure_column(conn, "github_projects", "technologies", "TEXT")
        _ensure_column(conn, "github_projects", "status", "TEXT NOT NULL DEFAULT 'idea'")
        _ensure_column(conn, "github_projects", "potential_impact", "TEXT")
        _ensure_column(conn, "github_projects", "generated_evidence", "TEXT")
        _ensure_column(conn, "github_projects", "related_articles", "TEXT")
        _ensure_column(conn, "github_projects", "related_criteria", "TEXT")

        _ensure_column(conn, "linkedin_content", "content_type", "TEXT NOT NULL DEFAULT 'short_post'")
        _ensure_column(conn, "linkedin_content", "theme", "TEXT")
        _ensure_column(conn, "linkedin_content", "planned_date", "TEXT")
        _ensure_column(conn, "linkedin_content", "published_link", "TEXT")
        _ensure_column(conn, "linkedin_content", "related_evidence", "TEXT")
        _ensure_column(conn, "linkedin_content", "objective", "TEXT NOT NULL DEFAULT 'authority'")

        _ensure_column(conn, "recommenders", "organization", "TEXT")
        _ensure_column(conn, "recommenders", "role_title", "TEXT")
        _ensure_column(conn, "recommenders", "email", "TEXT")
        _ensure_column(conn, "recommenders", "letter_strength", "TEXT NOT NULL DEFAULT 'medium'")
        _ensure_column(conn, "recommenders", "independence", "TEXT NOT NULL DEFAULT 'independent'")
        _ensure_column(conn, "recommenders", "validation_area", "TEXT")

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


AI_PROVIDER_TIMEOUT_SECONDS = 30
AI_SENSITIVE_CONTEXT_KEYS = {
    "address",
    "cpf",
    "document_number",
    "email",
    "passport",
    "phone",
    "ssn",
}


def _is_local_base_url(base_url: str) -> bool:
    parsed = urlparse(base_url)
    hostname = (parsed.hostname or "").lower()
    return hostname in {"localhost", "127.0.0.1", "::1"}


def _mask_sensitive_value(value: Any) -> Any:
    if value is None:
        return None
    return "[redacted]"


def sanitize_ai_context(context: dict[str, Any] | None, *, allow_private: bool) -> dict[str, Any]:
    if context is None:
        return {}

    def _sanitize(value: Any, key: str | None = None) -> Any:
        if isinstance(value, dict):
            sanitized: dict[str, Any] = {}
            for nested_key, nested_value in value.items():
                nested_key_str = str(nested_key)
                if not allow_private and nested_key_str in AI_SENSITIVE_CONTEXT_KEYS:
                    sanitized[nested_key_str] = _mask_sensitive_value(nested_value)
                    continue
                if nested_key_str == "evidences" and isinstance(nested_value, list):
                    evidences = [dict(item) for item in nested_value if isinstance(item, dict)]
                    sanitized[nested_key_str] = evidences if allow_private else filter_ai_allowed_evidences(evidences)
                    continue
                sanitized[nested_key_str] = _sanitize(nested_value, nested_key_str)
            return sanitized
        if isinstance(value, list):
            return [_sanitize(item, key) for item in value]
        if not allow_private and key in AI_SENSITIVE_CONTEXT_KEYS:
            return _mask_sensitive_value(value)
        return value

    return _sanitize(context)


def build_ai_error_result(
    provider: str,
    error_code: str,
    error_message: str,
    *,
    retryable: bool = False,
    model: str | None = None,
) -> dict[str, Any]:
    result = {
        "provider": provider,
        "status": "error",
        "error_code": error_code,
        "error_message": error_message,
        "retryable": retryable,
        "tokens_used": 0,
    }
    if model is not None:
        result["model"] = model
    return result


def build_ai_messages(prompt: str, context: dict[str, Any] | None) -> list[dict[str, str]]:
    if not context:
        return [{"role": "user", "content": prompt}]

    context_text = json.dumps(context, ensure_ascii=False, sort_keys=True)
    return [
        {
            "role": "user",
            "content": f"{prompt}\n\nContext:\n{context_text}",
        }
    ]


def parse_chat_completion_response(response: requests.Response, provider: str, model: str) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        return build_ai_error_result(provider, "invalid_response", "Provider returned invalid JSON.", retryable=False, model=model)

    analysis = ""
    tokens_used = 0
    if isinstance(payload, dict):
        choices = payload.get("choices") or []
        if choices:
            first_choice = choices[0] if isinstance(choices[0], dict) else {}
            message = first_choice.get("message") if isinstance(first_choice, dict) else {}
            if isinstance(message, dict):
                analysis = str(message.get("content", "")).strip()
            elif first_choice.get("text"):
                analysis = str(first_choice.get("text", "")).strip()
        usage = payload.get("usage")
        if isinstance(usage, dict):
            tokens_used = int(usage.get("total_tokens") or 0)
        elif isinstance(payload.get("total_tokens"), int):
            tokens_used = int(payload["total_tokens"])

    return {
        "provider": provider,
        "status": "ok",
        "model": model,
        "analysis": analysis or "No analysis content returned by provider.",
        "tokens_used": tokens_used,
    }


def perform_chat_completion(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    *,
    provider: str,
    model: str,
) -> dict[str, Any]:
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=AI_PROVIDER_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        return build_ai_error_result(provider, "request_error", str(exc), retryable=True, model=model)

    if response.status_code >= 400:
        retryable = response.status_code >= 500 or response.status_code == 429
        message = response.text.strip() or f"HTTP {response.status_code} from provider."
        return build_ai_error_result(provider, f"http_{response.status_code}", message, retryable=retryable, model=model)

    return parse_chat_completion_response(response, provider, model)


def record_ai_analysis_run(
    provider: str,
    run_type: str,
    status: str,
    metadata: dict[str, Any],
    *,
    db_path: str | None = None,
) -> None:
    target_db = db_path or DEFAULT_DB_PATH
    try:
        ensure_data_dir()
        conn = sqlite3.connect(target_db)
        try:
            conn.execute(
                """
                INSERT INTO ai_analysis_runs (provider, run_type, status, metadata_json)
                VALUES (?, ?, ?, ?)
                """,
                (provider, run_type, status, json.dumps(metadata, ensure_ascii=False, sort_keys=True)),
            )
            conn.commit()
        finally:
            conn.close()
    except sqlite3.Error:
        return


def analyze_with_provider(
    prompt: str,
    context: dict[str, Any] | None = None,
    provider_name: str | None = None,
    *,
    run_type: str = "analysis",
) -> dict[str, Any]:
    provider = get_ai_provider(provider_name)
    result = provider.analyze(prompt, context)
    record_ai_analysis_run(
        provider.provider_name,
        run_type,
        str(result.get("status", "error")),
        {
            "model": result.get("model"),
            "retryable": result.get("retryable"),
            "error_code": result.get("error_code"),
            "prompt_hash": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        },
    )
    return result


def build_export_payload(profile: dict[str, Any], evidences: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "disclaimer": "Educational and organizational only. Not legal or immigration advice. Not a real approval estimate.",
        "profile": profile,
        "evidences": filter_private_evidences(evidences),
    }


def build_markdown_report(payload: dict[str, Any]) -> str:
    lines = [
        "# Organizational report",
        "",
        payload.get("disclaimer", "Educational and organizational only. Not legal or immigration advice. Not a real approval estimate."),
        "",
        "## Profile",
    ]
    profile = payload.get("profile") if isinstance(payload.get("profile"), dict) else {}
    if profile:
        for key, value in profile.items():
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- No profile data available.")

    lines.extend(["", "## Evidences"])
    evidences = payload.get("evidences") if isinstance(payload.get("evidences"), list) else []
    if evidences:
        for evidence in evidences:
            if not isinstance(evidence, dict):
                continue
            title = evidence.get("title", "Untitled")
            category = evidence.get("category", "")
            status = evidence.get("status", "")
            lines.append(f"- {title} ({category}) {status}".strip())
    else:
        lines.append("- No evidences available.")

    return "\n".join(lines)


def build_csv_report(payload: dict[str, Any]) -> str:
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["section", "field", "value"])

    profile = payload.get("profile") if isinstance(payload.get("profile"), dict) else {}
    for key, value in profile.items():
        writer.writerow(["profile", key, value])

    evidences = payload.get("evidences") if isinstance(payload.get("evidences"), list) else []
    for evidence in evidences:
        if not isinstance(evidence, dict):
            continue
        writer.writerow(["evidence", "title", evidence.get("title", "")])
        writer.writerow(["evidence", "category", evidence.get("category", "")])
        writer.writerow(["evidence", "status", evidence.get("status", "")])

    return output.getvalue()


class ProviderConfigError(RuntimeError):
    pass


class BaseAIProvider(ABC):
    def name(self) -> str:
        return self.provider_name

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
        sanitized_context = sanitize_ai_context(context, allow_private=True)
        digest_input = json.dumps({"prompt": prompt, "context": sanitized_context}, ensure_ascii=False, sort_keys=True)
        digest = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()[:12]
        context_size = len(sanitized_context) if isinstance(sanitized_context, dict) else 0
        return {
            "provider": self.provider_name,
            "status": "ok",
            "model": "mock-v1",
            "analysis": f"Mock analysis generated for prompt hash {digest}.",
            "tokens_used": 0,
            "context_items": context_size,
        }

    def healthcheck(self) -> dict[str, Any]:
        return {"provider": self.provider_name, "status": "ok", "model": "mock-v1"}


class OpenAIProvider(BaseAIProvider):
    @property
    def provider_name(self) -> str:
        return "openai"

    def analyze(self, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        if not api_key:
            return build_ai_error_result(self.provider_name, "missing_configuration", "OPENAI_API_KEY is not configured.", model=model)

        payload = {
            "model": model,
            "messages": build_ai_messages(prompt, sanitize_ai_context(context, allow_private=False)),
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        return perform_chat_completion("https://api.openai.com/v1/chat/completions", headers, payload, provider=self.provider_name, model=model)


class AzureOpenAIProvider(BaseAIProvider):
    @property
    def provider_name(self) -> str:
        return "azure_openai"

    def analyze(self, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        required_vars = ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT"]
        missing = [name for name in required_vars if not os.getenv(name)]
        if missing:
            deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
            return build_ai_error_result(
                self.provider_name,
                "missing_configuration",
                f"Missing Azure OpenAI settings: {', '.join(missing)}",
                model=deployment,
            )

        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01")
        model = deployment
        payload = {
            "messages": build_ai_messages(prompt, sanitize_ai_context(context, allow_private=False)),
            "temperature": 0.2,
        }
        headers = {
            "api-key": os.getenv("AZURE_OPENAI_API_KEY", ""),
            "Content-Type": "application/json",
        }
        url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
        return perform_chat_completion(url, headers, payload, provider=self.provider_name, model=model)


class OllamaProvider(BaseAIProvider):
    @property
    def provider_name(self) -> str:
        return "ollama"

    def analyze(self, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        base_url = os.getenv("OLLAMA_BASE_URL")
        model = os.getenv("OLLAMA_MODEL", "llama3")
        if not base_url:
            return build_ai_error_result(self.provider_name, "missing_configuration", "OLLAMA_BASE_URL is not configured.", model=model)

        allow_private = _is_local_base_url(base_url)
        payload = {
            "model": model,
            "messages": build_ai_messages(prompt, sanitize_ai_context(context, allow_private=allow_private)),
            "stream": False,
        }
        url = f"{base_url.rstrip('/')}/api/chat"
        try:
            response = requests.post(url, json=payload, timeout=AI_PROVIDER_TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            return build_ai_error_result(self.provider_name, "request_error", str(exc), retryable=True, model=model)

        if response.status_code >= 400:
            retryable = response.status_code >= 500 or response.status_code == 429
            message = response.text.strip() or f"HTTP {response.status_code} from provider."
            return build_ai_error_result(self.provider_name, f"http_{response.status_code}", message, retryable=retryable, model=model)

        try:
            payload = response.json()
        except ValueError:
            return build_ai_error_result(self.provider_name, "invalid_response", "Provider returned invalid JSON.", model=model)

        analysis = ""
        tokens_used = 0
        if isinstance(payload, dict):
            message = payload.get("message")
            if isinstance(message, dict):
                analysis = str(message.get("content", "")).strip()
            tokens_used = int(payload.get("eval_count") or payload.get("prompt_eval_count") or 0)

        return {
            "provider": self.provider_name,
            "status": "ok",
            "model": model,
            "analysis": analysis or "No analysis content returned by provider.",
            "tokens_used": tokens_used,
        }

    def healthcheck(self) -> dict[str, Any]:
        base_url = os.getenv("OLLAMA_BASE_URL")
        model = os.getenv("OLLAMA_MODEL", "llama3")
        if not base_url:
            return {"provider": self.provider_name, "status": "error", "error_code": "missing_configuration", "error_message": "OLLAMA_BASE_URL is not configured.", "model": model}
        return {"provider": self.provider_name, "status": "ok", "model": model, "local": _is_local_base_url(base_url)}


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
                            .badge.low,
                            .badge.ready,
                            .badge.active,
                            .badge.recognized,
                            .badge.published,
                            .badge.confirmed {
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
                            .badge.medium,
                            .badge.in_review,
                            .badge.planned,
                            .badge.building,
                            .badge.maintenance,
                            .badge.contacted,
                            .badge.partially_independent,
                            .badge.peer {
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
                            .badge.critical,
                            .badge.idea,
                            .badge.prospect,
                            .badge.declined,
                            .badge.direct_manager {
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
                <a href="{{ url_for('proposed_endeavor', lang=lang) }}">{{ t('nav.proposed_endeavor', lang) }}</a>
                <a href="{{ url_for('authority', lang=lang) }}">{{ t('nav.authority', lang) }}</a>
                <a href="{{ url_for('github_projects', lang=lang) }}">{{ t('nav.github_projects', lang) }}</a>
                <a href="{{ url_for('linkedin_content', lang=lang) }}">{{ t('nav.linkedin_content', lang) }}</a>
                <a href="{{ url_for('recommenders', lang=lang) }}">{{ t('nav.recommenders', lang) }}</a>
                <a href="{{ url_for('export_report', lang=lang) }}">{{ t('nav.export_report', lang) }}</a>
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

    def fetch_proposed_endeavors() -> list[dict[str, Any]]:
        conn = get_db()
        rows = conn.execute(
            """
            SELECT
                id,
                area,
                problem_to_solve,
                impacted_sector,
                technologies,
                relevance,
                experience_evidence,
                expected_impact,
                broader_importance,
                short_version,
                long_version,
                status
            FROM proposed_endeavor
            ORDER BY id DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def fetch_proposed_endeavor_by_id(item_id: int) -> dict[str, Any] | None:
        conn = get_db()
        row = conn.execute(
            """
            SELECT
                id,
                area,
                problem_to_solve,
                impacted_sector,
                technologies,
                relevance,
                experience_evidence,
                expected_impact,
                broader_importance,
                short_version,
                long_version,
                status
            FROM proposed_endeavor
            WHERE id = ?
            """,
            (item_id,),
        ).fetchone()
        return dict(row) if row else None

    def upsert_proposed_endeavor(item_id: int | None, form_data: dict[str, str]) -> None:
        conn = get_db()
        payload = {
            "area": form_data.get("area", "").strip(),
            "problem_to_solve": form_data.get("problem_to_solve", "").strip(),
            "impacted_sector": form_data.get("impacted_sector", "").strip(),
            "technologies": form_data.get("technologies", "").strip(),
            "relevance": form_data.get("relevance", "").strip(),
            "experience_evidence": form_data.get("experience_evidence", "").strip(),
            "expected_impact": form_data.get("expected_impact", "").strip(),
            "broader_importance": form_data.get("broader_importance", "").strip(),
            "short_version": form_data.get("short_version", "").strip(),
            "long_version": form_data.get("long_version", "").strip(),
            "status": form_data.get("status", "draft").strip() or "draft",
        }
        if payload["status"] not in ENDEAVOR_STATUS_OPTIONS:
            payload["status"] = "draft"

        title = payload["short_version"][:180] or payload["area"][:180] or "Proposed endeavor"
        summary = payload["long_version"] or payload["short_version"]
        impact = payload["expected_impact"]

        if item_id is None:
            conn.execute(
                """
                INSERT INTO proposed_endeavor
                (title, summary, impact, area, problem_to_solve, impacted_sector, technologies, relevance, experience_evidence, expected_impact, broader_importance, short_version, long_version, status)
                VALUES (:title, :summary, :impact, :area, :problem_to_solve, :impacted_sector, :technologies, :relevance, :experience_evidence, :expected_impact, :broader_importance, :short_version, :long_version, :status)
                """,
                {**payload, "title": title, "summary": summary, "impact": impact},
            )
        else:
            conn.execute(
                """
                UPDATE proposed_endeavor
                SET title = :title,
                    summary = :summary,
                    impact = :impact,
                    area = :area,
                    problem_to_solve = :problem_to_solve,
                    impacted_sector = :impacted_sector,
                    technologies = :technologies,
                    relevance = :relevance,
                    experience_evidence = :experience_evidence,
                    expected_impact = :expected_impact,
                    broader_importance = :broader_importance,
                    short_version = :short_version,
                    long_version = :long_version,
                    status = :status
                WHERE id = :id
                """,
                {
                    **payload,
                    "id": item_id,
                    "title": title,
                    "summary": summary,
                    "impact": impact,
                },
            )
        conn.commit()

    def delete_proposed_endeavor(item_id: int) -> None:
        conn = get_db()
        conn.execute("DELETE FROM proposed_endeavor WHERE id = ?", (item_id,))
        conn.commit()

    def fetch_authority_items() -> list[dict[str, Any]]:
        conn = get_db()
        rows = conn.execute(
            """
            SELECT
                id,
                main_theme,
                target_communities,
                planned_articles,
                planned_talks,
                planned_github_repos,
                events,
                people_recommenders,
                public_evidence,
                status
            FROM authority_plan
            ORDER BY id DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def fetch_authority_item_by_id(item_id: int) -> dict[str, Any] | None:
        conn = get_db()
        row = conn.execute(
            """
            SELECT
                id,
                main_theme,
                target_communities,
                planned_articles,
                planned_talks,
                planned_github_repos,
                events,
                people_recommenders,
                public_evidence,
                status
            FROM authority_plan
            WHERE id = ?
            """,
            (item_id,),
        ).fetchone()
        return dict(row) if row else None

    def upsert_authority_item(item_id: int | None, form_data: dict[str, str]) -> None:
        conn = get_db()
        payload = {
            "main_theme": form_data.get("main_theme", "").strip(),
            "target_communities": form_data.get("target_communities", "").strip(),
            "planned_articles": form_data.get("planned_articles", "").strip(),
            "planned_talks": form_data.get("planned_talks", "").strip(),
            "planned_github_repos": form_data.get("planned_github_repos", "").strip(),
            "events": form_data.get("events", "").strip(),
            "people_recommenders": form_data.get("people_recommenders", "").strip(),
            "public_evidence": form_data.get("public_evidence", "").strip(),
            "status": form_data.get("status", "planned").strip() or "planned",
        }
        if payload["status"] not in AUTHORITY_STATUS_OPTIONS:
            payload["status"] = "planned"

        channel = payload["target_communities"] or "Comunidades tecnicas"
        objective = payload["main_theme"] or "Plano de autoridade tecnica"
        cadence = "cadencia flexivel"

        if item_id is None:
            conn.execute(
                """
                INSERT INTO authority_plan
                (channel, objective, cadence, status, main_theme, target_communities, planned_articles, planned_talks, planned_github_repos, events, people_recommenders, public_evidence)
                VALUES (:channel, :objective, :cadence, :status, :main_theme, :target_communities, :planned_articles, :planned_talks, :planned_github_repos, :events, :people_recommenders, :public_evidence)
                """,
                {
                    **payload,
                    "channel": channel,
                    "objective": objective,
                    "cadence": cadence,
                },
            )
        else:
            conn.execute(
                """
                UPDATE authority_plan
                SET channel = :channel,
                    objective = :objective,
                    cadence = :cadence,
                    status = :status,
                    main_theme = :main_theme,
                    target_communities = :target_communities,
                    planned_articles = :planned_articles,
                    planned_talks = :planned_talks,
                    planned_github_repos = :planned_github_repos,
                    events = :events,
                    people_recommenders = :people_recommenders,
                    public_evidence = :public_evidence
                WHERE id = :id
                """,
                {
                    **payload,
                    "id": item_id,
                    "channel": channel,
                    "objective": objective,
                    "cadence": cadence,
                },
            )
        conn.commit()

    def delete_authority_item(item_id: int) -> None:
        conn = get_db()
        conn.execute("DELETE FROM authority_plan WHERE id = ?", (item_id,))
        conn.commit()

    def fetch_github_projects() -> list[dict[str, Any]]:
        conn = get_db()
        rows = conn.execute(
            """
            SELECT
                id,
                name,
                summary,
                solved_problem,
                technologies,
                repo_url,
                status,
                potential_impact,
                generated_evidence,
                related_articles,
                related_criteria
            FROM github_projects
            ORDER BY id DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def fetch_github_project_by_id(item_id: int) -> dict[str, Any] | None:
        conn = get_db()
        row = conn.execute(
            """
            SELECT
                id,
                name,
                summary,
                solved_problem,
                technologies,
                repo_url,
                status,
                potential_impact,
                generated_evidence,
                related_articles,
                related_criteria
            FROM github_projects
            WHERE id = ?
            """,
            (item_id,),
        ).fetchone()
        return dict(row) if row else None

    def upsert_github_project(item_id: int | None, form_data: dict[str, str]) -> None:
        conn = get_db()
        payload = {
            "name": form_data.get("name", "").strip(),
            "summary": form_data.get("summary", "").strip(),
            "solved_problem": form_data.get("solved_problem", "").strip(),
            "technologies": form_data.get("technologies", "").strip(),
            "repo_url": form_data.get("repo_url", "").strip(),
            "status": form_data.get("status", "idea").strip() or "idea",
            "potential_impact": form_data.get("potential_impact", "").strip(),
            "generated_evidence": form_data.get("generated_evidence", "").strip(),
            "related_articles": form_data.get("related_articles", "").strip(),
            "related_criteria": form_data.get("related_criteria", "").strip(),
        }
        if payload["status"] not in GITHUB_PROJECT_STATUS_OPTIONS:
            payload["status"] = "idea"

        if item_id is None:
            conn.execute(
                """
                INSERT INTO github_projects
                (name, summary, solved_problem, technologies, repo_url, status, potential_impact, generated_evidence, related_articles, related_criteria)
                VALUES (:name, :summary, :solved_problem, :technologies, :repo_url, :status, :potential_impact, :generated_evidence, :related_articles, :related_criteria)
                """,
                payload,
            )
        else:
            conn.execute(
                """
                UPDATE github_projects
                SET name = :name,
                    summary = :summary,
                    solved_problem = :solved_problem,
                    technologies = :technologies,
                    repo_url = :repo_url,
                    status = :status,
                    potential_impact = :potential_impact,
                    generated_evidence = :generated_evidence,
                    related_articles = :related_articles,
                    related_criteria = :related_criteria
                WHERE id = :id
                """,
                {**payload, "id": item_id},
            )
        conn.commit()

    def delete_github_project(item_id: int) -> None:
        conn = get_db()
        conn.execute("DELETE FROM github_projects WHERE id = ?", (item_id,))
        conn.commit()

    def fetch_linkedin_contents() -> list[dict[str, Any]]:
        conn = get_db()
        rows = conn.execute(
            """
            SELECT
                id,
                title,
                content_type,
                theme,
                status,
                planned_date,
                published_link,
                related_evidence,
                objective
            FROM linkedin_content
            ORDER BY id DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def fetch_linkedin_content_by_id(item_id: int) -> dict[str, Any] | None:
        conn = get_db()
        row = conn.execute(
            """
            SELECT
                id,
                title,
                content_type,
                theme,
                status,
                planned_date,
                published_link,
                related_evidence,
                objective
            FROM linkedin_content
            WHERE id = ?
            """,
            (item_id,),
        ).fetchone()
        return dict(row) if row else None

    def upsert_linkedin_content(item_id: int | None, form_data: dict[str, str]) -> None:
        conn = get_db()
        payload = {
            "title": form_data.get("title", "").strip(),
            "content_type": form_data.get("content_type", "short_post").strip() or "short_post",
            "theme": form_data.get("theme", "").strip(),
            "status": form_data.get("status", "draft").strip() or "draft",
            "planned_date": form_data.get("planned_date", "").strip(),
            "published_link": form_data.get("published_link", "").strip(),
            "related_evidence": form_data.get("related_evidence", "").strip(),
            "objective": form_data.get("objective", "authority").strip() or "authority",
        }
        if payload["content_type"] not in LINKEDIN_CONTENT_TYPE_OPTIONS:
            payload["content_type"] = "short_post"
        if payload["status"] not in LINKEDIN_CONTENT_STATUS_OPTIONS:
            payload["status"] = "draft"
        if payload["objective"] not in LINKEDIN_CONTENT_OBJECTIVE_OPTIONS:
            payload["objective"] = "authority"

        idea = payload["theme"] or payload["title"]
        if item_id is None:
            conn.execute(
                """
                INSERT INTO linkedin_content
                (title, idea, content_type, theme, status, planned_date, published_link, related_evidence, objective)
                VALUES (:title, :idea, :content_type, :theme, :status, :planned_date, :published_link, :related_evidence, :objective)
                """,
                {**payload, "idea": idea},
            )
        else:
            conn.execute(
                """
                UPDATE linkedin_content
                SET title = :title,
                    idea = :idea,
                    content_type = :content_type,
                    theme = :theme,
                    status = :status,
                    planned_date = :planned_date,
                    published_link = :published_link,
                    related_evidence = :related_evidence,
                    objective = :objective
                WHERE id = :id
                """,
                {**payload, "id": item_id, "idea": idea},
            )
        conn.commit()

    def delete_linkedin_content(item_id: int) -> None:
        conn = get_db()
        conn.execute("DELETE FROM linkedin_content WHERE id = ?", (item_id,))
        conn.commit()

    def fetch_recommenders() -> list[dict[str, Any]]:
        conn = get_db()
        rows = conn.execute(
            """
            SELECT
                id,
                name,
                relationship,
                organization,
                role_title,
                email,
                letter_strength,
                independence,
                validation_area,
                status,
                notes
            FROM recommenders
            ORDER BY id DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def fetch_recommender_by_id(item_id: int) -> dict[str, Any] | None:
        conn = get_db()
        row = conn.execute(
            """
            SELECT
                id,
                name,
                relationship,
                organization,
                role_title,
                email,
                letter_strength,
                independence,
                validation_area,
                status,
                notes
            FROM recommenders
            WHERE id = ?
            """,
            (item_id,),
        ).fetchone()
        return dict(row) if row else None

    def upsert_recommender(item_id: int | None, form_data: dict[str, str]) -> None:
        conn = get_db()
        payload = {
            "name": form_data.get("name", "").strip(),
            "relationship": form_data.get("relationship", "").strip(),
            "organization": form_data.get("organization", "").strip(),
            "role_title": form_data.get("role_title", "").strip(),
            "email": form_data.get("email", "").strip(),
            "letter_strength": form_data.get("letter_strength", "medium").strip() or "medium",
            "independence": form_data.get("independence", "independent").strip() or "independent",
            "validation_area": form_data.get("validation_area", "").strip(),
            "status": form_data.get("status", "prospect").strip() or "prospect",
            "notes": form_data.get("notes", "").strip(),
        }
        if payload["letter_strength"] not in RECOMMENDER_STRENGTH_OPTIONS:
            payload["letter_strength"] = "medium"
        if payload["independence"] not in RECOMMENDER_INDEPENDENCE_OPTIONS:
            payload["independence"] = "independent"
        if payload["status"] not in RECOMMENDER_STATUS_OPTIONS:
            payload["status"] = "prospect"

        if item_id is None:
            conn.execute(
                """
                INSERT INTO recommenders
                (name, relationship, organization, role_title, email, letter_strength, independence, validation_area, status, notes)
                VALUES (:name, :relationship, :organization, :role_title, :email, :letter_strength, :independence, :validation_area, :status, :notes)
                """,
                payload,
            )
        else:
            conn.execute(
                """
                UPDATE recommenders
                SET name = :name,
                    relationship = :relationship,
                    organization = :organization,
                    role_title = :role_title,
                    email = :email,
                    letter_strength = :letter_strength,
                    independence = :independence,
                    validation_area = :validation_area,
                    status = :status,
                    notes = :notes
                WHERE id = :id
                """,
                {**payload, "id": item_id},
            )
        conn.commit()

    def delete_recommender(item_id: int) -> None:
        conn = get_db()
        conn.execute("DELETE FROM recommenders WHERE id = ?", (item_id,))
        conn.commit()

    def render_proposed_endeavor_form(lang: str, data: dict[str, Any]) -> str:
        form_template = """
        <label>{{ t('proposed.field.area', lang) }}
            <input type="text" name="area" value="{{ data.area }}" required />
        </label>
        <label>{{ t('proposed.field.problem_to_solve', lang) }}
            <textarea name="problem_to_solve" rows="2">{{ data.problem_to_solve }}</textarea>
        </label>
        <label>{{ t('proposed.field.impacted_sector', lang) }}
            <input type="text" name="impacted_sector" value="{{ data.impacted_sector }}" />
        </label>
        <label>{{ t('proposed.field.technologies', lang) }}
            <input type="text" name="technologies" value="{{ data.technologies }}" />
        </label>
        <label>{{ t('proposed.field.relevance', lang) }}
            <textarea name="relevance" rows="2">{{ data.relevance }}</textarea>
        </label>
        <label>{{ t('proposed.field.experience_evidence', lang) }}
            <textarea name="experience_evidence" rows="2">{{ data.experience_evidence }}</textarea>
        </label>
        <label>{{ t('proposed.field.expected_impact', lang) }}
            <textarea name="expected_impact" rows="2">{{ data.expected_impact }}</textarea>
        </label>
        <label>{{ t('proposed.field.broader_importance', lang) }}
            <textarea name="broader_importance" rows="2">{{ data.broader_importance }}</textarea>
        </label>
        <label>{{ t('proposed.field.short_version', lang) }}
            <textarea name="short_version" rows="2">{{ data.short_version }}</textarea>
        </label>
        <label>{{ t('proposed.field.long_version', lang) }}
            <textarea name="long_version" rows="4">{{ data.long_version }}</textarea>
        </label>
        <label>{{ t('proposed.field.status', lang) }}
            <select name="status">
                {% for opt in status_options %}
                    <option value="{{ opt }}" {% if data.status == opt %}selected{% endif %}>{{ t('status.' ~ opt, lang) }}</option>
                {% endfor %}
            </select>
        </label>
        """
        return render_template_string(form_template, lang=lang, t=t, data=data, status_options=ENDEAVOR_STATUS_OPTIONS)

    def render_authority_form(lang: str, data: dict[str, Any]) -> str:
        form_template = """
        <label>{{ t('authority.field.main_theme', lang) }}
            <input type="text" name="main_theme" value="{{ data.main_theme }}" required />
        </label>
        <label>{{ t('authority.field.target_communities', lang) }}
            <textarea name="target_communities" rows="2">{{ data.target_communities }}</textarea>
        </label>
        <label>{{ t('authority.field.planned_articles', lang) }}
            <textarea name="planned_articles" rows="2">{{ data.planned_articles }}</textarea>
        </label>
        <label>{{ t('authority.field.planned_talks', lang) }}
            <textarea name="planned_talks" rows="2">{{ data.planned_talks }}</textarea>
        </label>
        <label>{{ t('authority.field.planned_github_repos', lang) }}
            <textarea name="planned_github_repos" rows="2">{{ data.planned_github_repos }}</textarea>
        </label>
        <label>{{ t('authority.field.events', lang) }}
            <textarea name="events" rows="2">{{ data.events }}</textarea>
        </label>
        <label>{{ t('authority.field.people_recommenders', lang) }}
            <textarea name="people_recommenders" rows="2">{{ data.people_recommenders }}</textarea>
        </label>
        <label>{{ t('authority.field.public_evidence', lang) }}
            <textarea name="public_evidence" rows="2">{{ data.public_evidence }}</textarea>
        </label>
        <label>{{ t('authority.field.status', lang) }}
            <select name="status">
                {% for opt in status_options %}
                    <option value="{{ opt }}" {% if data.status == opt %}selected{% endif %}>{{ t('status.' ~ opt, lang) }}</option>
                {% endfor %}
            </select>
        </label>
        """
        return render_template_string(form_template, lang=lang, t=t, data=data, status_options=AUTHORITY_STATUS_OPTIONS)

    def render_github_project_form(lang: str, data: dict[str, Any]) -> str:
        form_template = """
        <label>{{ t('github.field.name', lang) }}
            <input type="text" name="name" value="{{ data.name }}" required />
        </label>
        <label>{{ t('github.field.summary', lang) }}
            <textarea name="summary" rows="2">{{ data.summary }}</textarea>
        </label>
        <label>{{ t('github.field.solved_problem', lang) }}
            <textarea name="solved_problem" rows="2">{{ data.solved_problem }}</textarea>
        </label>
        <label>{{ t('github.field.technologies', lang) }}
            <input type="text" name="technologies" value="{{ data.technologies }}" />
        </label>
        <label>{{ t('github.field.repo_url', lang) }}
            <input type="text" name="repo_url" value="{{ data.repo_url }}" />
        </label>
        <label>{{ t('github.field.status', lang) }}
            <select name="status">
                {% for opt in status_options %}
                    <option value="{{ opt }}" {% if data.status == opt %}selected{% endif %}>{{ t('status.' ~ opt, lang) }}</option>
                {% endfor %}
            </select>
        </label>
        <label>{{ t('github.field.potential_impact', lang) }}
            <textarea name="potential_impact" rows="2">{{ data.potential_impact }}</textarea>
        </label>
        <label>{{ t('github.field.generated_evidence', lang) }}
            <textarea name="generated_evidence" rows="2">{{ data.generated_evidence }}</textarea>
        </label>
        <label>{{ t('github.field.related_articles', lang) }}
            <textarea name="related_articles" rows="2">{{ data.related_articles }}</textarea>
        </label>
        <label>{{ t('github.field.related_criteria', lang) }}
            <input type="text" name="related_criteria" value="{{ data.related_criteria }}" />
        </label>
        """
        return render_template_string(form_template, lang=lang, t=t, data=data, status_options=GITHUB_PROJECT_STATUS_OPTIONS)

    def render_linkedin_content_form(lang: str, data: dict[str, Any]) -> str:
        form_template = """
        <label>{{ t('linkedin.field.title', lang) }}
            <input type="text" name="title" value="{{ data.title }}" required />
        </label>
        <label>{{ t('linkedin.field.content_type', lang) }}
            <select name="content_type">
                {% for opt in type_options %}
                    <option value="{{ opt }}" {% if data.content_type == opt %}selected{% endif %}>{{ t('linkedin.type.' ~ opt, lang) }}</option>
                {% endfor %}
            </select>
        </label>
        <label>{{ t('linkedin.field.theme', lang) }}
            <input type="text" name="theme" value="{{ data.theme }}" />
        </label>
        <label>{{ t('linkedin.field.status', lang) }}
            <select name="status">
                {% for opt in status_options %}
                    <option value="{{ opt }}" {% if data.status == opt %}selected{% endif %}>{{ t('status.' ~ opt, lang) }}</option>
                {% endfor %}
            </select>
        </label>
        <label>{{ t('linkedin.field.planned_date', lang) }}
            <input type="date" name="planned_date" value="{{ data.planned_date }}" />
        </label>
        <label>{{ t('linkedin.field.published_link', lang) }}
            <input type="text" name="published_link" value="{{ data.published_link }}" />
        </label>
        <label>{{ t('linkedin.field.related_evidence', lang) }}
            <textarea name="related_evidence" rows="2">{{ data.related_evidence }}</textarea>
        </label>
        <label>{{ t('linkedin.field.objective', lang) }}
            <select name="objective">
                {% for opt in objective_options %}
                    <option value="{{ opt }}" {% if data.objective == opt %}selected{% endif %}>{{ t('linkedin.objective.' ~ opt, lang) }}</option>
                {% endfor %}
            </select>
        </label>
        """
        return render_template_string(
            form_template,
            lang=lang,
            t=t,
            data=data,
            type_options=LINKEDIN_CONTENT_TYPE_OPTIONS,
            status_options=LINKEDIN_CONTENT_STATUS_OPTIONS,
            objective_options=LINKEDIN_CONTENT_OBJECTIVE_OPTIONS,
        )

    def render_recommender_form(lang: str, data: dict[str, Any]) -> str:
        form_template = """
        <label>{{ t('recommender.field.name', lang) }}
            <input type="text" name="name" value="{{ data.name }}" required />
        </label>
        <label>{{ t('recommender.field.relationship', lang) }}
            <input type="text" name="relationship" value="{{ data.relationship }}" />
        </label>
        <label>{{ t('recommender.field.organization', lang) }}
            <input type="text" name="organization" value="{{ data.organization }}" />
        </label>
        <label>{{ t('recommender.field.role_title', lang) }}
            <input type="text" name="role_title" value="{{ data.role_title }}" />
        </label>
        <label>{{ t('recommender.field.email', lang) }}
            <input type="text" name="email" value="{{ data.email }}" />
        </label>
        <label>{{ t('recommender.field.letter_strength', lang) }}
            <select name="letter_strength">
                {% for opt in strength_options %}
                    <option value="{{ opt }}" {% if data.letter_strength == opt %}selected{% endif %}>{{ t('strength.' ~ opt, lang) }}</option>
                {% endfor %}
            </select>
        </label>
        <label>{{ t('recommender.field.independence', lang) }}
            <select name="independence">
                {% for opt in independence_options %}
                    <option value="{{ opt }}" {% if data.independence == opt %}selected{% endif %}>{{ t('independence.' ~ opt, lang) }}</option>
                {% endfor %}
            </select>
        </label>
        <label>{{ t('recommender.field.validation_area', lang) }}
            <textarea name="validation_area" rows="2">{{ data.validation_area }}</textarea>
        </label>
        <label>{{ t('recommender.field.status', lang) }}
            <select name="status">
                {% for opt in status_options %}
                    <option value="{{ opt }}" {% if data.status == opt %}selected{% endif %}>{{ t('status.' ~ opt, lang) }}</option>
                {% endfor %}
            </select>
        </label>
        <label>{{ t('recommender.field.notes', lang) }}
            <textarea name="notes" rows="2">{{ data.notes }}</textarea>
        </label>
        """
        return render_template_string(
            form_template,
            lang=lang,
            t=t,
            data=data,
            strength_options=RECOMMENDER_STRENGTH_OPTIONS,
            independence_options=RECOMMENDER_INDEPENDENCE_OPTIONS,
            status_options=RECOMMENDER_STATUS_OPTIONS,
        )

    def build_organizational_report_payload() -> dict[str, Any]:
        conn = get_db()

        profile_row = conn.execute(
            """
            SELECT id, full_name, headline, target_domain, locale, created_at
            FROM profile
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        profile = dict(profile_row) if profile_row else {}

        evidence_rows = conn.execute(
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
                can_send_to_ai,
                is_private
            FROM evidences
            ORDER BY COALESCE(evidence_date, '') DESC, id DESC
            """
        ).fetchall()
        evidences = [dict(row) for row in evidence_rows]

        assessment_questions = fetch_assessment_questions_with_answers()
        eb2_score = calculate_eb2_scores(assessment_questions)
        niw_assessments = fetch_niw_assessments()
        niw_average = int(round(sum(item["score"] for item in niw_assessments) / max(1, len(niw_assessments))))

        return {
            "disclaimer": "Educational and organizational only. Not legal or immigration advice.",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "profile": profile,
            "readiness": {
                "eb2": eb2_score,
                "niw_average": niw_average,
                "niw_prongs": niw_assessments,
            },
            "proposed_endeavor": fetch_proposed_endeavors(),
            "authority": fetch_authority_items(),
            "github_projects": fetch_github_projects(),
            "linkedin_content": fetch_linkedin_contents(),
            "recommenders": fetch_recommenders(),
            "evidences": filter_private_evidences(evidences),
        }

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

    @app.route("/proposed-endeavor")
    def proposed_endeavor() -> str:
        lang = get_selected_language()
        items = fetch_proposed_endeavors()
        body = """
        <h1>{{ t('proposed.title', lang) }}</h1>
        <p>{{ t('proposed.subtitle', lang) }}</p>
        <a href="{{ url_for('proposed_endeavor_new', lang=lang) }}">{{ t('proposed.new', lang) }}</a>
        <table>
            <thead>
                <tr>
                    <th>{{ t('proposed.field.area', lang) }}</th>
                    <th>{{ t('proposed.field.short_version', lang) }}</th>
                    <th>{{ t('proposed.field.status', lang) }}</th>
                    <th>{{ t('common.actions', lang) }}</th>
                </tr>
            </thead>
            <tbody>
                {% for item in items %}
                    <tr>
                        <td>{{ item.area }}</td>
                        <td>{{ item.short_version }}</td>
                        <td><span class="badge {{ item.status }}">{{ t('status.' ~ item.status, lang) }}</span></td>
                        <td>
                            <div class="actions">
                                <a href="{{ url_for('proposed_endeavor_edit', item_id=item.id, lang=lang) }}">{{ t('common.edit', lang) }}</a>
                                <form method="post" action="{{ url_for('proposed_endeavor_delete', item_id=item.id, lang=lang) }}">
                                    <button type="submit">{{ t('common.delete', lang) }}</button>
                                </form>
                            </div>
                        </td>
                    </tr>
                {% endfor %}
            </tbody>
        </table>
        """
        return render_page(lang, t("proposed.title", lang), body, items=items)

    @app.route("/proposed-endeavor/new", methods=["GET", "POST"])
    def proposed_endeavor_new() -> str:
        lang = get_selected_language()
        if request.method == "POST":
            upsert_proposed_endeavor(None, dict(request.form))
            return redirect(url_for("proposed_endeavor", lang=lang))

        form_data = {
            "area": "",
            "problem_to_solve": "",
            "impacted_sector": "",
            "technologies": "",
            "relevance": "",
            "experience_evidence": "",
            "expected_impact": "",
            "broader_importance": "",
            "short_version": "Desenvolvimento e disseminacao de arquiteturas seguras, governadas e escalaveis de agentes de IA generativa para acelerar a transformacao digital de empresas, aumentar produtividade, reduzir riscos operacionais e melhorar a adocao responsavel de IA em setores estrategicos.",
            "long_version": "",
            "status": "draft",
        }
        body = """
        <h1>{{ t('proposed.new', lang) }}</h1>
        <form method="post" action="{{ url_for('proposed_endeavor_new', lang=lang) }}">
            {{ proposed_form|safe }}
            <button type="submit">{{ t('common.save', lang) }}</button>
        </form>
        """
        return render_page(
            lang,
            t("proposed.new", lang),
            body,
            proposed_form=render_proposed_endeavor_form(lang, form_data),
        )

    @app.route("/proposed-endeavor/<int:item_id>/edit", methods=["GET", "POST"])
    def proposed_endeavor_edit(item_id: int) -> str:
        lang = get_selected_language()
        item = fetch_proposed_endeavor_by_id(item_id)
        if not item:
            return redirect(url_for("proposed_endeavor", lang=lang))
        if request.method == "POST":
            upsert_proposed_endeavor(item_id, dict(request.form))
            return redirect(url_for("proposed_endeavor", lang=lang))

        body = """
        <h1>{{ t('proposed.edit', lang) }}</h1>
        <form method="post" action="{{ url_for('proposed_endeavor_edit', item_id=item.id, lang=lang) }}">
            {{ proposed_form|safe }}
            <button type="submit">{{ t('common.save', lang) }}</button>
        </form>
        """
        return render_page(
            lang,
            t("proposed.edit", lang),
            body,
            item=item,
            proposed_form=render_proposed_endeavor_form(lang, item),
        )

    @app.route("/proposed-endeavor/<int:item_id>/delete", methods=["POST"])
    def proposed_endeavor_delete(item_id: int) -> Any:
        lang = get_selected_language()
        delete_proposed_endeavor(item_id)
        return redirect(url_for("proposed_endeavor", lang=lang))

    @app.route("/authority")
    def authority() -> str:
        lang = get_selected_language()
        items = fetch_authority_items()
        body = """
        <h1>{{ t('authority.title', lang) }}</h1>
        <p>{{ t('authority.subtitle', lang) }}</p>
        <div class="disclaimer">{{ t('authority.explanation', lang) }}</div>
        <a href="{{ url_for('authority_new', lang=lang) }}">{{ t('authority.new', lang) }}</a>
        <table>
            <thead>
                <tr>
                    <th>{{ t('authority.field.main_theme', lang) }}</th>
                    <th>{{ t('authority.field.target_communities', lang) }}</th>
                    <th>{{ t('authority.field.status', lang) }}</th>
                    <th>{{ t('common.actions', lang) }}</th>
                </tr>
            </thead>
            <tbody>
                {% for item in items %}
                    <tr>
                        <td>{{ item.main_theme }}</td>
                        <td>{{ item.target_communities }}</td>
                        <td><span class="badge {{ item.status }}">{{ t('status.' ~ item.status, lang) }}</span></td>
                        <td>
                            <div class="actions">
                                <a href="{{ url_for('authority_edit', item_id=item.id, lang=lang) }}">{{ t('common.edit', lang) }}</a>
                                <form method="post" action="{{ url_for('authority_delete', item_id=item.id, lang=lang) }}">
                                    <button type="submit">{{ t('common.delete', lang) }}</button>
                                </form>
                            </div>
                        </td>
                    </tr>
                {% endfor %}
            </tbody>
        </table>
        """
        return render_page(lang, t("authority.title", lang), body, items=items)

    @app.route("/authority/new", methods=["GET", "POST"])
    def authority_new() -> str:
        lang = get_selected_language()
        if request.method == "POST":
            upsert_authority_item(None, dict(request.form))
            return redirect(url_for("authority", lang=lang))

        form_data = {
            "main_theme": "",
            "target_communities": "",
            "planned_articles": "",
            "planned_talks": "",
            "planned_github_repos": "",
            "events": "",
            "people_recommenders": "",
            "public_evidence": "",
            "status": "planned",
        }
        body = """
        <h1>{{ t('authority.new', lang) }}</h1>
        <form method="post" action="{{ url_for('authority_new', lang=lang) }}">
            {{ authority_form|safe }}
            <button type="submit">{{ t('common.save', lang) }}</button>
        </form>
        """
        return render_page(lang, t("authority.new", lang), body, authority_form=render_authority_form(lang, form_data))

    @app.route("/authority/<int:item_id>/edit", methods=["GET", "POST"])
    def authority_edit(item_id: int) -> str:
        lang = get_selected_language()
        item = fetch_authority_item_by_id(item_id)
        if not item:
            return redirect(url_for("authority", lang=lang))
        if request.method == "POST":
            upsert_authority_item(item_id, dict(request.form))
            return redirect(url_for("authority", lang=lang))

        body = """
        <h1>{{ t('authority.edit', lang) }}</h1>
        <form method="post" action="{{ url_for('authority_edit', item_id=item.id, lang=lang) }}">
            {{ authority_form|safe }}
            <button type="submit">{{ t('common.save', lang) }}</button>
        </form>
        """
        return render_page(lang, t("authority.edit", lang), body, item=item, authority_form=render_authority_form(lang, item))

    @app.route("/authority/<int:item_id>/delete", methods=["POST"])
    def authority_delete(item_id: int) -> Any:
        lang = get_selected_language()
        delete_authority_item(item_id)
        return redirect(url_for("authority", lang=lang))

    @app.route("/github-projects")
    def github_projects() -> str:
        lang = get_selected_language()
        items = fetch_github_projects()
        body = """
        <h1>{{ t('github.title', lang) }}</h1>
        <p>{{ t('github.subtitle', lang) }}</p>
        <a href="{{ url_for('github_project_new', lang=lang) }}">{{ t('github.new', lang) }}</a>
        <table>
            <thead>
                <tr>
                    <th>{{ t('github.field.name', lang) }}</th>
                    <th>{{ t('github.field.status', lang) }}</th>
                    <th>{{ t('github.field.potential_impact', lang) }}</th>
                    <th>{{ t('common.actions', lang) }}</th>
                </tr>
            </thead>
            <tbody>
                {% for item in items %}
                    <tr>
                        <td>{{ item.name }}</td>
                        <td><span class="badge {{ item.status }}">{{ t('status.' ~ item.status, lang) }}</span></td>
                        <td>{{ item.potential_impact }}</td>
                        <td>
                            <div class="actions">
                                <a href="{{ url_for('github_project_edit', item_id=item.id, lang=lang) }}">{{ t('common.edit', lang) }}</a>
                                <form method="post" action="{{ url_for('github_project_delete', item_id=item.id, lang=lang) }}">
                                    <button type="submit">{{ t('common.delete', lang) }}</button>
                                </form>
                            </div>
                        </td>
                    </tr>
                {% endfor %}
            </tbody>
        </table>
        """
        return render_page(lang, t("github.title", lang), body, items=items)

    @app.route("/github-projects/new", methods=["GET", "POST"])
    def github_project_new() -> str:
        lang = get_selected_language()
        if request.method == "POST":
            upsert_github_project(None, dict(request.form))
            return redirect(url_for("github_projects", lang=lang))

        form_data = {
            "name": "",
            "summary": "",
            "solved_problem": "",
            "technologies": "",
            "repo_url": "",
            "status": "idea",
            "potential_impact": "",
            "generated_evidence": "",
            "related_articles": "",
            "related_criteria": "",
        }
        body = """
        <h1>{{ t('github.new', lang) }}</h1>
        <form method="post" action="{{ url_for('github_project_new', lang=lang) }}">
            {{ github_form|safe }}
            <button type="submit">{{ t('common.save', lang) }}</button>
        </form>
        """
        return render_page(lang, t("github.new", lang), body, github_form=render_github_project_form(lang, form_data))

    @app.route("/github-projects/<int:item_id>/edit", methods=["GET", "POST"])
    def github_project_edit(item_id: int) -> str:
        lang = get_selected_language()
        item = fetch_github_project_by_id(item_id)
        if not item:
            return redirect(url_for("github_projects", lang=lang))
        if request.method == "POST":
            upsert_github_project(item_id, dict(request.form))
            return redirect(url_for("github_projects", lang=lang))

        body = """
        <h1>{{ t('github.edit', lang) }}</h1>
        <form method="post" action="{{ url_for('github_project_edit', item_id=item.id, lang=lang) }}">
            {{ github_form|safe }}
            <button type="submit">{{ t('common.save', lang) }}</button>
        </form>
        """
        return render_page(lang, t("github.edit", lang), body, item=item, github_form=render_github_project_form(lang, item))

    @app.route("/github-projects/<int:item_id>/delete", methods=["POST"])
    def github_project_delete(item_id: int) -> Any:
        lang = get_selected_language()
        delete_github_project(item_id)
        return redirect(url_for("github_projects", lang=lang))

    @app.route("/linkedin-content")
    def linkedin_content() -> str:
        lang = get_selected_language()
        items = fetch_linkedin_contents()
        body = """
        <h1>{{ t('linkedin.title', lang) }}</h1>
        <p>{{ t('linkedin.subtitle', lang) }}</p>
        <a href="{{ url_for('linkedin_content_new', lang=lang) }}">{{ t('linkedin.new', lang) }}</a>
        <table>
            <thead>
                <tr>
                    <th>{{ t('linkedin.field.title', lang) }}</th>
                    <th>{{ t('linkedin.field.content_type', lang) }}</th>
                    <th>{{ t('linkedin.field.status', lang) }}</th>
                    <th>{{ t('linkedin.field.objective', lang) }}</th>
                    <th>{{ t('common.actions', lang) }}</th>
                </tr>
            </thead>
            <tbody>
                {% for item in items %}
                    <tr>
                        <td>{{ item.title }}</td>
                        <td>{{ t('linkedin.type.' ~ item.content_type, lang) }}</td>
                        <td><span class="badge {{ item.status }}">{{ t('status.' ~ item.status, lang) }}</span></td>
                        <td>{{ t('linkedin.objective.' ~ item.objective, lang) }}</td>
                        <td>
                            <div class="actions">
                                <a href="{{ url_for('linkedin_content_edit', item_id=item.id, lang=lang) }}">{{ t('common.edit', lang) }}</a>
                                <form method="post" action="{{ url_for('linkedin_content_delete', item_id=item.id, lang=lang) }}">
                                    <button type="submit">{{ t('common.delete', lang) }}</button>
                                </form>
                            </div>
                        </td>
                    </tr>
                {% endfor %}
            </tbody>
        </table>
        """
        return render_page(lang, t("linkedin.title", lang), body, items=items)

    @app.route("/linkedin-content/new", methods=["GET", "POST"])
    def linkedin_content_new() -> str:
        lang = get_selected_language()
        if request.method == "POST":
            upsert_linkedin_content(None, dict(request.form))
            return redirect(url_for("linkedin_content", lang=lang))

        form_data = {
            "title": "",
            "content_type": "short_post",
            "theme": "",
            "status": "draft",
            "planned_date": "",
            "published_link": "",
            "related_evidence": "",
            "objective": "authority",
        }
        body = """
        <h1>{{ t('linkedin.new', lang) }}</h1>
        <form method="post" action="{{ url_for('linkedin_content_new', lang=lang) }}">
            {{ linkedin_form|safe }}
            <button type="submit">{{ t('common.save', lang) }}</button>
        </form>
        """
        return render_page(lang, t("linkedin.new", lang), body, linkedin_form=render_linkedin_content_form(lang, form_data))

    @app.route("/linkedin-content/<int:item_id>/edit", methods=["GET", "POST"])
    def linkedin_content_edit(item_id: int) -> str:
        lang = get_selected_language()
        item = fetch_linkedin_content_by_id(item_id)
        if not item:
            return redirect(url_for("linkedin_content", lang=lang))
        if request.method == "POST":
            upsert_linkedin_content(item_id, dict(request.form))
            return redirect(url_for("linkedin_content", lang=lang))

        body = """
        <h1>{{ t('linkedin.edit', lang) }}</h1>
        <form method="post" action="{{ url_for('linkedin_content_edit', item_id=item.id, lang=lang) }}">
            {{ linkedin_form|safe }}
            <button type="submit">{{ t('common.save', lang) }}</button>
        </form>
        """
        return render_page(lang, t("linkedin.edit", lang), body, item=item, linkedin_form=render_linkedin_content_form(lang, item))

    @app.route("/linkedin-content/<int:item_id>/delete", methods=["POST"])
    def linkedin_content_delete(item_id: int) -> Any:
        lang = get_selected_language()
        delete_linkedin_content(item_id)
        return redirect(url_for("linkedin_content", lang=lang))

    @app.route("/recommenders")
    def recommenders() -> str:
        lang = get_selected_language()
        items = fetch_recommenders()
        body = """
        <h1>{{ t('recommender.title', lang) }}</h1>
        <p>{{ t('recommender.subtitle', lang) }}</p>
        <a href="{{ url_for('recommender_new', lang=lang) }}">{{ t('recommender.new', lang) }}</a>
        <table>
            <thead>
                <tr>
                    <th>{{ t('recommender.field.name', lang) }}</th>
                    <th>{{ t('recommender.field.relationship', lang) }}</th>
                    <th>{{ t('recommender.field.letter_strength', lang) }}</th>
                    <th>{{ t('recommender.field.status', lang) }}</th>
                    <th>{{ t('common.actions', lang) }}</th>
                </tr>
            </thead>
            <tbody>
                {% for item in items %}
                    <tr>
                        <td>{{ item.name }}</td>
                        <td>{{ item.relationship }}</td>
                        <td><span class="badge {{ item.letter_strength }}">{{ t('strength.' ~ item.letter_strength, lang) }}</span></td>
                        <td><span class="badge {{ item.status }}">{{ t('status.' ~ item.status, lang) }}</span></td>
                        <td>
                            <div class="actions">
                                <a href="{{ url_for('recommender_edit', item_id=item.id, lang=lang) }}">{{ t('common.edit', lang) }}</a>
                                <form method="post" action="{{ url_for('recommender_delete', item_id=item.id, lang=lang) }}">
                                    <button type="submit">{{ t('common.delete', lang) }}</button>
                                </form>
                            </div>
                        </td>
                    </tr>
                {% endfor %}
            </tbody>
        </table>
        """
        return render_page(lang, t("recommender.title", lang), body, items=items)

    @app.route("/recommenders/new", methods=["GET", "POST"])
    def recommender_new() -> str:
        lang = get_selected_language()
        if request.method == "POST":
            upsert_recommender(None, dict(request.form))
            return redirect(url_for("recommenders", lang=lang))

        form_data = {
            "name": "",
            "relationship": "",
            "organization": "",
            "role_title": "",
            "email": "",
            "letter_strength": "medium",
            "independence": "independent",
            "validation_area": "",
            "status": "prospect",
            "notes": "",
        }
        body = """
        <h1>{{ t('recommender.new', lang) }}</h1>
        <form method="post" action="{{ url_for('recommender_new', lang=lang) }}">
            {{ recommender_form|safe }}
            <button type="submit">{{ t('common.save', lang) }}</button>
        </form>
        """
        return render_page(lang, t("recommender.new", lang), body, recommender_form=render_recommender_form(lang, form_data))

    @app.route("/recommenders/<int:item_id>/edit", methods=["GET", "POST"])
    def recommender_edit(item_id: int) -> str:
        lang = get_selected_language()
        item = fetch_recommender_by_id(item_id)
        if not item:
            return redirect(url_for("recommenders", lang=lang))
        if request.method == "POST":
            upsert_recommender(item_id, dict(request.form))
            return redirect(url_for("recommenders", lang=lang))

        body = """
        <h1>{{ t('recommender.edit', lang) }}</h1>
        <form method="post" action="{{ url_for('recommender_edit', item_id=item.id, lang=lang) }}">
            {{ recommender_form|safe }}
            <button type="submit">{{ t('common.save', lang) }}</button>
        </form>
        """
        return render_page(lang, t("recommender.edit", lang), body, item=item, recommender_form=render_recommender_form(lang, item))

    @app.route("/recommenders/<int:item_id>/delete", methods=["POST"])
    def recommender_delete(item_id: int) -> Any:
        lang = get_selected_language()
        delete_recommender(item_id)
        return redirect(url_for("recommenders", lang=lang))

    @app.route("/report/export")
    def export_report() -> Any:
        lang = get_selected_language()
        payload = build_organizational_report_payload()
        format_name = request.args.get("format", "json").strip().lower()

        if request.args.get("download") == "1":
            if format_name == "markdown":
                content = build_markdown_report(payload)
                mimetype = "text/markdown"
                filename = "readiness_report.md"
            elif format_name == "csv":
                content = build_csv_report(payload)
                mimetype = "text/csv"
                filename = "readiness_report.csv"
            else:
                content = json.dumps(payload, ensure_ascii=False, indent=2)
                mimetype = "application/json"
                filename = "readiness_report.json"
            return app.response_class(
                content,
                mimetype=mimetype,
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )

        body = """
        <h1>{{ t('report.title', lang) }}</h1>
        <p>{{ t('report.subtitle', lang) }}</p>
        <p class="small">{{ t('report.private_filter_note', lang) }}</p>
        <p>
            <a href="{{ url_for('export_report', lang=lang, download='1') }}">{{ t('report.download_json', lang) }}</a>
        </p>
        <p class="small">
            <a href="{{ url_for('export_report', lang=lang, download='1', format='markdown') }}">Markdown</a>
            |
            <a href="{{ url_for('export_report', lang=lang, download='1', format='csv') }}">CSV</a>
        </p>
        <div class="cards">
            <article class="card"><h3>{{ t('dashboard.card.evidences', lang) }}</h3><p class="metric">{{ payload.evidences|length }}</p></article>
            <article class="card"><h3>{{ t('dashboard.card.overall_score', lang) }}</h3><p class="metric">{{ payload.readiness.eb2.overall_score }}</p></article>
            <article class="card"><h3>{{ t('dashboard.card.niw_score', lang) }}</h3><p class="metric">{{ payload.readiness.niw_average }}</p></article>
        </div>
        """
        return render_page(lang, t("report.title", lang), body, payload=payload)

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
