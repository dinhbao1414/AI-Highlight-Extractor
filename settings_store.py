import os
import sqlite3
from typing import Dict


DB_PATH = os.path.join(os.path.dirname(__file__), "app_settings.db")


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    return conn


def load_settings() -> Dict[str, str]:
    with _get_connection() as conn:
        rows = conn.execute("SELECT key, value FROM app_settings").fetchall()
    return {key: value for key, value in rows}


def save_settings(settings: Dict[str, str]) -> None:
    rows = [(key, value or "") for key, value in settings.items()]
    with _get_connection() as conn:
        conn.executemany(
            """
            INSERT INTO app_settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
            """,
            rows,
        )
