"""Layer 0 — Genre Config Loader.

Loads genre configuration from JSON files under ``config/genres/`` and
validates it. Per the project spec (Section 7, Error Handling), a missing
or invalid genre config falls back to the ``generic`` genre with an
explicit warning — never a silent failure.

Musical assumptions:
- Chord degrees are Roman-numeral strings parsed by music21
  (e.g. ``i``, ``VI``, ``VII``, ``I``, ``ii``).
- Rhythm patterns are lists of 16th-note durations summing to 16
  (exactly one 4/4 bar).
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config" / "genres"
FALLBACK_GENRE = "generic"

REQUIRED_KEYS = {
    "genre": str,
    "default_bpm": (int, float),
    "scale_pool": list,
    "chord_pool": list,
    "transition_matrix": dict,
    "role_ranges": dict,
    "bass_patterns": dict,
    "instrument_intent": dict,
}


def _validate_patterns(config: dict) -> None:
    """Every rhythm pattern must fill exactly one 4/4 bar (16 sixteenths)."""
    for key, value in config.items():
        if not key.endswith("_patterns") or key == "drum_patterns":
            continue
        for complexity, patterns in value.items():
            for pattern in patterns:
                if sum(pattern) != 16:
                    raise ValueError(
                        f"{key}[{complexity}] pattern must sum to 16 "
                        f"sixteenth notes, got {pattern} (sum={sum(pattern)})"
                    )


def _validate_drum_patterns(config: dict) -> None:
    """Every drum step string must be exactly 16 characters (16 steps)."""
    drum_cfg = config.get("drum_patterns") or {}
    if not drum_cfg:
        return
    if "notes" in drum_cfg and not isinstance(drum_cfg["notes"], dict):
        raise ValueError("drum_patterns.notes must be an object")
    if "layer_notes" in drum_cfg and not isinstance(drum_cfg["layer_notes"], dict):
        raise ValueError("drum_patterns.layer_notes must be an object")

    def _check_section_voices(block: dict, label: str) -> None:
        if not isinstance(block, dict):
            raise ValueError(f"drum_patterns.{label} must be an object")
        for section, voices in block.items():
            if not isinstance(voices, dict):
                raise ValueError(
                    f"drum_patterns.{label}['{section}'] must be an object"
                )
            for voice, steps in voices.items():
                if not isinstance(steps, str) or len(steps) != 16:
                    raise ValueError(
                        f"drum step string for '{label}'/'{section}'/'{voice}' "
                        f"must be 16 characters, got "
                        f"{len(steps) if isinstance(steps, str) else steps}"
                    )
                invalid = set(steps) - {".", "x", "X"}
                if invalid:
                    raise ValueError(
                        f"drum step string for '{label}'/'{section}'/'{voice}' "
                        f"has invalid characters {sorted(invalid)} "
                        f"(allowed: '.', 'x', 'X')"
                    )

    _check_section_voices(drum_cfg.get("patterns"), "patterns")
    _check_section_voices(drum_cfg.get("layers"), "layers")


def _validate_role_params(config: dict) -> None:
    """Validate the optional per-role parameter block."""
    params = config.get("role_params") or {}
    if not isinstance(params, dict):
        raise ValueError("role_params must be an object")
    for role, block in params.items():
        if not isinstance(block, dict):
            raise ValueError(f"role_params['{role}'] must be an object")
        if "counter_lead" in block:
            for key, value in block["counter_lead"].items():
                if key == "delay_beats" and value < 0:
                    raise ValueError("role_params.counter_lead.delay_beats >= 0")


def _validate_sections(config: dict) -> None:
    """Validate optional section-template keys used by Layer 3."""
    template = config.get("section_template", [])
    if template and not all(isinstance(s, str) for s in template):
        raise ValueError("section_template must be a list of section names")
    section_names = set(template)
    bars_map = config.get("section_bars", {})
    for name, bars in bars_map.items():
        if name not in section_names:
            raise ValueError(f"section_bars references unknown section: {name}")
        if not (isinstance(bars, int) and bars >= 1):
            raise ValueError(f"section_bars['{name}'] must be an int >= 1")
    for key in ("section_density", "section_register", "section_velocity"):
        mapping = config.get(key, {})
        for name, value in mapping.items():
            if name not in section_names:
                raise ValueError(f"{key} references unknown section: {name}")
    for name, value in config.get("section_density", {}).items():
        if not (0.0 <= float(value) <= 1.0):
            raise ValueError(f"section_density['{name}'] must be in [0, 1]")
    for name, value in config.get("section_velocity", {}).items():
        if not (1 <= int(value) <= 127):
            raise ValueError(f"section_velocity['{name}'] must be in [1, 127]")
    for name, value in config.get("selector_weights", {}).items():
        if not (isinstance(value, (int, float)) and value > 0):
            raise ValueError(f"selector_weights['{name}'] must be positive")


def _validate_groove(config: dict) -> None:
    """Validate optional groove_profile and groove_strength keys."""
    profile = config.get("groove_profile")
    if profile is not None:
        if not isinstance(profile, str):
            raise ValueError("groove_profile must be a string (profile id)")
        groove_dir = Path(__file__).resolve().parent.parent / "config" / "grooves"
        path = groove_dir / f"{profile}.json"
        if not path.is_file():
            raise ValueError(
                f"groove_profile '{profile}' references missing file: {path}"
            )
    strength = config.get("groove_strength")
    if strength is not None:
        if not (isinstance(strength, (int, float)) and 0.0 <= strength <= 1.0):
            raise ValueError("groove_strength must be a float in [0.0, 1.0]")


def validate_genre_config(config) -> bool:
    """Validate a genre config dict. Raises ``ValueError`` on failure."""
    if not isinstance(config, dict):
        raise ValueError("genre config must be a JSON object")
    for key, expected in REQUIRED_KEYS.items():
        if key not in config:
            raise ValueError(f"genre config missing required key: {key}")
        if not isinstance(config[key], expected):
            raise ValueError(
                f"genre config key '{key}' must be of type {expected}, "
                f"got {type(config[key])}"
            )
    if config["default_bpm"] <= 0:
        raise ValueError("default_bpm must be positive")
    if not config["chord_pool"]:
        raise ValueError("chord_pool must not be empty")
    for item in config["chord_pool"]:
        if item.get("weight", 0) <= 0:
            raise ValueError(f"chord_pool item must have positive weight: {item}")
    for role in config["role_ranges"]:
        rng = config["role_ranges"][role]
        if not (0 <= rng["min"] <= rng["max"] <= 127):
            raise ValueError(f"role '{role}' range invalid: {rng}")
    _validate_patterns(config)
    _validate_drum_patterns(config)
    _validate_role_params(config)
    _validate_sections(config)
    _validate_groove(config)
    return True


def load_genre_config(genre: str, config_dir: Path = None) -> dict:
    """Load and validate a genre config, falling back to ``generic``.

    If a config contains ``parent_genre``, it inherits all keys from the
    parent and only overrides specified fields.  Override keys are merged
    recursively for dicts and replaced outright for other types.
    """
    config_dir = config_dir or CONFIG_DIR
    path = Path(config_dir) / f"{genre}.json"
    try:
        with open(path, encoding="utf-8") as fh:
            config = json.load(fh)
        parent_name = config.get("parent_genre")
        if parent_name:
            parent = load_genre_config(parent_name, config_dir)
            config = _merge_overrides(parent, config)
        validate_genre_config(config)
        return config
    except FileNotFoundError:
        if genre == FALLBACK_GENRE:
            raise
        logger.warning(
            "Genre '%s' not found at %s — falling back to '%s'.",
            genre, path, FALLBACK_GENRE,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        if genre == FALLBACK_GENRE:
            raise
        logger.warning(
            "Genre config '%s' invalid (%s) — falling back to '%s'.",
            genre, exc, FALLBACK_GENRE,
        )
    return load_genre_config(FALLBACK_GENRE, config_dir)


def _merge_overrides(parent: dict, child: dict) -> dict:
    """Merge *child* onto *parent*.  Keys not in child come from parent.

    - ``parent_genre`` is removed from the result (it was only used to
      select the parent).
    - Dict values are merged recursively.
    - All other types (list, int, str, …) are replaced outright.
    """
    result = dict(parent)
    for key, value in child.items():
        if key == "parent_genre":
            continue
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_overrides(result[key], value)
        else:
            result[key] = value
    return result
