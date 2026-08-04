@echo off
setlocal enabledelayedexpansion
title AUREON — AI Music Generator
cd /d "%~dp0"

:: ── Pre-flight checks ────────────────────────
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo.
    echo   Run setup.bat first to install all dependencies.
    echo.
    pause
    exit /b 1
)

if not exist "web\frontend\dist\index.html" (
    echo [WARN] Frontend not built. Building now...
    pushd web\frontend
    call npm install --silent 2>nul
    call npm run build --silent
    popd
    if !errorlevel! neq 0 (
        echo [ERROR] Frontend build failed. Run manually:
        echo   cd web^&frontend ^&^& npm install ^&^& npm run build
        pause
        exit /b 1
    )
    echo [OK] Frontend built.
    echo.
)

:: ── API key check ─────────────────────────────
set "HAS_KEY=0"
if exist ".env" (
    findstr /v "^#" ".env" | findstr /i "GEMINI_API_KEY=" | findstr /v "GEMINI_API_KEY= " | findstr /v "GEMINI_API_KEY=" >nul 2>&1
    if !errorlevel! equ 0 set "HAS_KEY=1"
    findstr /v "^#" ".env" | findstr /i "GROQ_API_KEY=" | findstr /v "GROQ_API_KEY= " | findstr /v "GROQ_API_KEY=" >nul 2>&1
    if !errorlevel! equ 0 set "HAS_KEY=1"
)

if "!HAS_KEY!"=="0" (
    echo ============================================
    echo   No API keys detected in .env
    echo ============================================
    echo.
    echo   AI features (smart suggestions, scoring)
    echo   won't work without at least one key.
    echo.
    echo   Free tiers available:
    echo     Gemini: https://aistudio.google.com/app/apikey
    echo     Groq:   https://console.groq.com/keys
    echo.
    echo   You can add keys later via the Settings page.
    echo.
)

:: ── Launch server ─────────────────────────────
echo Starting AUREON server on http://127.0.0.1:8000 ...
echo.

start "" http://127.0.0.1:8000
".venv\Scripts\python.exe" web\app.py

echo.
echo Server stopped.
pause
