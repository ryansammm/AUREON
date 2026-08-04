"""Groove Template Engine — consistent, genre-specific micro-timing.

Real producer-programmed grooves have *consistent, genre-specific*
micro-timing signatures (e.g. hi-hats slightly ahead, bass slightly
behind the grid) — randomness alone can't reproduce that because it
has no structure across repetitions.

A groove profile stores per-step timing/velocity offsets at 16th-note
resolution, extracted from a reference performance or hand-programmed.
The ``apply_groove()`` function applies these offsets to generated
MIDI events, replacing or blending with the existing random jitter.

Musical assumptions:
- Resolution is always 16 steps per bar (16th notes in 4/4).
- Timing offsets are in **ticks** (1 tick = 1/16th-note step / 4 =
  a 64th-note grid at default resolution).  Positive = ahead of grid.
- Velocity scalars are multipliers (1.0 = unchanged).
"""

import json
import logging
from pathlib import Path
from typing import List, Optional

from .models import Note

logger = logging.getLogger(__name__)

_GROOVE_DIR = Path(__file__).resolve().parent.parent / "config" / "grooves"


class GrooveProfile:
    """A timing/velocity offset pattern for one bar at 16th-note resolution."""

    def __init__(self, data: dict):
        self.id: str = data["id"]
        self.resolution: int = data.get("resolution", 16)
        self.offsets_ticks: List[int] = data.get("offsets_ticks", [0] * self.resolution)
        self.velocity_scalars: List[float] = data.get(
            "velocity_scalars", [1.0] * self.resolution
        )
        # Validate lengths
        if len(self.offsets_ticks) != self.resolution:
            raise ValueError(
                f"Groove '{self.id}': offsets_ticks length "
                f"({len(self.offsets_ticks)}) != resolution ({self.resolution})"
            )
        if len(self.velocity_scalars) != self.resolution:
            raise ValueError(
                f"Groove '{self.id}': velocity_scalars length "
                f"({len(self.velocity_scalars)}) != resolution ({self.resolution})"
            )

    def offset_for_step(self, step: int) -> int:
        """Return the timing offset (in ticks) for a 16th-note step."""
        return self.offsets_ticks[step % self.resolution]

    def velocity_for_step(self, step: int) -> float:
        """Return the velocity scalar for a 16th-note step."""
        return self.velocity_scalars[step % self.resolution]


def load_groove_profile(profile_id: str, groove_dir: Optional[Path] = None) -> GrooveProfile:
    """Load a groove profile by id from the groove config directory.

    Raises FileNotFoundError if the profile does not exist.
    """
    d = groove_dir or _GROOVE_DIR
    path = d / f"{profile_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Groove profile '{profile_id}' not found at {path}")
    data = json.loads(path.read_text())
    return GrooveProfile(data)


def apply_groove(
    notes: List[Note],
    profile: GrooveProfile,
    role: str,
    strength: float = 1.0,
    bpm: float = 140.0,
) -> List[Note]:
    """Apply a groove profile's offsets to a list of notes.

    Args:
        notes: list of :class:`Note` objects (mutated in place).
        profile: the groove profile to apply.
        role: the role name — sustained roles (pad, chord, sub_bass) skip
            timing offsets to avoid detuning sustained tones.
        strength: blend factor 0.0–1.0.  0.0 = no change, 1.0 = full
            groove offset.  Intermediate values scale the offsets.
        bpm: tempo — used to convert tick offsets to beat fractions.

    Returns:
        The same ``notes`` list, mutated.
    """
    if strength <= 0.0 or profile is None:
        return notes

    # Convert one tick (1/16th step / 4 = 1/64 note) to beats
    tick_to_beat = (1.0 / 4.0) / 4.0  # = 1/16 beat per tick
    skip_timing = role in ("pad", "chord", "sub_bass")

    for note in notes:
        if note.role != role:
            continue

        # Determine which 16th-note step this note falls on within its bar
        bar_beat = note.start_beat % 4.0
        step = int(round(bar_beat * 4.0)) % profile.resolution

        # Apply timing offset
        if not skip_timing:
            tick_offset = profile.offset_for_step(step)
            if tick_offset != 0:
                beat_offset = tick_offset * tick_to_beat * strength
                note.start_beat = max(0.0, note.start_beat + beat_offset)

        # Apply velocity scalar
        vel_scalar = profile.velocity_for_step(step)
        if vel_scalar != 1.0:
            blended = 1.0 + (vel_scalar - 1.0) * strength
            note.velocity = max(1, min(127, int(note.velocity * blended)))

    return notes
