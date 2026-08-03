"""Layer 6 — MIDI Export.

Writes standard Type-1 multi-track MIDI files readable by all major DAWs
(Ableton, FL Studio, Logic, Cubase). Track names carry instrument-intent
labels (FR-8); tempo and time signature live in track 0.

Musical assumption: note ``start_beat``/``duration_beat`` are quarter-note
beats, so tick = beat * ``ticks_per_beat``.
"""

import mido
from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo

DEFAULT_TICKS_PER_BEAT = 480


def export_midi(
    tracks,
    bpm: int,
    output_path: str,
    time_signature=(4, 4),
    ticks_per_beat: int = DEFAULT_TICKS_PER_BEAT,
    tempo_map: list = None,
) -> str:
    """Write ``tracks`` to a Type-1 MIDI file at ``output_path``.

    Args:
        tracks: iterable of :class:`Track` (one MIDI track per role).
        bpm: tempo in beats per minute (used when ``tempo_map`` is None).
        output_path: destination ``.mid`` path.
        time_signature: (numerator, denominator).
        ticks_per_beat: MIDI resolution.
        tempo_map: optional list of ``(beat, bpm)`` tempo changes written
            as consecutive ``set_tempo`` meta events (mid-song tempo
            automation).

    Returns:
        The resolved ``output_path`` string.
    """
    mid = MidiFile(ticks_per_beat=ticks_per_beat, type=1)

    meta_track = MidiTrack()
    meta_track.append(MetaMessage("track_name", name="Composition"))
    entries = {0: bpm}
    for beat, tempo_bpm in tempo_map or []:
        entries[beat] = int(tempo_bpm)
    elapsed = 0
    for beat, tempo_bpm in sorted(entries.items()):
        tick = int(round(beat * ticks_per_beat))
        delta = max(tick - elapsed, 0)
        meta_track.append(MetaMessage("set_tempo", tempo=bpm2tempo(int(tempo_bpm)), time=delta))
        elapsed = tick
    meta_track.append(
        MetaMessage(
            "time_signature",
            numerator=int(time_signature[0]),
            denominator=int(time_signature[1]),
        )
    )
    meta_track.append(MetaMessage("end_of_track"))
    mid.tracks.append(meta_track)

    for track in tracks:
        mid.tracks.append(_build_role_track(track, ticks_per_beat))

    mid.save(output_path)
    return output_path


def _build_role_track(track, ticks_per_beat: int) -> MidiTrack:
    mt = MidiTrack()
    mt.append(MetaMessage("track_name", name=track.track_name))

    channel = getattr(track, "channel", 0) or 0

    events = []
    for note in track.notes:
        on_tick = int(round(note.start_beat * ticks_per_beat))
        off_tick = on_tick + int(round(note.duration_beat * ticks_per_beat))
        velocity = max(1, min(127, int(note.velocity)))
        events.append((on_tick, "on", note.pitch, velocity))
        events.append((off_tick, "off", note.pitch, 0))

    for start_beat, cc_number, value in getattr(track, "cc", []):
        tick = int(round(start_beat * ticks_per_beat))
        events.append((tick, "cc", int(cc_number), max(0, min(127, int(value)))))

    events.sort(key=lambda e: (e[0], {"off": 0, "cc": 1, "on": 2}[e[1]]))
    elapsed = 0
    for tick, kind, first, second in events:
        delta = max(tick - elapsed, 0)
        if kind == "on":
            mt.append(
                Message(
                    "note_on", note=first, velocity=second,
                    time=delta, channel=channel,
                )
            )
        elif kind == "off":
            mt.append(
                Message(
                    "note_off", note=first, velocity=0,
                    time=delta, channel=channel,
                )
            )
        else:
            mt.append(
                Message(
                    "control_change", control=first, value=second,
                    time=delta, channel=channel,
                )
            )
        elapsed = tick

    mt.append(MetaMessage("end_of_track"))
    return mt
