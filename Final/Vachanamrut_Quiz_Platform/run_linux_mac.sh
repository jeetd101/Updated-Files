#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then python3 -m venv .venv; fi
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env. Configure MySQL values, then run this script again."
  exit 1
fi
python scripts/init_db.py
exec python -m uvicorn backend.app.main:app --host 0.0.0.0 --port "${PORT:-8030}"
