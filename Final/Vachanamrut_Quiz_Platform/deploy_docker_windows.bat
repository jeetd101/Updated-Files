@echo off
setlocal
cd /d "%~dp0"
where docker >nul 2>nul
if errorlevel 1 (
  echo Docker was not found. Install Docker Desktop first.
  pause
  exit /b 1
)
if not exist .env (
  copy .env.example .env >nul
  echo Created .env. For a public deployment, edit APP_SECRET and MySQL passwords.
)
docker compose up -d --build
if errorlevel 1 (
  echo Docker deployment failed. Run: docker compose logs
  pause
  exit /b 1
)
echo.
echo Deployment is running.
echo Local User : http://127.0.0.1:8030/
echo Admin      : http://127.0.0.1:8030/admin-access
echo Super Admin: http://127.0.0.1:8030/super-admin-access
start "" http://127.0.0.1:8030/
pause
