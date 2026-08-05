"""Tests for friendly MIDI download names (genre/key/roles parsing)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import web.app as app  # noqa: E402


RUN = "run179c6e_kawaii_future_bass_bass-lead-drum-drum_layers-counter_lead-stab-pad-chord-sub_bass-arp_emajor_seed887"


class TestParseBaseName:
    def test_underscore_genre_and_roles(self):
        meta = app.parse_base_name(RUN)
        assert meta["genre"] == "kawaii_future_bass"
        assert meta["roles"] == [
            "bass", "lead", "drum", "drum_layers", "counter_lead",
            "stab", "pad", "chord", "sub_bass", "arp",
        ]
        assert meta["key"] == "e"
        assert meta["mode"] == "major"
        assert meta["seed"] == 887

    def test_single_role_minor(self):
        meta = app.parse_base_name("run050426_techno_bass_dminor_seed3")
        assert meta["genre"] == "techno"
        assert meta["roles"] == ["bass"]
        assert meta["key"] == "d"
        assert meta["mode"] == "minor"
        assert meta["seed"] == 3

    def test_genre_prefix_not_mistaken(self):
        # "future_bass" is a prefix of "kawaii_future_bass"; the longer genre
        # must win, and the role list must still match.
        meta = app.parse_base_name(
            "run058196_future_bass_bass-lead-counter_lead-stab_fmajor_seed42"
        )
        assert meta["genre"] == "future_bass"
        assert meta["roles"] == ["bass", "lead", "counter_lead", "stab"]

    def test_sharp_key(self):
        meta = app.parse_base_name("runab12cd_house_bass-lead_c#minor_seed7")
        assert meta["genre"] == "house"
        assert meta["roles"] == ["bass", "lead"]
        assert meta["key"] == "c#"
        assert meta["mode"] == "minor"
        assert meta["seed"] == 7


class TestFriendlyMidiStem:
    def test_main_stem(self):
        assert app._friendly_midi_stem(f"{RUN}.mid") == \
            "kawaii_future_bass_emajor_seed887"

    def test_role_stem(self):
        assert app._friendly_midi_stem(f"{RUN}.mid", "counter_lead") == \
            "kawaii_future_bass_emajor_seed887_counter_lead"

    def test_simple_name(self):
        assert app._friendly_midi_stem("run050426_techno_bass_dminor_seed3.mid") == \
            "techno_dminor_seed3"


class TestDownloadHeader:
    def test_download_sets_friendly_name(self):
        fname = f"{RUN}.mid"
        path = app.app.config["OUTPUT_DIR"] / fname
        path.write_bytes(b"fake-midi")
        try:
            client = app.app.test_client()
            resp = client.get(f"/download/{fname}")
            assert resp.status_code == 200
            cd = resp.headers.get("Content-Disposition", "")
            assert "kawaii_future_bass_emajor_seed887.mid" in cd
            resp.close()
        finally:
            path.unlink(missing_ok=True)
