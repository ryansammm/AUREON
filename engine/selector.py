"""Layer 4 — Candidate Generator + Selector.

Generates several variations of the same track (different random seeds)
and scores them so the best candidate is picked instead of "first random
result". Scoring is an ensemble of music-theory heuristics and cheap
statistical features (Phase 6 upgrade):

- Dissonance rate: share of sequential intervals that are strongly
  dissonant (minor 2nd, tritone, major 7th).
- Repetition ratio: share of adjacent bars that are rhythm+pitch
  identical to their predecessor.
- Voice-leading smoothness: mean leap (in semitones) between adjacent
  notes.
- Tonality: share of notes whose pitch class sits in the genre's tonal
  palette (union of the scale pool for the active key/mode).
- Chord-tone alignment: share of notes on the bar's chord tones
  (needs the progression, optional).
- Pitch variety: number of distinct pitch classes used — penalizes
  single-pitch monotony.
- Density: notes per bar kept in a healthy window — penalizes dead air
  and note spam.
- Register adherence: share of notes inside the role's declared range.

All features are deterministic and O(n); weights come from the genre
config (``selector_weights``) with defaults when absent. Higher score =
better.
"""

import random

from .music_utils import get_scale_pitch_classes
from .pipeline import generate_composition, generate_track

DISSONANT_INTERVALS = {1, 6, 11}
BEATS_PER_BAR = 4.0
DENSITY_LOW = 2.0
DENSITY_HIGH = 16.0
MAX_DIATONIC_PCS = 7.0
DEFAULT_WEIGHTS = {
    "dissonance": 1.0,
    "repetition": 1.5,
    "voice_leading": 1.0,
    "tonality": 2.0,
    "chord_tone": 1.0,
    "pitch_variety": 1.5,
    "density": 0.5,
    "range": 0.6,
}


def _interval_class(a: int, b: int) -> int:
    d = abs(a - b) % 12
    return min(d, 12 - d)


def _tonal_palette(config: dict, key_root: str, mode: str):
    """Union of pitch classes across the genre's scale pool.

    ``None`` when no key/mode is available (feature is then neutral).
    """
    if not key_root or not mode:
        return None
    pool = config.get("scale_pool") or []
    if not pool:
        return get_scale_pitch_classes(key_root, mode)
    pcs = set()
    for name in pool:
        pcs |= get_scale_pitch_classes(key_root, mode, name)
    return pcs


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
    """Scores and ranks candidate tracks using an ensemble of features."""

    def __init__(
        self, config: dict, seed: int = None, key_root: str = None, mode: str = None
    ):
        self.config = config
        self.weights = {**DEFAULT_WEIGHTS, **(config.get("selector_weights") or {})}
        self.rng = random.Random(seed)
        self.key_root = key_root or config.get("default_key")
        self.mode = mode or config.get("default_mode")
        self._palette = _tonal_palette(config, self.key_root, self.mode)
        self._ranges = config.get("role_ranges") or {}

    @staticmethod
    def _empty_details() -> dict:
        return {
            "dissonance": 0.0,
            "repetition": 0.0,
            "voice_leading": 0.0,
            "tonality": 0.0,
            "chord_tone": 0.0,
            "pitch_variety": 0.0,
            "density": 0.0,
            "range": 0.0,
            "score": 0.0,
        }

    @staticmethod
    def _bar_chords(progression: list) -> dict:
        """Map bar index -> set of chord pitch classes."""
        out = {}
        for cb in progression:
            if cb.pitch_classes:
                out[cb.bar] = set(cb.pitch_classes)
        return out

    def score_track(self, track, progression: list = None):
        """Return ``(score, details)`` for a track. Higher is better."""
        notes = sorted(track.notes, key=lambda n: n.start_beat)
        if len(notes) < 2:
            return 0.0, self._empty_details()

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

        n_notes = len(notes)
        if self._palette:
            in_key = sum(1 for n in notes if n.pitch % 12 in self._palette)
            tonality = in_key / n_notes
        else:
            tonality = 1.0

        chords = self._bar_chords(progression) if progression else {}
        aligned = with_chord = 0
        for n in notes:
            pcs = chords.get(int(n.start_beat // BEATS_PER_BAR))
            if pcs is not None:
                with_chord += 1
                if n.pitch % 12 in pcs:
                    aligned += 1
        chord_tone = aligned / with_chord if with_chord else 1.0

        unique_pcs = len({n.pitch % 12 for n in notes})
        pitch_variety = min(1.0, unique_pcs / MAX_DIATONIC_PCS)

        max_bar = int(notes[-1].start_beat // BEATS_PER_BAR)
        density = n_notes / (max_bar + 1)

        bounds = self._ranges.get(track.role)
        if bounds:
            in_range = sum(
                1 for n in notes if bounds["min"] <= n.pitch <= bounds["max"]
            )
            range_rate = in_range / n_notes
        else:
            range_rate = 1.0

        w = self.weights
        if density < DENSITY_LOW:
            density_badness = min(1.0, (DENSITY_LOW - density) / DENSITY_LOW)
        elif density > DENSITY_HIGH:
            density_badness = min(1.0, (density - DENSITY_HIGH) / DENSITY_HIGH)
        else:
            density_badness = 0.0

        score = -(
            w["dissonance"] * dissonance_rate
            + w["repetition"] * repetition_ratio
            + w["voice_leading"] * (mean_leap / 12.0)
            + w["tonality"] * (1.0 - tonality)
            + w["chord_tone"] * (1.0 - chord_tone)
            + w["pitch_variety"] * (1.0 - pitch_variety)
            + w["density"] * density_badness
            + w["range"] * (1.0 - range_rate)
        )
        return score, {
            "dissonance": dissonance_rate,
            "repetition": repetition_ratio,
            "voice_leading": mean_leap,
            "tonality": tonality,
            "chord_tone": chord_tone,
            "pitch_variety": pitch_variety,
            "density": density,
            "range": range_rate,
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

    def score_composition(self, tracks: list, progression: list = None):
        """Average per-track score across a multi-track composition.

        Percussion tracks (roles ``drum`` and ``drum_layers``) are
        excluded — pitch-based heuristics are meaningless for percussion
        voices.

        Returns:
            Tuple of ``(mean_score, details)``.
        """
        melodic = [
            t for t in tracks
            if getattr(t, "role", "") not in ("drum", "drum_layers")
        ]
        if not melodic:
            return 0.0, {"score": 0.0}
        details_list = [self.score_track(t, progression)[1] for t in melodic]
        mean_score = sum(d["score"] for d in details_list) / len(details_list)
        return mean_score, {"score": mean_score}
