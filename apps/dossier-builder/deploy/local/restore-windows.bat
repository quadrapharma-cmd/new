@echo off
rem usage: restore-windows.bat backups\dossier-YYYY-MM-DD_HHMM.tgz   (replaces ALL data with the backup)
cd /d "%~dp0"
if "%~1"=="" (echo usage: restore-windows.bat backups\dossier-....tgz & pause & exit /b 1)
docker compose stop app
docker run --rm -v dossier-builder-data:/data -v "%~dp1":/b alpine sh -c "rm -rf /data/* /data/.[!.]* 2>/dev/null; tar xzf /b/%~nx1 -C /data && mv /data/workspace.snapshot.sqlite /data/workspace.sqlite && chown -R 10001 /data"
docker compose start app
echo [OK] restored from %1
pause
