"""Create the MySQL database and application user for non-Docker deployments.

Requires a MySQL account with CREATE DATABASE / CREATE USER privileges.
Set MYSQL_ADMIN_USER and MYSQL_ADMIN_PASSWORD in .env before running.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import sys

from dotenv import load_dotenv
import pymysql

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

host = os.getenv("MYSQL_HOST", "127.0.0.1")
port = int(os.getenv("MYSQL_PORT", "3306"))
database = os.getenv("MYSQL_DATABASE", "vachanamrut_quiz")
app_user = os.getenv("MYSQL_USER", "quiz_user")
app_password = os.getenv("MYSQL_PASSWORD", "")
admin_user = os.getenv("MYSQL_ADMIN_USER", "root")
admin_password = os.getenv("MYSQL_ADMIN_PASSWORD", os.getenv("MYSQL_ROOT_PASSWORD", ""))

for label, value in {"MYSQL_DATABASE": database, "MYSQL_USER": app_user}.items():
    if not re.fullmatch(r"[A-Za-z0-9_]+", value):
        raise SystemExit(f"{label} may contain only letters, numbers and underscore.")
if not app_password:
    raise SystemExit("MYSQL_PASSWORD is required in .env")

conn = pymysql.connect(host=host, port=port, user=admin_user, password=admin_password, autocommit=True, charset="utf8mb4")
try:
    with conn.cursor() as cur:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cur.execute(f"CREATE USER IF NOT EXISTS '{app_user}'@'%' IDENTIFIED BY %s", (app_password,))
        cur.execute(f"ALTER USER '{app_user}'@'%' IDENTIFIED BY %s", (app_password,))
        cur.execute(f"GRANT ALL PRIVILEGES ON `{database}`.* TO '{app_user}'@'%'")
        cur.execute("FLUSH PRIVILEGES")
finally:
    conn.close()

print(f"MySQL database '{database}' and application user '{app_user}' are ready.")
print("Now run: python scripts/init_db.py")
