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
DEFAULT_LAYER_NOTES = {"perc": 60, "tom": 50, "cymbal": 51, "shaker": 70}
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

    def extract_kick_mask(self, plan: list) -> set:
        """Return a set of beat positions where kick hits occur.

        The mask contains absolute beat positions (bar * 4 + step * 0.25)
        for every active kick step across all bars in the plan.  This is
        used by the bass interlock system to bias bass onsets toward or
        away from kick hits.
        """
        kick_voice = None
        for voice, note_number in self.notes_map.items():
            if note_number == DEFAULT_DRUM_NOTES["kick"]:
                kick_voice = voice
                break
        if kick_voice is None:
            return set()

        mask: set = set()
        for sb in plan:
            pattern = self._pattern_for(sb.name, kick_voice)
            for step, char in enumerate(pattern):
                if char in ("x", "X"):
                    mask.add(sb.bar * BEATS_PER_BAR + step * STEP_BEAT)
        return mask

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
            Humanizer(self.config, seed).humanize(notes, bpm, role="drum")

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

    # ------------------------------------------------------------------ #
    # Drum layers — extra percussion (percs/toms/cymbals) + transition fills
    # ------------------------------------------------------------------ #
    def generate_layers(self, plan: list, humanize=True, bpm=140, seed=None) -> Track:
        """Return a :class:`Track` with role ``drum_layers``.

        Reads ``drum_patterns["layers"]`` (per-section step strings for
        extra percussion voices) plus an optional fill engine: before a
        section whose density is higher than the current one, a 16th-note
        roll on the configured fill voices closes out the last bar so the
        transition "lifts" into the drop.
        """
        from .humanizer import Humanizer

        drum_cfg = self.config.get("drum_patterns") or {}
        layer_notes = {**DEFAULT_LAYER_NOTES, **(drum_cfg.get("layer_notes") or {})}
        layers = drum_cfg.get("layers") or {}
        fill_cfg = drum_cfg.get("fills") or {}
        fill_enabled = fill_cfg.get("enabled", True)
        fill_voices = [
            v for v in fill_cfg.get("voices", ["perc", "tom"]) if v in layer_notes
        ]
        fill_beats = float(fill_cfg.get("beats", 1))

        notes = []
        for idx, sb in enumerate(plan):
            base_velocity = int(sb.base_velocity * 0.9)
            next_density = plan[idx + 1].density if idx + 1 < len(plan) else 0.0
            fill_here = (
                fill_enabled
                and fill_voices
                and next_density > sb.density + 0.15
            )

            section_layers = layers.get(sb.name) or {}
            for voice, pattern in section_layers.items():
                note_number = layer_notes.get(voice)
                if note_number is None:
                    continue
                for step, char in enumerate(pattern):
                    velocity = self._velocity_for(char, base_velocity)
                    if velocity == 0:
                        continue
                    notes.append(
                        Note(
                            pitch=note_number,
                            start_beat=sb.bar * BEATS_PER_BAR + step * STEP_BEAT,
                            duration_beat=STEP_BEAT * 0.9 if voice in ("shaker", "cymbal") else STEP_BEAT,
                            velocity=velocity,
                            section=sb.name,
                            role="drum_layers",
                        )
                    )

            if fill_here:
                start16 = 16 - int(round(fill_beats * 4))
                for k in range(start16, 16):
                    for voice in fill_voices:
                        velocity = min(127, int(base_velocity * (0.7 + 0.4 * (k - start16) / max(1, 15 - start16))))
                        notes.append(
                            Note(
                                pitch=layer_notes[voice],
                                start_beat=sb.bar * BEATS_PER_BAR + k * STEP_BEAT,
                                duration_beat=STEP_BEAT * 0.8,
                                velocity=velocity,
                                section=sb.name,
                                role="drum_layers",
                            )
                        )

        if humanize:
            Humanizer(self.config, seed).humanize(notes, bpm, role="drum_layers")

        intent = self.config.get("instrument_intent", {}).get("drum_layers") or {
            "label": "Drum Layers - Percussion",
            "preset": "electronic_percussion",
        }
        return Track(
            role="drum_layers",
            track_name=intent["label"],
            suggested_preset=intent["preset"],
            notes=notes,
            channel=9,
        )
