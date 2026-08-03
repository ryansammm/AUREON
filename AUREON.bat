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

start "" http://127.0.0.1:8000
".venv\Scripts\python.exe" web\app.py

echo.
echo Server stopped.
pause
