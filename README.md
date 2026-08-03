# AUREON — Advanced MIDI Composition Engine

Rule-based MIDI composition engine that generates genre-aware, multi-track
music (bass, lead, chords, drums) with arrangement structure, humanized
timing and MIDI export. 100% local and free/open-source — no cloud APIs.

Generated MIDI opens in any DAW (Ableton, FL Studio, Logic, Cubase). A
numpy-based WAV renderer is included so you can listen to results without
a synth or soundfont.

## Features

- **Genre configs** — `dubstep`, `house`, `generic` (extensible; add a JSON file).
- **Multi-track composition** — shared arrangement + chord progression across
  `bass`, `lead`, `chord`/`pad`, and `drum` roles with register separation.
- **Arrangement & energy curve** — intro / buildup / breakdown / drop / outro
  with per-section density, register, velocity and tempo.
- **Layer 4 candidate selection** — generates N variations and ranks them with
  music-theory heuristics (dissonance, repetition, voice leading).
- **Humanization** — micro-timing, velocity arcs, and per-genre **swing/groove**.
- **MIDI automation** — CC 74 (filter cutoff) + CC 11 (expression) follow the
  energy curve; percussion on channel 10; mid-song **tempo map**; section
  **modulations** (e.g. key lift on the second drop).
- **Local web UI** — generate, A/B-compare candidates, and listen in the browser.
- **WAV render** — stereo synthesis with per-role panning, drum voices and
  reverb; plus a metrics report per track/section.

## Install

Python 3.11+.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

Dependencies: `music21`, `mido`, `pytest`, `numpy` (for the WAV render),
`flask` (for the web UI).

## CLI usage

```bash
# single track
python cli.py --genre dubstep --role bass --key a --mode minor --bpm 140

# multi-track composition with drums, ranked from 5 candidates
python cli.py --genre house --roles bass,lead,chord,drum --candidates 5 --top 1

# disable humanization for A/B comparison
python cli.py --genre dubstep --role bass --no-humanize

# metrics report
python cli.py --genre dubstep --roles bass,lead,chord,drum --report

# render exported MIDI to WAV (stereo + reverb)
python cli.py --genre dubstep --role bass --render
```

Output goes to the current directory (or `--output path.mid`); samples are
kept under `output/`.

## Listen (WAV render)

```bash
python tools\render_audio.py output\sample.mid
python tools\render_audio.py output\sample.mid --gain 0.6 --no-reverb
```

Timbre is a basic synth — enough to judge melody, progression, arrangement
and the humanizer's micro-timing.

## Web UI

```bash
python web\app.py
# open http://127.0.0.1:8000
```

Binds to `127.0.0.1` only. Do not expose to a public network without adding
authentication.

## Tests

```bash
python -m pytest -q     # 91 tests
```

## Architecture

Layer-based pipeline (`engine/`), each layer independently testable:

| Layer | Module | Responsibility |
|-------|--------|----------------|
| 0 | `config_loader.py` | genre config load/validate (fallback to `generic`) |
| 1 | `harmony.py` | chord progression (weighted pool + transition matrix) |
| 2 | `melody.py` / `drums.py` | bass/lead lines, chord voicings, drum patterns |
| 3 | `arrangement.py` | section plan + energy curve |
| 4 | `selector.py` | candidate generation + theory scoring |
| 5 | `humanizer.py` | micro-timing, velocity, swing |
| 6 | `exporter.py` | Type-1 multi-track MIDI, CC, tempo map |
| — | `pipeline.py` | wires 0→6; multi-role composition; CC/tempo/modulation |
| — | `metrics.py` | per-track/section stats report |

Genre configs live in `config/genres/*.json`. A genre is fully defined by
config — no engine code changes needed (spec Phase 2 DoD).

## Configuration highlights

```jsonc
{
  "default_bpm": 140,
  "section_template": ["intro", "buildup", "drop", "breakdown", "drop2", "outro"],
  "section_tempo": {"breakdown": 0.5},                       // mid-song tempo change
  "modulations": [{"section": "drop2", "semitones": 1}],     // key lift
  "automation": {"cc74_range": [30, 125], "cc11": true},     // CC automation
  "swing": {"resolution": 16, "amount": 0.12},               // groove
  "drum_patterns": {                                          // 16-step strings
    "notes": {"kick": 36, "snare": 38, "hat": 42},
    "patterns": {"drop": {"kick": "x...........x...", "snare": "........x......."}}
  }
}
```

## Project documents

- `PROJECT_SPEC_MIDI_Composition_Engine.md` — source of truth & roadmap.
- `CONTEXT_Diskusi_MIDI_Generation.md` — design rationale.

## Roadmap status

- Phase 1–4 (rule-based core, arrangement, quality/humanization,
  multi-role + interaction): **done**.
- Phase 5–6 (neural enhancement, scoring-model upgrade): future/experimental
  per spec — only if rule-based output is judged creatively stuck.
