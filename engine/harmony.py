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

from .models import ChordBar
from .music_utils import roman_chord


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
