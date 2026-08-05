"""Server-concurrency test (task 3): health checks during long generations.

Reproduces the watchdog false-positive: with single-threaded Flask, a long
generation occupies the only worker thread (the handler blocks in
``thread.join``), so ``GET /api/config`` cannot be served and the watchdog
counts a failure. With ``threaded=True`` the health check is served
concurrently with the in-progress generation.
"""

import socket
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import web.app as app  # noqa: E402


def test_run_server_launches_threaded(monkeypatch):
    """The production launch path must use threaded=True so health checks
    stay responsive during long generations."""
    calls = {}

    def fake_run(**kwargs):
        calls.update(kwargs)

    monkeypatch.setattr(app.app, "run", fake_run)
    app.run_server(host="127.0.0.1", port=8123)
    assert calls.get("threaded") is True


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_server(app_obj, threaded: bool):
    from werkzeug.serving import make_server

    port = _free_port()
    server = make_server("127.0.0.1", port, app_obj, threaded=threaded)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    # Wait for the socket to be bound and accepting.
    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return server, thread, port
        except OSError:
            time.sleep(0.05)
    raise RuntimeError("server did not start")


def _http_get(port: int, path: str, timeout: float):
    with urllib.request.urlopen(
        f"http://127.0.0.1:{port}{path}", timeout=timeout
    ) as r:
        return r.status


class TestConcurrentHealthCheck:
    def test_single_threaded_blocks_health_check_during_generation(self):
        server, thread, port = _start_server(app.app, threaded=False)
        try:
            fired = threading.Event()

            def generate():
                fired.set()
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/generate",
                    data=b'{"genre":"dubstep","roles":["bass","lead","chord",'
                         b'"drum"],"bars":60,"candidates":1,"seed":1,'
                         b'"stems":false}',
                    headers={"Content-Type": "application/json"},
                )
                try:
                    urllib.request.urlopen(req, timeout=60)
                except Exception:
                    pass

            t = threading.Thread(target=generate, daemon=True)
            t.start()
            fired.wait(timeout=5)
            time.sleep(0.3)  # let the worker actually start rendering
            # The health check must wait for the generation to finish.
            start = time.time()
            try:
                _http_get(port, "/api/config", timeout=1.5)
                served = True
            except Exception:
                served = False
            elapsed = time.time() - start
            assert not served, "health check served during single-threaded gen"
            assert elapsed >= 1.0
        finally:
            server.shutdown()
            thread.join(timeout=5)

    def test_threaded_serves_health_check_during_generation(self):
        server, thread, port = _start_server(app.app, threaded=True)
        try:
            fired = threading.Event()

            def generate():
                fired.set()
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/generate",
                    data=b'{"genre":"dubstep","roles":["bass","lead","chord",'
                         b'"drum"],"bars":60,"candidates":1,"seed":1,'
                         b'"stems":false}',
                    headers={"Content-Type": "application/json"},
                )
                try:
                    urllib.request.urlopen(req, timeout=60)
                except Exception:
                    pass

            t = threading.Thread(target=generate, daemon=True)
            t.start()
            fired.wait(timeout=5)
            time.sleep(0.3)
            start = time.time()
            status = _http_get(port, "/api/config", timeout=1.5)
            elapsed = time.time() - start
            assert status == 200
            assert elapsed < 1.0, f"health check took {elapsed:.2f}s"
        finally:
            server.shutdown()
            thread.join(timeout=5)
