"""Drum/percussion layer for the multi-track composition.

Generates a drum track from per-section 16-step patterns in the genre
config. Step strings use one character per 16th note:

- ``.`` off
- ``x`` hit at a normal velocity
- ``X`` accent (louder)

Example (half-time dubstep drop):
    "kick":  "x...........x...",
    "snare": "........x.......",
    "hat":   "xxxxxxxxxxxxxxxx",

Musical assumptions:
- Pattern steps are 16th notes in 4/4 (16 steps fill one bar).
- Drum notes are percussion MIDI numbers (kick 36, snare 38, hat 42/46);
  the track is written to MIDI channel 10 (index 9).
- Only velocities are generated here; timing/velocity humanization
  (Layer 5) and swing are applied upstream by the caller.
"""

from .models import Note, Track

BEATS_PER_BAR = 4.0
STEP_BEAT = 0.25
DEFAULT_DRUM_NOTES = {"kick": 36, "snare": 38, "clap": 39, "hat": 42, "hat_open": 46, "crash": 49}
DEFAULT_VELOCITY = 92
ACCENT_VELOCITY = 110


class DrumEngine:
    """Generates a drum track from config step patterns."""

    def __init__(self, config: dict, seed: int = None):
        self.config = config
        drum_cfg = config.get("drum_patterns") or {}
        self.notes_map = {**DEFAULT_DRUM_NOTES, **(drum_cfg.get("notes") or {})}
        self.patterns = drum_cfg.get("patterns") or {}

    def _velocity_for(self, step_char: str, base_velocity: int) -> int:
        if step_char == "X":
            return ACCENT_VELOCITY
        if step_char == "x":
            return base_velocity
        return 0

    def _pattern_for(self, section: str, voice: str) -> str:
        section_patterns = self.patterns.get(section) or {}
        return section_patterns.get(voice) or ""

    def generate_track(self, plan: list, humanize=True, bpm=140, seed=None) -> Track:
        """Return a :class:`Track` with role ``drum`` for the given plan.

        Args:
            plan: list of :class:`SectionBar` (Layer 3), one per bar.
            humanize: apply Layer 5 humanization to the generated notes.
            bpm: tempo for humanization micro-timing.
            seed: seed forwarded to the humanizer.
        """
        from .humanizer import Humanizer

        notes = []
        for sb in plan:
            base_velocity = int(sb.base_velocity * 0.92)
            for voice, note_number in self.notes_map.items():
                pattern = self._pattern_for(sb.name, voice)
                if not pattern:
                    continue
                for step, char in enumerate(pattern):
                    velocity = self._velocity_for(char, base_velocity)
                    if velocity == 0:
                        continue
                    duration = STEP_BEAT * 0.9 if voice == "hat" else STEP_BEAT
                    notes.append(
                        Note(
                            pitch=note_number,
                            start_beat=sb.bar * BEATS_PER_BAR + step * STEP_BEAT,
                            duration_beat=duration,
                            velocity=velocity,
                            section=sb.name,
                            role="drum",
                        )
                    )

        if humanize:
            Humanizer(self.config, seed).humanize(notes, bpm)

        intent = self.config.get("instrument_intent", {}).get("drum") or {
            "label": "Drums",
            "preset": "acoustic_kit / electronic_kit",
        }
        return Track(
            role="drum",
            track_name=intent["label"],
            suggested_preset=intent["preset"],
            notes=notes,
            channel=9,
        )
