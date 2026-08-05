# AUREON — agent notes

## Starting the dev server (for AI agents)

Do NOT launch the backend/frontend dev servers with ad-hoc `Start-Process ... -RedirectStandardOutput ...` PowerShell commands. On Windows, `Start-Process` with `-RedirectStandardOutput`/`-RedirectStandardError` forces handle inheritance, which can attach the spawned long-running process (e.g. `npm run dev` / Vite) to the invoking shell's console/pseudoconsole. Since the dev server never exits, the invoking shell session can hang indefinitely waiting for all console handles to close — even though the process is meant to run in the background.

Instead, always use the project's own dev tooling, which is already built to detach correctly and supervise the server:

    .\scripts\dev.ps1 -Watch

This starts the Flask backend and Vite dev server as properly detached background processes with a self-healing watchdog, and returns control immediately. Check status with:

    .\scripts\dev.ps1 -Status

Stop everything with:

    .\scripts\dev.ps1 -Stop

Logs are available via:

    .\scripts\dev.ps1 -Logs

If a command must be run without using dev.ps1 (e.g. a one-off script), avoid PowerShell's `-RedirectStandardOutput`/`-RedirectStandardError` on `Start-Process` for anything long-running. Instead wrap the command in a small `.bat` file that does its own `> logfile.txt 2>&1` redirection via `cmd.exe`, and launch that wrapper with `Start-Process -WindowStyle Hidden` without PowerShell-level redirection parameters, so no handle is bridged back to the calling shell's console.
