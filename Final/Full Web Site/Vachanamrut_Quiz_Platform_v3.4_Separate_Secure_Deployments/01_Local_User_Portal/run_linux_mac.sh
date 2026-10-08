#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created private .env. Set MYSQL_PASSWORD, then run this script again."
  exit 1
fi
export PORTAL_MODE=local_user
python scripts/init_db.py
exec python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8041
