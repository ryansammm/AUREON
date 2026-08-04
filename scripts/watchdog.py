"""AUREON Watchdog - process supervisor that keeps the app alive.

The Flask server behind AUREON can die, hang, or leak orphaned processes
(fluidsynth, stale python servers, stray Vite). Windows also makes
"background" servers tricky: a server started from a console window keeps
that window open until it exits, and a stale server keeps serving OLD code
after you edit source. This watchdog fixes that permanently:

  * health-checks the server every --interval seconds
    (TCP port probe + HTTP GET /api/config)
  * auto-restarts after --restart-after consecutive failures
  * exponential backoff if the server is crash-looping
  * cleans orphaned fluidsynth / stale app.py / stray Vite on restart
  * rotates server + watchdog logs so they never grow unbounded
  * optional --hot mode: restarts when backend/frontend sources change
  * --once mode: single check-and-fix, for Windows Scheduled Task use
  * writes server.status.json so scripts can report real state
  * PID lockfile prevents two watchdogs fighting

Only the Python stdlib plus built-in Windows tooling (PowerShell/WMI and
taskkill) is used, so it runs on a fresh checkout with no extra installs.

Run it in the background:   scripts\\dev.ps1 -Watch
Run it in the foreground:   scripts\\dev.ps1 -WatchForeground  (Ctrl+C stops)
Run it directly:            python scripts\\watchdog.py [--hot] [--dev]
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
if not PYTHON.is_file():
    PYTHON = Path(sys.executable)

DEFAULT_PORT = 8000
VITE_PORT = 5173

STATUS_FILE = ROOT / "server.status.json"
WATCHDOG_LOG = ROOT / "watchdog.log"
WATCHDOG_LOCK = ROOT / "watchdog.lock"

# 0x08000000 = CREATE_NO_WINDOW (no console flash for our sub-commands)
_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
# Detach a spawned server from any console entirely (Windows).
_DETACHED = 0
if os.name == "nt":
    _DETACHED = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS

_state = {"state": "starting", "started": time.time(), "checks": 0,
          "restarts": 0, "hot": 0}
_stop = False
_spawned_server_pid: int | None = None


# ── logging / status ───────────────────────────────────────────────────

def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with open(WATCHDOG_LOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def write_status(detail: str, **extra) -> None:
    payload = {
        "state": _state["state"],
        "detail": detail,
        "since": round(_state["started"], 1),
        "checks": _state["checks"],
        "restarts": _state["restarts"],
        "hot_reloads": _state["hot"],
        "pid": os.getpid(),
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        **extra,
    }
    try:
        STATUS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError:
        pass


def set_state(state: str, detail: str) -> None:
    _state["state"] = state
    write_status(detail)


# ── process helpers (stdlib + PowerShell/WMI, no external deps) ────────

def _ps(script: str, env: dict | None = None, timeout: int = 30) -> subprocess.CompletedProcess:
    full = dict(os.environ)
    if env:
        full.update(env)
    return subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-Command", script],
        capture_output=True, text=True, timeout=timeout,
        creationflags=_NO_WINDOW, env=full,
    )


def find_pids(pattern: str) -> list[int]:
    """PIDs whose command line matches the regex (passed safely via env)."""
    script = (
        "Get-CimInstance Win32_Process | Where-Object { "
        "$_.CommandLine -and ($_.CommandLine -match $env:WPAT) } | "
        "ForEach-Object { $_.ProcessId }"
    )
    r = _ps(script, env={"WPAT": pattern})
    return [int(x) for x in r.stdout.splitlines() if x.strip().isdigit()]


def pid_exists(pid: int) -> bool:
    r = _ps(f"(Get-Process -Id {pid} -ErrorAction SilentlyContinue) -ne $null")
    return r.stdout.strip() == "True"


def kill_pid(pid: int) -> None:
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                   capture_output=True, timeout=15)


def server_pids() -> list[int]:
    return find_pids(r"web[\\/]app\.py")


def vite_pids() -> list[int]:
    return find_pids(r"[vV]ite")


def fluidsynth_pids() -> list[int]:
    r = _ps("Get-Process -Name 'fluidsynth*' -ErrorAction SilentlyContinue | "
            "ForEach-Object { $_.Id }")
    return [int(x) for x in r.stdout.splitlines() if x.strip().isdigit()]


def clean_orphans(kill_vite: bool) -> None:
    killed: list[str] = []
    for pid in fluidsynth_pids():
        kill_pid(pid)
        killed.append(f"fluidsynth:{pid}")
    for pid in server_pids():
        kill_pid(pid)
        killed.append(f"app:{pid}")
    if kill_vite:
        for pid in vite_pids():
            kill_pid(pid)
            killed.append(f"vite:{pid}")
    if killed:
        log("cleaned orphans: " + ", ".join(killed))


def cleanup_on_exit() -> None:
    """Kill server, fluidsynth, vite — everything we started or that is orphaned."""
    killed: list[str] = []
    for pid in fluidsynth_pids():
        kill_pid(pid)
        killed.append(f"fluidsynth:{pid}")
    for pid in server_pids():
        kill_pid(pid)
        killed.append(f"app:{pid}")
    for pid in vite_pids():
        kill_pid(pid)
        killed.append(f"vite:{pid}")
    if killed:
        log("cleanup on exit: " + ", ".join(killed))
    release_lock()
    set_state("stopped", "watchdog exiting")


# ── spawning ───────────────────────────────────────────────────────────

def spawn(cmd: list[str], cwd: Path, out_log: Path, err_log: Path, env: dict | None = None) -> None:
    out_f = open(out_log, "ab", buffering=0)
    err_f = open(err_log, "ab", buffering=0)
    full = dict(os.environ)
    if env:
        full.update(env)
    try:
        subprocess.Popen(
            cmd, cwd=str(cwd), stdin=subprocess.DEVNULL,
            stdout=out_f, stderr=err_f, close_fds=True,
            creationflags=_DETACHED, env=full,
        )
    finally:
        out_f.close()
        err_f.close()


def start_server(port: int) -> None:
    env = {"AUREON_PORT": str(port)}
    spawn([str(PYTHON), "web/app.py"], ROOT,
          ROOT / "server.out.log", ROOT / "server.err.log", env=env)


def start_vite() -> None:
    spawn(["npm", "run", "dev"], ROOT / "web" / "frontend",
          ROOT / "vite.out.log", ROOT / "vite.err.log")


# ── health / rotation / sources ────────────────────────────────────────

def port_open(port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except OSError:
        return False


def http_ok(port: int, timeout: float = 3.0) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/config", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def healthy(port: int) -> tuple[bool, str]:
    if port_open(port) and http_ok(port):
        return True, "ok"
    if port_open(port):
        return False, "port-up-http-down"
    return False, "port-down"


def wait_healthy(port: int, timeout: float, ctx: str) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        ok, _ = healthy(port)
        if ok:
            return True
        time.sleep(1)
    return False


def rotate(path: Path, keep: int, max_bytes: int) -> None:
    if not path.exists():
        return
    try:
        size = path.stat().st_size
    except OSError:
        return
    if size <= max_bytes:
        return
    for i in range(keep - 1, 0, -1):
        src = Path(f"{path}.{i}")
        dst = Path(f"{path}.{i + 1}")
        try:
            if dst.exists():
                dst.unlink()
            if src.exists():
                src.rename(dst)
        except OSError:
            pass
    try:
        path.rename(Path(f"{path}.1"))
        log(f"rotated {path.name}")
    except OSError:
        pass


def source_sig() -> dict:
    sig: dict[str, int] = {}
    suffixes = {".py", ".js", ".jsx", ".ts", ".tsx", ".css", ".html", ".json"}
    skip = {"node_modules", "dist", "__pycache__", ".venv", ".git"}
    for base in (ROOT / "web", ROOT / "engine", ROOT / "tools"):
        if not base.exists():
            continue
        for f in base.rglob("*"):
            if f.suffix not in suffixes or f.is_symlink():
                continue
            if skip & set(f.parts):
                continue
            try:
                sig[str(f)] = f.stat().st_mtime_ns
            except OSError:
                pass
    return sig


# ── restart ────────────────────────────────────────────────────────────

def restart(port: int, dev: bool, reason: str, start_timeout: float) -> None:
    set_state("restarting", reason)
    log(f"restarting server ({reason})")
    clean_orphans(dev)
    start_server(port)
    if dev and not (port_open(VITE_PORT) or vite_pids()):
        start_vite()
    if wait_healthy(port, start_timeout, reason):
        _state["restarts"] += 1
        set_state("healthy", f"restarted ({reason})")
        log(f"server healthy after restart ({reason})")
    else:
        set_state("unhealthy", f"failed to recover ({reason})")
        log(f"server FAILED to recover ({reason})")


# ── lock / signals ─────────────────────────────────────────────────────

def acquire_lock() -> bool:
    if WATCHDOG_LOCK.exists():
        try:
            pid = int(WATCHDOG_LOCK.read_text().strip())
            if pid_exists(pid):
                log(f"another watchdog is already running (pid {pid}) - exiting")
                return False
        except Exception:
            pass
    WATCHDOG_LOCK.write_text(str(os.getpid()))
    return True


def release_lock() -> None:
    try:
        if int(WATCHDOG_LOCK.read_text().strip()) == os.getpid():
            WATCHDOG_LOCK.unlink()
    except Exception:
        pass


def _on_signal(signum, frame):  # noqa: ANN001
    global _stop
    log(f"received signal {signum} - shutting down")
    _stop = True


signal.signal(signal.SIGINT, _on_signal)
signal.signal(signal.SIGTERM, _on_signal)


# ── run modes ──────────────────────────────────────────────────────────

def run_daemon(args) -> None:
    failures = 0
    restart_times: list[float] = []
    last_sig = source_sig() if args.hot else None
    last_rotate = 0.0

    ok, detail = healthy(args.port)
    if ok:
        set_state("healthy", "already running")
        log("server already healthy")
    else:
        set_state("starting", detail)
        log(f"server not healthy ({detail}) - starting")
        clean_orphans(args.dev)
        start_server(args.port)
        if args.dev:
            start_vite()
        if wait_healthy(args.port, args.start_timeout, "initial start"):
            set_state("healthy", "started")
            log("server healthy after initial start")
        else:
            set_state("unhealthy", "initial start failed")
            log("server FAILED to start on first attempt; continuing to supervise")

    while not _stop:
        time.sleep(args.interval)

        now = time.time()
        if now - last_rotate >= 300:
            rotate(ROOT / "server.out.log", args.keep_logs, args.log_size)
            rotate(ROOT / "server.err.log", args.keep_logs, args.log_size)
            rotate(WATCHDOG_LOG, args.keep_logs, args.log_size)
            last_rotate = now

        ok, detail = healthy(args.port)
        _state["checks"] += 1
        if ok:
            failures = 0
            restart_times = [t for t in restart_times if now - t < 120]
            write_status("ok")
        else:
            failures += 1
            if failures >= args.restart_after:
                restart_times = [t for t in restart_times if now - t < 120]
                if len(restart_times) >= args.max_restarts:
                    set_state("backoff", f"{len(restart_times)} restarts in 120s - backing off")
                    log("crash loop detected - backing off for a while")
                    time.sleep(args.interval * 3)
                    failures = 0
                    continue
                restart_times.append(now)
                failures = 0
                restart(args.port, args.dev, detail, args.start_timeout)

        if args.hot and last_sig is not None:
            sig = source_sig()
            if sig != last_sig:
                log("source change detected - restarting")
                time.sleep(1.5)  # debounce burst edits
                restart(args.port, args.dev, "hot-reload", args.start_timeout)
                _state["hot"] += 1
                last_sig = source_sig()

        if args.dev:
            if not port_open(VITE_PORT) and not vite_pids():
                log("Vite went down - restarting")
                start_vite()

    set_state("stopped", "watchdog exiting")


def run_once(args) -> int:
    ok, detail = healthy(args.port)
    if ok:
        set_state("ok", "healthy (once)")
        log("health ok (once)")
        return 0
    set_state("starting", detail)
    clean_orphans(args.dev)
    start_server(args.port)
    if args.dev:
        start_vite()
    if wait_healthy(args.port, args.start_timeout, "once"):
        set_state("ok", "started (once)")
        log("server started (once)")
        return 0
    set_state("unhealthy", "start failed (once)")
    log("server start FAILED (once)")
    return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="AUREON server watchdog")
    parser.add_argument("--interval", type=float, default=10.0, help="health-check interval in seconds")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="server port to supervise")
    parser.add_argument("--restart-after", type=int, default=3, help="consecutive failures before restart")
    parser.add_argument("--start-timeout", type=float, default=60.0, help="seconds to wait for health")
    parser.add_argument("--max-restarts", type=int, default=4, help="restarts allowed in a 120s window")
    parser.add_argument("--keep-logs", type=int, default=3, help="rotated log backups to keep")
    parser.add_argument("--log-size", type=int, default=1_000_000, help="rotate logs above this byte size")
    parser.add_argument("--dev", action="store_true", help="also supervise the Vite dev server")
    parser.add_argument("--hot", action="store_true", help="restart when source files change")
    parser.add_argument("--once", action="store_true", help="check once, fix if needed, and exit")
    args = parser.parse_args()

    args.interval = max(1.0, args.interval)
    args.restart_after = max(1, args.restart_after)

    if not acquire_lock():
        sys.exit(0)
    try:
        set_state("starting", f"watchdog up (interval={args.interval}s, port={args.port})")
        log(f"watchdog starting (interval={args.interval}s, port={args.port}, "
            f"dev={args.dev}, hot={args.hot})")
        code = run_once(args) if args.once else None
        if args.once:
            release_lock()
            sys.exit(code or 0)
        run_daemon(args)
    finally:
        cleanup_on_exit()


if __name__ == "__main__":
    main()
