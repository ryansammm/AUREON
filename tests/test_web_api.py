"""API-level tests for the render_engine field (task 2)."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import web.app as app  # noqa: E402


class TestRenderEngineField:
    def test_generate_returns_numpy_fallback_without_fluidsynth(self, monkeypatch):
        # Force the soundfont renderer to be unavailable regardless of the
        # host machine, then check the API reports the fallback.
        import sf_render

        monkeypatch.setattr(sf_render, "soundfont_available", lambda: False)

        client = app.app.test_client()
        resp = client.post(
            "/api/generate",
            json={
                "genre": "house",
                "roles": ["bass"],
                "bars": 8,
                "candidates": 1,
                "seed": 1,
            },
        )
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert body["render_engine"] == "numpy_fallback"

    def test_generate_reports_fluidsynth_when_available(self, monkeypatch):
        import sf_render

        monkeypatch.setattr(sf_render, "soundfont_available", lambda: True)
        monkeypatch.setattr(
            sf_render, "render_midi_with_soundfont",
            lambda *a, **k: 16.0,
        )

        client = app.app.test_client()
        resp = client.post(
            "/api/generate",
            json={
                "genre": "house",
                "roles": ["bass"],
                "bars": 8,
                "candidates": 1,
                "seed": 2,
            },
        )
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert body["render_engine"] == "fluidsynth"

    def test_stream_result_includes_render_engine(self):
        import sf_render

        # SSE with 1 candidate is quick; numpy fallback is deterministic.
        client = app.app.test_client()
        resp = client.post(
            "/api/generate/stream",
            json={
                "genre": "techno",
                "roles": ["bass"],
                "bars": 8,
                "candidates": 1,
                "seed": 3,
            },
            buffered=True,
        )
        assert resp.status_code == 200
        data = resp.get_data(as_text=True)
        assert "render_engine" in data
