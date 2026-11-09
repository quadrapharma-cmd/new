#!/usr/bin/env sh
# usage: ./restore.sh backups/dossier-YYYY-MM-DD_HHMM.tgz   (stops the app, replaces ALL data with the backup)
set -e
cd "$(dirname "$0")"; [ -f "$1" ] || { echo "usage: $0 <backup.tgz>"; exit 1; }
docker compose stop app
docker run --rm -v dossier-builder-data:/data -v "$PWD/$(dirname "$1")":/b alpine sh -c "rm -rf /data/* /data/.[!.]* 2>/dev/null; tar xzf /b/$(basename "$1") -C /data && mv /data/workspace.snapshot.sqlite /data/workspace.sqlite && chown -R 10001 /data"
docker compose start app
echo "restored from $1"
