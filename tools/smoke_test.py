"""Deterministic end-to-end smoke test against the running dev server.

Never hangs: every socket call has a hard timeout, the SSE stream is bounded
by a watchdog, and a non-zero exit code is returned on any failure.

Usage::

    python tools/smoke_test.py [http://127.0.0.1:8000] [--seed 5]
"""

import json
import socket
import sys
import time
import urllib.request
from urllib.error import URLError

DEFAULT_BASE = "http://127.0.0.1:8000"
NET_TIMEOUT = 30
SSE_WATCHDOG = 180


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    print(f"[smoke] base={base} seed={seed}")
    socket.setdefaulttimeout(NET_TIMEOUT)

    try:
        req = urllib.request.urlopen(f"{base}/", timeout=NET_TIMEOUT)
        if req.status != 200:
            raise AssertionError(f"GET / -> {req.status}")
        print("[smoke] OK  GET / (SPA)")
    except URLError as exc:
        print(f"[smoke] FAIL cannot reach server: {exc}")
        print("        start it with  scripts/dev.ps1 -Start  (or -Restart)")
        return 2

    for path in ("/manifest.webmanifest", "/sw.js", "/icons/icon-192.png"):
        r = urllib.request.urlopen(f"{base}{path}", timeout=NET_TIMEOUT)
        assert r.status == 200, f"{path} -> {r.status}"
        print(f"[smoke] OK  GET {path}")

    payload = {
        "genre": "dubstep",
        "roles": ["bass", "lead"],
        "bars": 4,
        "candidates": 1,
        "stems": True,
        "seed": seed,
    }
    req = urllib.request.Request(
        f"{base}/api/generate/stream",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.monotonic()
    events = 0
    result = None
    body = b""
    try:
        with urllib.request.urlopen(req, timeout=NET_TIMEOUT) as resp:
            while time.monotonic() - started < SSE_WATCHDOG:
                chunk = resp.read(4096)
                if not chunk:
                    break
                body += chunk
        for ln in body.decode("utf-8", "replace").splitlines():
            ln = ln.strip()
            if ln.startswith("event: "):
                events += 1
            elif ln.startswith("data: "):
                obj = json.loads(ln[6:])
                if "result" in obj or "mid" in obj:
                    result = obj
        elapsed = time.monotonic() - started
        assert result, f"no result event in {elapsed:.1f}s (events={events})"
        print(f"[smoke] OK  SSE generate ({elapsed:.1f}s, {events} events)")
    except (URLError, AssertionError) as exc:
        print(f"[smoke] FAIL generate stream: {exc}")
        return 1

    from pathlib import Path

    mid = result.get("mid")
    assert mid, "result missing 'mid'"
    wav_name = Path(mid).with_suffix(".wav").name
    export = urllib.request.urlopen(f"{base}/api/export/{mid}", timeout=NET_TIMEOUT).read()
    assert export[:2] == b"PK", "export is not a zip"
    import io
    import zipfile

    with zipfile.ZipFile(io.BytesIO(export)) as z:
        names = z.namelist()
        for wanted in (
            "README.txt",
            "project.json",
            "MIDI/run_main.mid",
            "MIDI/stem_bass.mid",
            "MIDI/stem_lead.mid",
            "Audio/run_master.wav",
            "Audio/stem_bass.wav",
            "Audio/stem_lead.wav",
        ):
            assert wanted in names, f"zip missing {wanted}"
    print(f"[smoke] OK  export bundle mid={mid} ({len(export):,} bytes, {len(names)} entries)")

    audio = urllib.request.urlopen(f"{base}/play/{wav_name}", timeout=NET_TIMEOUT).read()
    assert len(audio) > 1024, f"master wav too small: {len(audio)} bytes"
    print(f"[smoke] OK  master wav {len(audio):,} bytes")

    print("[smoke] PASS all checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
