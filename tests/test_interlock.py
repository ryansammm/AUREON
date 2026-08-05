"""Tests for bass-drum interlock (Feature 2)."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.drums import DrumEngine
from engine.melody import MelodicEngine
from engine.models import SectionBar
from engine.pipeline import generate_composition


class TestKickMask:
    def test_extract_kick_mask_returns_set(self, house_config):
        engine = DrumEngine(house_config, seed=42)
        plan = [
            SectionBar(bar=i, name="drop", density=0.8,
                       register_shift=0, base_velocity=100)
            for i in range(4)
        ]
        mask = engine.extract_kick_mask(plan)
        assert isinstance(mask, set)

    def test_kick_mask_not_empty(self, house_config):
        engine = DrumEngine(house_config, seed=42)
        plan = [
            SectionBar(bar=i, name="drop", density=0.8,
                       register_shift=0, base_velocity=100)
            for i in range(4)
        ]
        mask = engine.extract_kick_mask(plan)
        assert len(mask) > 0

    def test_kick_mask_contains_beat_positions(self, house_config):
        engine = DrumEngine(house_config, seed=42)
        plan = [
            SectionBar(bar=0, name="drop", density=0.8,
                       register_shift=0, base_velocity=100),
        ]
        mask = engine.extract_kick_mask(plan)
        for pos in mask:
            assert isinstance(pos, float)
            assert 0.0 <= pos < 4.0  # within first bar


class TestBassInterlock:
    def test_lock_mode_biases_toward_kicks(self, house_config):
        engine = MelodicEngine(house_config, seed=42)
        from engine.harmony import HarmonicEngine
        from engine.music_utils import get_scale_pitch_classes

        harmony = HarmonicEngine(house_config, seed=42)
        progression = harmony.generate_progression("f", "major", 4)
        scale_pcs = get_scale_pitch_classes("f", "major")

        kick_mask = {0.0, 1.0, 2.0, 3.0}  # every beat
        plan = [
            SectionBar(bar=i, name="drop", density=0.8,
                       register_shift=0, base_velocity=100)
            for i in range(4)
        ]

        notes = engine.generate_bassline(
            progression, scale_pcs, role="bass", plan=plan,
            complexity="medium", kick_mask=kick_mask,
            interlock_mode="lock", interlock_probability=1.0,
        )
        # With lock_probability=1.0, all onsets should align with kick positions
        for note in notes:
            bar_pos = note.start_beat % 4.0
            near_kick = any(abs(bar_pos - kb % 4.0) < 0.3 for kb in kick_mask)
            assert near_kick, f"Note at beat {note.start_beat} not near any kick"

    def test_shift_mode_preserves_note_count(self, house_config):
        engine = MelodicEngine(house_config, seed=42)
        from engine.harmony import HarmonicEngine
        from engine.music_utils import get_scale_pitch_classes

        harmony = HarmonicEngine(house_config, seed=42)
        progression = harmony.generate_progression("f", "major", 4)
        scale_pcs = get_scale_pitch_classes("f", "major")

        kick_mask = {0.0}  # only downbeat -> most onsets conflict
        plan = [
            SectionBar(bar=i, name="drop", density=0.8,
                       register_shift=0, base_velocity=100)
            for i in range(4)
        ]

        notes_shift = engine.generate_bassline(
            progression, scale_pcs, role="bass", plan=plan,
            complexity="medium", kick_mask=kick_mask,
            interlock_mode="lock", interlock_probability=1.0,
            interlock_on_conflict="shift",
        )
        notes_drop = engine.generate_bassline(
            progression, scale_pcs, role="bass", plan=plan,
            complexity="medium", kick_mask=kick_mask,
            interlock_mode="lock", interlock_probability=1.0,
            interlock_on_conflict="drop",
        )
        # Shift keeps all onsets (snapped to kicks), drop removes conflicts
        assert len(notes_shift) > len(notes_drop)
        for note in notes_shift:
            bar_pos = note.start_beat % 4.0
            near_kick = any(abs(bar_pos - kb % 4.0) < 0.3 for kb in kick_mask)
            assert near_kick, f"Shifted note at beat {note.start_beat} not on kick"

    def test_shift_mode_snaps_offbeat_to_kick(self, house_config):
        engine = MelodicEngine(house_config, seed=42)
        from engine.harmony import HarmonicEngine
        from engine.music_utils import get_scale_pitch_classes

        harmony = HarmonicEngine(house_config, seed=42)
        progression = harmony.generate_progression("f", "major", 4)
        scale_pcs = get_scale_pitch_classes("f", "major")

        kick_mask = {0.0, 1.0, 2.0, 3.0}  # every beat
        plan = [
            SectionBar(bar=i, name="drop", density=0.8,
                       register_shift=0, base_velocity=100)
            for i in range(4)
        ]

        notes = engine.generate_bassline(
            progression, scale_pcs, role="bass", plan=plan,
            complexity="medium", kick_mask=kick_mask,
            interlock_mode="lock", interlock_probability=1.0,
            interlock_on_conflict="shift",
        )
        # Every note must land exactly on an integer beat
        for note in notes:
            assert note.start_beat % 1.0 == 0.0, (
                f"Note at beat {note.start_beat} not snapped to grid"
            )

    def test_independent_mode_ignores_kick_mask(self, house_config):
        engine = MelodicEngine(house_config, seed=42)
        from engine.harmony import HarmonicEngine
        from engine.music_utils import get_scale_pitch_classes

        harmony = HarmonicEngine(house_config, seed=42)
        progression = harmony.generate_progression("f", "major", 4)
        scale_pcs = get_scale_pitch_classes("f", "major")

        kick_mask = {0.0}  # only downbeat
        plan = [
            SectionBar(bar=i, name="drop", density=0.8,
                       register_shift=0, base_velocity=100)
            for i in range(4)
        ]

        notes_indep = engine.generate_bassline(
            progression, scale_pcs, role="bass", plan=plan,
            complexity="medium", kick_mask=kick_mask,
            interlock_mode="independent",
        )
        notes_no_mask = engine.generate_bassline(
            progression, scale_pcs, role="bass", plan=plan,
            complexity="medium", kick_mask=None,
            interlock_mode="independent",
        )
        # Independent mode with mask should produce same result as no mask
        assert len(notes_indep) == len(notes_no_mask)


class TestCompositionInterlock:
    def test_full_composition_with_interlock(self, house_config):
        tracks, progression, plan = generate_composition(
            house_config, ["bass", "drum"], "f", "major",
            bars=8, seed=42, humanize=False,
        )
        assert len(tracks) == 2
        bass_track = next(t for t in tracks if t.role == "bass")
        drum_track = next(t for t in tracks if t.role == "drum")
        assert len(bass_track.notes) > 0
        assert len(drum_track.notes) > 0

    def test_composition_without_interlock_config(self, generic_config):
        tracks, progression, plan = generate_composition(
            generic_config, ["bass", "drum"], "c", "minor",
            bars=4, seed=42, humanize=False,
        )
        assert len(tracks) == 2
