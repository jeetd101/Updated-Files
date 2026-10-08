#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
command -v docker >/dev/null || { echo "Docker is required."; exit 1; }
[ -f .env ] || cp .env.example .env
docker compose up -d --build
echo "Local User : http://127.0.0.1:8030/"
echo "Admin      : http://127.0.0.1:8030/admin-access"
echo "Super Admin: http://127.0.0.1:8030/super-admin-access"
