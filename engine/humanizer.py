"""Layer 5 — Humanization Engine.

Makes a generated line feel played rather than programmed (FR-6):

- Micro-timing: small random timing offsets are added to every note-on
  EXCEPT the first downbeat of each bar, which stays locked to the grid.
- Velocity: a gentle phrase arc (rising toward the phrase climax, falling
  at resolution) plus per-note jitter so notes are never identical.

Musical assumptions:
- Offsets are in milliseconds and converted to beats using the tempo, so
  the musical deviation stays constant regardless of BPM.
- Timing is clamped so no note can start before beat 0.0.
"""

import math
import random

from .models import Note

BEATS_PER_BAR = 4.0
DEFAULT_PARAMS = {"max_timing_ms": 25, "velocity_jitter": 4}


class Humanizer:
    """Applies micro-timing, swing and velocity humanization to notes."""

    def __init__(self, config: dict, seed: int = None):
        cfg = config.get("humanize") or {}
        self.params = {**DEFAULT_PARAMS, **cfg}
        self.swing = config.get("swing") or {}
        self.rng = random.Random(seed)

    def _apply_swing(self, note: Note) -> None:
        """Delay off-beat steps by a configurable groove amount.

        A note is an off-beat when it sits on an odd step index of the
        swing resolution (e.g. resolution 8 = every other eighth-note,
        resolution 16 = every other 16th). Sustained chord/pad roles and
        sub-bass (kick-locked by design) are left on the grid.
        """
        amount = self.swing.get("amount", 0.0)
        if not amount:
            return
        if note.role in ("pad", "chord", "sub_bass"):
            return
        resolution = int(self.swing.get("resolution", 8) or 8)
        step = BEATS_PER_BAR / resolution
        pos_in_bar = note.start_beat % BEATS_PER_BAR
        step_idx = round(pos_in_bar / step)
        on_offbeat = abs(pos_in_bar - step_idx * step) < 1e-6 and step_idx % 2 == 1
        if on_offbeat:
            note.start_beat += amount * step

    def humanize(self, notes: list, bpm: float) -> list:
        """Mutate and return ``notes`` with timing/velocity humanization.

        Args:
            notes: list of :class:`Note` (mutated in place).
            bpm: tempo used to convert millisecond offsets to beats.
        """
        max_offset = self.params["max_timing_ms"] * bpm / 60000.0
        jitter = self.params["velocity_jitter"]
        for note in notes:
            is_downbeat = abs(note.start_beat % BEATS_PER_BAR) < 1e-9
            if not is_downbeat:
                self._apply_swing(note)
                offset = self.rng.uniform(-max_offset, max_offset)
                note.start_beat = max(0.0, note.start_beat + offset)

            phrase_pos = (note.start_beat // BEATS_PER_BAR) % 8 / 7.0
            arc = math.sin(phrase_pos * math.pi)
            velocity = (
                note.velocity
                + self.rng.gauss(0, jitter / 2)
                + arc * 4.0
                - 2.0
            )
            note.velocity = max(1, min(127, int(round(velocity))))
        return notes
