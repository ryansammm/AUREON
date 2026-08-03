"""Shared data models for the MIDI composition engine.

These dataclasses are the contract between layers so each engine module
can be tested in isolation without knowing the internals of the others.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class Note:
    """A single MIDI note in beat units.

    Musical assumption: ``start_beat`` and ``duration_beat`` are in
    quarter-note beats within a 4/4 bar (beat 0.0 = downbeat of bar).
    """

    pitch: int
    start_beat: float
    duration_beat: float
    velocity: int = 92
    section: str = ""
    role: str = ""


@dataclass
class ChordBar:
    """A chord assigned to one bar of the composition."""

    bar: int
    degree: str
    root_pc: int
    quality: str
    pitch_classes: List[int] = field(default_factory=list)


@dataclass
class Track:
    """One output MIDI track with instrument-intent metadata (FR-8)."""

    role: str
    track_name: str
    suggested_preset: str
    notes: List[Note] = field(default_factory=list)
    channel: int = 0
    cc: List[tuple] = field(default_factory=list)


@dataclass
class SectionBar:
    """Energy-curve profile assigned to a single bar (Layer 3)."""

    bar: int
    name: str
    density: float
    register_shift: int
    base_velocity: int
