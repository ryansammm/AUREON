"""Regression tests for tools/render_audio.py"""

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))

from engine.config_loader import load_genre_config
from engine.pipeline import generate_track
from render_audio import render_to_wav


def test_render_produces_audible_wav(tmp_path):
    config = load_genre_config("dubstep")
    track, _, _ = generate_track(
        config, "bass", "a", "minor", bars=4, complexity="simple",
        seed=1, humanize=False, bpm=140,
    )
    mid_path = tmp_path / "test.mid"
    from engine.exporter import export_midi

    export_midi([track], 140, str(mid_path))
    wav_path = tmp_path / "test.wav"
    render_to_wav(mid_path, wav_path, gain=0.5)

    import wave

    with wave.open(str(wav_path)) as w:
        assert w.getnchannels() in (1, 2)
        assert w.getframerate() == 44100
        frames = w.readframes(w.getnframes())
    arr = np.frombuffer(frames, dtype="<i2")
    assert arr.size > 44100, "audio should be longer than one second"
    assert abs(arr).max() > 1000, "audio should not be silent"


def test_render_handles_zero_delta_note_offs(tmp_path):
    import wave

    import mido

    mid = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    track.append(mido.MetaMessage("set_tempo", tempo=500000))
    track.append(mido.Message("note_on", note=60, velocity=100, time=0))
    track.append(mido.Message("note_off", note=60, velocity=0, time=480))
    mid.tracks.append(track)
    mid_path = tmp_path / "zero_delta.mid"
    mid.save(str(mid_path))

    wav_path = tmp_path / "zero_delta.wav"
    render_to_wav(mid_path, wav_path, gain=0.5)
    with wave.open(str(wav_path)) as w:
        arr = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
    assert arr.size > 44100
    assert abs(arr).max() > 1000
