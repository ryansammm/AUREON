"""Unit tests for Layer 3 — Arrangement Engine."""

import pytest

from engine.arrangement import ArrangementEngine
from engine.config_loader import load_genre_config

CONFIG = load_genre_config("dubstep")


def test_full_template_length_matches_section_bars():
    engine = ArrangementEngine(CONFIG)
    expected = sum(CONFIG["section_bars"].values())
    assert engine.total_bars() == expected
    plan = engine.build_plan()
    assert len(plan) == expected
    assert plan[0].bar == 0
    assert plan[-1].bar == expected - 1


def test_section_order_follows_template():
    engine = ArrangementEngine(CONFIG)
    plan = engine.build_plan()
    names = [sb.name for sb in plan]
    expected = []
    for section in CONFIG["section_template"]:
        expected += [section] * CONFIG["section_bars"][section]
    assert names == expected
    for sb in plan:
        assert sb.name in CONFIG["section_template"]


def test_energy_curve_parameters_from_config():
    engine = ArrangementEngine(CONFIG)
    plan = engine.build_plan()
    for sb in plan:
        assert sb.density == CONFIG["section_density"][sb.name]
        assert sb.register_shift == CONFIG["section_register"][sb.name]
        assert sb.base_velocity == CONFIG["section_velocity"][sb.name]


def test_drop_section_is_most_energetic():
    engine = ArrangementEngine(CONFIG)
    plan = engine.build_plan()
    drop_density = CONFIG["section_density"]["drop"]
    for sb in plan:
        if sb.name in ("breakdown", "intro"):
            assert sb.density < drop_density


def test_custom_length_tiles_and_truncates_template():
    engine = ArrangementEngine(CONFIG)
    total = engine.total_bars()
    plan = engine.build_plan(num_bars=8)
    assert len(plan) == 8
    plan = engine.build_plan(num_bars=total + 3)
    assert len(plan) == total + 3
    assert plan[0].name == plan[total].name


def test_drop_register_is_lower_than_breakdown():
    engine = ArrangementEngine(CONFIG)
    plan = engine.build_plan()
    breakdown = next(sb for sb in plan if sb.name == "breakdown")
    drop = next(sb for sb in plan if sb.name == "drop")
    assert drop.register_shift < breakdown.register_shift


def test_zero_bars_rejected():
    with pytest.raises(ValueError):
        ArrangementEngine(CONFIG).build_plan(num_bars=0)


def test_missing_section_metadata_defaults_safely():
    config = dict(CONFIG)
    config.pop("section_density")
    config.pop("section_register")
    config.pop("section_velocity")
    plan = ArrangementEngine(config).build_plan(num_bars=2)
    for sb in plan:
        assert sb.density == 1.0
        assert sb.register_shift == 0
        assert sb.base_velocity == 92
