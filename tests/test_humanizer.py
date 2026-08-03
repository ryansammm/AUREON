"""Unit tests for Layer 5 — Humanization Engine."""

import pytest

from engine.config_loader import load_genre_config
from engine.humanizer import Humanizer
from engine.models import Note

CONFIG = load_genre_config("dubstep")
BPM = CONFIG["default_bpm"]
MAX_OFFSET = CONFIG["humanize"]["max_timing_ms"] * BPM / 60000.0


def _one_bar_notes():
    """8 eighth-notes in a single bar; index 0 is the only downbeat."""
    return [
        Note(pitch=40 + i, start_beat=i * 0.5, duration_beat=0.5, velocity=90)
        for i in range(8)
    ]


def test_downbeats_stay_on_grid():
    notes = _one_bar_notes()
    Humanizer(CONFIG, seed=1).humanize(notes, BPM)
    assert notes[0].start_beat == 0.0


def test_non_downbeats_shifted():
    notes = _one_bar_notes()
    original = [n.start_beat for n in notes]
    Humanizer(CONFIG, seed=1).humanize(notes, BPM)
    shifted = [
        n.start_beat != orig for n, orig in zip(notes, original)
    ]
    assert any(shifted[1:])  # at least one non-downbeat moved


def test_timing_offset_within_bound():
    notes = _one_bar_notes()
    original = [n.start_beat for n in notes]
    Humanizer(CONFIG, seed=3).humanize(notes, BPM)
    for n, orig in zip(notes, original):
        assert abs(n.start_beat - orig) <= MAX_OFFSET + 1e-9
        assert n.start_beat >= 0.0


def test_velocity_humanized_within_range():
    notes = _one_bar_notes()
    original = [n.velocity for n in notes]
    Humanizer(CONFIG, seed=5).humanize(notes, BPM)
    for n, orig in zip(notes, original):
        assert 1 <= n.velocity <= 127
    assert any(n.velocity != orig for n, orig in zip(notes, original))


def test_seeded_humanization_deterministic():
    a = _one_bar_notes()
    b = _one_bar_notes()
    Humanizer(CONFIG, seed=42).humanize(a, BPM)
    Humanizer(CONFIG, seed=42).humanize(b, BPM)
    assert [(n.start_beat, n.velocity) for n in a] == [
        (n.start_beat, n.velocity) for n in b
    ]


def test_higher_bpm_same_ms_offset_larger_beat_shift():
    notes_a = _one_bar_notes()
    notes_b = _one_bar_notes()
    Humanizer(CONFIG, seed=1).humanize(notes_a, 120)
    Humanizer(CONFIG, seed=1).humanize(notes_b, 200)
    shifts_a = max(
        abs(n.start_beat - o.start_beat) for n, o in zip(notes_a, _one_bar_notes())
    )
    shifts_b = max(
        abs(n.start_beat - o.start_beat) for n, o in zip(notes_b, _one_bar_notes())
    )
    assert shifts_b > shifts_a


def test_swing_delays_offbeats_but_keeps_even_steps():
    cfg = dict(CONFIG)
    cfg["swing"] = {"resolution": 8, "amount": 0.3}
    cfg["humanize"] = {"max_timing_ms": 0, "velocity_jitter": 0}
    notes = _one_bar_notes()  # eighth-notes: 0,0.5,1.0,...3.5
    Humanizer(cfg, seed=1).humanize(notes, BPM)
    actual = [n.start_beat for n in notes]
    for i in range(1, 8, 2):
        assert actual[i] == pytest.approx(i * 0.5 + 0.3 * 0.5, abs=0.001)
    for i in range(0, 8, 2):
        assert actual[i] == pytest.approx(i * 0.5, abs=1e-9)  # downbeat/on-beat locked


def test_swing_skips_pad_and_chord_roles():
    cfg = dict(CONFIG)
    cfg["swing"] = {"resolution": 8, "amount": 0.3}
    cfg["humanize"] = {"max_timing_ms": 0, "velocity_jitter": 0}
    notes = [
        Note(pitch=60, start_beat=0.5, duration_beat=1.0, velocity=80, role="pad"),
        Note(pitch=40, start_beat=0.5, duration_beat=0.5, velocity=90, role="bass"),
    ]
    Humanizer(cfg, seed=1).humanize(notes, BPM)
    assert notes[0].start_beat == pytest.approx(0.5)  # pad untouched by swing
    assert notes[1].start_beat == pytest.approx(0.5 + 0.3 * 0.5)  # bass offbeat swung
