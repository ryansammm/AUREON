"""End-to-end pipeline (Phase 2).

Wires Layer 0 -> 1 -> 2 -> 3 -> 6 into one call so the CLI and
integration tests share a single path. Selector (Layer 4) and
humanization (Layer 5) land in later phases and slot in here.
"""

import random

from .arrangement import ArrangementEngine
from .drums import DrumEngine
from .harmony import HarmonicEngine
from .humanizer import Humanizer
from .melody import MelodicEngine, CHORD_ROLES
from .models import Track
from .music_utils import get_scale_pitch_classes


def build_tempo_map(config: dict, plan: list, bpm: int) -> list:
    """Build ``[(beat, bpm), ...]`` from per-section tempo multipliers.

    Sections not listed in ``config["section_tempo"]`` keep the base tempo;
    only actual tempo changes are emitted.

    Returns:
        List of ``(beat, bpm)`` tuples, sorted by beat.
    """
    section_tempo = config.get("section_tempo") or {}
    tempo_map = []
    current = bpm
    for sb in plan:
        mult = section_tempo.get(sb.name, 1.0)
        section_bpm = int(round(bpm * mult))
        if section_bpm != current:
            tempo_map.append((sb.bar * 4.0, section_bpm))
            current = section_bpm
    return tempo_map


def apply_modulations(config: dict, tracks: list, plan: list) -> list:
    """Transpose whole sections by ``semitones`` (post-generation).

    Reads ``config["modulations"]`` (e.g. ``[{"section": "drop2",
    "semitones": 1}]``) and shifts every note whose bar belongs to that
    section. The uniform shift keeps all intervals intact, so the section
    stays in the new (transposed) key.

    Returns:
        The same ``tracks`` list, mutated.
    """
    for mod in config.get("modulations") or []:
        section = mod["section"]
        semitones = int(mod.get("semitones", 0))
        if semitones == 0:
            continue
        bar_bounds = [
            sb.bar for sb in plan if sb.name == section
        ]
        if not bar_bounds:
            continue
        for track in tracks:
            if getattr(track, "role", "") == "drum":
                continue
            for note in track.notes:
                bar = int(note.start_beat // 4.0)
                if bar in bar_bounds:
                    note.pitch = max(0, min(127, note.pitch + semitones))
    return tracks


def pick_scale_from_pool(config: dict, mode: str, seed: int = None) -> str:
    """Pick the active scale from the genre config's scale pool."""
    pool = config.get("scale_pool") or []
    if not pool:
        return "natural_minor" if mode == "minor" else "major"
    rng = random.Random(seed)
    return rng.choice(pool)


def build_cc_automation(config: dict, plan: list, role: str) -> list:
    """Build per-bar CC automation (filter cutoff + expression) from the plan.

    Follows the Layer 3 energy curve so the arrangement's shape is audible
    through the sound (brightness opens up in drops, expression follows the
    section's base velocity). Percussion gets no automation.

    Returns:
        List of ``(start_beat, cc_number, value)`` tuples.
    """
    if role == "drum":
        return []
    cfg = config.get("automation") or {}
    if cfg.get("enabled") is False:
        return []
    low, high = cfg.get("cc74_range", [20, 120])
    use_cc11 = cfg.get("cc11", True)
    cc = []
    for sb in plan:
        bar_beat = sb.bar * 4.0
        cutoff = int(low + (high - low) * sb.density)
        cc.append((bar_beat, 74, max(0, min(127, cutoff))))
        if use_cc11:
            expr = int(40 + 87 * sb.base_velocity / 127.0)
            cc.append((bar_beat, 11, max(0, min(127, expr))))
    return cc


def generate_track(
    config: dict,
    role: str,
    key_root: str,
    mode: str,
    bars: int = None,
    complexity: str = "medium",
    seed: int = None,
    scale_name: str = None,
    humanize: bool = True,
    bpm: int = None,
):
    """Generate one track (arrangement + progression + bassline) for a role.

    Args:
        config: genre config from :func:`load_genre_config`.
        role: instrument role key defined in ``role_ranges``.
        key_root: tonic letter, e.g. ``"a"``.
        mode: ``"minor"`` or ``"major"``.
        bars: requested length; ``None`` uses the full section template.
        complexity: user ceiling — ``simple`` / ``medium`` / ``complex``.
        seed: random seed for reproducibility.
        scale_name: force a scale from the config pool.
        humanize: apply Layer 5 humanization to the generated notes.
        bpm: tempo (for micro-timing); defaults to the config value.

    Returns:
        Tuple of (``Track``, list of :class:`ChordBar`, list of
        :class:`SectionBar`).
    """
    if role != "drum" and role not in config["role_ranges"]:
        raise ValueError(
            f"role '{role}' not defined in genre config "
            f"(available: {sorted(config['role_ranges']) + ['drum']})"
        )
    bpm = bpm or config["default_bpm"]
    scale_name = scale_name or pick_scale_from_pool(config, mode, seed)
    scale_pcs = get_scale_pitch_classes(key_root, mode, scale_name)

    arrangement = ArrangementEngine(config)
    plan = arrangement.build_plan(bars)

    harmony = HarmonicEngine(config, seed)
    progression = harmony.generate_progression(key_root, mode, len(plan))

    melody = MelodicEngine(config, seed)
    if role == "drum":
        notes = []
    else:
        notes = melody.generate_bassline(
            progression, scale_pcs, role=role, plan=plan, complexity=complexity
        )

    if humanize and notes:
        Humanizer(config, seed).humanize(notes, bpm)

    if role == "drum":
        track = DrumEngine(config, seed).generate_track(
            plan, humanize=humanize, bpm=bpm, seed=seed
        )
    else:
        intent = config["instrument_intent"][role]
        track = Track(
            role=role,
            track_name=intent["label"],
            suggested_preset=intent["preset"],
            notes=notes,
        )
    track.cc = build_cc_automation(config, plan, role)
    apply_modulations(config, [track], plan)
    return track, progression, plan


def generate_composition(
    config: dict,
    roles: list,
    key_root: str,
    mode: str,
    bars: int = None,
    complexity: str = "medium",
    seed: int = None,
    scale_name: str = None,
    humanize: bool = True,
    bpm: int = None,
):
    """Generate several tracks (e.g. bass + lead + chord) at once.

    All roles share the same arrangement plan and chord progression, so
    the result is one coherent composition. Rhythm-clash avoidance comes
    from distinct per-role rhythm profiles in the genre config and from
    register separation (bass low, chord mid, lead high).

    Returns:
        Tuple of (list of :class:`Track`, list of :class:`ChordBar`,
        list of :class:`SectionBar`).
    """
    if not roles:
        raise ValueError("roles must not be empty")
    for role in roles:
        if role != "drum" and role not in config["role_ranges"]:
            raise ValueError(
                f"role '{role}' not defined in genre config "
                f"(available: {sorted(config['role_ranges']) + ['drum']})"
            )
    bpm = bpm or config["default_bpm"]
    scale_name = scale_name or pick_scale_from_pool(config, mode, seed)
    scale_pcs = get_scale_pitch_classes(key_root, mode, scale_name)

    arrangement = ArrangementEngine(config)
    plan = arrangement.build_plan(bars)

    harmony = HarmonicEngine(config, seed)
    progression = harmony.generate_progression(key_root, mode, len(plan))

    melody = MelodicEngine(config, seed)
    tracks = []
    for role in roles:
        if role == "drum":
            track = DrumEngine(config, seed).generate_track(
                plan, humanize=humanize, bpm=bpm, seed=seed
            )
            track.cc = build_cc_automation(config, plan, role)
            tracks.append(track)
            continue
        if role in CHORD_ROLES:
            notes = melody.generate_chord_track(
                progression, scale_pcs, role=role, plan=plan
            )
        elif role == "lead":
            notes = melody.generate_bassline(
                progression, scale_pcs, role=role, plan=plan,
                complexity=complexity, allow_passing=True,
            )
        else:
            notes = melody.generate_bassline(
                progression, scale_pcs, role=role, plan=plan,
                complexity=complexity,
            )
        if humanize:
            Humanizer(config, seed).humanize(notes, bpm)
        intent = config["instrument_intent"][role]
        track = Track(
            role=role,
            track_name=intent["label"],
            suggested_preset=intent["preset"],
            notes=notes,
        )
        track.cc = build_cc_automation(config, plan, role)
        tracks.append(track)
    apply_modulations(config, tracks, plan)
    return tracks, progression, plan
