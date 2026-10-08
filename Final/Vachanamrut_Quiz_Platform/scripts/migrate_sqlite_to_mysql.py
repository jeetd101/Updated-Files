"""Migrate all existing v3 SQLite data into the configured MySQL database.

Default source: data/quiz_platform.db
The destination is the MySQL database configured in .env.
Run this once before switching a live deployment from SQLite to MySQL.
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.database import DB_DIALECT, db  # noqa: E402
from backend.app.main import init_db  # noqa: E402

TABLES = [
    "users",
    "subjects",
    "chapters",
    "course_materials",
    "questions",
    "question_bank_uploads",
    "attempts",
    "responses",
    "revision_items",
    "notifications",
    "app_settings",
    "password_reset_otps",
    "password_reset_tokens",
]


def qident(name: str) -> str:
    return "`" + name.replace("`", "``") + "`"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(ROOT / "data" / "quiz_platform.db"))
    args = parser.parse_args()
    source = Path(args.source).resolve()
    if not source.exists():
        raise SystemExit(f"SQLite source not found: {source}")
    if DB_DIALECT != "mysql":
        raise SystemExit("Destination is not MySQL. Set DB_BACKEND=mysql / MYSQL_* in .env first.")

    init_db()
    src = sqlite3.connect(source)
    src.row_factory = sqlite3.Row
    try:
        source_tables = {r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        with db() as dest:
            dest.execute("SET FOREIGN_KEY_CHECKS=0")
            try:
                for table in TABLES:
                    if table not in source_tables:
                        print(f"Skip {table}: not present in source")
                        continue
                    source_cols = [r[1] for r in src.execute(f"PRAGMA table_info({qident(table)})")]
                    # Destination columns are queried through INFORMATION_SCHEMA.
                    dest_cols = [r["COLUMN_NAME"] for r in dest.execute(
                        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=? ORDER BY ORDINAL_POSITION",
                        (table,),
                    ).fetchall()]
                    cols = [c for c in source_cols if c in dest_cols]
                    if not cols:
                        continue
                    rows = src.execute(f"SELECT {','.join(qident(c) for c in cols)} FROM {qident(table)}").fetchall()
                    if not rows:
                        print(f"{table}: 0 rows")
                        continue
                    placeholders = ",".join("?" for _ in cols)
                    update_cols = [c for c in cols if c != "id" and c != "setting_key"]
                    if update_cols:
                        update_sql = ",".join(f"{qident(c)}=VALUES({qident(c)})" for c in update_cols)
                        suffix = " ON DUPLICATE KEY UPDATE " + update_sql
                    else:
                        suffix = ""
                    sql = f"INSERT INTO {qident(table)} ({','.join(qident(c) for c in cols)}) VALUES ({placeholders}){suffix}"
                    for row in rows:
                        dest.execute(sql, tuple(row[c] for c in cols))
                    print(f"{table}: migrated {len(rows)} rows")
            finally:
                dest.execute("SET FOREIGN_KEY_CHECKS=1")
    finally:
        src.close()

    print("SQLite -> MySQL migration complete. All existing users, attempts, answers, revisions and settings were copied.")


if __name__ == "__main__":
    main()
