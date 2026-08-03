"""Shared music theory helpers.

Wraps music21 so the rest of the engine talks in simple primitives
(key root + mode, scale name, pitch classes, Roman numeral strings).
"""

from typing import Set

from music21 import key as key21
from music21 import roman
from music21 import scale


SCALE_FACTORIES = {
    "major": scale.MajorScale,
    "natural_minor": scale.MinorScale,
    "harmonic_minor": scale.HarmonicMinorScale,
    "melodic_minor": scale.MelodicMinorScale,
    "phrygian": scale.PhrygianScale,
    "dorian": scale.DorianScale,
    "aeolian": scale.MinorScale,
}


def get_scale_pitch_classes(
    key_root: str, mode: str, scale_name: str = None
) -> Set[int]:
    """Return the set of pitch classes (0-11) of the active scale.

    If ``scale_name`` is unknown, falls back to natural minor when the
    mode is minor and major otherwise.
    """
    name = (scale_name or "").lower()
    factory = SCALE_FACTORIES.get(name)
    if factory is None:
        factory = (
            SCALE_FACTORIES["natural_minor"]
            if mode == "minor"
            else SCALE_FACTORIES["major"]
        )
    sc = factory(key_root)
    return {p.pitchClass for p in sc.getPitches()}


def roman_chord(key_root: str, mode: str, degree: str) -> "roman.RomanNumeral":
    """Parse a Roman numeral degree (e.g. ``i``, ``VI``, ``VII``) in a key."""
    return roman.RomanNumeral(degree, key21.Key(key_root, mode))


def snap_pitch_to_scale(pitch: int, scale_pcs: Set[int]) -> int:
    """Move a pitch to the nearest pitch class present in the scale.

    Musical assumption: chromatic alteration is allowed only as a
    deliberate decision upstream; here we enforce the scale constraint
    (FR-3) by snapping to the closest scale tone.
    """
    pc = pitch % 12
    if pc in scale_pcs:
        return pitch
    best = min(scale_pcs, key=lambda s: min((s - pc) % 12, (pc - s) % 12))
    diff = (best - pc) % 12
    if diff > 6:
        diff -= 12
    return pitch + diff
