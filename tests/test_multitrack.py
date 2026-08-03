"""Tests for Phase 4 — multi-track composition + clash awareness."""

import pytest
from mido import MidiFile

from engine.config_loader import load_genre_config
from engine.exporter import export_midi
from engine.music_utils import get_scale_pitch_classes
from engine.pipeline import generate_composition
from engine.selector import CandidateGenerator, Selector

ROLES = ["bass", "lead", "chord"]


def _composition(seed=42, bars=None, **kwargs):
    config = dict(load_genre_config("dubstep"))
    config.pop("modulations", None)  # scale/voicing invariants assume one key
    tracks, progression, plan = generate_composition(
        config, ROLES, "a", "minor", bars=bars, seed=seed, **kwargs
    )
    return config, tracks, progression, plan


def test_multi_track_has_all_roles():
    config, tracks, _, _ = _composition()
    assert [t.role for t in tracks] == ROLES
    assert all(len(t.notes) > 0 for t in tracks)


def test_all_tracks_share_progression_length():
    _, tracks, progression, plan = _composition()
    for t in tracks:
        max_beat = max(n.start_beat for n in t.notes)
        assert int(max_beat // 4) <= len(progression) - 1
    assert len(progression) == len(plan)


def test_notes_within_role_range_and_scale():
    config, tracks, _, _ = _composition()
    scale_pcs = get_scale_pitch_classes("a", "minor", "natural_minor")
    for track in tracks:
        rng = config["role_ranges"][track.role]
        for note in track.notes:
            assert rng["min"] <= note.pitch <= rng["max"]
            assert note.pitch % 12 in scale_pcs


def test_chord_track_is_sustained_and_multivoice():
    _, tracks, _, _ = _composition()
    chord_track = tracks[2]
    assert chord_track.role == "chord"
    assert all(n.duration_beat >= 3.0 for n in chord_track.notes)
    first_bar_notes = [n for n in chord_track.notes if n.start_beat < 4.0]
    assert len(first_bar_notes) >= 3  # 3-4 voice voicing


def test_chord_voicing_matches_progression():
    _, tracks, progression, _ = _composition()
    chord_track = tracks[2]
    for chord in progression:
        bar_notes = [
            n.pitch % 12 for n in chord_track.notes
            if abs(n.start_beat - chord.bar * 4.0) < 1e-6
        ]
        assert bar_notes
        assert set(bar_notes) <= set(chord.pitch_classes) | {  # octave doublings
            pc for pc in chord.pitch_classes
        }


def test_bass_and_lead_registers_do_not_overlap():
    """Bass (max 55) and lead (min 60) can never sound the same pitch."""
    _, tracks, _, _ = _composition()
    bass = tracks[0]
    lead = tracks[1]
    bass_pitches = {n.pitch for n in bass.notes}
    lead_pitches = {n.pitch for n in lead.notes}
    assert bass_pitches.isdisjoint(lead_pitches)


def test_no_duplicate_same_pitch_same_beat_within_track():
    """No two identical (pitch, onset) events in a single track."""
    _, tracks, _, _ = _composition()
    for track in tracks:
        keys = [(n.pitch, round(n.start_beat, 3)) for n in track.notes]
        assert len(keys) == len(set(keys))


def test_lead_uses_different_rhythm_profile_than_bass():
    _, tracks, _, _ = _composition()
    bass_onsets = {round(n.start_beat % 4, 2) for n in tracks[0].notes}
    lead_onsets = {round(n.start_beat % 4, 2) for n in tracks[1].notes}
    assert lead_onsets != bass_onsets or len(lead_onsets) != len(bass_onsets)


def test_multi_track_export_is_valid_type1(tmp_path):
    _, tracks, _, _ = _composition()
    out = tmp_path / "comp.mid"
    export_midi(tracks, 140, str(out))
    mid = MidiFile(str(out))
    assert mid.type == 1
    assert len(mid.tracks) == 1 + len(ROLES)
    names = [
        m.name
        for track in mid.tracks[1:]
        for m in track
        if m.type == "track_name"
    ]
    assert len(names) == len(ROLES)


def test_candidate_generation_multi_role():
    config = load_genre_config("dubstep")
    generator = CandidateGenerator(config, seed=1)
    candidates = generator.generate(
        "bass", "a", "minor", bars=8, count=3, base_seed=3, roles=ROLES
    )
    assert len(candidates) == 3
    for tracks, _, _, seed in candidates:
        assert [t.role for t in tracks] == ROLES


def test_selector_scores_composition():
    config, tracks, _, _ = _composition()
    selector = Selector(config)
    score, det = selector.score_composition(tracks)
    assert det["score"] == score
    assert score <= 0.0  # scores are penalties, always <= 0


def test_multi_track_export_humanization_keeps_valid():
    config, tracks, _, _ = _composition(seed=9, humanize=True)
    for track in tracks:
        for note in track.notes:
            assert 1 <= note.velocity <= 127
            assert note.start_beat >= 0
            assert note.duration_beat > 0
