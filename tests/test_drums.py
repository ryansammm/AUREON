"""Tests for the drum layer (channel 10, per-section step patterns)."""

from mido import MidiFile, Message

from engine.config_loader import load_genre_config
from engine.drums import DrumEngine
from engine.exporter import export_midi
from engine.pipeline import generate_composition, generate_track

DRUM_PITCHES = {36, 38, 39, 42, 46, 49}


def test_drum_track_uses_channel_9_and_percussion_pitches(tmp_path):
    config = load_genre_config("dubstep")
    track, _, _ = generate_track(config, "drum", "a", "minor", bars=None, seed=3)
    assert track.role == "drum"
    assert track.channel == 9
    assert len(track.notes) > 0
    for note in track.notes:
        assert note.pitch in DRUM_PITCHES

    out = tmp_path / "drum.mid"
    export_midi([track], config["default_bpm"], str(out))
    mid = MidiFile(str(out))
    drum_track = mid.tracks[1]
    channels = {msg.channel for msg in drum_track if isinstance(msg, Message)}
    assert channels == {9}


def test_drum_pattern_follows_sections():
    config = load_genre_config("house")
    plan = None
    track, _, plan = generate_track(config, "drum", "f", "major", bars=None, seed=1)
    section_names = {sb.name for sb in plan}
    for section in section_names:
        pattern = config["drum_patterns"]["patterns"].get(section, {})
        for voice in pattern:
            assert len(pattern[voice]) == 16
    assert "drop" in section_names


def test_composition_includes_drum_when_requested():
    config = load_genre_config("dubstep")
    tracks, _, _ = generate_composition(
        config, ["bass", "drum", "lead"], "a", "minor", bars=None, seed=9
    )
    roles = {t.role for t in tracks}
    assert roles == {"bass", "lead", "drum"}
    drum = next(t for t in tracks if t.role == "drum")
    assert drum.channel == 9


def test_drum_pattern_validation():
    bad = {
        "genre": "x",
        "default_bpm": 120,
        "scale_pool": ["major"],
        "chord_pool": [{"degree": "I", "weight": 1.0}],
        "transition_matrix": {"I": {"I": 1.0}},
        "role_ranges": {"bass": {"min": 28, "max": 55, "preferred": 40}},
        "bass_patterns": {"simple": [[16]]},
        "instrument_intent": {"bass": {"label": "B", "preset": "P"}},
        "drum_patterns": {"patterns": {"drop": {"kick": "x"}}},
    }
    from engine.config_loader import validate_genre_config

    with pytest.raises(ValueError):
        validate_genre_config(bad)


import pytest  # noqa: E402  (import after use for clarity)
