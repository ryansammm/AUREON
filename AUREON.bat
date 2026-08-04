@echo off
setlocal enabledelayedexpansion
title AUREON by XYKS
cd /d "%~dp0"

rem ============================================================
rem   AUREON launcher
rem
rem   AUREON.bat                start (or reuse) the server in the
rem                             background with self-healing watchdog,
rem                             then open the browser
rem   AUREON.bat -stop          stop server, watchdog and orphans
rem   AUREON.bat -status        show current state
rem   AUREON.bat -console       run the server in the foreground
rem                             (server logs stay in this window)
rem   AUREON.bat -autostart     register logon auto-start task
rem   AUREON.bat -noautostart   remove the logon auto-start task
rem ============================================================

if /i "%~1"=="-stop"        goto :stop
if /i "%~1"=="-status"      goto :status
if /i "%~1"=="-console"     goto :console
if /i "%~1"=="-autostart"   goto :autostart
if /i "%~1"=="-noautostart" goto :noautostart

rem -- Pre-flight: virtual environment --------------------------
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo.
    echo   Run setup.bat first to install all dependencies.
    echo.
    pause
    exit /b 1
)

rem -- Kill ALL orphaned AUREON processes from previous runs ----
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -and ($_.CommandLine -match 'web[/\\]app\.py|watchdog\.py') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; " ^
  "Get-Process -Name 'fluidsynth*' -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue"
timeout /t 2 /nobreak >nul 2>&1

rem -- Pre-flight: frontend build --------------------------------
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

rem -- API key check ----------------------------------------------
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

rem -- Already healthy? Just open the browser. --------------------
for /f "delims=" %%c in ('curl -s -m 3 -o nul -w "%%{http_code}" http://127.0.0.1:8000/api/config 2^>nul') do set "HC=%%c"
if "!HC!"=="200" (
    echo AUREON is already running.
    start "" http://127.0.0.1:8000
    exit /b 0
)

rem -- Start server + watchdog in the background -------------------
echo Starting AUREON server + watchdog (background, self-healing)...
echo.
powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "%~dp0scripts\dev.ps1" -Watch
if !errorlevel! neq 0 (
    echo [ERROR] Failed to start AUREON. See watchdog.log for details.
    pause
    exit /b 1
)

start "" http://127.0.0.1:8000
echo.
echo AUREON is running in the background.
echo   - health checks + auto-restart handled by scripts\watchdog.py
echo   - stop:   AUREON.bat -stop
echo   - status: AUREON.bat -status
echo   - logs:   scripts\dev.ps1 -Logs
echo   - auto-start at logon: AUREON.bat -autostart
echo.
exit /b 0

:console
".venv\Scripts\python.exe" web\app.py
echo.
echo Server stopped.
pause
exit /b 0

:stop
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\dev.ps1" -Stop
echo.
exit /b 0

:status
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\dev.ps1" -Status
echo.
exit /b 0

:autostart
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\dev.ps1" -AutoStart
echo.
exit /b 0

:noautostart
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\dev.ps1" -NoAutoStart
echo.
exit /b 0
