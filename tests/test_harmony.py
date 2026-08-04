"""Tests for voice-leading smoothness (Feature 1)."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.models import ChordBar, VoicingCandidate
from engine.harmony import (
    HarmonicEngine,
    voice_chord,
    voice_leading_cost,
    generate_voicing_candidates,
    _pitches_for_pc,
)


class TestPitchesForPc:
    def test_returns_correct_pitches(self):
        result = _pitches_for_pc(0, 48, 72)  # C in [48, 72]
        assert result == [48, 60, 72]

    def test_empty_when_out_of_range(self):
        result = _pitches_for_pc(0, 61, 65)  # C not in [61, 65]
        assert result == []

    def test_single_pitch(self):
        result = _pitches_for_pc(0, 59, 65)  # C only at 60
        assert result == [60]


class TestVoiceLeadingCost:
    def test_identical_voicings_have_zero_cost(self):
        a = [48, 55, 60, 64]
        cost = voice_leading_cost(a, a, {"min": 36, "max": 84})
        assert cost == 0.0

    def test_small_movement_costs_less_than_large(self):
        a = [48, 55, 60, 64]
        b_small = [48, 55, 60, 65]  # one voice moves 1 semitone
        b_large = [48, 55, 60, 72]  # one voice moves 8 semitones
        cost_small = voice_leading_cost(a, b_small, {"min": 36, "max": 84})
        cost_large = voice_leading_cost(a, b_large, {"min": 36, "max": 84})
        assert cost_small < cost_large

    def test_out_of_register_adds_penalty(self):
        a = [48, 55, 60, 64]
        b = [48, 55, 60, 80]  # 80 > max of 72
        cost = voice_leading_cost(a, b, {"min": 36, "max": 72})
        assert cost > 0.0

    def test_empty_voicings_zero_cost(self):
        cost = voice_leading_cost([], [48, 55], {"min": 36, "max": 84})
        assert cost == 0.0


class TestGenerateVoicingCandidates:
    def test_returns_candidates(self):
        chord = ChordBar(bar=0, degree="I", root_pc=0, quality="major",
                         pitch_classes=[0, 4, 7])
        candidates = generate_voicing_candidates(chord, {"min": 48, "max": 72})
        assert len(candidates) >= 1
        assert all(isinstance(c, VoicingCandidate) for c in candidates)

    def test_root_position_first_candidate(self):
        chord = ChordBar(bar=0, degree="I", root_pc=0, quality="major",
                         pitch_classes=[0, 4, 7])
        candidates = generate_voicing_candidates(chord, {"min": 48, "max": 72})
        assert candidates[0].inversion == 0

    def test_all_pitches_within_range(self):
        chord = ChordBar(bar=0, degree="V", root_pc=7, quality="major",
                         pitch_classes=[7, 11, 2])
        role_range = {"min": 48, "max": 72}
        candidates = generate_voicing_candidates(chord, role_range)
        for c in candidates:
            for p in c.pitches:
                assert role_range["min"] <= p <= role_range["max"]

    def test_deduplication(self):
        chord = ChordBar(bar=0, degree="I", root_pc=0, quality="major",
                         pitch_classes=[0, 4, 7])
        candidates = generate_voicing_candidates(chord, {"min": 48, "max": 72})
        pitch_sets = [tuple(c.pitches) for c in candidates]
        assert len(pitch_sets) == len(set(pitch_sets))


class TestVoiceChord:
    def test_first_chord_picks_narrow_span(self):
        chord = ChordBar(bar=0, degree="I", root_pc=0, quality="major",
                         pitch_classes=[0, 4, 7])
        result = voice_chord(chord, None, {"min": 48, "max": 72})
        assert len(result.pitches) > 0

    def test_second_chord_minimizes_movement(self):
        chord_a = ChordBar(bar=0, degree="I", root_pc=0, quality="major",
                           pitch_classes=[0, 4, 7])
        chord_b = ChordBar(bar=1, degree="V", root_pc=7, quality="major",
                           pitch_classes=[7, 11, 2])
        role_range = {"min": 48, "max": 72}
        voicing_a = voice_chord(chord_a, None, role_range)
        voicing_b = voice_chord(chord_b, voicing_a.pitches, role_range)
        cost = voice_leading_cost(voicing_a.pitches, voicing_b.pitches, role_range)
        # Should be reasonable - not jumping wildly
        assert cost < 20.0

    def test_deterministic(self):
        chord = ChordBar(bar=0, degree="I", root_pc=0, quality="major",
                         pitch_classes=[0, 4, 7])
        role_range = {"min": 48, "max": 72}
        r1 = voice_chord(chord, None, role_range)
        r2 = voice_chord(chord, None, role_range)
        assert r1.pitches == r2.pitches


class TestHarmonicEngineProgression:
    def test_generate_progression_length(self, house_config):
        engine = HarmonicEngine(house_config, seed=42)
        prog = engine.generate_progression("f", "major", 8)
        assert len(prog) == 8

    def test_generate_progression_with_degrees(self, house_config):
        engine = HarmonicEngine(house_config, seed=42)
        prog = engine.generate_progression("f", "major", 4,
                                           degrees=["I", "V", "vi", "IV"])
        assert len(prog) == 4
        assert prog[0].degree == "I"
        assert prog[1].degree == "V"

    def test_chord_bar_has_pitch_classes(self, house_config):
        engine = HarmonicEngine(house_config, seed=42)
        prog = engine.generate_progression("f", "major", 1)
        assert len(prog[0].pitch_classes) >= 3
