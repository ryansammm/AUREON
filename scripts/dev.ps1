# AUREON dev server control. Usage (PowerShell):
#   .\scripts\dev.ps1 -Status            show server / watchdog / port state
#   .\scripts\dev.ps1 -Start             (re)build frontend, start server, wait healthy
#   .\scripts\dev.ps1 -Restart           stop everything, then Start
#   .\scripts\dev.ps1 -Stop              stop server + watchdog + orphans
#   .\scripts\dev.ps1 -Logs              tail server output
#   .\scripts\dev.ps1 -Watch             start the watchdog in the background (self-healing)
#   .\scripts\dev.ps1 -WatchForeground   run the watchdog in the foreground (Ctrl+C stops)
#   .\scripts\dev.ps1 -Dev               start Flask + Vite dev server (HMR on :5173)
#   .\scripts\dev.ps1 -Hot               (with -Watch / -WatchForeground) restart on source change
#   .\scripts\dev.ps1 -AutoStart         register scheduled task to start AUREON at logon
#   .\scripts\dev.ps1 -NoAutoStart       remove the logon scheduled task
param(
    [switch]$Status,
    [switch]$Start,
    [switch]$Dev,
    [switch]$Restart,
    [switch]$Stop,
    [switch]$Logs,
    [switch]$Watch,
    [switch]$WatchForeground,
    [switch]$Hot,
    [switch]$AutoStart,
    [switch]$NoAutoStart
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$port = 8000

function Get-ServerPids {
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match 'web[\\/]app\.py' }
}
function Get-WatchdogPids {
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match 'watchdog\.py' }
}
function Get-FluidsynthPids {
    Get-Process -Name "fluidsynth*" -ErrorAction SilentlyContinue
}
function Get-VitePids {
    Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match 'vite' }
}
function Test-PortFree {
    -not (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}
function Test-Healthy {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$port/api/config" -UseBasicParsing -TimeoutSec 3
        return $r.StatusCode -eq 200
    } catch { return $false }
}

# Launch a process fully detached from the caller's console. Launching the
# server via Start-Process inherits the console, so the calling cmd/PowerShell
# window waits for the server to exit before returning the prompt ("hang").
# Win32_Process.Create spawns it under WMI with its own console instead.
# NOTE: shell execution (UseShellExecute=$true) on purpose — it does NOT pass
# the caller's stdout/stderr handles to the child, so a long-running server
# cannot keep the invoking shell's output pipe open. With UseShellExecute=$false
# the child inherits those handles, which makes agent/tool sessions that capture
# stdout hang forever waiting for EOF (see AGENTS.md).
function Start-Detached([string]$CommandLine) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "cmd.exe"
    $psi.Arguments = "/c $CommandLine"
    $psi.UseShellExecute = $true
    $psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    [System.Diagnostics.Process]::Start($psi) | Out-Null
}

function Get-Python {
    $py = Join-Path $root ".venv\Scripts\python.exe"
    if (Test-Path $py) { return $py }
    return "python"
}

function Start-Server {
    $py = Get-Python
    $out = Join-Path $root "server.out.log"
    $err = Join-Path $root "server.err.log"
    $cmd = "cd /d `"$root`" && `"$py`" web\app.py > `"$out`" 2> `"$err`""
    Start-Detached $cmd
}

function Start-Vite {
    $out = Join-Path $root "vite.out.log"
    $err = Join-Path $root "vite.err.log"
    $fe = Join-Path $root "web\frontend"
    $node = (Get-Command node.exe -ErrorAction SilentlyContinue).Source
    $vite = Join-Path $fe "node_modules\vite\bin\vite.js"
    if ($node -and (Test-Path $vite)) {
        # Direct node spawn (no npm/cmd shim) so no stray console window can
        # appear when Vite (re)starts; see scripts/watchdog.py start_vite().
        $cmd = "cd /d `"$fe`" && `"$node`" `"$vite`" > `"$out`" 2> `"$err`""
    } else {
        $cmd = "cd /d `"$fe`" && npm run dev > `"$out`" 2> `"$err`""
    }
    Start-Detached $cmd
}

function Start-Watchdog {
    $py = Get-Python
    $out = Join-Path $root "watchdog.out.log"
    $flags = ""
    if ($Dev) { $flags += " --dev" }
    if ($Hot) { $flags += " --hot" }
    $cmd = "cd /d `"$root`" && `"$py`" scripts\watchdog.py$flags > `"$out`" 2>&1"
    Start-Detached $cmd
}

function Stop-All {
    foreach ($p in Get-WatchdogPids) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
    foreach ($p in Get-ServerPids) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
    foreach ($p in Get-FluidsynthPids) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
    foreach ($p in Get-VitePids) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
    # Safety net: whatever actually owns the port dies too (catches any
    # server started with a relative vs absolute path mismatch).
    foreach ($p in ($port, 5173)) {
        $conn = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
        foreach ($c in $conn) { Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue }
    }
    Start-Sleep -Milliseconds 800
}

if ($Status) {
    $srv = Get-ServerPids
    $wd = Get-WatchdogPids
    $statusFile = Join-Path $root "server.status.json"
    if ($srv) { "server:      RUNNING (pid $($srv.ProcessId -join ','))" }
    else { "server:      stopped" }
    if ($wd) { "watchdog:    RUNNING (pid $($wd.ProcessId -join ','))" }
    else { "watchdog:    stopped" }
    if (Test-Path $statusFile) {
        $j = Get-Content $statusFile -Raw | ConvertFrom-Json
        "last state:  $($j.state) ($($j.detail)) - checks $($j.checks), restarts $($j.restarts)"
    }
    if (Test-PortFree) { "port $port :  free" } else { "port $port :  IN USE" }
    $fs = Get-FluidsynthPids
    if ($fs) { "fluidsynth:   orphans: $($fs.Id -join ',')" } else { "fluidsynth:   none" }
    $vite = Get-VitePids
    if ($vite) { "vite:        RUNNING (pid $($vite.ProcessId -join ','))" } else { "vite:        stopped" }
    exit 0
}

if ($Stop) {
    Stop-All
    "stopped server, watchdog + orphans. port free: $(Test-PortFree)"
    exit 0
}

if ($Logs) {
    Get-Content (Join-Path $root "watchdog.log") -Tail 20 -ErrorAction SilentlyContinue
    Get-Content (Join-Path $root "server.out.log") -Tail 20 -ErrorAction SilentlyContinue
    Get-Content (Join-Path $root "server.err.log") -Tail 20 -ErrorAction SilentlyContinue
    exit 0
}

if ($WatchForeground) {
    Stop-All
    $py = Get-Python
    $wdArgs = @()
    if ($Dev) { $wdArgs += "--dev" }
    if ($Hot) { $wdArgs += "--hot" }
    "watchdog FOREGROUND (Ctrl+C to stop)..."
    & $py scripts\watchdog.py @wdArgs
    exit $LASTEXITCODE
}

if ($Watch) {
    Stop-All
    # Per AGENTS.md, -Watch supervises the full dev stack (Flask + Vite HMR):
    # the watchdog starts both, restarts them if they die, and this call
    # returns control immediately once Flask is healthy.
    $Dev = $true
    Start-Watchdog
    "starting watchdog (background, self-healing)..."
    $deadline = (Get-Date).AddSeconds(60)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 1000
        if (Test-Healthy) {
            "server UP on 127.0.0.1:$port (watchdog active)"
            "NOTE: the app runs as a detached background service and will"
            "      restart itself. Closing this terminal does NOT stop it."
            "      Stop everything with:  .\scripts\dev.ps1 -Stop"
            exit 0
        }
    }
    Write-Error "server did not become healthy in 60s; see watchdog.log"
    exit 1
}

if ($AutoStart) {
    $task = "AUREON Watchdog"
    $bootstrap = Join-Path $root "scripts\watchdog-onlogon.cmd"
    if (-not (Test-Path $bootstrap)) {
        Write-Error "bootstrap missing: $bootstrap"; exit 1
    }
    $registered = $false
    try {
        $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$bootstrap`""
        $trigger = New-ScheduledTaskTrigger -AtLogOn
        $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 0) -StartWhenAvailable
        Register-ScheduledTask -TaskName $task -Action $action -Trigger $trigger -Settings $settings -Force -ErrorAction Stop | Out-Null
        $registered = $true
    } catch {
        schtasks /Create /TN $task /TR "`"$bootstrap`"" /SC ONLOGON /RL LIMITED /F 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { $registered = $true }
    }
    if ($registered) {
        "registered scheduled task '$task' (starts AUREON at logon)"
        exit 0
    }
    Write-Error "could not register '$task'. Run this once as Administrator, or start AUREON manually (AUREON.bat)."
    exit 1
}

if ($NoAutoStart) {
    try {
        Unregister-ScheduledTask -TaskName "AUREON Watchdog" -Confirm:$false -ErrorAction Stop
        "removed scheduled task 'AUREON Watchdog'"
        exit 0
    } catch {
        schtasks /Delete /TN "AUREON Watchdog" /F 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { "removed scheduled task 'AUREON Watchdog'"; exit 0 }
    }
    Write-Error "could not remove the scheduled task. Run as Administrator if needed."
    exit 1
}

if ($Dev) {
    Stop-All
    "starting dev mode (Flask :$port + Vite HMR :5173)..."

    Start-Server

    $deadline = (Get-Date).AddSeconds(30)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 500
        if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) { break }
    }
    if (-not (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)) {
        Write-Error "Flask failed to start on port $port"; exit 1
    }
    "Flask UP on :$port"

    Start-Vite

    $deadline2 = (Get-Date).AddSeconds(20)
    while ((Get-Date) -lt $deadline2) {
        Start-Sleep -Milliseconds 500
        if (Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue) { break }
    }
    if (-not (Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue)) {
        Write-Error "Vite dev server failed to start on port 5173"; exit 1
    }
    "Vite HMR UP on :5173"
    "open http://localhost:5173 - changes in src/ appear instantly"
    exit 0
}

if ($Restart) {
    Stop-All
    "cleaned stale processes"
    $Start = $true
}

if (-not $Start) {
    Write-Host "no switch given; use -Status / -Start / -Restart / -Stop / -Watch / -WatchForeground / -Dev / -AutoStart / -NoAutoStart"
    exit 1
}

# Always clean orphans before starting to prevent stale processes
Stop-All

if (-not (Test-PortFree)) {
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

Start-Server

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
