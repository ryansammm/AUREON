# AUREON — Advanced MIDI Composition Engine

Rule-based MIDI composition engine that generates genre-aware, multi-track
music (bass, leads, arps, chords, pads, drums) with arrangement structure,
humanized timing and MIDI export. 100% local and free/open-source — no cloud
APIs.

Generated MIDI opens in any DAW (Ableton, FL Studio, Logic, Cubase). A
numpy-based WAV renderer is included so you can listen to results without
a synth or soundfont.

## Features

- **Genre configs** — 15 built-in genres (`techno`, `trance`,
  `progressive_house`, `big_room`, `electro_house`, `house`, `dubstep`,
  `drum_and_bass`, `trap`, `future_bass`, `hardstyle`, `psytrance`,
  `uk_garage`, `downtempo`, `generic`); extensible — add a JSON file.
- **Multi-track composition** — shared arrangement + chord progression across
  `bass`, `sub_bass`, `lead`, `counter_lead`, `arp`, `stab`, `chord`/`pad`,
  `drum` and `drum_layers` roles with register separation.
- **Arrangement & energy curve** — intro / buildup / breakdown / drop / outro
  with per-section density, register, velocity and tempo; long requests
  (up to ~280 bars / ~5 min) expand into repeated build-up/drop loops with
  a single intro and outro instead of blindly re-tiling the template.
- **Layer 4 candidate selection** — generates N variations and ranks them with an
  ensemble score: theory heuristics (dissonance, repetition, voice leading) plus
  statistical features (tonality in-key rate, chord-tone alignment, pitch variety,
  density balance, register adherence).
- **Humanization** — micro-timing, velocity arcs, and per-genre **swing/groove**.
- **MIDI automation** — CC 74 (filter cutoff) + CC 11 (expression) follow the
  energy curve; percussion on channel 10; mid-song **tempo map**; section
  **modulations** (e.g. key lift on the second drop).
- **Local web UI (English)** — generate, A/B-compare candidates, and listen
  in the browser.
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

```bash
# multi-track composition with drums, ranked from 5 candidates
python cli.py --genre house --roles bass,lead,chord,drum --candidates 5 --top 1

# full 10-role composition
python cli.py --genre dubstep --roles bass,sub_bass,lead,arp,stab,counter_lead,chord,pad,drum,drum_layers

# long-form composition (~5 min at 140 BPM)
python cli.py --genre dubstep --roles bass,lead,chord,drum --bars 180

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
python -m pytest -q     # 135 tests
```

## Architecture

Layer-based pipeline (`engine/`), each layer independently testable:

| Layer | Module | Responsibility |
|-------|--------|----------------|
| 0 | `config_loader.py` | genre config load/validate (fallback to `generic`) |
| 1 | `harmony.py` | chord progression (weighted pool + transition matrix) |
| 2 | `melody.py` / `drums.py` | bass/lead lines, chord voicings, drum patterns |
| 3 | `arrangement.py` | section plan + energy curve |
| 4 | `selector.py` | candidate generation + ensemble scoring |
| 5 | `humanizer.py` | micro-timing, velocity, swing |
| 6 | `exporter.py` | Type-1 multi-track MIDI, CC, tempo map |
| — | `pipeline.py` | wires 0→6; multi-role composition; CC/tempo/modulation |
| — | `metrics.py` | per-track/section stats report |

Genre configs live in `config/genres/*.json`. A genre is fully defined by
config — no engine code changes needed.

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
    "patterns": {"drop": {"kick": "x...........x...", "snare": "........x......."}},
    "layers": {"drop": {"shaker": ".x.x.x.x.x.x.x.x", "tom": "..............x."}}
  }
}
```

Genre knowledge is curated in `tools/gen_genre_kb.py` and regenerated into
`config/genres/*.json` with:

```bash
python tools\gen_genre_kb.py
```
