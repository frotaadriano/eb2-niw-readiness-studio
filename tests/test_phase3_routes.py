import sqlite3
import shutil
from pathlib import Path

import pytest

import app as app_module


@pytest.fixture
def client_with_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    original_base_dir = app_module.BASE_DIR
    locales_dir = tmp_path / "locales"
    locales_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(original_base_dir / "locales" / "pt-BR.json", locales_dir / "pt-BR.json")
    shutil.copyfile(original_base_dir / "locales" / "en-US.json", locales_dir / "en-US.json")

    monkeypatch.setattr(app_module, "BASE_DIR", tmp_path)
    db_path = tmp_path / "data" / "app.db"
    monkeypatch.setattr(app_module, "DEFAULT_DB_PATH", str(db_path))

    app_module.init_db(str(db_path))
    flask_app = app_module.create_app()
    flask_app.config["TESTING"] = True

    with flask_app.test_client() as client:
        yield client, db_path


def test_evidences_crud_basic(client_with_db) -> None:
    client, db_path = client_with_db

    create_response = client.post(
        "/evidences/new?lang=en-US",
        data={
            "title": "Demo Evidence",
            "evidence_type": "GitHub",
            "category": "assessment.category.public_projects",
            "description": "Project repository",
            "link_or_path": "https://example.com/repo",
            "evidence_date": "2026-01-10",
            "relevance": "4",
            "related_criteria": "Q_PUBLIC_PROJECTS",
            "status": "coletar",
            "notes": "Initial note",
            "can_send_to_ai": "on",
        },
    )
    assert create_response.status_code == 302

    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute("SELECT id, title, can_send_to_ai FROM evidences WHERE title = ?", ("Demo Evidence",)).fetchone()
        assert row is not None
        evidence_id = int(row[0])
        assert int(row[2]) == 1
    finally:
        conn.close()

    update_response = client.post(
        f"/evidences/{evidence_id}/edit?lang=en-US",
        data={
            "title": "Demo Evidence Updated",
            "evidence_type": "GitHub",
            "category": "assessment.category.public_projects",
            "description": "Updated description",
            "link_or_path": "https://example.com/repo2",
            "evidence_date": "2026-02-10",
            "relevance": "5",
            "related_criteria": "Q_PUBLIC_PROJECTS",
            "status": "pronto",
            "notes": "Ready",
        },
    )
    assert update_response.status_code == 302

    conn = sqlite3.connect(str(db_path))
    try:
        updated = conn.execute("SELECT title, status, can_send_to_ai FROM evidences WHERE id = ?", (evidence_id,)).fetchone()
        assert updated is not None
        assert updated[0] == "Demo Evidence Updated"
        assert updated[1] == "pronto"
        assert int(updated[2]) == 0
    finally:
        conn.close()

    delete_response = client.post(f"/evidences/{evidence_id}/delete?lang=en-US")
    assert delete_response.status_code == 302

    conn = sqlite3.connect(str(db_path))
    try:
        count = conn.execute("SELECT COUNT(*) FROM evidences WHERE id = ?", (evidence_id,)).fetchone()[0]
    finally:
        conn.close()
    assert count == 0


def test_roadmap_crud_basic(client_with_db) -> None:
    client, db_path = client_with_db

    create_response = client.post(
        "/roadmap/new?lang=en-US",
        data={
            "title": "Publish technical article",
            "description": "Draft and publish",
            "category": "authority",
            "priority": "high",
            "horizon": "30_90",
            "status": "backlog",
            "target_date": "2026-09-10",
            "estimated_effort": "6h",
            "estimated_impact": "high",
            "related_criteria": "assessment.category.publications",
        },
    )
    assert create_response.status_code == 302

    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute("SELECT id, title, status FROM roadmap_items WHERE title = ?", ("Publish technical article",)).fetchone()
        assert row is not None
        item_id = int(row[0])
        assert row[2] == "backlog"
    finally:
        conn.close()

    update_response = client.post(
        f"/roadmap/{item_id}/edit?lang=en-US",
        data={
            "title": "Publish technical article v2",
            "description": "Done",
            "category": "authority",
            "priority": "high",
            "horizon": "30_90",
            "status": "completed",
            "target_date": "2026-09-10",
            "estimated_effort": "8h",
            "estimated_impact": "high",
            "related_criteria": "assessment.category.publications",
        },
    )
    assert update_response.status_code == 302

    conn = sqlite3.connect(str(db_path))
    try:
        updated = conn.execute("SELECT title, status FROM roadmap_items WHERE id = ?", (item_id,)).fetchone()
        assert updated is not None
        assert updated[0] == "Publish technical article v2"
        assert updated[1] == "completed"
    finally:
        conn.close()

    delete_response = client.post(f"/roadmap/{item_id}/delete?lang=en-US")
    assert delete_response.status_code == 302

    conn = sqlite3.connect(str(db_path))
    try:
        count = conn.execute("SELECT COUNT(*) FROM roadmap_items WHERE id = ?", (item_id,)).fetchone()[0]
    finally:
        conn.close()
    assert count == 0


def test_gaps_page_is_generated_from_assessment_and_tasks(client_with_db) -> None:
    client, db_path = client_with_db

    conn = sqlite3.connect(str(db_path))
    try:
        question = conn.execute("SELECT id FROM assessment_questions ORDER BY sort_order LIMIT 1").fetchone()
        assert question is not None
        conn.execute(
            """
            INSERT INTO assessment_answers (question_id, answer, notes, score, justification, status, evidence_refs)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (int(question[0]), 1, "", 1, "low score", "fraco", ""),
        )
        conn.execute(
            """
            INSERT INTO roadmap_items
            (title, description, category, priority, horizon, status, target_date, estimated_effort, estimated_impact, related_criteria)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "Blocked task for tests",
                "",
                "execution",
                "critical",
                "0_30",
                "blocked",
                "2000-01-01",
                "2h",
                "high",
                "assessment.category.experience",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    response = client.get("/gaps?lang=en-US")
    assert response.status_code == 200
    content = response.get_data(as_text=True)
    assert "Blocked task for tests" in content
    assert "Critical" in content
