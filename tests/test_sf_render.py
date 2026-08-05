"""Tests for the SoundFont renderer (tasks: hardcoded paths, fallback)."""

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import sf_render  # noqa: E402


class TestNoHardcodedPaths:
    def test_source_has_no_devtools_or_drive_paths(self):
        src = Path(sf_render.__file__).read_text(encoding="utf-8")
        assert "DevTools" not in src
        assert "D:\\" not in src
        assert "D:\\\\" not in src

    def test_default_locations_are_not_personal(self):
        for p in sf_render._COMMON_BINS + sf_render._COMMON_SF_DIRS:
            text = str(p).lower()
            assert "devtools" not in text
            assert not text.startswith("d:")


class TestFallback:
    def test_render_returns_none_when_binary_missing(self, monkeypatch, tmp_path, caplog):
        monkeypatch.delenv("AUREON_FLUIDSYNTH", raising=False)
        monkeypatch.delenv("AUREON_SOUNDFONT", raising=False)
        monkeypatch.setattr(sf_render, "_COMMON_BINS", [])
        monkeypatch.setattr(sf_render, "_COMMON_SF_DIRS", [])
        monkeypatch.setattr(sf_render.shutil, "which", lambda name: None)

        mid = tmp_path / "in.mid"
        mid.write_bytes(b"dummy")
        out = tmp_path / "out.wav"

        with caplog.at_level(logging.WARNING, logger="sf_render"):
            result = sf_render.render_midi_with_soundfont(mid, out)
        assert result is None
        assert not out.exists()
        assert "FluidSynth binary not found" in caplog.text

    def test_render_returns_none_when_soundfont_missing(self, monkeypatch, tmp_path, caplog):
        monkeypatch.delenv("AUREON_SOUNDFONT", raising=False)
        monkeypatch.setenv("AUREON_FLUIDSYNTH", str(tmp_path / "fluidsynth.exe"))
        (tmp_path / "fluidsynth.exe").write_bytes(b"binary")
        monkeypatch.setattr(sf_render, "_COMMON_BINS", [])
        monkeypatch.setattr(sf_render, "_COMMON_SF_DIRS", [])

        mid = tmp_path / "in.mid"
        mid.write_bytes(b"dummy")
        out = tmp_path / "out.wav"

        with caplog.at_level(logging.WARNING, logger="sf_render"):
            result = sf_render.render_midi_with_soundfont(mid, out)
        assert result is None
        assert not out.exists()
        assert "SoundFont" in caplog.text

    def test_renderer_status_reports_missing_pieces(self, monkeypatch, tmp_path):
        monkeypatch.delenv("AUREON_FLUIDSYNTH", raising=False)
        monkeypatch.delenv("AUREON_SOUNDFONT", raising=False)
        monkeypatch.setattr(sf_render, "_COMMON_BINS", [])
        monkeypatch.setattr(sf_render, "_COMMON_SF_DIRS", [])
        monkeypatch.setattr(sf_render.shutil, "which", lambda name: None)

        status = sf_render.renderer_status()
        assert status["available"] is False
        assert status["binary"] is None
        assert status["soundfont"] is None
