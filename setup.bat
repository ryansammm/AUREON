@echo off
setlocal enabledelayedexpansion
title AUREON — First-Time Setup
cd /d "%~dp0"

echo ============================================
echo   AUREON — First-Time Setup
echo ============================================
echo.

set "HAS_ERROR=0"

:: ── 1. Python ──────────────────────────────────
echo [1/5] Checking Python...
python --version >nul 2>&1
if !errorlevel! neq 0 (
    echo   [X] Python NOT found.
    echo.
    set /p "INSTALL_PYTHON=   Install Python now via winget? (Y/n): "
    if /i "!INSTALL_PYTHON!"=="n" (
        echo   Aborted. Install Python 3.10+ from https://python.org and re-run setup.bat
        set "HAS_ERROR=1"
        goto :skip_python
    )
    winget install Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements
    if !errorlevel! neq 0 (
        echo   [X] winget install failed. Install manually: https://python.org
        set "HAS_ERROR=1"
    ) else (
        echo   [OK] Python installed. You may need to restart your terminal.
    )
) else (
    for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "PY_VER=%%v"
    echo   [OK] Python !PY_VER! found
)
:skip_python

:: ── 2. Node.js ─────────────────────────────────
echo.
echo [2/5] Checking Node.js...
node --version >nul 2>&1
if !errorlevel! neq 0 (
    echo   [X] Node.js NOT found.
    echo.
    set /p "INSTALL_NODE=   Install Node.js now via winget? (Y/n): "
    if /i "!INSTALL_NODE!"=="n" (
        echo   Aborted. Install Node.js 18+ from https://nodejs.org and re-run setup.bat
        set "HAS_ERROR=1"
        goto :skip_node
    )
    winget install OpenJS.NodeJS.LTS --silent --accept-source-agreements --accept-package-agreements
    if !errorlevel! neq 0 (
        echo   [X] winget install failed. Install manually: https://nodejs.org
        set "HAS_ERROR=1"
    ) else (
        echo   [OK] Node.js installed. You may need to restart your terminal.
    )
) else (
    for /f %%v in ('node --version 2^>^&1') do set "NODE_VER=%%v"
    echo   [OK] Node.js !NODE_VER! found
)
:skip_node

:: ── 3. Python venv + pip ──────────────────────
echo.
echo [3/5] Checking Python virtual environment...
if not exist ".venv\Scripts\python.exe" (
    echo   Creating .venv...
    python -m venv .venv
    if !errorlevel! neq 0 (
        echo   [X] Failed to create .venv
        set "HAS_ERROR=1"
        goto :skip_venv
    )
    echo   [OK] .venv created
)
echo   Installing Python dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet --disable-pip-version-check
if !errorlevel! neq 0 (
    echo   [X] pip install failed
    set "HAS_ERROR=1"
) else (
    echo   [OK] Python packages installed
)
:skip_venv

:: ── 4. npm install ────────────────────────────
echo.
echo [4/5] Checking frontend dependencies...
if not exist "web\frontend\node_modules" (
    echo   Installing npm packages...
    pushd web\frontend
    call npm install --silent
    popd
    if !errorlevel! neq 0 (
        echo   [X] npm install failed
        set "HAS_ERROR=1"
    ) else (
        echo   [OK] npm packages installed
    )
) else (
    echo   [OK] node_modules already present
)

:: ── 5. Frontend build ─────────────────────────
echo.
echo [5/5] Building frontend...
if not exist "web\frontend\dist\index.html" (
    pushd web\frontend
    call npm run build --silent
    popd
    if !errorlevel! neq 0 (
        echo   [X] Frontend build failed
        set "HAS_ERROR=1"
    ) else (
        echo   [OK] Frontend built
    )
) else (
    echo   [OK] dist/ already present
)

:: ── .env check ────────────────────────────────
echo.
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo   [i] Created .env from .env.example
        echo       Edit .env to add your API keys (optional for AI features).
        echo       Or use the Settings page in the app.
    )
) else (
    echo   [OK] .env found
)

:: ── Summary ───────────────────────────────────
echo.
echo ============================================
if "!HAS_ERROR!"=="0" (
    echo   Setup complete! Next steps:
    echo.
    echo     1. Double-click AUREON.bat to run
    echo     2. Open http://127.0.0.1:8000
    echo     3. Optional: add API keys in Settings page
) else (
    echo   Setup finished with errors. Fix the issues above
    echo   and re-run setup.bat, or proceed to AUREON.bat.
)
echo ============================================
echo.
pause
