"""Tests for config inheritance and cycle detection (Task 2)."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.config_loader import load_genre_config

# Minimal valid config satisfying validate_genre_config().
MINIMAL = {
    "genre": "minimal",
    "default_bpm": 120,
    "scale_pool": ["natural_minor", "major"],
    "chord_pool": [{"degree": "i", "weight": 1.0}],
    "transition_matrix": {"i": {"i": 1.0}},
    "role_ranges": {
        "bass": {"min": 28, "max": 55, "preferred": 40},
        "lead": {"min": 60, "max": 92, "preferred": 70},
    },
    "bass_patterns": {
        "simple": [[16]],
        "medium": [[8, 8]],
        "complex": [[4, 4, 4, 4]],
    },
    "lead_patterns": {
        "simple": [[16]],
        "medium": [[8, 8]],
        "complex": [[4, 4, 4, 4]],
    },
    "instrument_intent": {
        "bass": {"label": "Bass", "preset": "sub_bass_low"},
        "lead": {"label": "Lead", "preset": "lead_synth"},
    },
}

# Same, but the fallback genre (must pass validation under its own name).
GENERIC = dict(MINIMAL, genre="generic")


def _write_configs(tmp_path: Path, configs: dict):
    for name, cfg in configs.items():
        (tmp_path / f"{name}.json").write_text(json.dumps(cfg), encoding="utf-8")


class TestConfigInheritance:
    def test_child_inherits_and_overrides(self, tmp_path):
        parent = dict(MINIMAL, genre="parent")
        child = dict(MINIMAL, genre="child", parent_genre="parent", default_bpm=140)
        _write_configs(tmp_path, {"parent": parent, "child": child})

        merged = load_genre_config("child", tmp_path)
        assert merged["genre"] == "child"
        assert merged["default_bpm"] == 140  # child override
        assert merged["scale_pool"] == parent["scale_pool"]  # inherited

    def test_grandparent_parent_child(self, tmp_path):
        grand = dict(MINIMAL, genre="grand")
        parent = dict(MINIMAL, genre="parent", parent_genre="grand", default_bpm=130)
        child_cfg = dict(MINIMAL, genre="child", parent_genre="parent", scale_pool=["major"])
        child_cfg.pop("default_bpm")  # must be inherited from the parent
        _write_configs(tmp_path, {"grand": grand, "parent": parent, "child": child_cfg})

        merged = load_genre_config("child", tmp_path)
        assert merged["default_bpm"] == 130  # from parent
        assert merged["scale_pool"] == ["major"]  # child override
        assert merged["chord_pool"] == grand["chord_pool"]  # from grandparent


class TestCycleDetection:
    def _fallback(self, tmp_path, name):
        """Load a cyclic config; assert it falls back to a valid genre."""
        # The fallback target must exist in the same dir.
        _write_configs(tmp_path, {"generic": GENERIC})
        cfg = load_genre_config(name, tmp_path)
        assert cfg is not None
        return cfg

    def test_direct_cycle_falls_back(self, tmp_path):
        _write_configs(tmp_path, {
            "a": dict(MINIMAL, genre="a", parent_genre="a"),
        })
        cfg = self._fallback(tmp_path, "a")
        assert cfg["genre"] == "generic"

    def test_two_way_cycle_falls_back(self, tmp_path):
        _write_configs(tmp_path, {
            "a": dict(MINIMAL, genre="a", parent_genre="b"),
            "b": dict(MINIMAL, genre="b", parent_genre="a"),
        })
        cfg = self._fallback(tmp_path, "a")
        assert cfg["genre"] == "generic"

    def test_three_way_cycle_falls_back(self, tmp_path):
        _write_configs(tmp_path, {
            "a": dict(MINIMAL, genre="a", parent_genre="b"),
            "b": dict(MINIMAL, genre="b", parent_genre="c"),
            "c": dict(MINIMAL, genre="c", parent_genre="a"),
        })
        cfg = self._fallback(tmp_path, "a")
        assert cfg["genre"] == "generic"

    def test_no_infinite_recursion(self, tmp_path):
        """A cycle must not blow the stack — the guard raises instead."""
        import engine.config_loader as cl
        _write_configs(tmp_path, {
            "a": dict(MINIMAL, genre="a", parent_genre="a"),
            "generic": GENERIC,
        })
        # A frame that already saw the genre on the chain rejects it.
        with pytest.raises(ValueError, match="cycle in genre inheritance"):
            cl.load_genre_config("a", tmp_path, _chain=("a",))
        # But the public API converts the cycle into the generic fallback.
        cfg = cl.load_genre_config("a", tmp_path)
        assert cfg["genre"] == "generic"
