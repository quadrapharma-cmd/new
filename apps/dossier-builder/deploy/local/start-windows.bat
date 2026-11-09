@echo off
chcp 65001 >nul
cd /d "%~dp0"
where docker >nul 2>nul || (echo [!] Docker Desktop is not installed. Install it from https://www.docker.com/products/docker-desktop/ then run this again. & pause & exit /b 1)
docker info >nul 2>nul || (echo [!] Start Docker Desktop first, wait until it says "running", then run this again. & pause & exit /b 1)
if not exist .env (
  copy .env.example .env >nul
  echo [i] A settings file .env was created. Set DB_ADMIN_PASSWORD in it ^(10+ characters^), save, close Notepad.
  notepad .env
)
echo [i] Building and starting (the first time takes 10-20 minutes)...
docker compose up -d --build || (echo [!] Start failed. & pause & exit /b 1)
echo [OK] Running. Opening http://localhost:8765
start http://localhost:8765
pause
