import sqlite3

from app import init_db


def test_init_db_creates_tables(tmp_path) -> None:
    db_path = tmp_path / "test.db"
    init_db(str(db_path))

    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
    finally:
        conn.close()

    assert "profile" in tables
    assert "settings" in tables
    assert "assessment_questions" in tables
    assert "assessment_answers" in tables
    assert "niw_prongs" in tables
    assert "evidences" in tables
    assert "roadmap_tasks" in tables
    assert "proposed_endeavor" in tables
    assert "authority_plan" in tables
    assert "github_projects" in tables
    assert "linkedin_content" in tables
    assert "recommenders" in tables
    assert "ai_analysis_runs" in tables
    assert "niw_prong_assessments" in tables


def test_seed_is_idempotent(tmp_path) -> None:
    db_path = tmp_path / "seed.db"
    init_db(str(db_path))
    init_db(str(db_path))

    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM assessment_questions")
        questions = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM niw_prongs")
        prongs = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM roadmap_tasks")
        roadmap = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM proposed_endeavor")
        endeavors = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM github_projects")
        github_projects = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM linkedin_content")
        linkedin_posts = cursor.fetchone()[0]
    finally:
        conn.close()

    assert questions == 13
    assert prongs == 3
    assert roadmap == 4
    assert endeavors == 1
    assert github_projects == 1
    assert linkedin_posts == 3
