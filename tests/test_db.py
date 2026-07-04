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

    assert "profiles" in tables
    assert "evidences" in tables
