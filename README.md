# AUREON — Advanced MIDI Composition Engine

Rule-based MIDI composition engine that generates genre-aware, multi-track
music (bass, leads, arps, chords, pads, drums) with arrangement structure,
humanized timing and MIDI export. 100% local and free/open-source.

Optional **AI layer (Phase 5)** — the engine can ask a free-tier LLM (Gemini
→ Groq fallback) for creative ideas (progression + motif) and to re-score
candidate rankings. No key = fully rule-based; nothing ever leaves your
machine except the single prompt to the LLM you opt into.

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
- **AI assistance (optional)** — Gemini/Groq `LLMIdeator` suggests a chord
  progression + melodic motif (validated to the scale), and an `AIScorer`
  re-ranks candidates with musical reasoning. Both composable with the
  rule-based stack; provider chain falls back automatically.
- **Humanization** — micro-timing, velocity arcs, and per-genre **swing/groove**.
- **MIDI automation** — CC 74 (filter cutoff) + CC 11 (expression) follow the
  energy curve; percussion on channel 10; mid-song **tempo map**; section
  **modulations** (e.g. key lift on the second drop).
- **God-tier web UI** — React + Vite + Tailwind SPA served by a small Flask
  REST API: genre/role picker with live summary, animated generation overlay,
  waveform player, interactive **piano roll** (pan/zoom/hover), candidate
  **A/B audio compare** with AI reasoning.
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

The web UI additionally needs Node.js 18+ (only for building the SPA):

```bash
cd web\frontend
npm install
npm run build                  # outputs web/frontend/dist (optional if you use `npm run dev`)
```

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

# Phase 5: let Gemini/Groq design the progression + motif
python cli.py --genre dubstep --roles bass,lead,chord,drum --ai \
    --prompt "dark, cinematic with an emotional lead"

# Phase 5: AI also re-ranks the candidates (needs --candidates > 1)
python cli.py --genre dubstep --roles bass,lead,chord,drum --candidates 5 \
    --ai --ai-score --top 1
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

Flask is now a **REST JSON API** (`/api/config`, `/api/generate`, `/play`,
`/download`) that also serves the built React SPA from `web/frontend/dist`.

```bash
# 1. build the SPA once (after install)
cd web\frontend && npm install && npm run build

# 2. run the app (serves UI + API on the same port)
python web\app.py
# open http://127.0.0.1:8000
```

During development use the Vite dev server (hot reload) instead of the build —
it proxies `/api` to Flask on port 8000:

```bash
# terminal 1                       # terminal 2
python web\app.py                  cd web\frontend && npm run dev
```

Binds to `127.0.0.1` only. Do not expose to a public network without adding
authentication.

## AI layer (optional, Phase 5)

Copy `.env.example` → `.env` and add at least one key:

| Provider | Model | Free tier | Where to get it |
|----------|-------|-----------|-----------------|
| Gemini | `gemini-flash-latest` | ~1500 req/day | https://aistudio.google.com/app/apikey |
| Groq | `llama-3.3-70b-versatile` | ~1000 req/day | https://console.groq.com/keys |

Gemini is tried first; on failure the client falls back to Groq
automatically. With no key the engine stays 100% rule-based. In the UI,
flip the **AI assistance** toggle to send a vibe prompt and enable AI
ideation + AI re-scoring of candidates.

## Tests

```bash
python -m pytest -q     # 141 tests
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
| — | `llm.py` | Gemini/Groq provider chain + JSON extraction (Phase 5) |
| — | `ideation.py` | `LLMIdeator` — AI chord progression + motif, validated |
| — | `ai_scorer.py` | `AIScorer` — AI re-ranking of candidates (Phase 5) |

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
