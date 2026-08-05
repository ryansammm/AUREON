# Aureon by XYKS — AI Music Generator

Rule-based MIDI composition engine that generates genre-aware, multi-track
music (bass, leads, arps, chords, pads, drums) with arrangement structure,
humanized timing and MIDI export. 14 parent genres + 26 sub-genres, 15 groove
profiles, 10 instrument roles, real GM SoundFont rendering. 100% local and
free/open-source.

Optional **AI layer** — the engine can ask a free-tier LLM (Gemini → Groq
fallback) for creative ideas (progression + motif) and to re-score candidate
rankings. No key = fully rule-based; nothing ever leaves your machine except
the single prompt to the LLM you opt into.

## Quick Start (New Users)

```bat
:: 1. Clone the repo
git clone https://github.com/anomalyco/aureon.git
cd aureon

:: 2. Run setup — checks Python, Node.js, installs all dependencies
setup.bat

:: 3. Start Aureon
AUREON.bat
:: Opens http://127.0.0.1:8000 automatically
```

`setup.bat` will:
- Check Python 3.10+ and Node.js 18+ (offer install via winget if missing)
- Create virtual environment + install pip packages
- Install npm packages + build the frontend
- Create `.env` from `.env.example`

`AUREON.bat` will:
- Verify all dependencies are present
- Auto-build frontend if needed
- Warn if no API keys are set (AI features require at least one key)
- Start the server and open your browser

### API Keys (Optional)

AI features (smart suggestions, scoring) need at least one free API key:

| Provider | Free tier | Get key |
|----------|-----------|---------|
| Gemini | ~1500 req/day | https://aistudio.google.com/app/apikey |
| Groq | ~1000 req/day | https://console.groq.com/keys |

Add keys via the **Settings** page in the app, or edit `.env` directly.

## Features

- **40 genres** — 14 parent genres (`techno`, `trance`, `house`, `dubstep`,
  `drum_and_bass`, `trap`, `future_bass`, `hardstyle`, `uk_garage`,
  `downtempo`, `progressive_house`, `big_room`, `electro_house`,
  `generic`) + 26 sub-genres with genre-specific BPM, patterns, swing, and
  arrangement. Sub-genres inherit from parents via `parent_genre` config,
  and cyclic inheritance is detected with a `ConfigCycleError` instead of
  looping forever.
- **Multi-track composition** — shared arrangement + chord progression across
  `bass`, `sub_bass`, `lead`, `counter_lead`, `arp`, `stab`, `chord`/`pad`,
  `drum` and `drum_layers` roles with register separation.
- **Arrangement & energy curve** — intro / buildup / breakdown / drop / outro
  with per-section density, register, velocity and tempo; long requests
  (up to ~280 bars / ~5 min) expand into repeated build-up/drop loops.
- **Layer 4 candidate selection** — generates N variations and ranks them with
  an ensemble score: theory heuristics + statistical features.
- **AI assistance (optional)** — Gemini/Groq `LLMIdeator` suggests chord
  progressions + melodic motifs, and `AIScorer` re-ranks candidates.
- **Humanization** — micro-timing, velocity arcs, per-genre swing/groove.
  Drums keep velocity humanization but skip timing humanization.
- **Groove profiles** — 15 per-genre timing/velocity templates
  (`config/grooves/*.json`) applied to bass and drums; each genre config
  picks a profile via `groove_profile` + `groove_strength`. Grooves add
  micro-offsets and velocity accents to drums and drum_layers in addition
  to melodic roles.
- **Bass-drum interlock** — optional `bass_drum_interlock` block per genre
  biases the bassline around the kick pattern: `lock` keeps bass on the
  kick grid, `syncopate` pushes it off-beat, `independent` ignores the kick.
  In `lock` mode rejected onsets are dropped by default or snapped onto the
  nearest kick with `"on_conflict": "shift"`.
- **MIDI automation** — CC 74 + CC 11, percussion on channel 10, tempo map,
  section modulations.
- **Web UI** — React + Vite + Tailwind SPA with:
  - Grouped genre selector (parent → sub-genres)
  - Live SSE generation progress
  - Waveform player + interactive piano roll
  - Candidate A/B audio compare with AI reasoning
  - Per-track stems & browser mixer
  - History, compare, MIDI import
  - **Settings page** — manage API keys without touching `.env`
- **PWA** — installable with offline shell, plays compositions in the browser
  with real GM instruments via Tone.js + SoundFont-player.
- **WAV render** — FluidSynth + GeneralUser GS SoundFont, with numpy fallback.
  Master chain: sidechain duck → compression → saturation → limiter.
  When FluidSynth or a SoundFont is missing, the app logs a warning and the
  generate API returns `"render_engine": "numpy_fallback"` (vs `"fluidsynth"`)
  so the UI can flag the preview-quality audio. No personal machine paths are
  baked in — FluidSynth is located via `AUREON_FLUIDSYNTH`, `PATH`, or common
  install locations, and the SoundFont via `AUREON_SOUNDFONT` or common dirs.

## Install (Manual)

Python 3.10+, Node.js 18+.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

```bash
cd web\frontend
npm install
npm run build
```

## CLI Usage

```bash
# single track
python cli.py --genre dubstep --role bass --key a --mode minor --bpm 140

# multi-track with drums, ranked from 5 candidates
python cli.py --genre house --roles bass,lead,chord,drum --candidates 5 --top 1

# full 10-role composition
python cli.py --genre dubstep --roles bass,sub_bass,lead,arp,stab,counter_lead,chord,pad,drum,drum_layers

# long-form (~5 min at 140 BPM)
python cli.py --genre dubstep --roles bass,lead,chord,drum --bars 180

# sub-genre
python cli.py --genre liquid_dnb --roles bass,lead,chord,drum

# Phase 5: AI ideation
python cli.py --genre dubstep --roles bass,lead,chord,drum --ai \
    --prompt "dark, cinematic with an emotional lead"
```

## Web UI

Flask serves a REST JSON API + the built React SPA from `web/frontend/dist`:

| Endpoint | Purpose |
|----------|---------|
| `GET  /api/config` | genres + groups, defaults, roles, gains |
| `GET  /api/settings` | read API keys from `.env` |
| `POST /api/settings` | write API keys to `.env` |
| `POST /api/generate` | generate + rank a composition |
| `POST /api/generate/stream` | SSE progress stream (`step`/`result`/`error`) |
| `GET  /api/track/<file>?role=` | download a single-role MIDI stem |
| `POST /api/import/midi` | upload `.mid` → GM-mapped channel report |
| `GET  /api/export/<file>` | ZIP bundle: master + stems + project.json |
| `GET  /play/<file>` | stream a rendered WAV |
| `GET  /download/<file>` | download a MIDI/WAV file |

```bash
python web\app.py
# open http://127.0.0.1:8000
```

### Dev Mode (HMR)

```powershell
.\scripts\dev.ps1 -Dev     # Flask :8000 + Vite :5173 paralel
# open http://localhost:5173 — changes in src/ appear instantly
```

### Dev Server Control

```powershell
.\scripts\dev.ps1 -Status            # server + watchdog state, port, orphans
.\scripts\dev.ps1 -Restart           # kill all, rebuild, start
.\scripts\dev.ps1 -Stop              # stop server + watchdog + orphans
.\scripts\dev.ps1 -Logs              # tail watchdog + server logs
.\scripts\dev.ps1 -Watch             # start self-healing watchdog in background
.\scripts\dev.ps1 -WatchForeground   # run watchdog in foreground (Ctrl+C stops)
.\scripts\dev.ps1 -Hot               # with -Watch: restart on backend/frontend source change
.\scripts\dev.ps1 -AutoStart         # register logon auto-start task (admin may be needed)
.\scripts\dev.ps1 -NoAutoStart       # remove the logon auto-start task
```

### Supervision / Auto-Heal (watchdog)

`scripts\watchdog.py` is a permanent supervisor that keeps AUREON running
smoothly. It is launched automatically by `AUREON.bat` and by
`dev.ps1 -Watch`, and it:

- health-checks the server every 10s (TCP probe + `GET /api/config`)
- auto-restarts after 3 consecutive failures, with backoff if the server
  is crash-looping
- cleans orphaned processes (FluidSynth, stale python servers, stray Vite)
- rotates `server.out.log` / `server.err.log` / `watchdog.log` (keeps 3 × 1 MB)
- `--hot`: restarts when `web/engine/tools` sources change
- `--once`: single check-and-fix — drop this into a Windows Scheduled Task
  for a second layer of self-healing
- writes `server.status.json` (read by `dev.ps1 -Status`) and a PID lockfile
  so only one watchdog runs

The Flask server runs with `threaded=True` (`web/app.py` → `run_server`), so
the `GET /api/config` health check is served concurrently with a long-running
generation. This prevents the watchdog from mistaking a busy server for a dead
one and restarting mid-generation.

> **Manual test (watchdog during long generation):** launch the watchdog
> (`.\scripts\dev.ps1 -Watch`), then start a long generation
> (`python cli.py --genre dubstep --roles bass,lead,chord,drum --bars 180`).
> The generation should complete without the watchdog logging a restart; a
> healthy server shows `state: healthy` in `server.status.json` throughout.

```powershell
# Manual watchdog control
.\scripts\dev.ps1 -Watch                # background (production-style)
.\scripts\dev.ps1 -WatchForeground -Hot # foreground + auto-reload sources
python scripts\watchdog.py --once       # single check-and-fix, exit code 0/1
```

### Smoke Test

```bash
python tools\smoke_test.py
```

## AI Layer (Optional)

Copy `.env.example` → `.env` and add at least one key, or use the Settings
page in the app. Gemini is tried first; on failure falls back to Groq.
With no key the engine stays 100% rule-based.

## Docker

Run the full stack in a container (Flask server + built SPA):

```bash
docker compose up -d --build
# open http://127.0.0.1:8000
```

- `./.env` is bind-mounted into the container at `/aureon/.env`, so API keys
  written via the Settings page persist across container restarts and rebuilds.
- The image bundles **GeneralUser GS** (the documented default SoundFont) at
  `/aureon/soundfonts/GeneralUser.sf2` and sets `AUREON_SOUNDFONT` to it, so
  Docker-rendered audio matches a native setup. FluidR3_GM is also installed
  as a fallback if you override `AUREON_SOUNDFONT`.
- The app runs as a **non-root user** (UID 1000). The `output/` dir and the
  mounted `./.env` are writable by that user; on native Linux hosts, ensure
  your host `.env` is writable by UID 1000 (Docker Desktop bind mounts are
  writable regardless). If upgrading from an older image that ran as root,
  remove the old volume once so it is re-created with the new ownership:
  `docker compose down -v && docker compose up -d`.
- Generated output is stored in the named `aureon-output` volume.
- `restart: unless-stopped` keeps the server running after reboots.

## Tests

```bash
python -m pytest -q     # --timeout=120 always on via pytest.ini
```

## Architecture

Layer-based pipeline (`engine/`), each layer independently testable:

| Layer | Module | Responsibility |
|-------|--------|----------------|
| 0 | `config_loader.py` | genre config load/validate + `parent_genre` inheritance with cycle detection |
| 1 | `harmony.py` | chord progression (weighted pool + transition matrix) |
| 2 | `melody.py` / `drums.py` | bass/lead lines, chord voicings, drum patterns |
| 3 | `arrangement.py` | section plan + energy curve |
| 4 | `selector.py` | candidate generation + ensemble scoring |
| 5 | `humanizer.py` | micro-timing, velocity, swing |
| 6 | `exporter.py` | Type-1 multi-track MIDI, CC, tempo map |
| — | `groove.py` | groove profile load + timing/velocity application |
| — | `pipeline.py` | wires 0→6; multi-role composition |
| — | `metrics.py` | per-track/section stats report |
| — | `llm.py` | Gemini/Groq provider chain + JSON extraction |
| — | `ideation.py` | `LLMIdeator` — AI chord progression + motif |
| — | `ai_scorer.py` | `AIScorer` — AI re-ranking of candidates |
| — | `gm_map.py` | GM patch/drum maps + MIDI Program Change parser |
| — | `sf_render.py` | FluidSynth + GM SoundFont renderer |
| — | `render_audio.py` | stereo WAV render + master chain |

### Sub-genre Inheritance

Sub-genre configs use `parent_genre` to inherit all keys from the parent and
only override specific fields (BPM, swing, patterns, instrument labels, etc.):

```jsonc
// config/genres/acid_techno.json
{
  "parent_genre": "techno",
  "genre": "acid_techno",
  "default_bpm": 140,
  "swing": {"resolution": 16, "amount": 0.08},
  "instrument_intent": {
    "bass": {"label": "Bass - Acid 303 (Techno)", "preset": "acid_bass / 303"}
  }
}
```

## License

Developed by XYKS.
