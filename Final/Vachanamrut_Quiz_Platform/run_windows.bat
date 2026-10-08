@echo off
setlocal
cd /d "%~dp0"

echo ====================================================
echo Vachanamrut Quiz Platform v3.1 - MySQL
echo ====================================================

where py >nul 2>nul
if %errorlevel%==0 (
    set PY=py
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        set PY=python
    ) else (
        echo Python was not found. Install Python 3.11 or newer first.
        pause
        exit /b 1
    )
)

if not exist .venv (
    echo Creating virtual environment...
    %PY% -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

if not exist .env (
    copy .env.example .env >nul
    echo.
    echo IMPORTANT: .env was created.
    echo Configure MYSQL_HOST, MYSQL_DATABASE, MYSQL_USER and MYSQL_PASSWORD first.
    echo If MySQL is not already installed/running, use Docker Compose instead.
    echo.
    notepad .env
    pause
)

python scripts\init_db.py
if errorlevel 1 (
    echo.
    echo Could not connect to MySQL. Check the MySQL values in .env.
    echo For the easiest setup run: docker compose up -d --build
    pause
    exit /b 1
)

echo.
echo Local User : http://127.0.0.1:8030/
echo Admin      : http://127.0.0.1:8030/admin-access
echo Super Admin: http://127.0.0.1:8030/super-admin-access
echo.
start "" http://127.0.0.1:8030/
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8030
pause
