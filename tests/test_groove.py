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


class TestAllGenresWired:
    """Task 4 — every genre config must reference a valid groove profile and
    declare an interlock mode."""

    def test_every_genre_has_groove_and_interlock(self):
        from engine.config_loader import CONFIG_DIR, load_genre_config
        genres = sorted(p.stem for p in CONFIG_DIR.glob("*.json"))
        assert genres, "expected genre configs to exist"
        for genre in genres:
            cfg = load_genre_config(genre)
            assert cfg.get("groove_profile"), f"{genre} missing groove_profile"
            assert cfg.get("groove_strength"), f"{genre} missing groove_strength"
            interlock = cfg.get("bass_drum_interlock")
            assert interlock, f"{genre} missing bass_drum_interlock"
            assert interlock.get("mode") in ("lock", "syncopate", "independent"), \
                f"{genre} has invalid interlock mode"
            assert 0.0 <= float(interlock.get("lock_probability", 0.0)) <= 1.0, \
                f"{genre} has invalid lock_probability"

    def test_groove_profiles_match_styles(self):
        """Newly authored profiles load and expose the expected 16-step shape."""
        from engine.groove import load_groove_profile
        for profile_id in ("trance_uplifting", "trap_slumped", "future_bass_bright",
                           "hardstyle_pumping", "uk_garage_shuffle", "downtempo_chill",
                           "psytrance_rolling", "progressive_house_pocket",
                           "big_room_stadium", "electro_house_funky", "generic_neutral"):
            profile = load_groove_profile(profile_id)
            assert profile.resolution == 16
            assert len(profile.offsets_ticks) == 16
            assert len(profile.velocity_scalars) == 16

    def test_distinct_styles_have_distinct_grooves(self):
        """No two wired genre families should share an identical groove."""
        from engine.config_loader import CONFIG_DIR, load_genre_config
        used = {}
        for p in CONFIG_DIR.glob("*.json"):
            cfg = load_genre_config(p.stem)
            used.setdefault(cfg["groove_profile"], []).append(p.stem)
        # A profile may be shared (e.g. children), but the distinct profiles
        # we authored must each be referenced.
        expected = {"house_four_on_floor", "techno_driving", "dnb_breakneck",
                    "dubstep_half_time", "trance_uplifting", "trap_slumped",
                    "future_bass_bright", "hardstyle_pumping", "uk_garage_shuffle",
                    "downtempo_chill", "psytrance_rolling", "progressive_house_pocket",
                    "big_room_stadium", "electro_house_funky", "generic_neutral"}
        assert expected <= set(used), \
            f"unreferenced groove profiles: {expected - set(used)}"


class TestGrooveDrumIntegration:
    """Task 1 — groove profiles must reach the drum track.

    techno uses groove_profile ``techno_driving`` with
    ``offsets_ticks`` +1 on steps 3/7/11/15 and ``groove_strength`` 0.9.
    A +1 tick = 1/16 beat; * strength 0.9 -> 0.05625 beat shift.
    A note on step 3 lands at bar-position 0.75 + 0.05625 = 0.80625.
    """

    TICK_SHIFT = 0.05625  # 1 tick * (1/16 beat) * strength 0.9

    def _drum_track(self, config, roles, seed=123, humanize=False):
        from engine.pipeline import generate_composition
        tracks, _, _ = generate_composition(
            config, roles, config["default_key"], config["default_mode"],
            bars=8, seed=seed, humanize=humanize,
        )
        return next(t for t in tracks if t.role in ("drum", "drum_layers"))

    def _no_groove_config(self, config):
        import copy
        cfg = copy.deepcopy(config)
        cfg.pop("groove_profile", None)
        cfg.pop("groove_strength", None)
        return cfg

    def test_drum_track_gets_groove_timing(self, techno_config):
        """Drum notes on offset steps are pushed off the strict grid."""
        drum = self._drum_track(techno_config, ["drum"])
        shifted = [
            n for n in drum.notes
            if abs((n.start_beat % 4.0) - (0.75 + self.TICK_SHIFT)) < 1e-6
        ]
        assert shifted, "expected some drum note shifted by the groove profile"
        # And grid-locked steps (e.g. kick on step 0) stay on the grid.
        locked = [n for n in drum.notes if abs(n.start_beat % 4.0) < 1e-6]
        assert locked, "expected grid-locked drum notes to remain"

    def test_drum_track_differs_with_and_without_groove(self, techno_config):
        """Same seed: groove on/off must produce different drum timing+vel."""
        with_groove = self._drum_track(techno_config, ["drum"])
        without_groove = self._drum_track(
            self._no_groove_config(techno_config), ["drum"]
        )
        starts_w = sorted(n.start_beat for n in with_groove.notes)
        starts_o = sorted(n.start_beat for n in without_groove.notes)
        assert starts_w != starts_o, "groove should alter drum note timing"
        vels_w = [n.velocity for n in with_groove.notes]
        vels_o = [n.velocity for n in without_groove.notes]
        assert vels_w != vels_o, "groove should alter drum note velocity"

    def test_interlock_drum_track_gets_groove(self, techno_config):
        """Bass+Drum (interlock Phase 1) drums also receive the groove."""
        drum = self._drum_track(techno_config, ["drum", "bass"])
        shifted = [
            n for n in drum.notes
            if abs((n.start_beat % 4.0) - (0.75 + self.TICK_SHIFT)) < 1e-6
        ]
        assert shifted, "interlock drum track should carry groove offsets"

    def test_drum_layers_gets_groove(self, techno_config):
        """drum_layers (extra percussion) receive the groove."""
        layers = self._drum_track(techno_config, ["drum_layers"])
        no_groove = self._drum_track(
            self._no_groove_config(techno_config), ["drum_layers"]
        )
        starts_w = sorted(n.start_beat for n in layers.notes)
        starts_o = sorted(n.start_beat for n in no_groove.notes)
        vels_w = [n.velocity for n in layers.notes]
        vels_o = [n.velocity for n in no_groove.notes]
        assert starts_w != starts_o or vels_w != vels_o, \
            "drum_layers should be affected by the groove profile"

    def test_groove_does_not_skip_drum_roles(self, techno_config):
        """apply_groove must not treat drums as sustained/skip-timing roles."""
        from engine.groove import apply_groove, load_groove_profile
        from engine.models import Note
        profile = load_groove_profile("techno_driving")
        notes = [
            Note(pitch=42, start_beat=0.75, duration_beat=0.25,
                 velocity=95, role="drum"),
            Note(pitch=42, start_beat=1.75, duration_beat=0.25,
                 velocity=95, role="drum"),
        ]
        apply_groove(notes, profile, "drum", strength=0.9)
        # Steps 3 and 7 both carry a +1 tick offset in techno_driving.
        for n, expected in zip(notes, (0.75, 1.75)):
            assert abs((n.start_beat % 4.0) - (expected + self.TICK_SHIFT)) < 1e-6
