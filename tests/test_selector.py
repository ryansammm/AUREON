"""Unit tests for Layer 4 — Candidate Generator + Selector."""

import pytest

from engine.config_loader import load_genre_config
from engine.models import Note, Track
from engine.selector import CandidateGenerator, Selector

CONFIG = load_genre_config("dubstep")


def _track_with_pattern(pattern, bars=4):
    """Build a track whose bars repeat ``pattern`` (pitch, beat, dur)."""
    notes = []
    for bar in range(bars):
        for pitch, onset, dur in pattern:
            notes.append(
                Note(pitch=pitch, start_beat=bar * 4.0 + onset, duration_beat=dur, velocity=90)
            )
    return Track(role="bass", track_name="t", suggested_preset="p", notes=notes)


def test_score_is_deterministic():
    selector = Selector(CONFIG)
    track = _track_with_pattern([(36, 0.0, 1.0), (43, 2.0, 2.0)])
    assert selector.score_track(track) == selector.score_track(track)


def test_repetition_penalized():
    selector = Selector(CONFIG)
    repetitive = _track_with_pattern([(36, 0.0, 1.0)], bars=8)
    varied = Track(
        role="bass", track_name="t", suggested_preset="p",
        notes=[
            Note(pitch=36 + (bar % 7), start_beat=bar * 4.0, duration_beat=1.0, velocity=90)
            for bar in range(8)
        ],
    )
    score_rep, det_rep = selector.score_track(repetitive)
    score_var, det_var = selector.score_track(varied)
    assert det_rep["repetition"] > det_var["repetition"]
    assert score_rep < score_var


def test_dissonance_penalized():
    selector = Selector(CONFIG)
    # stepwise chromatic motion = many minor seconds (dissonant)
    chromatic = _track_with_pattern([(40 + i, 0.0, 1.0) for i in range(8)])
    # chordal leaps of a fifth = consonant
    fifths = _track_with_pattern(
        [(40 + (i % 2) * 7, 0.0, 1.0) for i in range(8)]
    )
    _, det_chrom = selector.score_track(chromatic)
    _, det_fifth = selector.score_track(fifths)
    assert det_chrom["dissonance"] > det_fifth["dissonance"]


def test_voice_leading_smoothness_penalized():
    selector = Selector(CONFIG)
    wild = _track_with_pattern([(28, 0.0, 1.0), (76, 0.5, 1.0)])
    smooth = _track_with_pattern([(36, 0.0, 1.0), (43, 0.5, 1.0)])
    _, det_wild = selector.score_track(wild)
    _, det_smooth = selector.score_track(smooth)
    assert det_wild["voice_leading"] > det_smooth["voice_leading"]
    assert selector.score_track(wild)[0] < selector.score_track(smooth)[0]


def test_select_returns_top_n():
    selector = Selector(CONFIG)
    tracks = [_track_with_pattern([(40 + i, 0.0, 1.0)], bars=2) for i in range(5)]
    ranked = selector.rank(tracks)
    assert ranked == sorted(tracks, key=selector.score_track, reverse=True)
    assert selector.select(tracks, top_n=3) == ranked[:3]


def test_candidate_generator_produces_distinct_tracks():
    generator = CandidateGenerator(CONFIG, seed=1)
    candidates = generator.generate("bass", "a", "minor", bars=8, count=5, base_seed=7)
    tracks = [c[0][0] for c in candidates]  # single role -> one track each
    assert len(tracks) == 5
    signatures = {
        tuple((n.pitch, round(n.start_beat, 3)) for n in t.notes) for t in tracks
    }
    assert len(signatures) > 1


def test_candidate_generation_and_selection_end_to_end():
    config = load_genre_config("dubstep")
    generator = CandidateGenerator(config, seed=1)
    selector = Selector(config, seed=1)
    candidates = generator.generate("bass", "a", "minor", bars=8, count=4, base_seed=11)
    best = selector.rank([c[0][0] for c in candidates])[0]
    # best candidate must be scored at least as high as every other
    for c in candidates:
        assert selector.score_track(best)[0] >= selector.score_track(c[0][0])[0]


def test_zero_length_track_scores_zero():
    selector = Selector(CONFIG)
    empty = Track(role="bass", track_name="t", suggested_preset="p", notes=[])
    assert selector.score_track(empty)[0] == 0.0


def test_bad_top_n_rejected():
    with pytest.raises(ValueError):
        Selector(CONFIG).select([], top_n=0)


def test_candidate_sort_key_uses_single_track_for_one_role():
    """Regression: c[0] is a list of tracks, score_track needs a Track."""
    config = load_genre_config("dubstep")
    generator = CandidateGenerator(config, seed=1)
    selector = Selector(config, seed=1)
    candidates = generator.generate("bass", "a", "minor", bars=8, count=3, base_seed=3)
    score_key = lambda c: selector.score_track(c[0][0])[0]  # noqa: E731
    ranked = sorted(candidates, key=score_key, reverse=True)
    for i in range(len(ranked) - 1):
        assert score_key(ranked[i]) >= score_key(ranked[i + 1])


def test_score_composition_skips_drums():
    selector = Selector(CONFIG)
    melodic = _track_with_pattern([(36, 0.0, 1.0), (43, 2.0, 1.0)])
    drum = Track(role="drum", track_name="Drums", suggested_preset="kit", notes=[
        Note(pitch=36, start_beat=0.0, duration_beat=0.25, velocity=100),
        Note(pitch=38, start_beat=1.0, duration_beat=0.25, velocity=90),
    ])
    score_with_drum, _ = selector.score_composition([melodic, drum])
    score_only, _ = selector.score_composition([melodic])
    assert score_with_drum == score_only
