"""Tests for CC automation + modulation + tempo-map export (exporter Layer 6)."""

import pytest
from mido import MidiFile, Message

from engine.config_loader import load_genre_config
from engine.exporter import export_midi
from engine.pipeline import (
    apply_modulations,
    build_cc_automation,
    build_tempo_map,
    generate_composition,
)


def test_cc_automation_follows_energy_curve():
    config = load_genre_config("dubstep")
    tracks, _, plan = generate_composition(
        config, ["bass", "drum", "lead"], "a", "minor", bars=None, seed=5
    )
    bass = next(t for t in tracks if t.role == "bass")
    drum = next(t for t in tracks if t.role == "drum")
    assert bass.cc, "melodic track should carry automation"
    assert drum.cc == [], "drum track should have no automation"

    cc_by_bar = {round(b / 4.0): (n, v) for b, n, v in bass.cc}
    drop_bars = [sb.bar for sb in plan if sb.name == "drop"]
    intro_bars = [sb.bar for sb in plan if sb.name == "intro"]
    drop_cutoff = max(cc_by_bar[b][1] for b in drop_bars if b in cc_by_bar)
    intro_cutoff = min(cc_by_bar[b][1] for b in intro_bars if b in cc_by_bar)
    assert drop_cutoff > intro_cutoff, "filter cutoff should open up in the drop"


def test_cc_messages_written_to_midi(tmp_path):
    config = load_genre_config("dubstep")
    tracks, _, _ = generate_composition(
        config, ["bass", "chord"], "a", "minor", bars=8, seed=6
    )
    out = tmp_path / "cc.mid"
    export_midi(tracks, config["default_bpm"], str(out))
    mid = MidiFile(str(out))
    bass_track = mid.tracks[1]
    ccs = [m for m in bass_track if m.type == "control_change"]
    assert ccs, "expected control-change messages"
    assert any(m.control == 74 for m in ccs)
    assert all(0 <= m.value <= 127 for m in ccs)
    for m in ccs:
        assert isinstance(m, Message)


def test_disabled_automation_skips_cc():
    config = load_genre_config("dubstep")
    config = dict(config)
    config["automation"] = {"enabled": False}
    plan = []
    from engine.arrangement import ArrangementEngine

    plan = ArrangementEngine(config).build_plan(None)
    assert build_cc_automation(config, plan, "bass") == []


def test_tempo_map_emits_only_changes():
    config = load_genre_config("dubstep")
    plan = []
    from engine.arrangement import ArrangementEngine

    plan = ArrangementEngine(config).build_plan(None)
    tempo_map = build_tempo_map(config, plan, 140)
    assert tempo_map, "dubstep breakdown is half-tempo, so a change is expected"
    for beat, bpm in tempo_map:
        assert 0 <= beat < len(plan) * 4
        assert 50 <= bpm <= 200
    assert tempo_map[0][0] > 0, "first bar stays at base tempo"


def test_tempo_map_written_as_set_tempo_events(tmp_path):
    config = load_genre_config("dubstep")
    tracks, _, plan = generate_composition(
        config, ["bass"], "a", "minor", bars=None, seed=4
    )
    tempo_map = build_tempo_map(config, plan, 140)
    out = tmp_path / "tempo.mid"
    export_midi(tracks, 140, str(out), tempo_map=tempo_map)
    mid = MidiFile(str(out))
    tempos = [
        (m.time, m.tempo) for m in mid.tracks[0] if m.type == "set_tempo"
    ]
    assert len(tempos) == len(tempo_map) + 1  # initial + each change
    assert len(set(t for _, t in tempos)) >= 2, "different tempi expected in the file"
    assert tempos[0][0] == 0, "first set_tempo must sit at tick 0"


def test_modulation_transposes_only_target_section():
    config = load_genre_config("dubstep")
    tracks, _, plan = generate_composition(
        config, ["bass", "chord"], "a", "minor", bars=None, seed=8, humanize=False
    )
    drop2_bars = {sb.bar for sb in plan if sb.name == "drop2"}
    bass = next(t for t in tracks if t.role == "bass")
    notes_before = {id(n): n.pitch for n in bass.notes}
    apply_modulations(config, [bass], plan)
    shifted = moved = 0
    for n in bass.notes:
        bar = int(n.start_beat // 4.0)
        if bar in drop2_bars:
            assert n.pitch == notes_before[id(n)] + 1
            shifted += 1
        else:
            assert n.pitch == notes_before[id(n)]
            moved += 1
    assert shifted > 0
    assert moved > 0
