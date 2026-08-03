"""Layer 2 — Melodic/Bassline Engine.

Generates monophonic bass/melody lines locked to a chord progression
using motif development: an interval motif (relative to the chord root)
is sequenced across bars and inverted periodically. Rhythmic variation
comes from alternating patterns within the section's density tier and
from tier changes when the arrangement's energy curve shifts density.
Also generates sustained chord voicings (pad/chord roles) with smooth
voice leading between bars.

Musical assumptions:
- Bass/lead lines are monophonic and chord-tone based (FR-3); the lead
  may add deliberate scale-step passing tones (still snapped to scale).
- Every pitch is forced inside the role's register (plus the section's
  octave shift) and snapped to the active scale, so no out-of-scale note
  can reach the exporter.
- Chord voicings use 3-4 notes from the chord, placed in the role
  register, choosing octaves that minimize movement from the previous
  bar (voice leading).
- Beats are quarter-note units within 4/4 bars (beat 0.0 = downbeat).
"""

import random
from typing import Set

from .models import Note
from .music_utils import snap_pitch_to_scale

BEATS_PER_BAR = 4.0
SIXTEENTH_BEAT = 0.25
DENSITY_TIERS = ["simple", "medium", "complex"]
CHORD_ROLES = {"pad", "chord"}


class MelodicEngine:
    """Generates and develops bass/melody/chord lines for a progression."""

    def __init__(self, config: dict, seed: int = None):
        self.config = config
        self.rng = random.Random(seed)

    # ------------------------------------------------------------------ #
    # Monophonic lines (bass / lead)
    # ------------------------------------------------------------------ #
    def generate_bassline(
        self,
        progression,
        scale_pcs: Set[int],
        role: str = "bass",
        plan=None,
        complexity: str = "medium",
        base_velocity: int = 92,
        allow_passing: bool = False,
    ) -> list:
        """Return a list of :class:`Note` for the whole progression.

        Args:
            progression: output of :class:`HarmonicEngine`.
            scale_pcs: set of pitch classes the melody must stay inside.
            role: instrument role key from the genre config.
            plan: list of :class:`SectionBar` (Layer 3) — one per bar.
                ``None`` uses uniform density/register/velocity.
            complexity: user ceiling — ``simple`` / ``medium`` / ``complex``.
            base_velocity: fallback base velocity when plan is ``None``.
            allow_passing: allow scale-step passing tones (lead role).
        """
        role_range = self.config["role_ranges"][role]
        default_section = self.config.get("section_template", ["drop"])[0]

        motif_intervals = None
        current_pattern = None
        notes = []

        for bar, chord in enumerate(progression):
            profile = plan[bar] if plan else None
            density = profile.density if profile else 1.0
            register_shift = profile.register_shift if profile else 0
            velocity_base = profile.base_velocity if profile else base_velocity
            section = profile.name if profile else default_section

            patterns = self._patterns_for(role, complexity, density)
            rhythm = patterns[bar % 2] if len(patterns) > 1 else patterns[0]
            invert = (bar % 4 == 2) and bar > 1

            if motif_intervals is None or patterns[0] is not current_pattern:
                motif_intervals = self._build_motif_intervals(
                    chord, rhythm, role_range, scale_pcs, allow_passing
                )
                current_pattern = patterns[0]

            onsets = self._onsets_from_pattern(rhythm)
            for k, (onset, dur) in enumerate(onsets):
                interval = motif_intervals[k % len(motif_intervals)]
                if invert:
                    interval = -interval
                pitch = self._resolve_pitch(
                    interval, chord.root_pc, role_range, scale_pcs, register_shift
                )
                velocity = self._contour_velocity(
                    velocity_base, onset, bar, len(progression)
                )
                notes.append(
                    Note(
                        pitch=pitch,
                        start_beat=bar * BEATS_PER_BAR + onset,
                        duration_beat=dur,
                        velocity=velocity,
                        section=section,
                        role=role,
                    )
                )
        return notes

    # ------------------------------------------------------------------ #
    # Sustained chord voicings (pad / chord)
    # ------------------------------------------------------------------ #
    def generate_chord_track(
        self,
        progression,
        scale_pcs: Set[int],
        role: str = "pad",
        plan=None,
        base_velocity: int = 80,
        duration_beat: float = 3.75,
    ) -> list:
        """Return one sustained chord voicing per bar (3-4 voices)."""
        role_range = self.config["role_ranges"][role]
        default_section = self.config.get("section_template", ["drop"])[0]
        prev_voicing = None
        notes = []
        for bar, chord in enumerate(progression):
            profile = plan[bar] if plan else None
            register_shift = profile.register_shift if profile else 0
            velocity_base = profile.base_velocity if profile else base_velocity
            section = profile.name if profile else default_section
            shifted = {
                "min": role_range["min"] + register_shift * 12,
                "max": role_range["max"] + register_shift * 12,
            }
            voicing = self._smooth_voicing(chord, shifted, prev_voicing)
            for pitch in voicing:
                pitch = snap_pitch_to_scale(pitch, scale_pcs)
                while pitch < shifted["min"]:
                    pitch += 12
                while pitch > shifted["max"]:
                    pitch -= 12
                notes.append(
                    Note(
                        pitch=pitch,
                        start_beat=bar * BEATS_PER_BAR,
                        duration_beat=duration_beat,
                        velocity=velocity_base,
                        section=section,
                        role=role,
                    )
                )
            prev_voicing = voicing
        return notes

    # ------------------------------------------------------------------ #
    # Rhythm + motif helpers
    # ------------------------------------------------------------------ #
    def _patterns_for(self, role: str, complexity: str, density: float) -> list:
        """Pick the rhythm tier for this bar from complexity + density."""
        patterns_by_role = self.config.get(f"{role}_patterns")
        if not patterns_by_role:
            patterns_by_role = self.config["bass_patterns"]
        base_idx = DENSITY_TIERS.index(complexity) if complexity in DENSITY_TIERS else 1
        target_idx = min(2, max(0, int(round(base_idx * max(0.0, min(1.0, density))))))
        tier = DENSITY_TIERS[target_idx]
        patterns = patterns_by_role.get(tier)
        if not patterns:
            patterns = patterns_by_role.get("medium")
        if not patterns:
            raise ValueError(
                f"no rhythm patterns found for role '{role}' / tier '{tier}' "
                f"in genre config"
            )
        return patterns

    def _build_motif_intervals(
        self, chord, pattern, role_range, scale_pcs, allow_passing=False
    ) -> list:
        """Build the motif as a list of chord-tone intervals from the root."""
        pool = self._interval_pool(chord, allow_passing)
        return [self._weighted_choice(pool) for _ in pattern]

    def _onsets_from_pattern(self, pattern) -> list:
        """Turn a 16th-duration pattern into (onset, duration) beat tuples."""
        onsets = []
        onset = 0.0
        for d16 in pattern:
            dur = d16 * SIXTEENTH_BEAT
            onsets.append((onset, dur))
            onset += dur
        return onsets

    def _interval_pool(self, chord, allow_passing=False):
        """Chord-tone intervals (0-24) relative to the root, weighted."""
        chord_intervals = sorted(
            {(pc - chord.root_pc) % 12 for pc in chord.pitch_classes}
        )
        third = next((i for i in chord_intervals if 0 < i < 7), 3)
        pool = {}
        for i in chord_intervals:
            if i == 0:
                pool[i] = 5.0
            elif i == 7:
                pool[i] = 3.0
            elif i == third:
                pool[i] = 2.0
        pool[12] = 2.0
        pool[12 + 7] = 1.0
        pool[12 + third] = 1.0
        if allow_passing:
            pool[2] = 1.2
            pool[10] = 1.0
        return list(pool.items())

    def _weighted_choice(self, pool):
        choices = [item[0] for item in pool]
        weights = [item[1] for item in pool]
        return self.rng.choices(choices, weights=weights, k=1)[0]

    def _resolve_pitch(self, interval, root_pc, role_range, scale_pcs, register_shift):
        """Place pitch in the role register (+section octave shift), snap to scale."""
        low = role_range["min"] + register_shift * 12
        high = role_range["max"] + register_shift * 12
        pitch = root_pc + interval
        while pitch < low:
            pitch += 12
        while pitch > high:
            pitch -= 12
        pitch = snap_pitch_to_scale(pitch, scale_pcs)
        while pitch < low:
            pitch += 12
        while pitch > high:
            pitch -= 12
        return pitch

    def _contour_velocity(self, base_velocity, onset, bar, num_bars):
        velocity = base_velocity
        if onset == 0.0:
            velocity += 3
        if bar == num_bars - 1:
            velocity -= 4
        return max(1, min(127, int(velocity)))

    # ------------------------------------------------------------------ #
    # Voice-leading helpers
    # ------------------------------------------------------------------ #
    def _smooth_voicing(self, chord, role_range, prev_voicing, num_notes=4) -> list:
        """Pick chord tones spread in register with smooth motion."""
        voicing = []
        for pc in sorted(set(chord.pitch_classes)):
            opts = self._pitches_for_pc(pc, role_range["min"], role_range["max"])
            if opts:
                voicing.append(self._best_pitch(opts, prev_voicing))
        while len(voicing) < num_notes:
            root = chord.root_pc % 12
            opts = [
                p
                for p in self._pitches_for_pc(root, role_range["min"], role_range["max"])
                if p not in voicing
            ]
            if not opts:
                break
            voicing.append(self._best_pitch(opts, prev_voicing))
        return sorted(voicing)

    def _pitches_for_pc(self, pc, low, high) -> list:
        out = []
        p = pc
        while p <= high:
            if p >= low:
                out.append(p)
            p += 12
        return out

    def _best_pitch(self, candidates, prev_voicing):
        if not prev_voicing:
            return candidates[0]
        return min(
            candidates, key=lambda p: min(abs(p - q) for q in prev_voicing)
        )
