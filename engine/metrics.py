"""Composition metrics — quick numeric judgement without a DAW.

Produces per-track and per-section statistics so the output can be sanity
checked at a glance (density, register, velocity, motion, consonance).
Reuses the same interval vocabulary as the Layer 4 selector.
"""

from .selector import DISSONANT_INTERVALS

BEATS_PER_BAR = 4.0


def _dissonance_rate(notes: list) -> float:
    ordered = sorted(notes, key=lambda n: n.start_beat)
    if len(ordered) < 2:
        return 0.0
    dissonant = 0
    total = 0
    for i in range(len(ordered) - 1):
        d = abs(ordered[i + 1].pitch - ordered[i].pitch) % 12
        if min(d, 12 - d) in DISSONANT_INTERVALS:
            dissonant += 1
        total += 1
    return dissonant / total


def _mean_leap(notes: list) -> float:
    ordered = sorted(notes, key=lambda n: n.start_beat)
    if len(ordered) < 2:
        return 0.0
    leaps = [
        abs(ordered[i + 1].pitch - ordered[i].pitch) for i in range(len(ordered) - 1)
    ]
    return sum(leaps) / len(leaps)


def _bar_map(notes: list) -> dict:
    bars = {}
    for n in notes:
        bars.setdefault(int(n.start_beat // BEATS_PER_BAR), []).append(n)
    return bars


def analyze_track(track, num_bars: int = None) -> dict:
    """Return per-track stats for one :class:`Track`."""
    notes = track.notes
    if not notes:
        return {
            "role": track.role,
            "notes": 0, "density": 0.0, "pitch_min": 0, "pitch_max": 0,
            "pitch_span": 0, "avg_velocity": 0.0,
            "mean_leap": 0.0, "dissonance_rate": 0.0,
        }
    bars = _bar_map(notes)
    num_bars = num_bars or (max(bars) + 1)
    return {
        "role": track.role,
        "notes": len(notes),
        "density": round(len(notes) / num_bars, 2),
        "pitch_min": min(n.pitch for n in notes),
        "pitch_max": max(n.pitch for n in notes),
        "pitch_span": max(n.pitch for n in notes) - min(n.pitch for n in notes),
        "avg_velocity": round(sum(n.velocity for n in notes) / len(notes), 1),
        "mean_leap": round(_mean_leap(notes), 1),
        "dissonance_rate": round(_dissonance_rate(notes), 3),
    }


def analyze_sections(tracks: list, plan: list) -> list:
    """Aggregate note counts + density per section across all tracks."""
    if not plan:
        return []
    out = []
    for sb in plan:
        bar_notes = 0
        for track in tracks:
            bar_notes += sum(
                1 for n in track.notes if int(n.start_beat // BEATS_PER_BAR) == sb.bar
            )
        out.append(
            {
                "bar": sb.bar,
                "section": sb.name,
                "notes": bar_notes,
                "density": round(bar_notes / max(1, len(tracks)), 2),
            }
        )
    return out


def analyze_composition(tracks: list, plan: list) -> dict:
    """Full report: summary + per-track stats + per-section table."""
    num_bars = len(plan) or None
    track_stats = [analyze_track(t, num_bars) for t in tracks]
    total_notes = sum(s["notes"] for s in track_stats)
    summary = {
        "bars": num_bars or 0,
        "tracks": len(tracks),
        "total_notes": total_notes,
        "avg_density": round(total_notes / num_bars, 2) if num_bars else 0.0,
    }
    return {
        "summary": summary,
        "tracks": track_stats,
        "sections": analyze_sections(tracks, plan),
    }
