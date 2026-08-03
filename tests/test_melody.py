"""Unit tests for Layer 2 — Melodic/Bassline Engine."""

from engine.config_loader import load_genre_config
from engine.harmony import HarmonicEngine
from engine.melody import MelodicEngine
from engine.music_utils import get_scale_pitch_classes

CONFIG = load_genre_config("dubstep")

BEATS_PER_BAR = 4.0


def _generate_notes(seed=42, bars=8, complexity="medium"):
    harmony = HarmonicEngine(CONFIG, seed=seed)
    prog = harmony.generate_progression("a", "minor", bars)
    scale_pcs = get_scale_pitch_classes("a", "minor", "natural_minor")
    melody = MelodicEngine(CONFIG, seed=seed)
    return melody.generate_bassline(prog, scale_pcs, role="bass", complexity=complexity), scale_pcs


def test_notes_inside_role_range():
    notes, _ = _generate_notes()
    rng = CONFIG["role_ranges"]["bass"]
    for note in notes:
        assert rng["min"] <= note.pitch <= rng["max"]


def test_all_pitch_classes_in_scale():
    notes, scale_pcs = _generate_notes()
    for note in notes:
        assert note.pitch % 12 in scale_pcs


def test_no_negative_or_zero_timing():
    notes, _ = _generate_notes()
    for note in notes:
        assert note.start_beat >= 0
        assert note.duration_beat > 0


def test_notes_cover_every_bar():
    notes, _ = _generate_notes(bars=8)
    bars_covered = {int(note.start_beat // BEATS_PER_BAR) for note in notes}
    assert bars_covered == set(range(8))


def test_velocity_within_midi_range():
    notes, _ = _generate_notes()
    for note in notes:
        assert 1 <= note.velocity <= 127


def test_seeded_output_deterministic():
    a, _ = _generate_notes(seed=123)
    b, _ = _generate_notes(seed=123)
    assert [(n.pitch, n.start_beat, n.duration_beat) for n in a] == [
        (n.pitch, n.start_beat, n.duration_beat) for n in b
    ]


def test_simple_less_dense_than_complex():
    simple_notes, _ = _generate_notes(seed=42, complexity="simple")
    complex_notes, _ = _generate_notes(seed=42, complexity="complex")
    assert len(simple_notes) < len(complex_notes)


def test_notes_carry_role_and_section_metadata():
    notes, _ = _generate_notes()
    for note in notes:
        assert note.role == "bass"
        assert note.section == CONFIG["section_template"][0]
