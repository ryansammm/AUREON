"""Generate 25 sub-genre JSON config files under config/genres/."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "config" / "genres"

SUBGENRES = [
    # (filename, parent_genre, overrides dict)
    # --- Techno sub-genres ---
    ("minimal_techno", "techno", {
        "default_bpm": 128,
        "swing": {"resolution": 16, "amount": 0.03},
        "section_density": {"intro": 0.2, "breakdown": 0.25, "build": 0.55, "drop": 0.8, "drop2": 0.8, "outro": 0.25},
        "section_velocity": {"intro": 68, "breakdown": 72, "build": 85, "drop": 96, "drop2": 96, "outro": 66},
        "instrument_intent": {
            "bass": {"label": "Bass - Minimal (Techno)", "preset": "sub_bass / sine"},
            "lead": {"label": "Lead - Minimal (Techno)", "preset": "pluck_synth"},
            "pad": {"label": "Pad - Texture (Minimal)", "preset": "dark_pad"},
            "drum": {"label": "Drums - Minimal (Techno)", "preset": "909_kit"},
        },
    }),
    ("acid_techno", "techno", {
        "default_bpm": 140,
        "swing": {"resolution": 16, "amount": 0.08},
        "section_density": {"intro": 0.4, "breakdown": 0.3, "build": 0.75, "drop": 1.0, "drop2": 1.0, "outro": 0.35},
        "section_velocity": {"intro": 78, "breakdown": 82, "build": 94, "drop": 108, "drop2": 108, "outro": 74},
        "instrument_intent": {
            "bass": {"label": "Bass - Acid 303 (Techno)", "preset": "acid_bass / 303"},
            "lead": {"label": "Lead - Acid Stab (Techno)", "preset": "acid_synth / 303"},
            "pad": {"label": "Pad - Distorted (Acid)", "preset": "dark_pad / detuned"},
            "drum": {"label": "Drums - Driving (Acid)", "preset": "909_kit / distorted"},
        },
    }),
    ("detroit_techno", "techno", {
        "default_bpm": 130,
        "swing": {"resolution": 16, "amount": 0.06},
        "scale_pool": ["dorian", "lydian"],
        "section_velocity": {"intro": 72, "breakdown": 78, "build": 88, "drop": 100, "drop2": 100, "outro": 70},
        "instrument_intent": {
            "bass": {"label": "Bass - Soul (Detroit)", "preset": "fm_bass / analog"},
            "lead": {"label": "Lead - Detroid (Techno)", "preset": "lead_synth / saw"},
            "pad": {"label": "Pad - Warm (Detroit)", "preset": "warm_pad / strings"},
            "chord": {"label": "Chord - Jazzy (Detroit)", "preset": "rhodes / electric_piano"},
            "drum": {"label": "Drums - Classic (Detroit)", "preset": "909_kit"},
        },
    }),
    # --- Trance sub-genres ---
    ("progressive_trance", "trance", {
        "default_bpm": 132,
        "swing": {"resolution": 16, "amount": 0.04},
        "section_template": ["intro", "breakdown", "build", "drop", "drop2", "outro"],
        "section_bars": {"intro": 4, "breakdown": 4, "build": 4, "drop": 8, "drop2": 8, "outro": 4},
        "section_density": {"intro": 0.2, "breakdown": 0.25, "build": 0.55, "drop": 0.8, "drop2": 0.85, "outro": 0.2},
        "section_velocity": {"intro": 68, "breakdown": 72, "build": 88, "drop": 100, "drop2": 102, "outro": 66},
        "instrument_intent": {
            "bass": {"label": "Bass - Rolling (Progressive)", "preset": "analog_bass / rolling"},
            "lead": {"label": "Lead - Melodic (Progressive)", "preset": "saw_lead / pluck"},
            "pad": {"label": "Pad - Ethereal (Progressive)", "preset": "ethereal_pad / warm"},
            "drum": {"label": "Drums - Progressive", "preset": "progressive_kit / 909"},
        },
    }),
    ("uplifting_trance", "trance", {
        "default_bpm": 140,
        "swing": {"resolution": 16, "amount": 0.04},
        "section_density": {"intro": 0.3, "breakdown": 0.25, "build": 0.7, "drop": 1.0, "drop2": 1.0, "outro": 0.25},
        "section_velocity": {"intro": 72, "breakdown": 76, "build": 92, "drop": 110, "drop2": 110, "outro": 68},
        "instrument_intent": {
            "bass": {"label": "Bass - Offbeat (Uplifting)", "preset": "saw_bass / offbeat"},
            "lead": {"label": "Lead - Supersaw (Uplifting)", "preset": "supersaw / detuned"},
            "pad": {"label": "Pad - Anthem (Uplifting)", "preset": "anthem_pad / bright"},
            "arp": {"label": "Arp - Euphoric (Trance)", "preset": "pluck_synth / euphoric"},
            "drum": {"label": "Drums - Uplifting 4x4", "preset": "trance_kit / 909"},
        },
    }),
    ("psytrance", "trance", {
        "default_bpm": 145,
        "swing": {"resolution": 16, "amount": 0.02},
        "scale_pool": ["natural_minor", "phrygian", "harmonic_minor"],
        "section_density": {"intro": 0.4, "breakdown": 0.3, "build": 0.75, "drop": 1.0, "drop2": 1.0, "outro": 0.35},
        "section_velocity": {"intro": 76, "breakdown": 80, "build": 94, "drop": 112, "drop2": 112, "outro": 74},
        "instrument_intent": {
            "bass": {"label": "Bass - KBB (Psytrance)", "preset": "psy_bass / rolling"},
            "lead": {"label": "Lead - Acid (Psytrance)", "preset": "acid_synth / squelchy"},
            "arp": {"label": "Arp - Psy (Trance)", "preset": "psy_pluck / detuned"},
            "pad": {"label": "Pad - Dark (Psytrance)", "preset": "dark_pad / evolving"},
            "drum": {"label": "Drums - Psy 4x4", "preset": "psy_kit / 909"},
        },
    }),
    # --- House sub-genres ---
    ("deep_house", "house", {
        "default_bpm": 122,
        "swing": {"resolution": 8, "amount": 0.28},
        "scale_pool": ["dorian", "major", "mixolydian"],
        "section_velocity": {"intro": 68, "breakdown": 74, "build": 84, "drop": 94, "outro": 66},
        "instrument_intent": {
            "bass": {"label": "Bass - Deep (House)", "preset": "sub_bass / analog"},
            "lead": {"label": "Lead - Jazzy (Deep)", "preset": "epiano / rhodes"},
            "pad": {"label": "Pad - Warm (Deep)", "preset": "warm_pad / soft"},
            "chord": {"label": "Chord - Jazzy (Deep)", "preset": "rhodes / electric_piano"},
            "drum": {"label": "Drums - Deep House", "preset": "deep_kit / 909"},
        },
    }),
    ("tech_house", "house", {
        "default_bpm": 128,
        "swing": {"resolution": 8, "amount": 0.18},
        "section_density": {"intro": 0.35, "breakdown": 0.3, "build": 0.65, "drop": 0.9, "outro": 0.3},
        "section_velocity": {"intro": 74, "breakdown": 78, "build": 90, "drop": 102, "outro": 72},
        "instrument_intent": {
            "bass": {"label": "Bass - Rolling (Tech House)", "preset": "analog_bass / percussive"},
            "lead": {"label": "Lead - Stab (Tech House)", "preset": "stab_synth / percussive"},
            "pad": {"label": "Pad - Texture (Tech)", "preset": "dark_pad / minimal"},
            "drum": {"label": "Drums - Tech House 4x4", "preset": "tech_house_kit / 909"},
        },
    }),
    ("afro_house", "house", {
        "default_bpm": 124,
        "swing": {"resolution": 8, "amount": 0.32},
        "scale_pool": ["dorian", "mixolydian", "major"],
        "section_velocity": {"intro": 70, "breakdown": 76, "build": 86, "drop": 96, "outro": 68},
        "instrument_intent": {
            "bass": {"label": "Bass - Organic (Afro)", "preset": "analog_bass / percussive"},
            "lead": {"label": "Lead - Vocal Chop (Afro)", "preset": "vocal_chop / percussive"},
            "pad": {"label": "Pad - Warm (Afro)", "preset": "warm_pad / organic"},
            "chord": {"label": "Chord - Rhodes (Afro)", "preset": "rhodes / warm"},
            "drum": {"label": "Drums - Afro Percussion", "preset": "afro_kit / percussion"},
            "drum_layers": {"label": "Percussion - Afro", "preset": "conga / bongo / shaker"},
        },
    }),
    # --- Dubstep sub-genres ---
    ("riddim", "dubstep", {
        "default_bpm": 140,
        "swing": {"resolution": 16, "amount": 0.05},
        "scale_pool": ["natural_minor", "phrygian"],
        "section_density": {"intro": 0.25, "buildup": 0.5, "drop": 1.0, "breakdown": 0.15, "drop2": 1.0, "outro": 0.2},
        "instrument_intent": {
            "bass": {"label": "Bass - Metallic (Riddim)", "preset": "riddim_bass / metallic"},
            "lead": {"label": "Lead - Minimal (Riddim)", "preset": "pluck_synth / minimal"},
            "pad": {"label": "Pad - Dark (Riddim)", "preset": "dark_pad / sparse"},
            "drum": {"label": "Drums - Half-Time (Riddim)", "preset": "dubstep_kit / punchy"},
        },
    }),
    ("melodic_dubstep", "dubstep", {
        "default_bpm": 140,
        "swing": {"resolution": 16, "amount": 0.06},
        "scale_pool": ["natural_minor", "major"],
        "section_density": {"intro": 0.3, "buildup": 0.65, "drop": 0.95, "breakdown": 0.25, "drop2": 0.95, "outro": 0.3},
        "section_velocity": {"intro": 68, "buildup": 88, "drop": 104, "breakdown": 72, "drop2": 106, "outro": 66},
        "instrument_intent": {
            "bass": {"label": "Bass - Reece (Melodic)", "preset": "reece_bass / saw"},
            "lead": {"label": "Lead - Supersaw (Melodic)", "preset": "supersaw / detuned"},
            "pad": {"label": "Pad - Ethereal (Melodic)", "preset": "ethereal_pad / bright"},
            "arp": {"label": "Arp - Emotional (Dubstep)", "preset": "pluck_synth / emotional"},
            "drum": {"label": "Drums - Half-Time (Melodic)", "preset": "dubstep_kit / clean"},
        },
    }),
    ("brostep", "dubstep", {
        "default_bpm": 140,
        "swing": {"resolution": 16, "amount": 0.03},
        "section_density": {"intro": 0.35, "buildup": 0.7, "drop": 1.0, "breakdown": 0.2, "drop2": 1.0, "outro": 0.25},
        "section_velocity": {"intro": 74, "buildup": 92, "drop": 112, "breakdown": 78, "drop2": 114, "outro": 70},
        "instrument_intent": {
            "bass": {"label": "Bass - Wobble (Brostep)", "preset": "wobble_bass / growl"},
            "lead": {"label": "Lead - Aggressive (Brostep)", "preset": "lead_synth / distorted"},
            "pad": {"label": "Pad - Scary (Brostep)", "preset": "dark_pad / distorted"},
            "drum": {"label": "Drums - Aggressive (Brostep)", "preset": "dubstep_kit / distorted"},
        },
    }),
    # --- Drum and Bass sub-genres ---
    ("liquid_dnb", "drum_and_bass", {
        "default_bpm": 174,
        "swing": {"resolution": 16, "amount": 0.06},
        "scale_pool": ["dorian", "major", "mixolydian"],
        "section_density": {"intro": 0.25, "breakdown": 0.2, "build": 0.55, "drop": 0.8, "drop2": 0.85, "outro": 0.2},
        "section_velocity": {"intro": 66, "breakdown": 70, "build": 84, "drop": 96, "drop2": 98, "outro": 64},
        "instrument_intent": {
            "bass": {"label": "Bass - Reese (Liquid)", "preset": "reece_bass / smooth"},
            "lead": {"label": "Lead - Smooth (Liquid)", "preset": "saw_lead / soft"},
            "pad": {"label": "Pad - Warm (Liquid)", "preset": "warm_pad / lush"},
            "chord": {"label": "Chord - Jazz (Liquid)", "preset": "rhodes / electric_piano"},
            "arp": {"label": "Arp - Pluck (Liquid)", "preset": "pluck_synth / bright"},
            "drum": {"label": "Drums - Breakbeat (Liquid)", "preset": "dnb_kit / smooth"},
        },
    }),
    ("jump_up", "drum_and_bass", {
        "default_bpm": 174,
        "swing": {"resolution": 16, "amount": 0.03},
        "scale_pool": ["natural_minor", "phrygian"],
        "section_density": {"intro": 0.35, "breakdown": 0.25, "build": 0.7, "drop": 1.0, "drop2": 1.0, "outro": 0.3},
        "section_velocity": {"intro": 74, "breakdown": 78, "build": 94, "drop": 112, "drop2": 114, "outro": 72},
        "instrument_intent": {
            "bass": {"label": "Bass - Wobble (Jump Up)", "preset": "wobble_bass / distorted"},
            "lead": {"label": "Lead - Screech (Jump Up)", "preset": "lead_synth / screech"},
            "pad": {"label": "Pad - Dark (Jump Up)", "preset": "dark_pad"},
            "drum": {"label": "Drums - Punchy (Jump Up)", "preset": "dnb_kit / punchy"},
        },
    }),
    ("neurofunk", "drum_and_bass", {
        "default_bpm": 174,
        "swing": {"resolution": 16, "amount": 0.04},
        "scale_pool": ["phrygian", "natural_minor", "harmonic_minor"],
        "section_density": {"intro": 0.3, "breakdown": 0.2, "build": 0.65, "drop": 1.0, "drop2": 1.0, "outro": 0.25},
        "section_velocity": {"intro": 72, "breakdown": 76, "build": 90, "drop": 108, "drop2": 110, "outro": 68},
        "instrument_intent": {
            "bass": {"label": "Bass - Neuro (Funk)", "preset": "neuro_bass / distorted"},
            "lead": {"label": "Lead - Tech (Neuro)", "preset": "lead_synth / distorted"},
            "pad": {"label": "Pad - Dark (Neuro)", "preset": "dark_pad / evolving"},
            "drum": {"label": "Drums - Tight (Neurofunk)", "preset": "dnb_kit / tight"},
        },
    }),
    # --- Trap sub-genres ---
    ("drill", "trap", {
        "default_bpm": 140,
        "swing": {"resolution": 16, "amount": 0.1},
        "scale_pool": ["natural_minor", "phrygian"],
        "section_density": {"intro": 0.3, "breakdown": 0.5, "buildup": 0.65, "drop": 0.9, "outro": 0.25},
        "section_velocity": {"intro": 70, "breakdown": 82, "buildup": 88, "drop": 100, "outro": 66},
        "instrument_intent": {
            "bass": {"label": "Bass - 808 (Drill)", "preset": "808_bass / distorted"},
            "lead": {"label": "Lead - Pluck (Drill)", "preset": "pluck_synth / dark"},
            "pad": {"label": "Pad - Dark (Drill)", "preset": "dark_pad / minimal"},
            "drum": {"label": "Drums - Drill", "preset": "drill_kit / trap"},
        },
    }),
    ("cloud_rap", "trap", {
        "default_bpm": 130,
        "swing": {"resolution": 16, "amount": 0.08},
        "scale_pool": ["major", "dorian", "mixolydian"],
        "section_density": {"intro": 0.2, "breakdown": 0.4, "buildup": 0.5, "drop": 0.75, "outro": 0.2},
        "section_velocity": {"intro": 64, "breakdown": 76, "buildup": 82, "drop": 92, "outro": 62},
        "instrument_intent": {
            "bass": {"label": "Bass - Soft 808 (Cloud)", "preset": "808_bass / soft"},
            "lead": {"label": "Lead - Ethereal (Cloud)", "preset": "pluck_synth / ethereal"},
            "pad": {"label": "Pad - Dreamy (Cloud)", "preset": "warm_pad / dreamy"},
            "chord": {"label": "Chord - Lofi (Cloud)", "preset": "rhodes / filtered"},
            "drum": {"label": "Drums - Cloud", "preset": "trap_kit / soft"},
        },
    }),
    # --- Future Bass sub-genres ---
    ("kawaii_future_bass", "future_bass", {
        "default_bpm": 160,
        "swing": {"resolution": 16, "amount": 0.06},
        "scale_pool": ["major", "lydian"],
        "section_density": {"intro": 0.3, "breakdown": 0.25, "buildup": 0.6, "drop": 0.85, "outro": 0.25},
        "section_velocity": {"intro": 72, "breakdown": 76, "buildup": 90, "drop": 106, "outro": 70},
        "instrument_intent": {
            "bass": {"label": "Bass - Cute (Kawaii)", "preset": "sine_bass / soft"},
            "lead": {"label": "Lead - Chiptune (Kawaii)", "preset": "chiptune / square"},
            "pad": {"label": "Pad - Happy (Kawaii)", "preset": "warm_pad / bright"},
            "arp": {"label": "Arp - Bouncy (Kawaii)", "preset": "pluck_synth / cute"},
            "chord": {"label": "Chord - SuperSaw (Kawaii)", "preset": "supersaw / bright"},
            "drum": {"label": "Drums - Kawaii", "preset": "kawaii_kit / 808"},
        },
    }),
    ("future_ghettotech", "future_bass", {
        "default_bpm": 140,
        "swing": {"resolution": 16, "amount": 0.1},
        "scale_pool": ["natural_minor", "phrygian"],
        "section_density": {"intro": 0.35, "breakdown": 0.3, "buildup": 0.7, "drop": 0.95, "outro": 0.3},
        "section_velocity": {"intro": 76, "breakdown": 80, "buildup": 92, "drop": 108, "outro": 74},
        "instrument_intent": {
            "bass": {"label": "Bass - Heavy 808 (Ghetto)", "preset": "808_bass / distorted"},
            "lead": {"label": "Lead - Distorted (Ghetto)", "preset": "lead_synth / distorted"},
            "pad": {"label": "Pad - Dark (Ghetto)", "preset": "dark_pad"},
            "drum": {"label": "Drums - Ghetto Tech", "preset": "ghetto_kit / distorted"},
        },
    }),
    # --- Hardstyle sub-genres ---
    ("rawstyle", "hardstyle", {
        "default_bpm": 155,
        "swing": {"resolution": 16, "amount": 0.02},
        "scale_pool": ["phrygian", "natural_minor", "harmonic_minor"],
        "section_density": {"intro": 0.4, "breakdown": 0.3, "build": 0.75, "drop": 1.0, "drop2": 1.0, "outro": 0.35},
        "section_velocity": {"intro": 78, "breakdown": 82, "build": 96, "drop": 116, "drop2": 116, "outro": 76},
        "instrument_intent": {
            "bass": {"label": "Bass - Distorted (Raw)", "preset": "distorted_bass / raw"},
            "lead": {"label": "Lead - Screech (Rawstyle)", "preset": "screech_synth / distorted"},
            "pad": {"label": "Pad - Dark (Rawstyle)", "preset": "dark_pad / distorted"},
            "drum": {"label": "Drums - Hard (Rawstyle)", "preset": "hardstyle_kit / distorted"},
        },
    }),
    ("euphoric_hardstyle", "hardstyle", {
        "default_bpm": 150,
        "swing": {"resolution": 16, "amount": 0.03},
        "scale_pool": ["major", "dorian", "natural_minor"],
        "section_density": {"intro": 0.35, "breakdown": 0.25, "build": 0.7, "drop": 1.0, "drop2": 1.0, "outro": 0.3},
        "section_velocity": {"intro": 74, "breakdown": 78, "build": 94, "drop": 114, "drop2": 114, "outro": 72},
        "instrument_intent": {
            "bass": {"label": "Bass - Offbeat (Euphoric)", "preset": "saw_bass / offbeat"},
            "lead": {"label": "Lead - Anthem (Euphoric)", "preset": "supersaw / anthem"},
            "pad": {"label": "Pad - Euphoric", "preset": "ethereal_pad / bright"},
            "arp": {"label": "Arp - Trance (Euphoric)", "preset": "pluck_synth / euphoric"},
            "drum": {"label": "Drums - Hard (Euphoric)", "preset": "hardstyle_kit / clean"},
        },
    }),
    # --- UK Garage sub-genres ---
    ("bassline", "uk_garage", {
        "default_bpm": 130,
        "swing": {"resolution": 8, "amount": 0.35},
        "scale_pool": ["dorian", "major"],
        "section_density": {"intro": 0.3, "breakdown": 0.25, "build": 0.6, "drop": 0.85, "outro": 0.25},
        "section_velocity": {"intro": 70, "breakdown": 74, "build": 86, "drop": 98, "outro": 68},
        "instrument_intent": {
            "bass": {"label": "Bass - Wobbly (Bassline)", "preset": "analog_bass / wobble"},
            "lead": {"label": "Lead - Pluck (Bassline)", "preset": "pluck_synth / percussive"},
            "pad": {"label": "Pad - Warm (Bassline)", "preset": "warm_pad / soft"},
            "chord": {"label": "Chord - Organ (Bassline)", "preset": "organ / house"},
            "drum": {"label": "Drums - Bassline 4x4", "preset": "ukg_kit / 4x4"},
        },
    }),
    ("speed_garage", "uk_garage", {
        "default_bpm": 134,
        "swing": {"resolution": 8, "amount": 0.3},
        "scale_pool": ["dorian", "mixolydian"],
        "section_density": {"intro": 0.3, "breakdown": 0.25, "build": 0.65, "drop": 0.9, "outro": 0.25},
        "section_velocity": {"intro": 72, "breakdown": 76, "build": 88, "drop": 100, "outro": 70},
        "instrument_intent": {
            "bass": {"label": "Bass - Reese (Speed)", "preset": "reece_bass / dark"},
            "lead": {"label": "Lead - Vocal (Speed)", "preset": "vocal_chop / pitched"},
            "pad": {"label": "Pad - Dark (Speed)", "preset": "dark_pad / warm"},
            "chord": {"label": "Chord - Stab (Speed)", "preset": "chord_stab / percussive"},
            "drum": {"label": "Drums - Speed Garage", "preset": "ukg_kit / shuffled"},
        },
    }),
    # --- Downtempo sub-genres ---
    ("trip_hop", "downtempo", {
        "default_bpm": 85,
        "swing": {"resolution": 8, "amount": 0.35},
        "scale_pool": ["natural_minor", "dorian", "phrygian"],
        "section_velocity": {"intro": 62, "verse": 72, "chorus": 80, "outro": 58},
        "instrument_intent": {
            "bass": {"label": "Bass - Upright (Trip Hop)", "preset": "acoustic_bass / upright"},
            "lead": {"label": "Lead - Sax (Trip Hop)", "preset": "saxophone / tenor"},
            "pad": {"label": "Pad - Vinyl (Trip Hop)", "preset": "dark_pad / lofi"},
            "chord": {"label": "Chord - Rhodes (Trip Hop)", "preset": "rhodes / vintage"},
            "drum": {"label": "Drums - Breakbeat (Trip Hop)", "preset": "hiphop_kit / breakbeat"},
            "drum_layers": {"label": "Percussion - Vinyl", "preset": "vinyl_crackle / percussion"},
        },
    }),
    ("lo_fi", "downtempo", {
        "default_bpm": 80,
        "swing": {"resolution": 8, "amount": 0.4},
        "scale_pool": ["major", "dorian", "mixolydian"],
        "section_velocity": {"intro": 58, "verse": 68, "chorus": 76, "outro": 56},
        "instrument_intent": {
            "bass": {"label": "Bass - Soft (Lo-Fi)", "preset": "sub_bass / sine"},
            "lead": {"label": "Lead - Piano (Lo-Fi)", "preset": "piano / felt"},
            "pad": {"label": "Pad - Nostalgic (Lo-Fi)", "preset": "warm_pad / filtered"},
            "chord": {"label": "Chord - Jazz (Lo-Fi)", "preset": "rhodes / lofi"},
            "drum": {"label": "Drums - Lo-Fi", "preset": "lofi_kit / dusty"},
            "drum_layers": {"label": "Percussion - Lo-Fi", "preset": "vinyl_crackle"},
        },
    }),
    ("ambient", "downtempo", {
        "default_bpm": 90,
        "swing": {"resolution": 16, "amount": 0.02},
        "scale_pool": ["major", "lydian", "mixolydian"],
        "section_bars": {"intro": 4, "verse": 8, "chorus": 8, "outro": 4},
        "section_density": {"intro": 0.15, "verse": 0.25, "chorus": 0.5, "outro": 0.1},
        "section_velocity": {"intro": 52, "verse": 62, "chorus": 80, "outro": 50},
        "instrument_intent": {
            "bass": {"label": "Bass - Sub (Ambient)", "preset": "sub_bass / sine"},
            "lead": {"label": "Lead - Flute (Ambient)", "preset": "flute / airy"},
            "pad": {"label": "Pad - Ambient", "preset": "ambient_pad / evolving"},
            "chord": {"label": "Chord - Shimmer (Ambient)", "preset": "shimmer_pad / reverb"},
            "drum": {"label": "Drums - Sparse (Ambient)", "preset": "ambient_kit / minimal"},
        },
    }),
]


def main():
    for name, parent, overrides in SUBGENRES:
        cfg = {"parent_genre": parent, "genre": name}
        cfg.update(overrides)
        path = DIR / f"{name}.json"
        path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"  wrote {path.name} ({parent} + {len(overrides)} overrides)")
    print(f"\n{len(SUBGENRES)} sub-genre configs created")


if __name__ == "__main__":
    main()
