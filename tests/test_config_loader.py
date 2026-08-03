"""Unit tests for Layer 0 — Genre Config Loader."""

import json
import pytest

from engine.config_loader import (
    CONFIG_DIR,
    FALLBACK_GENRE,
    load_genre_config,
    validate_genre_config,
)


def test_dubstep_config_loads():
    config = load_genre_config("dubstep")
    assert config["genre"] == "dubstep"
    assert config["default_bpm"] == 140


def test_house_config_loads():
    config = load_genre_config("house")
    assert config["genre"] == "house"
    assert config["default_bpm"] == 126
    assert config["default_mode"] == "major"


def test_missing_genre_falls_back_to_generic():
    config = load_genre_config("no_such_genre")
    assert config["genre"] == FALLBACK_GENRE


def test_invalid_chord_pool_rejected():
    config = dict(load_genre_config("dubstep"))
    config["chord_pool"] = []
    with pytest.raises(ValueError):
        validate_genre_config(config)


def test_pattern_must_fill_one_bar():
    config = dict(load_genre_config("dubstep"))
    config["bass_patterns"]["medium"] = [[2, 2]]
    with pytest.raises(ValueError):
        validate_genre_config(config)


def test_bad_bpm_rejected():
    config = dict(load_genre_config("dubstep"))
    config["default_bpm"] = -1
    with pytest.raises(ValueError):
        validate_genre_config(config)


def test_invalid_genre_json_raises_when_generic_itself(tmp_path):
    (tmp_path / "generic.json").write_text("{ not valid json", encoding="utf-8")
    with pytest.raises((json.JSONDecodeError, ValueError)):
        load_genre_config("generic", tmp_path)


def test_dubstep_patterns_sum_to_sixteen():
    config = load_genre_config("dubstep")
    for patterns in config["bass_patterns"].values():
        for pattern in patterns:
            assert sum(pattern) == 16


def test_config_dir_exists():
    assert CONFIG_DIR.exists()


def test_section_bars_unknown_section_rejected():
    config = dict(load_genre_config("dubstep"))
    config["section_bars"]["nope"] = 1
    with pytest.raises(ValueError):
        validate_genre_config(config)


def test_section_density_out_of_range_rejected():
    config = dict(load_genre_config("dubstep"))
    config["section_density"]["drop"] = 1.5
    with pytest.raises(ValueError):
        validate_genre_config(config)


def test_section_velocity_out_of_range_rejected():
    config = dict(load_genre_config("dubstep"))
    config["section_velocity"]["drop"] = 200
    with pytest.raises(ValueError):
        validate_genre_config(config)


def test_all_genres_load_and_validate():
    for path in CONFIG_DIR.glob("*.json"):
        config = load_genre_config(path.stem)
        assert config["genre"] == path.stem
