@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Run run_windows.bat once first so dependencies are installed.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
if not exist data\quiz_platform.db (
  echo data\quiz_platform.db was not found.
  echo Copy your OLD live quiz_platform.db into the data folder first.
  pause
  exit /b 1
)
python scripts\init_db.py
python scripts\migrate_sqlite_to_mysql.py --source data\quiz_platform.db
python scripts\check_project.py
pause
