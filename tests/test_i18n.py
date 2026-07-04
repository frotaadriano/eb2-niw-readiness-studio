import shutil
from pathlib import Path

import pytest

import app as app_module
from app import load_locale, t


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
        yield client


def test_locale_key_parity_minimum() -> None:
    pt = load_locale("pt-BR")
    en = load_locale("en-US")
    assert set(pt.keys()) == set(en.keys())


def test_fallback_to_english_locale() -> None:
    unknown = load_locale("fr-FR")
    en = load_locale("en-US")
    assert unknown == en


def test_missing_key_returns_key_name() -> None:
    assert t("missing.key", "en-US") == "missing.key"


def test_home_page_renders_in_english(client_with_db) -> None:
    response = client_with_db.get("/?lang=en-US")
    assert response.status_code == 200

    content = response.get_data(as_text=True)
    assert "EB2-NIW Readiness Studio" in content
    assert "Current language" in content
