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
from .harmony import voice_chord

BEATS_PER_BAR = 4.0
SIXTEENTH_BEAT = 0.25
STEP_BEAT = 0.25
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
        motif: list = None,
        kick_mask: set = None,
        interlock_mode: str = "independent",
        interlock_probability: float = 0.7,
        interlock_on_conflict: str = "drop",
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
            motif: optional scale-step contour (list of ints) from the LLM
                ideation layer. When given it replaces the random motif so
                the line carries a recognizable theme (re-anchored to each
                bar's chord root, no periodic inversion).
            kick_mask: set of absolute beat positions where kick hits occur.
                When provided with interlock_mode != "independent", bass
                onsets are biased toward or away from these positions.
            interlock_mode: ``"lock"`` biases toward kick hits,
                ``"syncopate"`` biases away, ``"independent"`` ignores mask.
            interlock_probability: probability (0-1) of conforming to the
                interlock constraint.  1.0 = strict, 0.0 = independent.
            interlock_on_conflict: how a rejected ``lock`` onset is handled —
                ``"drop"`` removes the note, ``"shift"`` snaps it onto the
                nearest kick hit so the note count is preserved.
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
            invert = (bar % 4 == 2) and bar > 1 and not motif

            if motif and motif_intervals is None:
                motif_intervals = self._motif_to_intervals(
                    motif, chord.root_pc, scale_pcs
                )
                current_pattern = patterns[0]
            elif motif_intervals is None or patterns[0] is not current_pattern:
                motif_intervals = self._build_motif_intervals(
                    chord, rhythm, role_range, scale_pcs, allow_passing
                )
                current_pattern = patterns[0]

            onsets = self._onsets_from_pattern(rhythm)
            for k, (onset, dur) in enumerate(onsets):
                # Bass-drum interlock: bias onset selection
                if kick_mask and interlock_mode != "independent":
                    bar_start = bar * BEATS_PER_BAR
                    abs_onset = bar_start + onset
                    near_kick = any(
                        abs(abs_onset - kb) < STEP_BEAT * 0.6 for kb in kick_mask
                    )
                    if interlock_mode == "lock":
                        if near_kick or self.rng.random() > interlock_probability:
                            pass
                        elif interlock_on_conflict == "shift":
                            # Snap the onset onto the nearest kick hit so the
                            # bass still lands on the grid (keeps the note).
                            onset = min(
                                kick_mask,
                                key=lambda kb: abs(abs_onset - kb),
                            ) - bar_start
                            abs_onset = bar_start + onset
                        else:
                            # Default: drop the note entirely.
                            continue
                    elif interlock_mode == "syncopate":
                        accept = not near_kick or self.rng.random() > interlock_probability
                        if not accept:
                            continue

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
    # Arp / pluck — rhythmic arpeggios cycling through chord tones
    # ------------------------------------------------------------------ #
    def generate_arp(
        self,
        progression,
        scale_pcs: Set[int],
        role: str = "arp",
        plan=None,
        complexity: str = "medium",
        base_velocity: int = 92,
    ) -> list:
        """Return a note-per-onset arpeggio line (Layer 2 extension).

        Chord tones are cycled through the role register in an order
        chosen by ``role_params["arp"]["order"]`` (up/down/updown/random).
        Note length is fixed (``note_length``) so the arp reads as a
        pulsing pluck rather than a sustained line.
        """
        role_range = self.config["role_ranges"][role]
        default_section = self.config.get("section_template", ["drop"])[0]
        params = self.config.get("role_params", {}).get("arp", {})
        order = params.get("order", "up")
        note_length = float(params.get("note_length", 0.22))
        octaves = int(params.get("octave_span", 2))

        notes = []
        for bar, chord in enumerate(progression):
            profile = plan[bar] if plan else None
            density = profile.density if profile else 1.0
            register_shift = profile.register_shift if profile else 0
            velocity_base = profile.base_velocity if profile else base_velocity
            section = profile.name if profile else default_section

            patterns = self._patterns_for(role, complexity, density)
            rhythm = patterns[bar % 2] if len(patterns) > 1 else patterns[0]

            pool = self._arp_pool(chord, role_range, register_shift, octaves, order)
            if not pool:
                continue
            pool = self._order_pool(pool, order)

            for k, (onset, dur) in enumerate(self._onsets_from_pattern(rhythm)):
                pitch = pool[k % len(pool)]
                pitch = snap_pitch_to_scale(pitch, scale_pcs)
                low = role_range["min"] + register_shift * 12
                high = role_range["max"] + register_shift * 12
                while pitch < low:
                    pitch += 12
                while pitch > high:
                    pitch -= 12
                velocity = min(127, velocity_base - (6 if k % 2 == 1 else 0))
                notes.append(
                    Note(
                        pitch=pitch,
                        start_beat=bar * BEATS_PER_BAR + onset,
                        duration_beat=min(note_length, max(0.05, dur)),
                        velocity=velocity,
                        section=section,
                        role=role,
                    )
                )
        return notes

    def _arp_pool(self, chord, role_range, register_shift, octaves, order) -> list:
        """Chord-tone pitch candidates spread across the role register."""
        low = role_range["min"] + register_shift * 12
        high = role_range["max"] + register_shift * 12
        seen = set()
        pool = []
        for pc in chord.pitch_classes:
            for octave in range(octaves + 1):
                p = (pc % 12) + 12 * octave
                while p < low:
                    p += 12
                while p > high:
                    p -= 12
                if p not in seen:
                    seen.add(p)
                    pool.append(p)
        if not pool:
            root = chord.root_pc
            while root < low:
                root += 12
            while root > high:
                root -= 12
            pool = [root]
        return pool

    def _order_pool(self, pool: list, order: str) -> list:
        if order == "up":
            return sorted(pool)
        if order == "down":
            return sorted(pool, reverse=True)
        if order == "updown":
            asc = sorted(pool)
            return asc + asc[-2:0:-1]
        shuffled = list(pool)
        self.rng.shuffle(shuffled)
        return shuffled

    # ------------------------------------------------------------------ #
    # Chord stabs — staccato stacked voicings on a rhythmic grid
    # ------------------------------------------------------------------ #
    def generate_stab(
        self,
        progression,
        scale_pcs: Set[int],
        role: str = "stab",
        plan=None,
        complexity: str = "medium",
        base_velocity: int = 100,
    ) -> list:
        """Return staccato chord hits (3-4 voices) on each rhythm onset."""
        role_range = self.config["role_ranges"][role]
        default_section = self.config.get("section_template", ["drop"])[0]
        params = self.config.get("role_params", {}).get("stab", {})
        duration = float(params.get("duration_beat", 0.4))
        velocity_boost = int(params.get("velocity_boost", 8))

        notes = []
        prev_voicing = None
        for bar, chord in enumerate(progression):
            profile = plan[bar] if plan else None
            density = profile.density if profile else 1.0
            register_shift = profile.register_shift if profile else 0
            velocity_base = profile.base_velocity if profile else base_velocity
            section = profile.name if profile else default_section
            shifted = {
                "min": role_range["min"] + register_shift * 12,
                "max": role_range["max"] + register_shift * 12,
            }
            voicing = self._smooth_voicing(chord, shifted, prev_voicing)
            prev_voicing = voicing

            patterns = self._patterns_for(role, complexity, density)
            rhythm = patterns[bar % 2] if len(patterns) > 1 else patterns[0]
            velocity = min(127, velocity_base + velocity_boost)
            for onset, _ in self._onsets_from_pattern(rhythm):
                for pitch in voicing:
                    pitch = snap_pitch_to_scale(pitch, scale_pcs)
                    while pitch < shifted["min"]:
                        pitch += 12
                    while pitch > shifted["max"]:
                        pitch -= 12
                    notes.append(
                        Note(
                            pitch=pitch,
                            start_beat=bar * BEATS_PER_BAR + onset,
                            duration_beat=duration,
                            velocity=velocity,
                            section=section,
                            role=role,
                        )
                    )
        return notes

    # ------------------------------------------------------------------ #
    # Counter lead — a delayed, harmonically related answering voice
    # ------------------------------------------------------------------ #
    def generate_counter_lead(
        self,
        progression,
        scale_pcs: Set[int],
        role: str = "counter_lead",
        plan=None,
        complexity: str = "medium",
        base_velocity: int = 88,
    ) -> list:
        """Return a second melodic voice that answers the main lead.

        Uses its own sparse rhythm profile, then shifts the whole line by
        ``role_params["counter_lead"]["delay_beats"]`` (call & response)
        and optionally transposes it so it harmonizes with the lead.
        """
        params = self.config.get("role_params", {}).get("counter_lead", {})
        delay_beats = float(params.get("delay_beats", 1.0))
        transpose = int(params.get("transpose", 0))
        velocity_scale = float(params.get("velocity_scale", 0.9))

        notes = self.generate_bassline(
            progression, scale_pcs, role=role, plan=plan,
            complexity=complexity, base_velocity=base_velocity,
            allow_passing=True,
        )
        role_range = self.config["role_ranges"][role]
        for note in notes:
            note.start_beat += delay_beats
            note.start_beat = max(0.0, note.start_beat)
            if transpose:
                note.pitch = snap_pitch_to_scale(
                    note.pitch + transpose, scale_pcs
                )
                low, high = role_range["min"], role_range["max"]
                while note.pitch < low:
                    note.pitch += 12
                while note.pitch > high:
                    note.pitch -= 12
            note.velocity = max(1, min(127, int(note.velocity * velocity_scale)))
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

    def _motif_to_intervals(self, steps, root_pc, scale_pcs) -> list:
        """Convert a scale-step contour into semitone offsets from the root.

        Each step moves one scale tone up/down along the active scale,
        so the motif stays in key while reading as a real melodic theme.
        """
        scale = sorted(scale_pcs)
        if (root_pc % 12) not in scale:
            return [0] * len(steps)
        idx = scale.index(root_pc % 12)
        intervals = []
        for step in steps:
            idx += int(step)
            pc = scale[idx % len(scale)]
            iv = (pc - root_pc) % 12
            if iv > 6:
                iv -= 12
            intervals.append(iv)
        return intervals

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
        """Pick chord tones with smooth motion via cost-based voicing selection."""
        candidate = voice_chord(chord, prev_voicing, role_range)
        if candidate.pitches:
            return candidate.pitches
        # Fallback: basic voicing if no candidates generated
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
