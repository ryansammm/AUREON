"""General MIDI (GM Level 1) instrument/drum maps and import mapping.

Parses Program Change + channel from a .mid file and maps each channel to the
internal role/preset system (engine instrument_intent vocabulary), falling back
to generic instruments for unknown/out-of-range programs.
"""

from dataclasses import dataclass, field

# ───────────────────────── GM Instrument Patch Map ─────────────────────────
# Official GM Level 1 order: index == MIDI program number (0-127).
GM_INSTRUMENTS = [
    "Acoustic Grand Piano", "Bright Acoustic Piano", "Electric Grand Piano",
    "Honky-tonk Piano", "Electric Piano 1", "Electric Piano 2",
    "Harpsichord", "Clavinet", "Celesta", "Glockenspiel", "Music Box",
    "Vibraphone", "Marimba", "Xylophone", "Tubular Bells", "Dulcimer",
    "Drawbar Organ", "Percussive Organ", "Rock Organ", "Church Organ",
    "Reed Organ", "Accordion", "Harmonica", "Tango Accordion",
    "Acoustic Guitar (nylon)", "Acoustic Guitar (steel)",
    "Electric Guitar (jazz)", "Electric Guitar (clean)",
    "Electric Guitar (muted)", "Overdriven Guitar", "Distortion Guitar",
    "Guitar Harmonics", "Acoustic Bass", "Electric Bass (finger)",
    "Electric Bass (pick)", "Fretless Bass", "Slap Bass 1", "Slap Bass 2",
    "Synth Bass 1", "Synth Bass 2", "Violin", "Viola", "Cello",
    "Contrabass", "Tremolo Strings", "Pizzicato Strings", "Orchestral Harp",
    "Timpani", "String Ensemble 1", "String Ensemble 2", "Synth Strings 1",
    "Synth Strings 2", "Choir Aahs", "Voice Oohs", "Synth Voice",
    "Orchestra Hit", "Trumpet", "Trombone", "Tuba", "Muted Trumpet",
    "French Horn", "Brass Section", "Synth Brass 1", "Synth Brass 2",
    "Soprano Sax", "Alto Sax", "Tenor Sax", "Baritone Sax", "Oboe",
    "English Horn", "Bassoon", "Clarinet", "Piccolo", "Flute", "Recorder",
    "Pan Flute", "Blown Bottle", "Shakuhachi", "Whistle", "Ocarina",
    "Lead 1 (square)", "Lead 2 (sawtooth)", "Lead 3 (calliope)",
    "Lead 4 (chiff)", "Lead 5 (charang)", "Lead 6 (voice)",
    "Lead 7 (fifths)", "Lead 8 (bass + lead)", "Pad 1 (new age)",
    "Pad 2 (warm)", "Pad 3 (polysynth)", "Pad 4 (choir)", "Pad 5 (bowed)",
    "Pad 6 (metallic)", "Pad 7 (halo)", "Pad 8 (sweep)", "FX 1 (rain)",
    "FX 2 (soundtrack)", "FX 3 (crystal)", "FX 4 (atmosphere)",
    "FX 5 (brightness)", "FX 6 (goblins)", "FX 7 (echoes)", "FX 8 (sci-fi)",
    "Sitar", "Banjo", "Shamisen", "Koto", "Kalimba", "Bag pipe", "Fiddle",
    "Shanai", "Tinkle Bell", "Agogo", "Steel Drums", "Woodblock",
    "Taiko Drum", "Melodic Tom", "Synth Drum", "Reverse Cymbal",
    "Guitar Fret Noise", "Breath Noise", "Seashore", "Bird Tweet",
    "Telephone Ring", "Helicopter", "Applause", "Gunshot",
]

# Program ranges grouped into broad GM categories (program -> category).
GM_CATEGORIES = [
    (0, 7, "piano"), (8, 15, "chromatic_percussion"), (16, 23, "organ"),
    (24, 31, "guitar"), (32, 39, "bass"), (40, 51, "strings"),
    (52, 55, "choir"), (56, 63, "brass"), (64, 79, "reed_wind"),
    (80, 87, "synth_lead"), (88, 95, "synth_pad"), (96, 103, "fx"),
    (104, 111, "ethnic"), (112, 119, "percussive"), (120, 127, "sound_effect"),
]

# ─────────────────────────── GM Drum Map (35-81) ───────────────────────────
# GM drum note -> name. Channel 9 (10th) is always drums.
GM_DRUMS = {
    35: "Acoustic Bass Drum", 36: "Bass Drum 1", 37: "Side Stick",
    38: "Acoustic Snare", 39: "Hand Clap", 40: "Electric Snare",
    41: "Low Floor Tom", 42: "Closed Hi Hat", 43: "High Floor Tom",
    44: "Pedal Hi-Hat", 45: "Low Tom", 46: "Open Hi-Hat", 47: "Low-Mid Tom",
    48: "Hi-Mid Tom", 49: "Crash Cymbal 1", 50: "High Tom",
    51: "Ride Cymbal 1", 52: "Chinese Cymbal", 53: "Ride Bell",
    54: "Tambourine", 55: "Splash Cymbal", 56: "Cowbell",
    57: "Crash Cymbal 2", 58: "Vibraslap", 59: "Ride Cymbal 2",
    60: "Hi Bongo", 61: "Low Bongo", 62: "Mute Hi Conga",
    63: "Open Hi Conga", 64: "Low Conga", 65: "High Timbale",
    66: "Low Timbale", 67: "High Agogo", 68: "Low Agogo", 69: "Cabasa",
    70: "Maracas", 71: "Short Whistle", 72: "Long Whistle",
    73: "Short Guiro", 74: "Long Guiro", 75: "Claves",
    76: "Hi Wood Block", 77: "Low Wood Block", 78: "Mute Cuica",
    79: "Open Cuica", 80: "Mute Triangle", 81: "Open Triangle",
}

GM_DRUM_CATEGORY = {
    "kick": (35, 36), "snare": (37, 38, 40), "hat": (42, 44, 46),
    "tom": (41, 43, 45, 47, 48, 50), "cymbal": (49, 51, 52, 53, 55, 57, 59),
    "perc": tuple(range(54, 82)),
}

# GM channel for drums (0-indexed 10th channel).
GM_DRUM_CHANNEL = 9


# ─────────────────────────── internal role mapping ─────────────────────────
# GM category -> (internal role, suggested preset from the system vocabulary).
CATEGORY_MAP = {
    "piano": ("chord", "chord_synth / rhodes"),
    "chromatic_percussion": ("arp", "pluck_synth / arp_synth"),
    "organ": ("chord", "chord_synth / rhodes"),
    "guitar": ("lead", "pluck_lead"),
    "bass": ("bass", "generic_bass"),
    "strings": ("pad", "string_pad / warm_pad"),
    "choir": ("pad", "warm_pad / string_pad"),
    "brass": ("lead", "bright_lead"),
    "reed_wind": ("lead", "soft_lead"),
    "synth_lead": ("lead", "lead_synth / saw_stack"),
    "synth_pad": ("pad", "pad_synth / dark_pad"),
    "fx": ("arp", "pluck_synth / arp_synth"),
    "ethnic": ("lead", "soft_lead"),
    "percussive": ("arp", "electronic_percussion"),
    "sound_effect": ("arp", "electronic_percussion"),
}

# Synth bass programs get the sub-bass treatment; acoustic bass stays generic.
SYNTH_BASS_PROGRAMS = (38, 39)


def category_of(program):
    for start, end, cat in GM_CATEGORIES:
        if start <= program <= end:
            return cat
    return None


def instrument_name(program):
    """GM name for a program number, or None when out of 0-127 range."""
    if 0 <= program < len(GM_INSTRUMENTS):
        return GM_INSTRUMENTS[program]
    return None


def map_program_to_plugin(program):
    """Map a GM program (0-127) to (internal_role, suggested_preset).

    Falls back to the generic lead for unknown/out-of-range programs.
    """
    if not (0 <= program < 128):
        return "lead", "generic_lead"
    if program in SYNTH_BASS_PROGRAMS:
        return "bass", "sub_bass / analog_synth"
    cat = category_of(program)
    if cat and cat in CATEGORY_MAP:
        return CATEGORY_MAP[cat]
    return "lead", "generic_lead"


def map_drum_channel(role="drum"):
    """Internal plugin for a GM drum channel."""
    return role, "acoustic_kit / electronic_kit"


_NAME_ROLE_HINTS = [
    ("sub bass", "sub_bass"), ("sub", "sub_bass"), ("bass", "bass"),
    ("counter lead", "counter_lead"), ("counter", "counter_lead"),
    ("drums", "drum"), ("drum", "drum"), ("percussion", "drum_layers"),
    ("chord", "chord"), ("lead", "lead"), ("pluck", "lead"), ("stab", "stab"),
    ("arp", "arp"), ("pad", "pad"),
]
_NAME_ROLE_PRESETS = {
    "sub_bass": "sub_bass / sine", "bass": "generic_bass",
    "counter_lead": "lead_synth_2 / square", "drum": "electronic_kit",
    "drum_layers": "electronic_percussion", "lead": "lead_synth / saw_stack",
    "arp": "pluck_synth / arp_synth", "stab": "chord_stab / detuned_synth",
    "chord": "chord_synth / rhodes", "pad": "pad_synth / dark_pad",
}


def role_from_track_name(track_name):
    """Guess an internal role from a human-readable track name, or None."""
    lowered = (track_name or "").lower()
    for keyword, role in _NAME_ROLE_HINTS:
        if keyword in lowered:
            return role
    return None


def drum_hit_category(note):
    """Classify a drum note into kick/snare/hat/tom/cymbal/perc (or None)."""
    for cat, notes in GM_DRUM_CATEGORY.items():
        if note in notes:
            return cat
    return None


# ─────────────────────────────── MIDI parser ───────────────────────────────
@dataclass
class ChannelStats:
    channel: int
    program: int = 0
    program_events: int = 0
    note_count: int = 0
    note_min: int = 127
    note_max: int = 0
    pitchbend: bool = False
    sustain_cc64: bool = False
    drum_hits: dict = field(default_factory=dict)


def _walk_track(track, ticks_per_beat, stats):
    """Collect per-channel stats from one mido track."""
    import mido

    now = 0
    for msg in track:
        now += msg.time
        if msg.is_meta or msg.type == "end_of_track":
            continue
        ch = getattr(msg, "channel", None)
        if ch is None:
            continue
        s = stats.setdefault(ch, ChannelStats(channel=ch))
        if msg.type == "program_change":
            s.program = msg.program
            s.program_events += 1
        elif msg.type == "note_on":
            if msg.velocity == 0:
                continue
            s.note_count += 1
            s.note_min = min(s.note_min, msg.note)
            s.note_max = max(s.note_max, msg.note)
            if ch == GM_DRUM_CHANNEL:
                cat = drum_hit_category(msg.note)
                s.drum_hits[cat or f"note{msg.note}"] = (
                    s.drum_hits.get(cat or f"note{msg.note}", 0) + 1
                )
        elif msg.type == "pitchwheel":
            s.pitchbend = True
        elif msg.type == "control_change" and msg.control == 64:
            s.sustain_cc64 = True


def parse_midi_channels(path):
    """Parse a .mid file and return one entry per channel that plays notes.

    Each entry: dict with track info, channel (0-indexed), GM program,
    instrument name/category, whether it's the GM drum channel, note range,
    and CC/pitch-bend flags. Velocity and sustain/pitch-bend data are only
    inspected, never modified.
    """
    import mido

    mid = mido.MidiFile(str(path))
    entries = []
    for idx, track in enumerate(mid.tracks):
        stats = {}
        _walk_track(track, mid.ticks_per_beat, stats)
        for ch, s in sorted(stats.items(), key=lambda kv: kv[1].note_count, reverse=True):
            if s.note_count == 0:
                continue
            is_drum = ch == GM_DRUM_CHANNEL
            if is_drum:
                role, preset = map_drum_channel()
            elif s.program_events > 0:
                role, preset = map_program_to_plugin(s.program)
            else:
                hint = role_from_track_name(track.name)
                role, preset = (
                    (hint, _NAME_ROLE_PRESETS[hint])
                    if hint
                    else map_program_to_plugin(s.program)
                )
            entries.append(
                {
                    "track_index": idx,
                    "track_name": track.name or f"Track {idx + 1}",
                    "channel": ch,
                    "program": s.program,
                    "program_events": s.program_events,
                    "instrument": "GM Drum" if is_drum else instrument_name(s.program),
                    "category": None if is_drum else category_of(s.program),
                    "is_drum_channel": is_drum,
                    "role": role,
                    "preset": preset,
                    "note_count": s.note_count,
                    "note_min": s.note_min,
                    "note_max": s.note_max,
                    "pitchbend": s.pitchbend,
                    "sustain_cc64": s.sustain_cc64,
                    "drum_hits": s.drum_hits or None,
                    "gm_compliant": s.program < 128,
                }
            )
    return entries


def analyze_midi(path):
    """Full report: entries plus a non-GM-compliance warning list."""
    entries = parse_midi_channels(path)
    warnings = []
    for e in entries:
        if e["program_events"] == 0:
            warnings.append(
                f"Track {e['track_index'] + 1} ({e['track_name']}): no Program "
                f"Change — defaulted to program 0 ({instrument_name(0)})."
            )
        elif not e["gm_compliant"]:
            warnings.append(
                f"Track {e['track_index'] + 1} ({e['track_name']}): program "
                f"{e['program']} outside GM standard (custom soundfont?)."
            )
        elif e["is_drum_channel"] and any(
            not (35 <= note <= 81) for note in _drum_note_keys(e)
        ):
            warnings.append(
                f"Track {e['track_index'] + 1} ({e['track_name']}): drum channel "
                f"contains notes outside GM drum range 35-81 (non-standard kit)."
            )
    return {"channels": entries, "warnings": warnings}


def _drum_note_keys(entry):
    hits = entry.get("drum_hits") or {}
    keys = []
    for k, v in hits.items():
        if k.startswith("note") and k[4:].isdigit():
            keys.append(int(k[4:]))
    return keys
