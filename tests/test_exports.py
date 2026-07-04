import shutil
from pathlib import Path

import pytest

import app as app_module
from app import build_export_payload


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


def test_export_omits_private_evidences() -> None:
    profile = {"full_name": "Demo"}
    evidences = [
        {"title": "Public Item", "is_private": False},
        {"title": "Private Item", "is_private": True},
    ]

    payload = build_export_payload(profile, evidences)
    titles = [ev["title"] for ev in payload["evidences"]]
    assert "Public Item" in titles
    assert "Private Item" not in titles
    assert "Educational" in payload["disclaimer"]


def test_report_export_route_excludes_private_evidences(client_with_db) -> None:
    client, db_path = client_with_db

    create_public = client.post(
        "/evidences/new?lang=en-US",
        data={
            "title": "Public Evidence",
            "evidence_type": "GitHub",
            "category": "assessment.category.public_projects",
            "description": "Public",
            "link_or_path": "https://example.com/public",
            "evidence_date": "2026-07-04",
            "relevance": "4",
            "related_criteria": "Q_PUBLIC_PROJECTS",
            "status": "pronto",
            "notes": "",
            "can_send_to_ai": "on",
        },
    )
    assert create_public.status_code == 302

    create_private = client.post(
        "/evidences/new?lang=en-US",
        data={
            "title": "Private Evidence",
            "evidence_type": "Carta de recomendacao",
            "category": "assessment.category.recommendation_letters",
            "description": "Private",
            "link_or_path": "",
            "evidence_date": "2026-07-04",
            "relevance": "4",
            "related_criteria": "Q_RECOMMENDATION_LETTERS",
            "status": "coletar",
            "notes": "",
        },
    )
    assert create_private.status_code == 302

    response = client.get("/report/export?lang=en-US&download=1")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload is not None
    exported_titles = [item["title"] for item in payload["evidences"]]
    assert "Public Evidence" in exported_titles
    assert "Private Evidence" not in exported_titles

    # Keep db_path in fixture usage explicit so CI catches setup regressions.
    assert db_path.exists()
