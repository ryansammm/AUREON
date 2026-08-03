"""Unit tests for Layer 1 — Harmonic Engine."""

import pytest

from engine.config_loader import load_genre_config
from engine.harmony import HarmonicEngine
from engine.music_utils import get_scale_pitch_classes

CONFIG = load_genre_config("dubstep")


def test_generates_expected_bar_count():
    engine = HarmonicEngine(CONFIG, seed=42)
    prog = engine.generate_progression("a", "minor", 8)
    assert len(prog) == 8
    assert [c.bar for c in prog] == list(range(8))


def test_all_chords_valid_in_scale():
    engine = HarmonicEngine(CONFIG, seed=42)
    prog = engine.generate_progression("a", "minor", 8)
    scale_pcs = get_scale_pitch_classes("a", "minor", "natural_minor")
    for chord in prog:
        assert set(chord.pitch_classes) <= scale_pcs


def test_degrees_come_from_chord_pool():
    pool = {item["degree"] for item in CONFIG["chord_pool"]}
    engine = HarmonicEngine(CONFIG, seed=1)
    prog = engine.generate_progression("a", "minor", 16)
    for chord in prog:
        assert chord.degree in pool


def test_transitions_follow_matrix():
    engine = HarmonicEngine(CONFIG, seed=42)
    prog = engine.generate_progression("a", "minor", 8)
    matrix = CONFIG["transition_matrix"]
    for prev, nxt in zip(prog, prog[1:]):
        allowed = set(matrix.get(prev.degree, {}))
        assert nxt.degree in allowed


def test_seeded_progression_deterministic():
    a = HarmonicEngine(CONFIG, seed=7).generate_progression("a", "minor", 8)
    b = HarmonicEngine(CONFIG, seed=7).generate_progression("a", "minor", 8)
    assert [c.degree for c in a] == [c.degree for c in b]


def test_zero_bars_rejected():
    with pytest.raises(ValueError):
        HarmonicEngine(CONFIG, seed=1).generate_progression("a", "minor", 0)
