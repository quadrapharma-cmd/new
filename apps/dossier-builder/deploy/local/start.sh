#!/usr/bin/env sh
set -e
cd "$(dirname "$0")"
command -v docker >/dev/null || { echo "Install Docker first: https://docs.docker.com/engine/install/"; exit 1; }
[ -f .env ] || { cp .env.example .env; echo "Edit .env (DB_ADMIN_PASSWORD, 10+ characters), then run ./start.sh again."; exit 1; }
docker compose up -d --build
echo "Running: http://localhost:${PORT:-8765}  (colleagues: http://$(hostname -I 2>/dev/null | awk '{print $1}'):8765)"
