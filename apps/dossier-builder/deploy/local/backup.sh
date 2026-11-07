#!/usr/bin/env sh
# Consistent backup while the app keeps running: SQLite online snapshot + files, into backups/
set -e
cd "$(dirname "$0")"; mkdir -p backups
TS=$(date +%F_%H%M)
docker compose exec -T app python -c 'import sqlite3; s=sqlite3.connect("/data/workspace.sqlite"); d=sqlite3.connect("/data/workspace.snapshot.sqlite"); s.backup(d); d.close(); print("snapshot ok")'
docker run --rm -v dossier-builder-data:/data -v "$PWD/backups":/b alpine sh -c "tar czf /b/dossier-$TS.tgz -C /data --exclude=./workspace.sqlite --exclude=./workspace.sqlite-wal --exclude=./workspace.sqlite-shm . && rm -f /data/workspace.snapshot.sqlite"
echo "backups/dossier-$TS.tgz"
