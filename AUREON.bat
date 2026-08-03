@echo off
title AUREON Web UI
cd /d "D:\Friday\AUREON"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] .venv not found. Create it first:
    echo     python -m venv .venv
    echo     .venv\Scripts\python -m pip install -r requirements.txt
    pause
    exit /b 1
)

if not exist "web\frontend\dist\index.html" (
    echo [WARN] Frontend not built. Run:
    echo     cd web\frontend
    echo     npm install
    echo     npm run build
    echo (the API will still work at /api while the page shows a dev hint)
    echo.
)

start "" http://127.0.0.1:8000
".venv\Scripts\python.exe" web\app.py

echo.
echo Server stopped.
pause
