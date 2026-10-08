"""Deployment structure and configured database connectivity check."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

required = [
    ROOT / "frontend/local_user/login.html",
    ROOT / "frontend/local_user/dashboard.html",
    ROOT / "frontend/admin/login.html",
    ROOT / "frontend/admin/dashboard.html",
    ROOT / "frontend/super_admin/login.html",
    ROOT / "frontend/super_admin/dashboard.html",
    ROOT / "backend/app/main.py",
    ROOT / "backend/app/database.py",
    ROOT / "database/mysql_schema.sql",
]
missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
if missing:
    raise SystemExit("Missing files: " + ", ".join(missing))

from sqlalchemy import inspect  # noqa: E402
from backend.app.database import ENGINE, database_info  # noqa: E402
from backend.app.main import init_db  # noqa: E402

init_db()
expected = {
    "users", "subjects", "chapters", "course_materials", "questions",
    "question_bank_uploads", "attempts", "responses", "revision_items",
    "notifications", "app_settings", "password_reset_otps", "password_reset_tokens",
}
with ENGINE.connect() as conn:
    tables = set(inspect(conn).get_table_names())
    conn.exec_driver_sql("SELECT 1")
missing_tables = expected - tables
if missing_tables:
    raise SystemExit(f"Database missing tables: {sorted(missing_tables)}")

print("Project structure: OK")
print(f"Database: OK ({database_info()})")
