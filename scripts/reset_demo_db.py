import sqlite3
from pathlib import Path

from app import BASE_DIR, init_db


def reset_demo_db() -> None:
    db_path = BASE_DIR / "data" / "studio.db"
    init_db(str(db_path))
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM evidences")
        cursor.execute("DELETE FROM profiles")
        cursor.execute(
            "INSERT INTO profiles (full_name, headline, target_domain, locale) VALUES (?, ?, ?, ?)",
            ("Demo Profile", "Senior Engineer", "AI Platforms", "en-US"),
        )
        profile_id = cursor.lastrowid
        cursor.execute(
            """
            INSERT INTO evidences (profile_id, category, title, description, impact_level, is_private)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                profile_id,
                "open_source",
                "Public OSS Maintainer",
                "Maintains demo open-source repositories and technical docs.",
                4,
                0,
            ),
        )
        conn.commit()
        print(f"Demo DB reset at: {db_path}")
    finally:
        conn.close()


if __name__ == "__main__":
    reset_demo_db()
