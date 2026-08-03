"""Unit tests for Layer 6 — MIDI Exporter."""

from mido import MidiFile, bpm2tempo

from engine.exporter import export_midi
from engine.models import Note, Track


def _sample_track():
    notes = [
        Note(pitch=45, start_beat=0.0, duration_beat=1.0, velocity=100),
        Note(pitch=48, start_beat=1.0, duration_beat=0.5, velocity=90),
        Note(pitch=52, start_beat=1.5, duration_beat=2.5, velocity=95),
    ]
    return Track(
        role="bass",
        track_name="Bass - Wobble Style (Dubstep)",
        suggested_preset="sub_bass / wobble_synth",
        notes=notes,
    )


def test_export_is_type_one_multitrack(tmp_path):
    out = tmp_path / "test.mid"
    export_midi([_sample_track()], 140, str(out))
    mid = MidiFile(str(out))
    assert mid.type == 1
    assert len(mid.tracks) == 2


def test_tempo_and_time_signature_embedded(tmp_path):
    out = tmp_path / "test.mid"
    export_midi([_sample_track()], 140, str(out))
    mid = MidiFile(str(out))
    meta = mid.tracks[0]
    tempos = [m for m in meta if m.type == "set_tempo"]
    sigs = [m for m in meta if m.type == "time_signature"]
    assert tempos and tempos[0].tempo == bpm2tempo(140)
    assert sigs and sigs[0].numerator == 4 and sigs[0].denominator == 4


def test_note_on_matches_notes_and_track_name(tmp_path):
    out = tmp_path / "test.mid"
    export_midi([_sample_track()], 140, str(out))
    mid = MidiFile(str(out))
    role_track = mid.tracks[1]
    names = [m for m in role_track if m.type == "track_name"]
    assert names[0].name == "Bass - Wobble Style (Dubstep)"
    note_ons = [m for m in role_track if m.type == "note_on"]
    assert len(note_ons) == 3
    assert {m.note for m in note_ons} == {45, 48, 52}
    note_offs = [m for m in role_track if m.type == "note_off"]
    assert len(note_offs) == 3


def test_velocity_clamped_to_valid_range(tmp_path):
    notes = [
        Note(pitch=40, start_beat=0.0, duration_beat=1.0, velocity=300),
        Note(pitch=41, start_beat=1.0, duration_beat=1.0, velocity=0),
    ]
    track = Track(role="bass", track_name="t", suggested_preset="p", notes=notes)
    out = tmp_path / "clamp.mid"
    export_midi([track], 120, str(out))
    mid = MidiFile(str(out))
    velocities = [m.velocity for m in mid.tracks[1] if m.type == "note_on"]
    assert all(1 <= v <= 127 for v in velocities)


def test_file_roundtrips_through_mido(tmp_path):
    out = tmp_path / "roundtrip.mid"
    export_midi([_sample_track()], 174, str(out))
    MidiFile(str(out))  # must parse without raising
