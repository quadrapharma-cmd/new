@echo off
rem Consistent backup while the app keeps running (SQLite snapshot + files) into backups\
cd /d "%~dp0"
if not exist backups mkdir backups
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HHmm"') do set TS=%%i
docker compose exec -T app python -c 'import sqlite3; s=sqlite3.connect("/data/workspace.sqlite"); d=sqlite3.connect("/data/workspace.snapshot.sqlite"); s.backup(d); d.close(); print("snapshot ok")'
docker run --rm -v dossier-builder-data:/data -v "%cd%\backups":/b alpine sh -c "tar czf /b/dossier-%TS%.tgz -C /data --exclude=./workspace.sqlite --exclude=./workspace.sqlite-wal --exclude=./workspace.sqlite-shm . && rm -f /data/workspace.snapshot.sqlite"
echo [OK] backups\dossier-%TS%.tgz  - copy it to another disk or place.
pause
