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


def test_phase4_pages_are_available(client_with_db) -> None:
    client, _ = client_with_db

    for route in [
        "/proposed-endeavor?lang=en-US",
        "/authority?lang=en-US",
        "/github-projects?lang=en-US",
        "/linkedin-content?lang=en-US",
        "/recommenders?lang=en-US",
    ]:
        response = client.get(route)
        assert response.status_code == 200


def test_proposed_endeavor_crud(client_with_db) -> None:
    client, db_path = client_with_db

    create_response = client.post(
        "/proposed-endeavor/new?lang=en-US",
        data={
            "area": "AI Governance",
            "problem_to_solve": "Lack of governance in enterprise AI agents",
            "impacted_sector": "Health",
            "technologies": "Python, Azure OpenAI",
            "relevance": "Operational and regulatory relevance",
            "experience_evidence": "Architecture reviews and playbooks",
            "expected_impact": "Reduce incidents and improve adoption",
            "broader_importance": "Reusable model beyond one company",
            "short_version": "Build secure and scalable AI agent architectures.",
            "long_version": "Long narrative about public-impact architecture.",
            "status": "in_review",
        },
    )
    assert create_response.status_code == 302

    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            "SELECT id, area, status FROM proposed_endeavor WHERE area = ? ORDER BY id DESC",
            ("AI Governance",),
        ).fetchone()
        assert row is not None
        item_id = int(row[0])
        assert row[2] == "in_review"
    finally:
        conn.close()

    update_response = client.post(
        f"/proposed-endeavor/{item_id}/edit?lang=en-US",
        data={
            "area": "AI Governance Updated",
            "problem_to_solve": "Updated",
            "impacted_sector": "Finance",
            "technologies": "Python",
            "relevance": "Updated",
            "experience_evidence": "Updated",
            "expected_impact": "Updated",
            "broader_importance": "Updated",
            "short_version": "Updated short version",
            "long_version": "Updated long version",
            "status": "ready",
        },
    )
    assert update_response.status_code == 302

    conn = sqlite3.connect(str(db_path))
    try:
        updated = conn.execute(
            "SELECT area, status FROM proposed_endeavor WHERE id = ?",
            (item_id,),
        ).fetchone()
        assert updated is not None
        assert updated[0] == "AI Governance Updated"
        assert updated[1] == "ready"
    finally:
        conn.close()

    delete_response = client.post(f"/proposed-endeavor/{item_id}/delete?lang=en-US")
    assert delete_response.status_code == 302


def test_authority_github_linkedin_recommenders_crud(client_with_db) -> None:
    client, db_path = client_with_db

    authority_resp = client.post(
        "/authority/new?lang=en-US",
        data={
            "main_theme": "Applied AI architecture",
            "target_communities": "Cloud architects",
            "planned_articles": "2",
            "planned_talks": "1",
            "planned_github_repos": "1",
            "events": "Meetup",
            "people_recommenders": "Mentors",
            "public_evidence": "Talk recordings",
            "status": "active",
        },
    )
    assert authority_resp.status_code == 302

    github_resp = client.post(
        "/github-projects/new?lang=en-US",
        data={
            "name": "phase4-gh-project",
            "summary": "Demo",
            "solved_problem": "Problem",
            "technologies": "Flask",
            "repo_url": "https://example.com/repo",
            "status": "building",
            "potential_impact": "Medium",
            "generated_evidence": "Commits",
            "related_articles": "Blog",
            "related_criteria": "assessment.category.public_projects",
        },
    )
    assert github_resp.status_code == 302

    linkedin_resp = client.post(
        "/linkedin-content/new?lang=en-US",
        data={
            "title": "Phase 4 post",
            "content_type": "tutorial",
            "theme": "Local-first",
            "status": "planned",
            "planned_date": "2026-12-10",
            "published_link": "",
            "related_evidence": "project artifacts",
            "objective": "education",
        },
    )
    assert linkedin_resp.status_code == 302

    recommender_resp = client.post(
        "/recommenders/new?lang=en-US",
        data={
            "name": "Demo Recommender 2",
            "relationship": "Peer",
            "organization": "Demo Org",
            "role_title": "Principal Engineer",
            "email": "",
            "letter_strength": "high",
            "independence": "peer",
            "validation_area": "System architecture",
            "status": "contacted",
            "notes": "Synthetic profile",
        },
    )
    assert recommender_resp.status_code == 302

    conn = sqlite3.connect(str(db_path))
    try:
        authority = conn.execute(
            "SELECT status FROM authority_plan WHERE main_theme = ? ORDER BY id DESC",
            ("Applied AI architecture",),
        ).fetchone()
        github = conn.execute(
            "SELECT status FROM github_projects WHERE name = ?",
            ("phase4-gh-project",),
        ).fetchone()
        linkedin = conn.execute(
            "SELECT content_type, objective FROM linkedin_content WHERE title = ?",
            ("Phase 4 post",),
        ).fetchone()
        recommender = conn.execute(
            "SELECT status, letter_strength FROM recommenders WHERE name = ? ORDER BY id DESC",
            ("Demo Recommender 2",),
        ).fetchone()

        assert authority is not None
        assert authority[0] == "active"
        assert github is not None
        assert github[0] == "building"
        assert linkedin is not None
        assert linkedin[0] == "tutorial"
        assert linkedin[1] == "education"
        assert recommender is not None
        assert recommender[0] == "contacted"
        assert recommender[1] == "high"
    finally:
        conn.close()
