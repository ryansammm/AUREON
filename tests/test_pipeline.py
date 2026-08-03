"""Integration tests — full Phase 1/2 pipeline end to end."""

import pytest
from mido import MidiFile

from engine.config_loader import load_genre_config
from engine.exporter import export_midi
from engine.music_utils import get_scale_pitch_classes
from engine.pipeline import generate_track, pick_scale_from_pool

GENRES = ["dubstep", "house"]


@pytest.mark.parametrize("genre", GENRES)
def test_end_to_end_generates_valid_midi(tmp_path, genre):
    config = load_genre_config(genre)
    track, progression, plan = generate_track(
        config, "bass", config["default_key"], config["default_mode"],
        bars=None, complexity="medium", seed=123,
    )
    assert len(progression) == len(plan) > 0
    assert len(track.notes) > 0

    out = tmp_path / f"{genre}.mid"
    export_midi([track], config["default_bpm"], str(out))
    mid = MidiFile(str(out))
    assert mid.type == 1
    assert len(mid.tracks) == 2


@pytest.mark.parametrize("genre", GENRES)
def test_pipeline_notes_respect_scale_and_range(genre):
    config = dict(load_genre_config(genre))
    config.pop("modulations", None)  # modulation intentionally leaves the key
    scale_name = config["scale_pool"][0]
    track, _, _ = generate_track(
        config, "bass", config["default_key"], config["default_mode"],
        bars=None, complexity="medium", seed=7, scale_name=scale_name,
    )
    scale_pcs = get_scale_pitch_classes(
        config["default_key"], config["default_mode"], scale_name
    )
    rng = config["role_ranges"]["bass"]
    for note in track.notes:
        assert rng["min"] <= note.pitch <= rng["max"]
        assert note.pitch % 12 in scale_pcs


def test_unknown_role_rejected():
    config = load_genre_config("dubstep")
    with pytest.raises(ValueError):
        generate_track(config, "theremin", "a", "minor", bars=4, seed=1)


def test_scale_pick_uses_config_pool():
    config = load_genre_config("dubstep")
    scale = pick_scale_from_pool(config, "minor", seed=0)
    assert scale in config["scale_pool"]


def test_humanization_changes_timing_and_velocity_but_keeps_downbeats():
    config = load_genre_config("dubstep")
    raw, _, _ = generate_track(config, "bass", "a", "minor", bars=8, seed=5, humanize=False)
    human, _, _ = generate_track(config, "bass", "a", "minor", bars=8, seed=5, humanize=True)

    assert len(human.notes) == len(raw.notes)
    assert [(n.pitch, n.velocity) for n in human.notes] != [
        (n.pitch, n.velocity) for n in raw.notes
    ]
    assert [(n.start_beat, n.velocity) for n in human.notes] != [
        (n.start_beat, n.velocity) for n in raw.notes
    ]

    raw_by_beat = {(round(n.start_beat, 4)): n for n in raw.notes}
    for note in human.notes:
        if abs(note.start_beat % 4.0) < 1e-9:
            assert raw_by_beat[round(note.start_beat, 4)].start_beat == note.start_beat
        assert 1 <= note.velocity <= 127


def test_same_pipeline_accepts_both_genres_without_code_change():
    """Phase 2 DoD: two genre configs run through the SAME pipeline."""
    for genre in GENRES:
        config = load_genre_config(genre)
        track, _, _ = generate_track(
            config, "bass", config["default_key"], config["default_mode"],
            bars=None, seed=42,
        )
        assert track.notes
