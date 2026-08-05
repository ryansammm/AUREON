"""Layer 5 — Humanization Engine.

Makes a generated line feel played rather than programmed (FR-6):

- Micro-timing: small random timing offsets are added to every note-on
  EXCEPT the first downbeat of each bar, which stays locked to the grid.
- Velocity: a gentle phrase arc (rising toward the phrase climax, falling
  at resolution) plus per-note jitter so notes are never identical.
- Groove profiles: when a genre config specifies a ``groove_profile``,
  deterministic per-step timing/velocity offsets replace or blend with
  the random jitter, producing a consistent, genre-typical feel.

Groove offsets themselves are applied upstream (pipeline calls
``groove.apply_groove`` before this engine for every role, including
drum/drum_layers).  This engine therefore never adds *random* timing
jitter to drums — the deterministic groove profile is the only timing
signal drums receive — while the phrase-arc velocity still applies.

Musical assumptions:
- Offsets are in milliseconds and converted to beats using the tempo, so
  the musical deviation stays constant regardless of BPM.
- Timing is clamped so no note can start before beat 0.0.
"""

import logging
import math
import random

from .models import Note

BEATS_PER_BAR = 4.0
DEFAULT_PARAMS = {"max_timing_ms": 10, "velocity_jitter": 4}
_DRUM_ROLES = frozenset({"drum", "drum_layers"})

logger = logging.getLogger(__name__)


class Humanizer:
    """Applies micro-timing, swing and velocity humanization to notes."""

    def __init__(self, config: dict, seed: int = None):
        cfg = config.get("humanize") or {}
        self.params = {**DEFAULT_PARAMS, **cfg}
        self.swing = config.get("swing") or {}
        self.rng = random.Random(seed)

        # Groove profile integration
        self._groove_profile = None
        self._groove_strength = 0.0
        groove_id = config.get("groove_profile")
        if groove_id:
            try:
                from .groove import load_groove_profile
                self._groove_profile = load_groove_profile(groove_id)
                self._groove_strength = float(config.get("groove_strength", 1.0))
            except FileNotFoundError:
                logger.warning(
                    "Groove profile '%s' not found, falling back to random jitter",
                    groove_id,
                )

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

    def humanize(self, notes: list, bpm: float, role: str = None) -> list:
        """Mutate and return ``notes`` with timing/velocity humanization.

        Args:
            notes: list of :class:`Note` (mutated in place).
            bpm: tempo used to convert millisecond offsets to beats.
            role: instrument role.  Drums keep velocity humanization
                  (jitter + phrase arc) but skip micro-timing and swing
                  so the groove stays tight.
        """
        max_offset = self.params["max_timing_ms"] * bpm / 60000.0
        jitter = self.params["velocity_jitter"]
        drum = role in _DRUM_ROLES

        # When a groove profile is active, use it for timing/velocity
        # instead of (or blended with) random jitter
        use_groove = self._groove_profile is not None and self._groove_strength > 0.0

        for note in notes:
            is_downbeat = abs(note.start_beat % BEATS_PER_BAR) < 1e-9

            if use_groove and not drum:
                # Apply groove profile offsets (handled by groove.apply_groove
                # which is called upstream before humanize, so here we only
                # add residual random jitter scaled by (1 - strength))
                residual = 1.0 - self._groove_strength
                if not is_downbeat and residual > 0.01:
                    self._apply_swing(note)
                    offset = self.rng.uniform(-max_offset, max_offset) * residual
                    note.start_beat = max(0.0, note.start_beat + offset)
                    vel_jitter = self.rng.gauss(0, jitter / 2) * residual
                    note.velocity = max(1, min(127, int(round(note.velocity + vel_jitter))))
            elif not drum and not is_downbeat:
                # Original random jitter path
                self._apply_swing(note)
                offset = self.rng.uniform(-max_offset, max_offset)
                note.start_beat = max(0.0, note.start_beat + offset)

            # Phrase arc velocity (always applied, even with groove)
            phrase_pos = (note.start_beat // BEATS_PER_BAR) % 8 / 7.0
            arc = math.sin(phrase_pos * math.pi)
            velocity = note.velocity + arc * 4.0 - 2.0
            note.velocity = max(1, min(127, int(round(velocity))))

        return notes
