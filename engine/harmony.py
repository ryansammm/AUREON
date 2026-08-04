"""Layer 1 — Harmonic Engine.

Generates a per-bar chord progression using the genre config's weighted
chord pool + transition matrix (a hand-weighted Markov chain, not uniform
random). Chords are parsed via music21 Roman numerals so they are valid
in the requested key.

Musical assumptions:
- Progression is generated as one chord per bar.
- The transition matrix probabilities do not need to sum to 1; they are
  normalized at selection time.
"""

import random
from typing import List, Optional, Set

from .models import ChordBar, VoicingCandidate
from .music_utils import roman_chord

_CROSSING_PENALTY = 3.0
_OOR_PENALTY = 5.0
_NUM_CANDIDATES = 8


def _pitches_for_pc(pc: int, low: int, high: int) -> List[int]:
    """Return all MIDI pitches for *pc* within [low, high]."""
    out = []
    p = pc
    while p <= high:
        if p >= low:
            out.append(p)
        p += 12
    return out


def generate_voicing_candidates(
    chord: ChordBar,
    role_range: dict,
    num_candidates: int = _NUM_CANDIDATES,
) -> List[VoicingCandidate]:
    """Generate candidate voicings for a chord within a role's register.

    Each candidate is a different inversion / octave arrangement of the
    chord's pitch classes, respecting the role's min/max MIDI range.
    """
    pcs = sorted(set(chord.pitch_classes))
    if not pcs:
        return []

    all_pitches = [_pitches_for_pc(pc, role_range["min"], role_range["max"]) for pc in pcs]
    if any(len(p) == 0 for p in all_pitches):
        return []

    candidates: List[VoicingCandidate] = []

    # Root position: each PC at its lowest valid pitch
    rp = [p[0] for p in all_pitches]
    candidates.append(VoicingCandidate(
        pitches=sorted(rp),
        inversion=0,
        register_span=max(rp) - min(rp),
    ))

    # First inversion: shift lowest voice up an octave
    if len(pcs) >= 3:
        fi = list(rp)
        fi[0] = fi[0] + 12 if fi[0] + 12 <= role_range["max"] else fi[0]
        candidates.append(VoicingCandidate(
            pitches=sorted(fi),
            inversion=1,
            register_span=max(fi) - min(fi),
        ))

    # Second inversion
    if len(pcs) >= 3:
        si = list(rp)
        si[1] = si[1] + 12 if si[1] + 12 <= role_range["max"] else si[1]
        candidates.append(VoicingCandidate(
            pitches=sorted(si),
            inversion=2,
            register_span=max(si) - min(si),
        ))

    # Spread voicings: spread voices across wider register
    for spread in range(1, min(3, len(pcs))):
        sv = list(rp)
        for i in range(spread, len(sv)):
            if i < len(all_pitches):
                high_opts = [p for p in all_pitches[i] if p > sv[i - 1] + 2]
                if high_opts:
                    sv[i] = high_opts[0]
        candidates.append(VoicingCandidate(
            pitches=sorted(sv),
            inversion=0,
            register_span=max(sv) - min(sv),
        ))

    # Close-position variants with octave shifts
    for i in range(len(pcs)):
        for shift in (-12, 12):
            v = list(rp)
            v[i] += shift
            if role_range["min"] <= v[i] <= role_range["max"]:
                candidates.append(VoicingCandidate(
                    pitches=sorted(v),
                    inversion=i,
                    register_span=max(v) - min(v),
                ))

    # Deduplicate by pitch set
    seen: set = set()
    unique: List[VoicingCandidate] = []
    for c in candidates:
        key = tuple(c.pitches)
        if key not in seen:
            seen.add(key)
            unique.append(c)

    return unique[:num_candidates]


def voice_leading_cost(
    voicing_a: List[int],
    voicing_b: List[int],
    role_range: dict,
) -> float:
    """Score the voice-leading cost between two consecutive voicings.

    Lower is better. Components:
    - Sum of minimum pitch movement for each voice in voicing_b
    - Penalty for voice crossing (a lower-index voice ending higher)
    - Penalty for notes outside the role's register range
    """
    if not voicing_a or not voicing_b:
        return 0.0

    cost = 0.0

    # Match each voice in B to its closest voice in A
    matched_a = list(voicing_a)
    movement = 0.0
    for pitch_b in sorted(voicing_b):
        if matched_a:
            best_idx = min(range(len(matched_a)), key=lambda i: abs(pitch_b - matched_a[i]))
            movement += abs(pitch_b - matched_a[best_a := best_idx])
            matched_a.pop(best_a)
        else:
            # Extra voice in B — cost its distance from nearest A voice
            movement += min(abs(pitch_b - a) for a in voicing_a)

    cost += movement

    # Voice crossing penalty
    sorted_b = sorted(voicing_b)
    for i in range(len(sorted_b) - 1):
        if sorted_b[i] > sorted_b[i + 1]:
            cost += _CROSSING_PENALTY

    # Out-of-register penalty
    for p in voicing_b:
        if p < role_range["min"] or p > role_range["max"]:
            cost += _OOR_PENALTY

    return cost


def voice_chord(
    chord: ChordBar,
    previous_voicing: Optional[List[int]],
    role_range: dict,
    num_candidates: int = _NUM_CANDIDATES,
) -> VoicingCandidate:
    """Select the best voicing for a chord given the previous voicing.

    Generates N candidate inversions/voicings within the role's register
    range and selects the one that minimizes the voice-leading cost against
    the previous chord's voicing.
    """
    candidates = generate_voicing_candidates(chord, role_range, num_candidates)
    if not candidates:
        return VoicingCandidate(pitches=[], inversion=0, register_span=0)

    if previous_voicing is None:
        # First chord: prefer root position with narrow span
        return min(candidates, key=lambda c: c.register_span)

    return min(
        candidates,
        key=lambda c: voice_leading_cost(
            previous_voicing, c.pitches, role_range
        ),
    )


class HarmonicEngine:
    """Generates and validates chord progressions for a genre."""

    def __init__(self, config: dict, seed: int = None):
        self.config = config
        self.rng = random.Random(seed)

    def generate_progression(
        self, key_root: str, mode: str, num_bars: int, degrees: list = None
    ) -> list:
        """Return one :class:`ChordBar` per bar.

        Args:
            key_root: tonic letter, e.g. ``"a"``.
            mode: ``"minor"`` or ``"major"``.
            num_bars: number of bars in the progression.
            degrees: optional fixed sequence of Roman numeral degrees
                (from the LLM ideation layer); tiled/truncated to
                ``num_bars``. ``None`` walks the genre transition matrix.
        """
        if num_bars < 1:
            raise ValueError("num_bars must be >= 1")
        if degrees:
            degree_list = [
                degrees[bar % len(degrees)] for bar in range(num_bars)
            ]
        else:
            degree_list = self._walk_chords(num_bars)
        return [
            self._chord_bar(bar, degree, key_root, mode)
            for bar, degree in enumerate(degree_list)
        ]

    def _walk_chords(self, num_bars: int) -> list:
        """Walk the transition matrix to pick degree strings per bar."""
        pool = self.config["chord_pool"]
        matrix = self.config.get("transition_matrix", {})
        current = self._weighted_pool_degree(pool)
        degrees = [current]
        for _ in range(num_bars - 1):
            transitions = matrix.get(current)
            if transitions:
                current = self._weighted_choice(transitions)
            else:
                current = self._weighted_pool_degree(pool)
            degrees.append(current)
        return degrees

    def _weighted_pool_degree(self, pool) -> str:
        weights = [float(item["weight"]) for item in pool]
        choice = self.rng.choices(pool, weights=weights, k=1)[0]
        return choice["degree"]

    def _weighted_choice(self, mapping: dict) -> str:
        choices = list(mapping.keys())
        weights = [float(mapping[c]) for c in choices]
        return self.rng.choices(choices, weights=weights, k=1)[0]

    def _chord_bar(self, bar: int, degree: str, key_root: str, mode: str) -> ChordBar:
        r = roman_chord(key_root, mode, degree)
        return ChordBar(
            bar=bar,
            degree=degree,
            root_pc=r.root().pitchClass,
            quality=str(r.quality),
            pitch_classes=sorted(r.pitchClasses),
        )
