"""Tests for groove template engine (Feature 3)."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.groove import GrooveProfile, load_groove_profile, apply_groove
from engine.models import Note


GROOVE_DIR = ROOT / "config" / "grooves"


class TestGrooveProfile:
    def test_load_house_profile(self):
        profile = load_groove_profile("house_four_on_floor")
        assert profile.id == "house_four_on_floor"
        assert profile.resolution == 16
        assert len(profile.offsets_ticks) == 16
        assert len(profile.velocity_scalars) == 16

    def test_load_techno_profile(self):
        profile = load_groove_profile("techno_driving")
        assert profile.id == "techno_driving"

    def test_load_dnb_profile(self):
        profile = load_groove_profile("dnb_breakneck")
        assert profile.id == "dnb_breakneck"

    def test_load_dubstep_profile(self):
        profile = load_groove_profile("dubstep_half_time")
        assert profile.id == "dubstep_half_time"

    def test_missing_profile_raises(self):
        with pytest.raises(FileNotFoundError):
            load_groove_profile("nonexistent_groove")

    def test_offset_for_step_wraps(self):
        profile = load_groove_profile("house_four_on_floor")
        assert profile.offset_for_step(0) == profile.offset_for_step(16)
        assert profile.offset_for_step(1) == profile.offset_for_step(17)

    def test_velocity_for_step_wraps(self):
        profile = load_groove_profile("house_four_on_floor")
        assert profile.velocity_for_step(0) == profile.velocity_for_step(16)


class TestApplyGroove:
    def _make_notes(self, role="bass"):
        return [
            Note(pitch=48, start_beat=0.0, duration_beat=0.25, velocity=100, role=role),
            Note(pitch=48, start_beat=0.25, duration_beat=0.25, velocity=100, role=role),
            Note(pitch=48, start_beat=0.5, duration_beat=0.25, velocity=100, role=role),
            Note(pitch=48, start_beat=1.0, duration_beat=0.25, velocity=100, role=role),
        ]

    def test_groove_modifies_timing(self):
        profile = load_groove_profile("house_four_on_floor")
        notes = self._make_notes()
        original_starts = [n.start_beat for n in notes]
        apply_groove(notes, profile, "bass", strength=1.0)
        # At least some notes should have shifted timing
        changed = any(n.start_beat != orig
                      for n, orig in zip(notes, original_starts))
        assert changed

    def test_groove_modifies_velocity(self):
        profile = load_groove_profile("house_four_on_floor")
        notes = self._make_notes()
        original_vels = [n.velocity for n in notes]
        apply_groove(notes, profile, "bass", strength=1.0)
        changed = any(n.velocity != orig
                      for n, orig in zip(notes, original_vels))
        assert changed

    def test_strength_zero_no_change(self):
        profile = load_groove_profile("house_four_on_floor")
        notes = self._make_notes()
        original_starts = [n.start_beat for n in notes]
        original_vels = [n.velocity for n in notes]
        apply_groove(notes, profile, "bass", strength=0.0)
        for n, orig_s, orig_v in zip(notes, original_starts, original_vels):
            assert n.start_beat == orig_s
            assert n.velocity == orig_v

    def test_sustained_roles_skip_timing(self):
        profile = load_groove_profile("house_four_on_floor")
        notes = self._make_notes(role="pad")
        original_starts = [n.start_beat for n in notes]
        apply_groove(notes, profile, "pad", strength=1.0)
        # Pad notes should NOT have timing changes
        for n, orig in zip(notes, original_starts):
            assert n.start_beat == orig

    def test_deterministic_output(self):
        profile = load_groove_profile("house_four_on_floor")
        notes1 = self._make_notes()
        notes2 = self._make_notes()
        apply_groove(notes1, profile, "bass", strength=1.0)
        apply_groove(notes2, profile, "bass", strength=1.0)
        for n1, n2 in zip(notes1, notes2):
            assert n1.start_beat == n2.start_beat
            assert n1.velocity == n2.velocity


class TestGrooveConfigValidation:
    def test_valid_groove_profile_passes(self, house_config):
        from engine.config_loader import _validate_groove
        _validate_groove(house_config)

    def test_invalid_groove_profile_fails(self):
        from engine.config_loader import _validate_groove
        config = {"groove_profile": "nonexistent_groove"}
        with pytest.raises(ValueError, match="references missing file"):
            _validate_groove(config)

    def test_groove_strength_range(self):
        from engine.config_loader import _validate_groove
        config = {"groove_strength": 1.5}
        with pytest.raises(ValueError, match="groove_strength"):
            _validate_groove(config)
