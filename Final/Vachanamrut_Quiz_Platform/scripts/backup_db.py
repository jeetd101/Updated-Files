"""Create a portable JSON backup of every application table from MySQL or SQLite."""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import inspect  # noqa: E402
from backend.app.database import ENGINE, database_info  # noqa: E402

BACKUP_DIR = ROOT / "database" / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
backup = BACKUP_DIR / f"quiz_platform_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

payload = {"database": database_info(), "created_at": datetime.utcnow().isoformat() + "Z", "tables": {}}
with ENGINE.connect() as conn:
    inspector = inspect(conn)
    for table in inspector.get_table_names():
        result = conn.exec_driver_sql(f"SELECT * FROM `{table}`" if ENGINE.dialect.name == "mysql" else f'SELECT * FROM "{table}"')
        keys = list(result.keys())
        payload["tables"][table] = [dict(zip(keys, row)) for row in result.fetchall()]
backup.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
print(f"Backup created: {backup}")
