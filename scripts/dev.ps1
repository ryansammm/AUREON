# AUREON dev server control. Usage (PowerShell):
#   .\scripts\dev.ps1 -Status     show server state
#   .\scripts\dev.ps1 -Start      (re)build frontend, start server, wait healthy
#   .\scripts\dev.ps1 -Restart    stop everything, then Start
#   .\scripts\dev.ps1 -Stop       stop server + orphaned fluidsynth
#   .\scripts\dev.ps1 -Logs       tail server output
param(
    [switch]$Status,
    [switch]$Start,
    [switch]$Restart,
    [switch]$Stop,
    [switch]$Logs
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$port = 8000

function Get-ServerPids {
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match 'web[\\/]app\.py' }
}
function Get-FluidsynthPids {
    Get-Process -Name "fluidsynth*" -ErrorAction SilentlyContinue
}
function Test-PortFree {
    -not (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}

function Stop-All {
    foreach ($p in Get-ServerPids) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
    foreach ($p in Get-FluidsynthPids) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
    # Safety net: whatever actually owns the port dies too (catches any
    # server started with a relative vs absolute path mismatch).
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $conn) { Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Milliseconds 800
}

if ($Status) {
    $srv = Get-ServerPids
    if ($srv) { "server: RUNNING (pid $($srv.ProcessId -join ','))" }
    else { "server: stopped" }
    if (Test-PortFree) { "port $port : free" } else { "port $port : IN USE" }
    $fs = Get-FluidsynthPids
    if ($fs) { "fluidsynth orphans: $($fs.Id -join ',')" } else { "fluidsynth orphans: none" }
    exit 0
}

if ($Stop) {
    Stop-All
    "stopped. port free: $(Test-PortFree)"
    exit 0
}

if ($Logs) {
    Get-Content (Join-Path $root "server.out.log") -Tail 30 -ErrorAction SilentlyContinue
    Get-Content (Join-Path $root "server.err.log") -Tail 30 -ErrorAction SilentlyContinue
    exit 0
}

if ($Restart) {
    Stop-All
    "cleaned stale processes"
    $Start = $true
}

if (-not $Start) {
    Write-Host "no switch given; use -Status / -Start / -Restart / -Stop / -Logs"
    exit 1
}

if (-not (Test-PortFree)) {
    Stop-All
    "port $port was in use -> cleared"
}

if (Test-Path (Join-Path $root "web\frontend\package.json")) {
    "building frontend..."
    Push-Location (Join-Path $root "web\frontend")
    npm run build 2>&1 | Select-Object -Last 3
    if ($LASTEXITCODE -ne 0) { Pop-Location; Write-Error "frontend build failed"; exit 1 }
    Pop-Location
} else {
    "skipping frontend build (no package.json)"
}

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

Start-Process -FilePath $py -ArgumentList "web\app.py" -WorkingDirectory $root `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $root "server.out.log") `
    -RedirectStandardError (Join-Path $root "server.err.log")

$deadline = (Get-Date).AddSeconds(30)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 500
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        "server UP on 127.0.0.1:$port"
        exit 0
    }
}
"server FAILED to start within 30s; last log lines:"
Get-Content (Join-Path $root "server.err.log") -Tail 20 -ErrorAction SilentlyContinue
exit 1
