@echo off
setlocal
cd /d "%~dp0"
echo ===============================================
echo Vachanamrut Quiz - Local User Portal v3.4
echo ===============================================
where py >nul 2>nul
if %errorlevel%==0 (set PY=py) else (where python >nul 2>nul && (set PY=python) || (echo Python 3.11+ not found.& pause & exit /b 1))
if not exist .venv %PY% -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist .env (
  copy .env.example .env >nul
  echo A PRIVATE .env file was created. Set the MySQL password used by the shared database.
  notepad .env
  pause
)
set PORTAL_MODE=local_user
python scripts\init_db.py
if errorlevel 1 (echo MySQL connection failed. Check your private .env file.& pause & exit /b 1)
start "" http://127.0.0.1:8041/
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8041
pause
