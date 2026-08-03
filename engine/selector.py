"""Layer 4 — Candidate Generator + Selector.

Generates several variations of the same track (different random seeds)
and scores them with pure music-theory heuristics so the best candidate
is picked instead of "first random result":

- Dissonance rate: share of sequential intervals that are strongly
  dissonant (minor 2nd, tritone, major 7th).
- Repetition ratio: share of adjacent bars that are rhythm+pitch
  identical to their predecessor.
- Voice-leading smoothness: mean leap (in semitones) between adjacent
  notes.

Higher score = better. Weights come from the genre config
(``selector_weights``) and default when absent.
"""

import random

from .pipeline import generate_composition, generate_track

DISSONANT_INTERVALS = {1, 6, 11}
BEATS_PER_BAR = 4.0
DEFAULT_WEIGHTS = {"dissonance": 1.0, "repetition": 1.5, "voice_leading": 1.0}


def _interval_class(a: int, b: int) -> int:
    d = abs(a - b) % 12
    return min(d, 12 - d)


class CandidateGenerator:
    """Generates N candidate tracks/compositions with distinct seeds."""

    def __init__(self, config: dict, seed: int = None):
        self.config = config
        self.rng = random.Random(seed)

    def generate(
        self,
        role: str,
        key_root: str,
        mode: str,
        bars: int = None,
        complexity: str = "medium",
        count: int = 5,
        base_seed: int = None,
        humanize: bool = True,
        roles: list = None,
    ) -> list:
        """Return ``count`` candidates.

        Each candidate is ``(tracks, progression, plan, seed)`` where
        ``tracks`` is a list of :class:`Track` (one per role).
        """
        roles = roles or [role]
        base = base_seed if base_seed is not None else self.rng.randint(0, 10**6)
        candidates = []
        for i in range(count):
            seed = base + i * 1009
            if len(roles) > 1:
                tracks, progression, plan = generate_composition(
                    self.config,
                    roles,
                    key_root,
                    mode,
                    bars=bars,
                    complexity=complexity,
                    seed=seed,
                    humanize=humanize,
                )
            else:
                track, progression, plan = generate_track(
                    self.config,
                    role,
                    key_root,
                    mode,
                    bars=bars,
                    complexity=complexity,
                    seed=seed,
                    humanize=humanize,
                )
                tracks = [track]
            candidates.append((tracks, progression, plan, seed))
        return candidates


class Selector:
    """Scores and ranks candidate tracks using theory heuristics."""

    def __init__(self, config: dict, seed: int = None):
        self.config = config
        self.weights = {**DEFAULT_WEIGHTS, **(config.get("selector_weights") or {})}
        self.rng = random.Random(seed)

    def score_track(self, track):
        """Return ``(score, details)`` for a track. Higher is better."""
        notes = sorted(track.notes, key=lambda n: n.start_beat)
        if len(notes) < 2:
            return 0.0, {
                "dissonance": 0.0,
                "repetition": 0.0,
                "voice_leading": 0.0,
                "score": 0.0,
            }

        intervals = [
            _interval_class(notes[i + 1].pitch, notes[i].pitch)
            for i in range(len(notes) - 1)
        ]
        dissonance_rate = (
            sum(1 for iv in intervals if iv in DISSONANT_INTERVALS) / len(intervals)
        )
        mean_leap = (
            sum(abs(notes[i + 1].pitch - notes[i].pitch) for i in range(len(notes) - 1))
            / len(intervals)
        )

        bars = {}
        for n in notes:
            bar = int(n.start_beat // BEATS_PER_BAR)
            bars.setdefault(bar, []).append(
                (n.pitch, round(n.start_beat % BEATS_PER_BAR, 3), round(n.duration_beat, 3))
            )
        bar_ids = sorted(bars)
        repeats = sum(
            1 for i in range(1, len(bar_ids)) if bars[bar_ids[i]] == bars[bar_ids[i - 1]]
        )
        repetition_ratio = repeats / len(bar_ids) if bar_ids else 0.0

        w = self.weights
        score = -(
            w["dissonance"] * dissonance_rate
            + w["repetition"] * repetition_ratio
            + w["voice_leading"] * (mean_leap / 12.0)
        )
        return score, {
            "dissonance": dissonance_rate,
            "repetition": repetition_ratio,
            "voice_leading": mean_leap,
            "score": score,
        }

    def rank(self, tracks: list) -> list:
        """Return ``tracks`` sorted by score, best first."""
        return sorted(tracks, key=self.score_track, reverse=True)

    def select(self, tracks: list, top_n: int = 1) -> list:
        """Return the ``top_n`` best tracks."""
        if top_n < 1:
            raise ValueError("top_n must be >= 1")
        return self.rank(tracks)[:top_n]

    def score_composition(self, tracks: list):
        """Average per-track score across a multi-track composition.

        Percussion tracks (role ``drum``) are excluded — pitch-based
        dissonance heuristics are meaningless for drum voices.

        Returns:
            Tuple of ``(mean_score, details)``.
        """
        melodic = [t for t in tracks if getattr(t, "role", "") != "drum"]
        if not melodic:
            return 0.0, {"score": 0.0}
        details_list = [self.score_track(t)[1] for t in melodic]
        mean_score = sum(d["score"] for d in details_list) / len(details_list)
        return mean_score, {"score": mean_score}
