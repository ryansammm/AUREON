"""Tests for the numpy audio renderer (role inference, empty-midi errors)."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import render_audio  # noqa: E402


class TestTrackRole:
    def test_genre_suffix_does_not_leak_role_keywords(self):
        # "(future_bass)" must not classify these tracks as "bass".
        assert render_audio.track_role("Counter Lead (future_bass)", []) == "counter_lead"
        assert render_audio.track_role("Stab - Supersaw (Future Bass)", []) == "stab"
        assert render_audio.track_role("Lead - Emotional (Future Bass)", []) == "lead"

    def test_drum_and_bass_genre_does_not_leak_drum_keyword(self):
        assert render_audio.track_role("Lead - Roller (drum_and_bass)", []) == "lead"
        assert render_audio.track_role("Pad - Deep (drum_and_bass)", []) == "pad"

    def test_bassline_genre_does_not_leak_bass_keyword(self):
        assert render_audio.track_role("Lead - Phat (bassline)", []) == "lead"
        assert render_audio.track_role("Pad - Airy (bassline)", []) == "pad"

    def test_specific_roles_win_over_generic_words(self):
        assert render_audio.track_role("Drums - 4x4 (Future Bass)", []) == "drum"
        assert render_audio.track_role("Drum Layers - Percussion (future_bass)", []) == "drum_layers"
        assert render_audio.track_role("Sub Bass (future_bass)", []) == "sub_bass"
        assert render_audio.track_role("Bass - Pump (Future Bass)", []) == "bass"
        assert render_audio.track_role("Chord (future_bass)", []) == "chord"
        assert render_audio.track_role("Arp (future_bass)", []) == "arp"

    def test_drum_channel_is_drum(self):
        notes = [(0.0, 1.0, 60, 100, 9)]
        assert render_audio.track_role("Anything", notes) == "drum"


class TestEmptyRender:
    def test_render_to_wav_raises_value_error_not_system_exit(self, tmp_path):
        mid = tmp_path / "empty.mid"
        out = tmp_path / "out.wav"
        # A MIDI with only a meta track (no notes).
        from mido import MidiFile, MetaMessage, MidiTrack

        m = MidiFile(ticks_per_beat=480)
        tr = MidiTrack()
        tr.append(MetaMessage("track_name", name="Composition"))
        m.tracks.append(tr)
        m.save(str(mid))

        with pytest.raises(ValueError, match="no notes found"):
            render_audio.render_to_wav(mid, out, roles=["bass"])
        assert not out.exists()
