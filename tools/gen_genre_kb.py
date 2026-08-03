"""AI-curated EDM genre knowledge base -> ``config/genres/*.json``.

The engine (``engine/``) contains ZERO genre knowledge: every genre's
musical character lives here as DATA — the JSON files under
``config/genres/`` are the dataset, filled from musicology/AI knowledge
about how each EDM genre is actually built (tempo, harmonic pools,
rhythm profiles, drum kits, arrangement shapes, swing, automation).

The patterns below are the "AI filling the dataset": a compact knowledge
table that expands into complete, valid genre configs.

Regenerate the dataset with:

    python tools\\gen_genre_kb.py
"""

import json
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "config" / "genres"


# --------------------------------------------------------------------------- #
# Rhythm pattern libraries — each tier is a list of 16th-duration lists
# that each sum to exactly 16 (one 4/4 bar).
# --------------------------------------------------------------------------- #
BASS = {
    "four_floor": {
        "simple": [[16], [8, 8], [4, 4, 4, 4]],
        "medium": [[4, 4, 4, 4], [2, 2, 2, 2, 2, 2, 2, 2], [2, 2, 4, 2, 2, 4]],
        "complex": [[2, 2, 2, 2, 2, 2, 2, 2], [2, 1, 1, 2, 1, 1, 2, 1, 1, 2, 1, 1], [4, 1, 1, 2, 1, 1, 2, 1, 1, 1, 1]],
    },
    "offbeat": {
        "simple": [[16], [8, 8], [4, 4, 4, 4]],
        "medium": [[2, 2, 4, 2, 2, 4], [8, 2, 2, 2, 2], [4, 2, 4, 2, 4]],
        "complex": [[2, 2, 2, 2, 2, 2, 2, 2], [2, 4, 1, 1, 4, 2, 2], [2, 1, 1, 2, 2, 2, 1, 1, 2, 2]],
    },
    "rolling": {
        "simple": [[16], [8, 8], [4, 4, 4, 4]],
        "medium": [[2, 2, 2, 2, 2, 2, 2, 2], [4, 4, 2, 2, 4], [2, 2, 4, 2, 2, 4]],
        "complex": [[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1], [2, 2, 2, 2, 2, 2, 2, 2], [1, 1, 2, 1, 1, 2, 1, 1, 2, 1, 1, 2]],
    },
    "syncopated": {
        "simple": [[16], [8, 8], [4, 4, 4, 4]],
        "medium": [[4, 2, 4, 2, 4], [2, 6, 2, 6], [4, 4, 2, 2, 2, 2]],
        "complex": [[2, 4, 1, 1, 4, 2, 2], [1, 3, 1, 1, 3, 1, 1, 3, 1, 1], [2, 2, 2, 2, 2, 2, 2, 2]],
    },
}

LEAD = {
    "legato": {
        "simple": [[16], [8, 8], [4, 4, 4, 4]],
        "medium": [[8, 8], [4, 4, 4, 4], [2, 2, 4, 2, 2, 4]],
        "complex": [[2, 2, 2, 2, 2, 2, 2, 2], [4, 2, 2, 2, 2, 2, 2], [2, 4, 1, 1, 4, 2, 2]],
    },
    "staccato": {
        "simple": [[4, 4, 4, 4], [8, 8], [16]],
        "medium": [[2, 2, 4, 2, 2, 4], [4, 4, 2, 2, 2, 2], [2, 4, 4, 2, 4]],
        "complex": [[1, 1, 2, 2, 2, 2, 2, 2, 2], [2, 2, 1, 1, 2, 1, 1, 2, 2, 2], [1, 1, 1, 1, 1, 1, 2, 2, 2, 4]],
    },
    "syncopated": {
        "simple": [[8, 8], [4, 4, 4, 4], [16]],
        "medium": [[4, 2, 4, 2, 4], [2, 2, 4, 2, 2, 4], [2, 6, 2, 6]],
        "complex": [[2, 4, 1, 1, 4, 2, 2], [1, 3, 1, 1, 3, 1, 1, 3, 1, 1], [2, 2, 4, 2, 2, 2, 2]],
    },
    "melodic": {
        "simple": [[8, 8], [4, 4, 4, 4], [16]],
        "medium": [[2, 2, 4, 2, 2, 4], [4, 4, 2, 2, 2, 2], [2, 4, 4, 2, 4]],
        "complex": [[1, 1, 2, 2, 2, 2, 2, 2, 2], [2, 2, 1, 1, 2, 1, 1, 2, 2, 2], [1, 1, 1, 1, 1, 1, 2, 2, 2, 4]],
    },
}

ARP = {
    "straight": {
        "simple": [[4, 4, 4, 4], [2, 2, 2, 2, 2, 2, 2, 2], [8, 8]],
        "medium": [[2, 2, 2, 2, 2, 2, 2, 2], [2, 2, 4, 2, 2, 4]],
        "complex": [[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1], [1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2]],
    },
    "rolling": {
        "simple": [[4, 4, 4, 4], [2, 2, 2, 2, 2, 2, 2, 2]],
        "medium": [[2, 2, 2, 2, 2, 2, 2, 2], [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]],
        "complex": [[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1], [2, 2, 2, 2, 2, 2, 2, 2]],
    },
    "broken": {
        "simple": [[2, 2, 4, 2, 2, 4], [4, 4, 2, 2, 2, 2]],
        "medium": [[2, 2, 4, 2, 2, 4], [2, 4, 2, 2, 4, 2]],
        "complex": [[1, 1, 2, 1, 1, 2, 1, 1, 2, 1, 1, 2], [1, 3, 1, 1, 3, 1, 1, 3, 1, 1]],
    },
    "offbeat": {
        "simple": [[2, 6, 2, 6], [4, 2, 4, 2, 4]],
        "medium": [[4, 2, 4, 2, 4], [2, 6, 2, 6]],
        "complex": [[2, 4, 1, 1, 4, 2, 2], [2, 2, 2, 2, 2, 2, 2, 2]],
    },
}

STAB = {
    "quarter": {
        "simple": [[4, 4, 4, 4], [8, 8], [16]],
        "medium": [[4, 4, 4, 4], [2, 2, 4, 2, 2, 4]],
        "complex": [[4, 4, 2, 2, 2, 2], [2, 2, 4, 2, 2, 4]],
    },
    "offbeat": {
        "simple": [[2, 6, 2, 6], [4, 2, 4, 2, 4]],
        "medium": [[2, 6, 2, 6], [2, 2, 4, 2, 2, 4]],
        "complex": [[2, 4, 1, 1, 4, 2, 2], [2, 2, 2, 2, 2, 2, 2, 2]],
    },
    "eighth": {
        "simple": [[2, 2, 2, 2, 2, 2, 2, 2], [4, 4, 4, 4]],
        "medium": [[2, 2, 2, 2, 2, 2, 2, 2], [2, 2, 4, 2, 2, 4]],
        "complex": [[2, 2, 2, 2, 2, 2, 2, 2], [4, 2, 2, 2, 2, 2, 2]],
    },
}

SUB = {
    "whole": {
        "simple": [[16], [8, 8], [4, 4, 4, 4]],
        "medium": [[16], [8, 8], [4, 4, 4, 4]],
        "complex": [[8, 8], [4, 4, 4, 4], [2, 2, 4, 2, 2, 4]],
    },
    "kicker": {
        "simple": [[16], [8, 8], [4, 4, 4, 4]],
        "medium": [[4, 4, 4, 4], [8, 8], [2, 2, 4, 2, 2, 4]],
        "complex": [[4, 4, 4, 4], [2, 2, 4, 2, 2, 4], [2, 2, 2, 2, 2, 2, 2, 2]],
    },
    "sync": {
        "simple": [[16], [8, 8], [4, 4, 4, 4]],
        "medium": [[4, 2, 4, 2, 4], [2, 6, 2, 6]],
        "complex": [[2, 2, 4, 2, 2, 4], [2, 4, 1, 1, 4, 2, 2]],
    },
}

COUNTER = {
    "answer": {
        "simple": [[8, 8], [16]],
        "medium": [[8, 8], [4, 4, 4, 4]],
        "complex": [[4, 4, 4, 4], [2, 2, 4, 2, 2, 4]],
    },
    "sync": {
        "simple": [[8, 8]],
        "medium": [[4, 2, 4, 2, 4]],
        "complex": [[2, 4, 1, 1, 4, 2, 2]],
    },
    "staccato": {
        "simple": [[4, 4, 4, 4]],
        "medium": [[2, 2, 4, 2, 2, 4]],
        "complex": [[2, 2, 2, 2, 2, 2, 2, 2]],
    },
}


# --------------------------------------------------------------------------- #
# Chord templates — weighted pool + transition matrix (hand-weighted Markov).
# --------------------------------------------------------------------------- #
CHORDS = {
    "minor_emotional": {
        "pool": [
            {"degree": "i", "weight": 1.0},
            {"degree": "VI", "weight": 0.8},
            {"degree": "III", "weight": 0.6},
            {"degree": "VII", "weight": 0.6},
            {"degree": "iv", "weight": 0.4},
        ],
        "trans": {
            "i": {"VI": 0.4, "III": 0.3, "VII": 0.2, "iv": 0.1},
            "VI": {"VII": 0.4, "III": 0.3, "i": 0.3},
            "III": {"VII": 0.3, "VI": 0.4, "iv": 0.3},
            "VII": {"i": 0.5, "III": 0.3, "VI": 0.2},
            "iv": {"i": 0.5, "VII": 0.3, "III": 0.2},
        },
    },
    "minor_dark": {
        "pool": [
            {"degree": "i", "weight": 1.0},
            {"degree": "VII", "weight": 0.8},
            {"degree": "VI", "weight": 0.7},
            {"degree": "iv", "weight": 0.5},
        ],
        "trans": {
            "i": {"VII": 0.45, "VI": 0.35, "iv": 0.2},
            "VII": {"i": 0.5, "VI": 0.3, "iv": 0.2},
            "VI": {"VII": 0.4, "i": 0.4, "iv": 0.2},
            "iv": {"i": 0.6, "VI": 0.4},
        },
    },
    "minor_phrygian": {
        "pool": [
            {"degree": "i", "weight": 1.0},
            {"degree": "VII", "weight": 0.9},
            {"degree": "VI", "weight": 0.6},
            {"degree": "ii", "weight": 0.3},
        ],
        "trans": {
            "i": {"VII": 0.5, "VI": 0.3, "ii": 0.2},
            "VII": {"i": 0.6, "VI": 0.4},
            "VI": {"VII": 0.5, "i": 0.5},
            "ii": {"VII": 0.6, "i": 0.4},
        },
    },
    "dorian": {
        "pool": [
            {"degree": "i", "weight": 1.0},
            {"degree": "IV", "weight": 0.8},
            {"degree": "VII", "weight": 0.6},
            {"degree": "III", "weight": 0.4},
        ],
        "trans": {
            "i": {"IV": 0.45, "VII": 0.35, "III": 0.2},
            "IV": {"VII": 0.5, "i": 0.3, "III": 0.2},
            "VII": {"i": 0.5, "IV": 0.5},
            "III": {"VII": 0.5, "i": 0.5},
        },
    },
    "major_prog": {
        "pool": [
            {"degree": "I", "weight": 1.0},
            {"degree": "IV", "weight": 0.8},
            {"degree": "V", "weight": 0.7},
            {"degree": "vi", "weight": 0.6},
            {"degree": "ii", "weight": 0.5},
            {"degree": "iii", "weight": 0.3},
        ],
        "trans": {
            "I": {"IV": 0.3, "V": 0.3, "vi": 0.25, "ii": 0.15},
            "IV": {"V": 0.4, "I": 0.3, "ii": 0.3},
            "V": {"I": 0.6, "vi": 0.25, "IV": 0.15},
            "vi": {"IV": 0.4, "V": 0.3, "ii": 0.3},
            "ii": {"V": 0.5, "IV": 0.3, "I": 0.2},
            "iii": {"vi": 0.6, "IV": 0.4},
        },
    },
    "major_uplift": {
        "pool": [
            {"degree": "I", "weight": 1.0},
            {"degree": "V", "weight": 0.9},
            {"degree": "vi", "weight": 0.7},
            {"degree": "IV", "weight": 0.7},
        ],
        "trans": {
            "I": {"V": 0.45, "vi": 0.3, "IV": 0.25},
            "V": {"I": 0.55, "vi": 0.45},
            "vi": {"IV": 0.5, "V": 0.5},
            "IV": {"V": 0.4, "I": 0.6},
        },
    },
    "major_house": {
        "pool": [
            {"degree": "I", "weight": 1.0},
            {"degree": "IV", "weight": 0.8},
            {"degree": "V", "weight": 0.6},
            {"degree": "vi", "weight": 0.7},
            {"degree": "ii", "weight": 0.5},
        ],
        "trans": {
            "I": {"IV": 0.35, "V": 0.25, "vi": 0.25, "ii": 0.15},
            "IV": {"V": 0.4, "I": 0.4, "ii": 0.2},
            "V": {"I": 0.6, "vi": 0.4},
            "vi": {"IV": 0.45, "V": 0.3, "ii": 0.25},
            "ii": {"V": 0.6, "IV": 0.4},
        },
    },
}


# --------------------------------------------------------------------------- #
# Drum kits — per-section step strings for the main percussion track.
# --------------------------------------------------------------------------- #
KIT_FOUR_FLOOR = {
    "intro": {"hat": "...x...x...x...x"},
    "breakdown": {"hat": "...x...x...x...x"},
    "build": {"kick": "x...x...x...x...", "hat": "x.x.x.x.x.x.x.x.", "snare": "...............X"},
    "drop": {"kick": "x...x...x...x...", "snare": "....x.......x...", "hat": "x.x.x.x.x.x.x.x.", "hat_open": "...............X", "crash": "X..............."},
    "drop2": {"kick": "x...x...x...x...", "snare": "....x.......x...", "hat": "x.x.x.x.x.x.x.x.", "hat_open": "...............X", "crash": "X..............."},
    "outro": {"kick": "x...x...x...x...", "hat": "x.x.x.x.x.x.x.x."},
}

KIT_HALF_TIME = {
    "intro": {"kick": "x...............", "hat": "...x...x...x...x"},
    "buildup": {"kick": "x...x...x...x...", "hat": "..x...x...x...x.", "snare": "...............x"},
    "drop": {"kick": "x...........x...", "snare": "........x.......", "hat": "xxxxxxxxxxxxxxxx", "hat_open": "...........x....", "crash": "X..............."},
    "breakdown": {"kick": "x...............", "hat": "....x....x......"},
    "drop2": {"kick": "x...........x...", "snare": "........x.......", "hat": "xxxxxxxxxxxxxxxx", "hat_open": "...........x....", "crash": "X..............."},
    "outro": {"kick": "x...........x...", "snare": "........x.......", "hat": "...x...x...x...x"},
}

KIT_DNB = {
    "intro": {"kick": "x...............", "hat": ".x.x.x.x.x.x.x.x"},
    "breakdown": {"kick": "x...............", "hat": "x.x.x.x.x.x.x.x."},
    "build": {"kick": "x...x.x...x.....", "snare": "....x.......x...", "hat": "x.x.x.x.x.x.x.x."},
    "drop": {"kick": "x...x...x.x.....", "snare": "....x.......x...", "hat": "x.x.x.x.x.x.x.x.", "hat_open": "..........x.....", "crash": "X..............."},
    "drop2": {"kick": "x...x...x.x.....", "snare": "....x.......x...", "hat": "x.x.x.x.x.x.x.x.", "hat_open": "..........x.....", "crash": "X..............."},
    "outro": {"kick": "x...x...x.......", "hat": "x.x.x.x.x.x.x.x."},
}

KIT_TRAP = {
    "intro": {"kick": "x...............", "hat": ".x.x.x.x.x.x.x.x"},
    "buildup": {"kick": "x...x...x...x...", "clap": "........X.......", "hat": ".x.x.x.x.x.x.x.x"},
    "drop": {"kick": "x.........x.....", "clap": "........X.......", "hat": ".x.x.x.x.x.x.x.x", "hat_open": "........x.x.x.x.", "crash": "X..............."},
    "breakdown": {"kick": "x...............", "hat": "....x...x......."},
    "drop2": {"kick": "x.........x.....", "clap": "........X.......", "hat": ".x.x.x.x.x.x.x.x", "hat_open": "........x.x.x.x.", "crash": "X..............."},
    "outro": {"kick": "x...........x...", "hat": "x...x...x...x..."},
}

KIT_PSY = {
    "intro": {"kick": "x...x...x...x...", "hat": "....x...x...x..."},
    "breakdown": {"hat": "...x...x...x...x"},
    "build": {"kick": "x...x...x...x...", "hat": "x.x.x.x.x.x.x.x.", "snare": "...............x"},
    "drop": {"kick": "x...x...x...x...", "hat": "x.x.x.x.x.x.x.x.", "hat_open": ".......x........", "crash": "X..............."},
    "drop2": {"kick": "x...x...x...x...", "hat": "x.x.x.x.x.x.x.x.", "hat_open": ".......x........", "crash": "X..............."},
    "outro": {"kick": "x...x...x...x...", "hat": "x.x.x.x.x.x.x.x."},
}

KIT_HARDSTYLE = {
    "intro": {"kick": "x...x...x...x...", "hat": "....x...x...x..."},
    "breakdown": {"hat": "...x...x...x...x"},
    "build": {"kick": "x...x...x...x...", "hat": "x.x.x.x.x.x.x.x.", "snare": "...............x"},
    "drop": {"kick": "X...X...X...X...", "clap": "....x.......x...", "hat": "x.x.x.x.x.x.x.x.", "crash": "X..............."},
    "drop2": {"kick": "X...X...X...X...", "clap": "....x.......x...", "hat": "x.x.x.x.x.x.x.x.", "crash": "X..............."},
    "outro": {"kick": "x...x...x...x...", "hat": "x.x.x.x.x.x.x.x."},
}

KIT_GARAGE = {
    "intro": {"kick": "x...............", "hat": "x.x.x.x.x.x.x.x."},
    "breakdown": {"kick": "x...............", "hat": "x.x.x.x.x.x.x.x."},
    "build": {"kick": "x...x........x..", "clap": "....x.......x...", "hat": "x.x.x.x.x.x.x.x."},
    "drop": {"kick": "x...x........x..", "clap": "....x.......x...", "hat": "x.x.x.x.x.x.x.x.", "hat_open": ".......x.......x", "crash": "X..............."},
    "drop2": {"kick": "x...x........x..", "clap": "....x.......x...", "hat": "x.x.x.x.x.x.x.x.", "hat_open": ".......x.......x", "crash": "X..............."},
    "outro": {"kick": "x...x........x..", "hat": "x.x.x.x.x.x.x.x."},
}

KIT_DOWNTEMPO = {
    "intro": {"kick": "x...............", "hat": "...x.......x...."},
    "verse": {"kick": "x...x...........", "hat": "...x...x...x...."},
    "chorus": {"kick": "x...x...x...x...", "snare": "....x.......x...", "hat": "x.x.x...x.x.x..."},
    "outro": {"kick": "x...............", "hat": "...x.......x...."},
}


# --------------------------------------------------------------------------- #
# Layer (extra percussion) patterns per genre + fill behaviour.
# --------------------------------------------------------------------------- #
LAYER_FOUR_FLOOR = {
    "build": {"shaker": "x.x.x.x.x.x.x.x.", "tom": "..............x."},
    "drop": {"shaker": "x.x.x.x.x.x.x.x.", "perc": "....x...x...x...", "cymbal": "...............x"},
    "drop2": {"shaker": "x.x.x.x.x.x.x.x.", "perc": "....x...x...x..."},
}

LAYER_HALF_TIME = {
    "buildup": {"perc": "x...x...x...x...", "tom": "....x...x...x..."},
    "drop": {"perc": "....x...x.......", "tom": "...........x....", "cymbal": "...............x"},
    "drop2": {"perc": "....x...x.......", "tom": "...........x...."},
}

LAYER_DNB = {
    "build": {"shaker": "x.x.x.x.x.x.x.x.", "tom": "............x..."},
    "drop": {"shaker": "x.x.x.x.x.x.x.x.", "perc": "........x.......", "tom": "....x....x......"},
    "drop2": {"shaker": "x.x.x.x.x.x.x.x.", "perc": "........x......."},
}

LAYER_TRAP = {
    "buildup": {"shaker": ".x.x.x.x.x.x.x.x", "tom": "............x..."},
    "drop": {"shaker": ".x.x.x.x.x.x.x.x", "perc": "...........x....", "cymbal": "..............x."},
    "drop2": {"shaker": ".x.x.x.x.x.x.x.x", "perc": "...........x...."},
}

LAYER_PSY = {
    "build": {"shaker": "x.x.x.x.x.x.x.x.", "tom": "..............x."},
    "drop": {"shaker": "x.x.x.x.x.x.x.x.", "perc": "....x...x...x...", "cymbal": "...............x"},
    "drop2": {"shaker": "x.x.x.x.x.x.x.x.", "perc": "....x...x...x..."},
}

LAYER_GARAGE = {
    "build": {"shaker": "x.x.x.x.x.x.x.x."},
    "drop": {"shaker": "x.x.x.x.x.x.x.x.", "perc": "x.x...x.x...x.x.", "cymbal": "...............x"},
    "drop2": {"shaker": "x.x.x.x.x.x.x.x.", "perc": "x.x...x.x...x.x."},
}

LAYER_DOWNTEMPO = {
    "chorus": {"shaker": "x...x...x...x...", "tom": "...........x...."},
}

FILL_STD = {"enabled": True, "voices": ["perc", "tom"], "beats": 1}
FILL_GARAGE = {"enabled": True, "voices": ["shaker", "perc"], "beats": 1}
FILL_NONE = {"enabled": False, "voices": [], "beats": 1}


# --------------------------------------------------------------------------- #
# Shared defaults expanded into every genre config.
# --------------------------------------------------------------------------- #
ROLE_RANGES = {
    "bass": {"min": 28, "max": 55, "preferred": 36},
    "lead": {"min": 60, "max": 96, "preferred": 72},
    "pad": {"min": 48, "max": 84, "preferred": 60},
    "chord": {"min": 48, "max": 84, "preferred": 60},
    "arp": {"min": 60, "max": 96, "preferred": 72},
    "stab": {"min": 55, "max": 84, "preferred": 67},
    "sub_bass": {"min": 24, "max": 45, "preferred": 33},
    "counter_lead": {"min": 55, "max": 84, "preferred": 67},
}

ROLE_PARAMS = {
    "arp": {"order": "up", "note_length": 0.22, "octave_span": 2},
    "stab": {"duration_beat": 0.4, "velocity_boost": 8},
    "counter_lead": {"delay_beats": 1.0, "transpose": 0, "velocity_scale": 0.9},
    "sub_bass": {"follow": "root"},
}

LAYER_NOTES = {"perc": 60, "tom": 50, "cymbal": 51, "shaker": 70}
DRUM_NOTES = {"kick": 36, "snare": 38, "clap": 39, "hat": 42, "hat_open": 46, "crash": 49}


def default_intent(genre: str) -> dict:
    return {
        "bass": {"label": f"Bass ({genre})", "preset": "sub_bass / analog_synth"},
        "sub_bass": {"label": f"Sub Bass ({genre})", "preset": "sub_bass_low / sine"},
        "lead": {"label": f"Lead ({genre})", "preset": "lead_synth / saw_stack"},
        "arp": {"label": f"Arp ({genre})", "preset": "pluck_synth / arp_synth"},
        "stab": {"label": f"Stab ({genre})", "preset": "chord_stab / detuned_synth"},
        "counter_lead": {"label": f"Counter Lead ({genre})", "preset": "lead_synth_2 / square"},
        "pad": {"label": f"Pad ({genre})", "preset": "pad_synth / dark_pad"},
        "chord": {"label": f"Chord ({genre})", "preset": "chord_synth / rhodes"},
        "drum": {"label": f"Drums ({genre})", "preset": "electronic_kit"},
        "drum_layers": {"label": f"Drum Layers - Percussion ({genre})", "preset": "electronic_percussion"},
    }


def merge(a: dict, b: dict) -> dict:
    out = dict(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = merge(out[k], v)
        else:
            out[k] = v
    return out


def _sections(template, bars, density, register, velocity, tempo=None):
    out = {
        "section_template": template,
        "section_bars": {s: b for s, b in zip(template, bars)},
        "section_density": density,
        "section_register": register,
        "section_velocity": velocity,
    }
    if tempo:
        out["section_tempo"] = tempo
    return out


# --------------------------------------------------------------------------- #
# Per-genre knowledge (the "AI dataset"). Each genre keeps the musical
# character that identifies it; everything else is filled by the builder.
# --------------------------------------------------------------------------- #
GENRES = [
    {
        "genre": "techno",
        "bpm": 133, "key": "d", "mode": "minor",
        "scale": ["dorian", "natural_minor", "phrygian"],
        "chords": "dorian",
        "patterns": {"bass": "offbeat", "lead": "syncopated", "arp": "rolling",
                     "stab": "offbeat", "sub": "kicker", "counter": "sync"},
        "sections": _sections(
            ["intro", "breakdown", "build", "drop", "drop2", "outro"],
            [2, 2, 4, 4, 4, 2],
            {"intro": 0.5, "breakdown": 0.35, "build": 0.7, "drop": 1.0, "drop2": 1.0, "outro": 0.4},
            {"intro": 0, "breakdown": 1, "build": 0, "drop": 0, "drop2": 0, "outro": 0},
            {"intro": 74, "breakdown": 80, "build": 90, "drop": 104, "drop2": 104, "outro": 72},
        ),
        "swing": {"resolution": 16, "amount": 0.05},
        "automation": {"enabled": True, "cc74_range": [30, 122], "cc11": True},
        "drum": KIT_FOUR_FLOOR,
        "layers": LAYER_FOUR_FLOOR,
        "fills": FILL_STD,
        "role_params": {"arp": {"order": "down", "note_length": 0.2}},
        "ranges": {"bass": {"min": 28, "max": 55, "preferred": 38}, "lead": {"min": 60, "max": 92, "preferred": 70}},
        "intent": {
            "bass": {"label": "Bass - Rolling (Techno)", "preset": "acid_bass / 303"},
            "lead": {"label": "Lead - Stab (Techno)", "preset": "stab_synth"},
            "arp": {"label": "Arp - Percussive (Techno)", "preset": "pluck_synth"},
            "pad": {"label": "Pad - Texture (Techno)", "preset": "dark_pad"},
            "drum": {"label": "Drums - 4x4 (Techno)", "preset": "909_kit"},
        },
    },
    {
        "genre": "trance",
        "bpm": 138, "key": "a", "mode": "minor",
        "scale": ["natural_minor", "major"],
        "chords": "minor_emotional",
        "patterns": {"bass": "four_floor", "lead": "legato", "arp": "rolling",
                     "stab": "eighth", "sub": "kicker", "counter": "answer"},
        "sections": _sections(
            ["intro", "breakdown", "build", "drop", "drop2", "outro"],
            [2, 4, 4, 4, 4, 2],
            {"intro": 0.3, "breakdown": 0.3, "build": 0.7, "drop": 1.0, "drop2": 1.0, "outro": 0.35},
            {"intro": 0, "breakdown": 1, "build": 0, "drop": 0, "drop2": 0, "outro": 0},
            {"intro": 72, "breakdown": 76, "build": 88, "drop": 102, "drop2": 102, "outro": 70},
        ),
        "swing": {"resolution": 16, "amount": 0.04},
        "automation": {"enabled": True, "cc74_range": [25, 125], "cc11": True},
        "drum": KIT_FOUR_FLOOR,
        "layers": LAYER_FOUR_FLOOR,
        "fills": FILL_STD,
        "role_params": {"arp": {"order": "up", "note_length": 0.16}},
        "ranges": {"lead": {"min": 62, "max": 100, "preferred": 76}, "arp": {"min": 62, "max": 100, "preferred": 76}},
        "intent": {
            "bass": {"label": "Bass - Driving (Trance)", "preset": "acid_bass / reese"},
            "lead": {"label": "Lead - Supersaw (Trance)", "preset": "supersaw_stack"},
            "arp": {"label": "Arp - Roll (Trance)", "preset": "pluck_synth"},
            "drum": {"label": "Drums - 4x4 (Trance)", "preset": "trance_kit"},
        },
    },
    {
        "genre": "progressive_house",
        "bpm": 126, "key": "f", "mode": "major",
        "scale": ["major", "dorian", "natural_minor"],
        "chords": "major_uplift",
        "patterns": {"bass": "four_floor", "lead": "legato", "arp": "straight",
                     "stab": "quarter", "sub": "kicker", "counter": "answer"},
        "sections": _sections(
            ["intro", "breakdown", "build", "drop", "drop2", "outro"],
            [2, 4, 8, 4, 4, 2],
            {"intro": 0.3, "breakdown": 0.25, "build": 0.7, "drop": 1.0, "drop2": 1.0, "outro": 0.3},
            {"intro": 0, "breakdown": 1, "build": 0, "drop": 0, "drop2": 0, "outro": 0},
            {"intro": 72, "breakdown": 76, "build": 86, "drop": 100, "drop2": 100, "outro": 70},
        ),
        "swing": {"resolution": 8, "amount": 0.1},
        "automation": {"enabled": True, "cc74_range": [25, 120], "cc11": True},
        "drum": KIT_FOUR_FLOOR,
        "layers": LAYER_FOUR_FLOOR,
        "fills": FILL_STD,
        "role_params": {"arp": {"order": "updown", "note_length": 0.24}},
        "ranges": {"stab": {"min": 55, "max": 88, "preferred": 72}, "chord": {"min": 48, "max": 84, "preferred": 62}},
        "intent": {
            "bass": {"label": "Bass - Deep (Progressive House)", "preset": "deep_bass"},
            "lead": {"label": "Lead - Melodic (Progressive House)", "preset": "pluck_lead"},
            "arp": {"label": "Arp - Pulse (Progressive House)", "preset": "pluck_synth"},
            "drum": {"label": "Drums - 4x4 (Progressive House)", "preset": "prog_house_kit"},
        },
    },
    {
        "genre": "big_room",
        "bpm": 128, "key": "a", "mode": "minor",
        "scale": ["natural_minor", "phrygian"],
        "chords": "minor_emotional",
        "patterns": {"bass": "four_floor", "lead": "staccato", "arp": "straight",
                     "stab": "offbeat", "sub": "kicker", "counter": "answer"},
        "sections": _sections(
            ["intro", "buildup", "drop", "breakdown", "drop2", "outro"],
            [2, 4, 4, 2, 4, 2],
            {"intro": 0.3, "buildup": 0.6, "drop": 1.0, "breakdown": 0.2, "drop2": 1.0, "outro": 0.3},
            {"intro": 0, "buildup": 0, "drop": 0, "breakdown": 1, "drop2": 0, "outro": 0},
            {"intro": 70, "buildup": 84, "drop": 102, "breakdown": 76, "drop2": 102, "outro": 68},
        ),
        "swing": {"resolution": 16, "amount": 0.04},
        "automation": {"enabled": True, "cc74_range": [20, 127], "cc11": True},
        "drum": KIT_FOUR_FLOOR,
        "layers": LAYER_FOUR_FLOOR,
        "fills": FILL_STD,
        "role_params": {"stab": {"duration_beat": 0.42, "velocity_boost": 12}},
        "ranges": {"stab": {"min": 55, "max": 88, "preferred": 72}},
        "intent": {
            "bass": {"label": "Bass - Rumble (Big Room)", "preset": "rumble_bass"},
            "stab": {"label": "Stab - Massive (Big Room)", "preset": "supersaw_stab"},
            "lead": {"label": "Lead - Ho (Big Room)", "preset": "hoarse_saw"},
            "drum": {"label": "Drums - 4x4 (Big Room)", "preset": "bigroom_kit"},
        },
    },
    {
        "genre": "electro_house",
        "bpm": 128, "key": "e", "mode": "minor",
        "scale": ["natural_minor", "dorian"],
        "chords": "minor_dark",
        "patterns": {"bass": "syncopated", "lead": "staccato", "arp": "broken",
                     "stab": "offbeat", "sub": "sync", "counter": "sync"},
        "sections": _sections(
            ["intro", "buildup", "drop", "breakdown", "drop2", "outro"],
            [2, 4, 4, 2, 4, 2],
            {"intro": 0.3, "buildup": 0.6, "drop": 1.0, "breakdown": 0.2, "drop2": 1.0, "outro": 0.3},
            {"intro": 0, "buildup": 0, "drop": 0, "breakdown": 1, "drop2": 0, "outro": 0},
            {"intro": 72, "buildup": 84, "drop": 100, "breakdown": 76, "drop2": 100, "outro": 70},
        ),
        "swing": {"resolution": 8, "amount": 0.12},
        "automation": {"enabled": True, "cc74_range": [30, 120], "cc11": True},
        "drum": KIT_FOUR_FLOOR,
        "layers": LAYER_FOUR_FLOOR,
        "fills": FILL_STD,
        "role_params": {"arp": {"order": "down", "note_length": 0.2}},
        "ranges": {"bass": {"min": 28, "max": 60, "preferred": 40}},
        "intent": {
            "bass": {"label": "Bass - Groovy (Electro House)", "preset": "electro_bass"},
            "stab": {"label": "Stab - Detuned (Electro House)", "preset": "detuned_stab"},
            "drum": {"label": "Drums - 4x4 (Electro House)", "preset": "electro_kit"},
        },
    },
    {
        "genre": "house",
        "bpm": 126, "key": "f", "mode": "major",
        "scale": ["major", "dorian"],
        "chords": "major_prog",
        "patterns": {"bass": "four_floor", "lead": "staccato", "arp": "straight",
                     "stab": "quarter", "sub": "kicker", "counter": "answer"},
        "sections": _sections(
            ["intro", "breakdown", "build", "drop", "outro"],
            [2, 4, 4, 4, 2],
            {"intro": 0.3, "breakdown": 0.25, "build": 0.6, "drop": 0.85, "outro": 0.3},
            {"intro": 0, "breakdown": 1, "build": 0, "drop": 0, "outro": 0},
            {"intro": 72, "breakdown": 78, "build": 88, "drop": 100, "outro": 70},
        ),
        "swing": {"resolution": 8, "amount": 0.22},
        "automation": {"enabled": True, "cc74_range": [25, 118], "cc11": True},
        "drum": KIT_FOUR_FLOOR,
        "layers": LAYER_FOUR_FLOOR,
        "fills": FILL_STD,
        "role_params": {"stab": {"duration_beat": 0.35}},
        "ranges": {"stab": {"min": 52, "max": 84, "preferred": 67}},
        "intent": {
            "bass": {"label": "Bass - Deep House", "preset": "deep_bass / analog_synth"},
            "lead": {"label": "Lead - Stab (House)", "preset": "stab_pluck / chord_stab"},
            "pad": {"label": "Pad - Warm (House)", "preset": "warm_pad / string_pad"},
            "chord": {"label": "Chord - Warm Stabs (House)", "preset": "chord_stabs / rhodes"},
            "drum": {"label": "Drums - 4 on Floor (House)", "preset": "house_kit / 909_kit"},
        },
    },
    {
        "genre": "dubstep",
        "bpm": 140, "key": "a", "mode": "minor",
        "scale": ["natural_minor", "phrygian"],
        "chords": "minor_emotional",
        "patterns": {"bass": "syncopated", "lead": "staccato", "arp": "broken",
                     "stab": "quarter", "sub": "sync", "counter": "sync"},
        "sections": _sections(
            ["intro", "buildup", "drop", "breakdown", "drop2", "outro"],
            [2, 4, 4, 2, 4, 2],
            {"intro": 0.3, "buildup": 0.6, "drop": 1.0, "breakdown": 0.2, "drop2": 1.0, "outro": 0.3},
            {"intro": 0, "buildup": 0, "drop": 0, "breakdown": 1, "drop2": 0, "outro": 0},
            {"intro": 70, "buildup": 85, "drop": 100, "breakdown": 78, "drop2": 100, "outro": 68},
            tempo={"breakdown": 0.5},
        ),
        "modulations": [{"section": "drop2", "semitones": 1}],
        "swing": {"resolution": 16, "amount": 0.12},
        "automation": {"enabled": True, "cc74_range": [30, 125], "cc11": True},
        "drum": KIT_HALF_TIME,
        "layers": LAYER_HALF_TIME,
        "fills": FILL_STD,
        "role_params": {"arp": {"order": "updown", "note_length": 0.2}},
        "ranges": {"sub_bass": {"min": 24, "max": 45, "preferred": 33}, "bass": {"min": 28, "max": 55, "preferred": 36}},
        "intent": {
            "bass": {"label": "Bass - Wobble Style (Dubstep)", "preset": "sub_bass / wobble_synth"},
            "lead": {"label": "Lead - Pluck (Dubstep)", "preset": "pluck_synth / saw_stack"},
            "pad": {"label": "Pad - Dark Texture (Dubstep)", "preset": "dark_pad / detuned_pad"},
            "chord": {"label": "Chord - Dark Stabs (Dubstep)", "preset": "chord_stabs / detuned_synth"},
            "drum": {"label": "Drums - Half-Time (Dubstep)", "preset": "dubstep_kit / sidechain_kick"},
        },
    },
    {
        "genre": "drum_and_bass",
        "bpm": 172, "key": "d", "mode": "minor",
        "scale": ["natural_minor", "dorian"],
        "chords": "minor_dark",
        "patterns": {"bass": "rolling", "lead": "syncopated", "arp": "broken",
                     "stab": "eighth", "sub": "sync", "counter": "sync"},
        "sections": _sections(
            ["intro", "breakdown", "build", "drop", "drop2", "outro"],
            [2, 2, 4, 4, 4, 2],
            {"intro": 0.3, "breakdown": 0.3, "build": 0.6, "drop": 1.0, "drop2": 1.0, "outro": 0.35},
            {"intro": 0, "breakdown": 1, "build": 0, "drop": 0, "drop2": 0, "outro": 0},
            {"intro": 72, "breakdown": 78, "build": 88, "drop": 104, "drop2": 104, "outro": 72},
        ),
        "swing": {"resolution": 16, "amount": 0.05},
        "automation": {"enabled": True, "cc74_range": [30, 120], "cc11": True},
        "drum": KIT_DNB,
        "layers": LAYER_DNB,
        "fills": FILL_STD,
        "role_params": {"arp": {"order": "down", "note_length": 0.12}},
        "ranges": {"bass": {"min": 24, "max": 60, "preferred": 36}, "lead": {"min": 60, "max": 96, "preferred": 72}},
        "intent": {
            "bass": {"label": "Bass - Reese (DnB)", "preset": "reese_bass"},
            "lead": {"label": "Lead - Stab (DnB)", "preset": "neuro_stab"},
            "drum": {"label": "Drums - Breakbeat (DnB)", "preset": "dnb_kit / amens"},
        },
    },
    {
        "genre": "trap",
        "bpm": 140, "key": "b", "mode": "minor",
        "scale": ["phrygian", "natural_minor"],
        "chords": "minor_phrygian",
        "patterns": {"bass": "syncopated", "lead": "syncopated", "arp": "broken",
                     "stab": "offbeat", "sub": "kicker", "counter": "sync"},
        "sections": _sections(
            ["intro", "buildup", "drop", "breakdown", "drop2", "outro"],
            [2, 4, 4, 2, 4, 2],
            {"intro": 0.3, "buildup": 0.5, "drop": 0.9, "breakdown": 0.2, "drop2": 0.9, "outro": 0.3},
            {"intro": 0, "buildup": 0, "drop": 0, "breakdown": 1, "drop2": 0, "outro": 0},
            {"intro": 70, "buildup": 82, "drop": 98, "breakdown": 74, "drop2": 98, "outro": 68},
        ),
        "swing": {"resolution": 16, "amount": 0.08},
        "automation": {"enabled": True, "cc74_range": [20, 124], "cc11": True},
        "drum": KIT_TRAP,
        "layers": LAYER_TRAP,
        "fills": FILL_STD,
        "role_params": {"arp": {"order": "down", "note_length": 0.16}},
        "ranges": {"sub_bass": {"min": 24, "max": 45, "preferred": 33}, "lead": {"min": 60, "max": 92, "preferred": 69}},
        "intent": {
            "bass": {"label": "Bass - Sub (Trap)", "preset": "808_sub"},
            "lead": {"label": "Lead - Dark (Trap)", "preset": "dark_pluck"},
            "drum": {"label": "Drums - Trap Kit", "preset": "trap_kit / 808_kit"},
        },
    },
    {
        "genre": "future_bass",
        "bpm": 150, "key": "f", "mode": "major",
        "scale": ["major", "natural_minor"],
        "chords": "major_uplift",
        "patterns": {"bass": "four_floor", "lead": "melodic", "arp": "straight",
                     "stab": "eighth", "sub": "kicker", "counter": "answer"},
        "sections": _sections(
            ["intro", "buildup", "drop", "breakdown", "drop2", "outro"],
            [2, 4, 4, 2, 4, 2],
            {"intro": 0.3, "buildup": 0.6, "drop": 1.0, "breakdown": 0.25, "drop2": 1.0, "outro": 0.3},
            {"intro": 0, "buildup": 0, "drop": 0, "breakdown": 1, "drop2": 0, "outro": 0},
            {"intro": 72, "buildup": 84, "drop": 102, "breakdown": 76, "drop2": 102, "outro": 70},
        ),
        "modulations": [{"section": "drop2", "semitones": 1}],
        "swing": {"resolution": 16, "amount": 0.06},
        "automation": {"enabled": True, "cc74_range": [25, 125], "cc11": True},
        "drum": KIT_FOUR_FLOOR,
        "layers": LAYER_FOUR_FLOOR,
        "fills": FILL_STD,
        "role_params": {"stab": {"duration_beat": 0.34}},
        "ranges": {"stab": {"min": 57, "max": 88, "preferred": 74}},
        "intent": {
            "bass": {"label": "Bass - Pump (Future Bass)", "preset": "sidechain_bass"},
            "stab": {"label": "Stab - Supersaw (Future Bass)", "preset": "supersaw_stab"},
            "lead": {"label": "Lead - Emotional (Future Bass)", "preset": "bright_lead"},
            "drum": {"label": "Drums - 4x4 (Future Bass)", "preset": "future_bass_kit"},
        },
    },
    {
        "genre": "hardstyle",
        "bpm": 150, "key": "e", "mode": "minor",
        "scale": ["natural_minor", "phrygian"],
        "chords": "minor_emotional",
        "patterns": {"bass": "offbeat", "lead": "legato", "arp": "straight",
                     "stab": "quarter", "sub": "kicker", "counter": "answer"},
        "sections": _sections(
            ["intro", "breakdown", "build", "drop", "drop2", "outro"],
            [2, 2, 4, 4, 4, 2],
            {"intro": 0.3, "breakdown": 0.3, "build": 0.6, "drop": 1.0, "drop2": 1.0, "outro": 0.35},
            {"intro": 0, "breakdown": 1, "build": 0, "drop": 0, "drop2": 0, "outro": 0},
            {"intro": 72, "breakdown": 76, "build": 86, "drop": 104, "drop2": 104, "outro": 72},
        ),
        "swing": {"resolution": 16, "amount": 0.04},
        "automation": {"enabled": True, "cc74_range": [30, 126], "cc11": True},
        "drum": KIT_HARDSTYLE,
        "layers": LAYER_FOUR_FLOOR,
        "fills": FILL_STD,
        "role_params": {"arp": {"order": "up", "note_length": 0.2}},
        "ranges": {"bass": {"min": 28, "max": 55, "preferred": 36}},
        "intent": {
            "bass": {"label": "Bass - Reverse (Hardstyle)", "preset": "reverse_bass"},
            "lead": {"label": "Lead - Distorted (Hardstyle)", "preset": "hardstyle_lead"},
            "drum": {"label": "Drums - Hardstyle Kit", "preset": "hardstyle_kit"},
        },
    },
    {
        "genre": "psytrance",
        "bpm": 145, "key": "d", "mode": "minor",
        "scale": ["phrygian", "dorian"],
        "chords": "minor_phrygian",
        "patterns": {"bass": "rolling", "lead": "syncopated", "arp": "rolling",
                     "stab": "offbeat", "sub": "kicker", "counter": "sync"},
        "sections": _sections(
            ["intro", "breakdown", "build", "drop", "drop2", "outro"],
            [2, 2, 4, 4, 4, 2],
            {"intro": 0.4, "breakdown": 0.3, "build": 0.7, "drop": 1.0, "drop2": 1.0, "outro": 0.4},
            {"intro": 0, "breakdown": 1, "build": 0, "drop": 0, "drop2": 0, "outro": 0},
            {"intro": 74, "breakdown": 78, "build": 90, "drop": 104, "drop2": 104, "outro": 74},
        ),
        "swing": {"resolution": 16, "amount": 0.03},
        "automation": {"enabled": True, "cc74_range": [25, 124], "cc11": True},
        "drum": KIT_PSY,
        "layers": LAYER_PSY,
        "fills": FILL_STD,
        "role_params": {"arp": {"order": "up", "note_length": 0.14}},
        "ranges": {"bass": {"min": 24, "max": 55, "preferred": 33}, "lead": {"min": 60, "max": 96, "preferred": 72}},
        "intent": {
            "bass": {"label": "Bass - Squelch (Psytrance)", "preset": "psy_bass / 303"},
            "lead": {"label": "Lead - Acid (Psytrance)", "preset": "acid_lead"},
            "arp": {"label": "Arp - Twisted (Psytrance)", "preset": "psy_pluck"},
            "drum": {"label": "Drums - 4x4 (Psytrance)", "preset": "psy_kit"},
        },
    },
    {
        "genre": "uk_garage",
        "bpm": 134, "key": "g", "mode": "minor",
        "scale": ["dorian", "natural_minor"],
        "chords": "dorian",
        "patterns": {"bass": "offbeat", "lead": "syncopated", "arp": "offbeat",
                     "stab": "offbeat", "sub": "sync", "counter": "sync"},
        "sections": _sections(
            ["intro", "breakdown", "build", "drop", "drop2", "outro"],
            [2, 2, 4, 4, 4, 2],
            {"intro": 0.3, "breakdown": 0.25, "build": 0.6, "drop": 0.9, "drop2": 0.9, "outro": 0.3},
            {"intro": 0, "breakdown": 1, "build": 0, "drop": 0, "drop2": 0, "outro": 0},
            {"intro": 72, "breakdown": 76, "build": 86, "drop": 100, "drop2": 100, "outro": 70},
        ),
        "swing": {"resolution": 16, "amount": 0.18},
        "automation": {"enabled": True, "cc74_range": [28, 118], "cc11": True},
        "drum": KIT_GARAGE,
        "layers": LAYER_GARAGE,
        "fills": FILL_GARAGE,
        "role_params": {"arp": {"order": "down", "note_length": 0.18}},
        "ranges": {"bass": {"min": 28, "max": 55, "preferred": 36}},
        "intent": {
            "bass": {"label": "Bass - 2-Step (UK Garage)", "preset": "garage_bass"},
            "lead": {"label": "Lead - Shuffled (UK Garage)", "preset": "vocal_pluck"},
            "drum": {"label": "Drums - 2-Step (UK Garage)", "preset": "garage_kit"},
        },
    },
    {
        "genre": "downtempo",
        "bpm": 90, "key": "d", "mode": "minor",
        "scale": ["major", "natural_minor", "dorian"],
        "chords": "major_uplift",
        "patterns": {"bass": "syncopated", "lead": "legato", "arp": "straight",
                     "stab": "quarter", "sub": "whole", "counter": "answer"},
        "sections": _sections(
            ["intro", "verse", "chorus", "outro"],
            [2, 4, 4, 2],
            {"intro": 0.25, "verse": 0.5, "chorus": 0.8, "outro": 0.25},
            {"intro": 0, "verse": 0, "chorus": 0, "outro": 0},
            {"intro": 68, "verse": 80, "chorus": 94, "outro": 66},
        ),
        "swing": {"resolution": 8, "amount": 0.08},
        "automation": {"enabled": True, "cc74_range": [20, 110], "cc11": True},
        "drum": KIT_DOWNTEMPO,
        "layers": LAYER_DOWNTEMPO,
        "fills": FILL_NONE,
        "role_params": {"arp": {"order": "updown", "note_length": 0.3}},
        "intent": {
            "bass": {"label": "Bass - Chill (Downtempo)", "preset": "soft_bass"},
            "lead": {"label": "Lead - Dreamy (Downtempo)", "preset": "soft_lead"},
            "pad": {"label": "Pad - Ambient (Downtempo)", "preset": "ambient_pad"},
            "drum": {"label": "Drums - Sparse (Downtempo)", "preset": "lofi_kit"},
        },
    },
    {
        "genre": "generic",
        "bpm": 120, "key": "c", "mode": "major",
        "scale": ["major", "natural_minor"],
        "chords": "major_prog",
        "patterns": {"bass": "four_floor", "lead": "melodic", "arp": "straight",
                     "stab": "quarter", "sub": "whole", "counter": "answer"},
        "sections": _sections(
            ["intro", "breakdown", "build", "drop", "drop2", "outro"],
            [2, 2, 4, 4, 4, 2],
            {"intro": 0.3, "breakdown": 0.25, "build": 0.6, "drop": 0.9, "drop2": 0.9, "outro": 0.3},
            {"intro": 0, "breakdown": 1, "build": 0, "drop": 0, "drop2": 0, "outro": 0},
            {"intro": 72, "breakdown": 76, "build": 86, "drop": 100, "drop2": 100, "outro": 70},
        ),
        "swing": {"resolution": 8, "amount": 0.1},
        "automation": {"enabled": True, "cc74_range": [20, 120], "cc11": True},
        "drum": KIT_FOUR_FLOOR,
        "layers": LAYER_FOUR_FLOOR,
        "fills": FILL_STD,
        "intent": {
            "bass": {"label": "Bass (Generic)", "preset": "generic_bass"},
            "lead": {"label": "Lead (Generic)", "preset": "generic_lead"},
            "pad": {"label": "Pad (Generic)", "preset": "generic_pad"},
            "chord": {"label": "Chord (Generic)", "preset": "generic_chord"},
            "drum": {"label": "Drums (Generic)", "preset": "generic_kit"},
        },
    },
]


def build_config(kb: dict) -> dict:
    chords = CHORDS[kb["chords"]]
    pat = kb["patterns"]
    cfg = {
        "genre": kb["genre"],
        "default_bpm": kb["bpm"],
        "time_signature": [4, 4],
        "default_key": kb["key"],
        "default_mode": kb["mode"],
        "scale_pool": kb["scale"],
        "chord_pool": chords["pool"],
        "transition_matrix": chords["trans"],
        "role_ranges": merge(ROLE_RANGES, kb.get("ranges") or {}),
        "role_params": merge(ROLE_PARAMS, kb.get("role_params") or {}),
        "bass_patterns": BASS[pat["bass"]],
        "lead_patterns": LEAD[pat["lead"]],
        "arp_patterns": ARP[pat["arp"]],
        "stab_patterns": STAB[pat["stab"]],
        "sub_bass_patterns": SUB[pat["sub"]],
        "counter_lead_patterns": COUNTER[pat["counter"]],
        **kb["sections"],
        "automation": kb["automation"],
        "humanize": {"max_timing_ms": 25, "velocity_jitter": 4},
        "swing": kb["swing"],
        "selector_weights": {"dissonance": 1.0, "repetition": 1.5, "voice_leading": 1.0},
        "drum_patterns": {
            "notes": DRUM_NOTES,
            "patterns": kb["drum"],
            "layer_notes": LAYER_NOTES,
            "layers": kb["layers"],
            "fills": kb["fills"],
        },
        "instrument_intent": merge(default_intent(kb["genre"]), kb.get("intent") or {}),
    }
    if kb.get("modulations"):
        cfg["modulations"] = kb["modulations"]
    return cfg


def main() -> int:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from engine.config_loader import validate_genre_config

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for kb in GENRES:
        cfg = build_config(kb)
        validate_genre_config(cfg)
        path = OUT_DIR / f"{kb['genre']}.json"
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=2, ensure_ascii=False)
        written.append(kb["genre"])
    print(f"generated {len(written)} genre configs: {', '.join(written)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
