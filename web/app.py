"""AUREON REST API + static SPA host (Phase 5 / God-tier UI).

Backend contract for the React frontend:

- ``GET  /api/config``          -> genres (+ defaults), roles, bpm map
- ``POST /api/generate``        -> generate + rank a composition (JSON body)
- ``POST /api/generate/stream`` -> same, but streams SSE progress events
- ``GET  /api/track/<file>``    -> download a single-role MIDI stem
- ``POST /api/import/midi``     -> upload .mid, returns GM-mapped channel report
- ``GET  /play/<file>``         -> stream a rendered WAV
- ``GET  /download/<file>``     -> download a MIDI/WAV file
- ``GET  /`` (or any non-api path) -> serve the built SPA from
  ``web/frontend/dist`` when present; otherwise a dev hint.

Binds to 127.0.0.1 only. Run with ``python web\\app.py`` and open
http://127.0.0.1:8000
"""

import io
import json
import os
import queue
import re
import sys
import threading
import uuid
import zipfile
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from engine.ai_scorer import AIScorer, build_candidate_summary  # noqa: E402
from engine.config_loader import CONFIG_DIR, load_genre_config  # noqa: E402
from engine.exporter import export_midi  # noqa: E402
from engine.ideation import LLMIdeator  # noqa: E402
from engine.pipeline import build_tempo_map  # noqa: E402
from engine.selector import CandidateGenerator, Selector  # noqa: E402

app = Flask(__name__, static_folder=None)
app.config["OUTPUT_DIR"] = ROOT / "output"
app.config["MAX_CANDIDATE_AUDIO"] = 5

DIST_DIR = ROOT / "web" / "frontend" / "dist"
ROLES = ["bass", "lead", "chord", "pad", "arp", "stab", "sub_bass",
         "counter_lead", "drum", "drum_layers"]
GAIN_DEFAULTS = {"bass": 0.6, "lead": 0.5, "pad": 0.42, "chord": 0.42,
                 "drum": 0.78, "drum_layers": 0.55, "arp": 0.42,
                 "stab": 0.48, "sub_bass": 0.62, "counter_lead": 0.4}
MAX_PIANO_NOTES_PER_TRACK = 4000


def available_genres() -> list:
    return sorted(p.stem for p in CONFIG_DIR.glob("*.json"))


def genre_defaults() -> dict:
    out = {}
    for genre in available_genres():
        try:
            cfg = load_genre_config(genre)
            out[genre] = {
                "bpm": cfg["default_bpm"],
                "key": cfg["default_key"],
                "mode": cfg["default_mode"],
            }
        except Exception:
            continue
    return out


def _render_wav(mid_path: Path, wav_path: Path, gains: dict,
                roles: list = None, reverb: bool = True) -> None:
    from render_audio import render_to_wav

    # Prefer the SoundFont renderer (real GM instruments) when available;
    # it still runs the numpy master chain, and falls back to the synth.
    try:
        import sf_render

        if sf_render.soundfont_available():
            seconds = sf_render.render_midi_with_soundfont(
                mid_path, wav_path, gain=1.0, roles=roles,
                master=roles is None,
            )
            if seconds is not None:
                return
    except Exception:  # noqa: BLE001 - never break generation on render issues
        pass

    render_to_wav(mid_path, wav_path, gain=0.55, gains=gains, reverb=reverb,
                  roles=roles, master=roles is None)


def _serialize_notes(track) -> list:
    notes = sorted(track.notes, key=lambda n: n.start_beat)
    if len(notes) > MAX_PIANO_NOTES_PER_TRACK:
        notes = notes[:MAX_PIANO_NOTES_PER_TRACK]
    return [
        [n.pitch, round(n.start_beat, 3), round(n.duration_beat, 3), n.velocity]
        for n in notes
    ]


def _run_pipeline(config, roles, key_root, mode, bpm, bars, complexity,
                  candidates, seed, humanize, ai_idea=None, ai_scoring=False):
    """Return (tracks, progression, plan, ranked_list, ai_scores)."""
    degrees = ai_idea.get("progression") if ai_idea else None
    motif = ai_idea.get("motif") if ai_idea else None
    ai_scores = {}
    if candidates <= 1:
        if len(roles) > 1:
            from engine.pipeline import generate_composition

            tracks, progression, plan = generate_composition(
                config, roles, key_root, mode, bars=bars, complexity=complexity,
                seed=seed, humanize=humanize, bpm=bpm,
                progression_degrees=degrees, motif=motif,
            )
        else:
            from engine.pipeline import generate_track

            track, progression, plan = generate_track(
                config, roles[0], key_root, mode, bars=bars, complexity=complexity,
                seed=seed, humanize=humanize, bpm=bpm,
                progression_degrees=degrees, motif=motif,
            )
            tracks = [track]
        return tracks, progression, plan, [], ai_scores

    generator = CandidateGenerator(config, seed=seed)
    candidates_list = generator.generate(
        roles[0], key_root, mode, bars=bars, complexity=complexity,
        count=candidates, base_seed=seed, humanize=humanize, roles=roles,
        progression_degrees=degrees, motif=motif,
    )
    selector = Selector(config, seed=seed, key_root=key_root, mode=mode)
    multi = len(roles) > 1
    score_key = (
        lambda c: selector.score_composition(c[0], c[1])[0]
        if multi
        else selector.score_track(c[0][0], c[1])[0]
    )
    ranked = sorted(candidates_list, key=score_key, reverse=True)

    if ai_scoring:
        try:
            scorer = AIScorer(config)
            summaries = [
                build_candidate_summary(c[0], c[1], idx)
                for idx, c in enumerate(ranked)
            ]
            ai_scores, _provider = scorer.score_candidates(summaries, key_root, mode)
        except Exception:
            ai_scores = {}

    def _combined(c, idx):
        base = (
            selector.score_composition(c[0], c[1])[0]
            if multi
            else selector.score_track(c[0][0], c[1])[0]
        )
        ai = ai_scores.get(idx, {}).get("score", 5.0)
        return base + (ai - 5.0) * 0.05

    if ai_scores:
        ranked = sorted(
            enumerate(ranked), key=lambda t: _combined(t[1], t[0]), reverse=True
        )
        reordered = []
        new_scores = {}
        for new_idx, (orig_idx, c) in enumerate(ranked):
            reordered.append(c)
            if orig_idx in ai_scores:
                new_scores[new_idx] = ai_scores[orig_idx]
        ranked = reordered
        ai_scores = new_scores

    tracks, progression, plan = ranked[0][0], ranked[0][1], ranked[0][2]
    summary = []
    for i, (c_tracks, c_prog, _, c_seed) in enumerate(ranked, start=1):
        score, _ = (
            selector.score_composition(c_tracks, c_prog)
            if multi
            else selector.score_track(c_tracks[0], c_prog)
        )
        entry = {"rank": i, "seed": c_seed, "score": round(score, 3),
                 "tracks": c_tracks}
        ai_info = ai_scores.get(i - 1)
        if ai_info:
            entry["ai_score"] = round(ai_info["score"], 1)
            entry["ai_reason"] = ai_info["reason"]
        summary.append(entry)
    return tracks, progression, plan, summary, ai_scores


def _generate_payload(data: dict, report=None) -> dict:
    """Run one full generation. ``report(message, pct)`` is called as stages
    complete (used by the SSE endpoint). Raises ValueError for bad input."""
    report = report or (lambda message, pct: None)

    def step(message: str, pct: float):
        report(message, pct)

    roles = [r for r in data.get("roles") or [] if r in ROLES] or ["bass"]
    key_root = data.get("key") or None
    mode = data.get("mode") or None
    try:
        candidates = max(1, min(20, int(data.get("candidates") or 1)))
    except (TypeError, ValueError):
        candidates = 1
    try:
        seed = int(data.get("seed") or 0)
    except (TypeError, ValueError):
        seed = 0
    bars = data.get("bars") or None
    complexity = data.get("complexity", "medium")
    humanize = bool(data.get("humanize", True))
    ai_enabled = bool(data.get("ai", False))
    ai_prompt = (data.get("prompt") or "").strip() or None
    make_stems = bool(data.get("stems", False))
    gains = {k: max(0.0, min(2.0, float(v))) for k, v in
             (data.get("gains") or {}).items() if k in GAIN_DEFAULTS}

    app.config["OUTPUT_DIR"].mkdir(parents=True, exist_ok=True)
    output_dir = app.config["OUTPUT_DIR"]

    step("Loading genre DNA", 0.05)
    try:
        config = load_genre_config(data.get("genre") or "dubstep")
    except Exception as exc:
        raise ValueError(f"unknown genre: {exc}") from exc

    key_root = key_root or config["default_key"]
    mode = mode or config["default_mode"]
    try:
        bpm = int(data.get("bpm") or config["default_bpm"])
    except (TypeError, ValueError):
        bpm = config["default_bpm"]
    if bars:
        try:
            bars = int(bars)
        except (TypeError, ValueError):
            bars = None

    ai_idea = None
    ai_note = None
    ai_score_note = None
    if ai_enabled:
        step("Asking the AI for an idea", 0.12)
        ideator = LLMIdeator(config)
        if ideator.available():
            try:
                ai_idea = ideator.generate_idea(
                    key_root, mode, roles, bars=bars, prompt=ai_prompt
                )
            except Exception as exc:
                ai_note = f"AI idea failed, using rule-based ({exc})"
        else:
            ai_note = ("AI not configured: set GEMINI_API_KEY / GROQ_API_KEY "
                       "in a .env file")

    step("Designing chord progression", 0.20)
    ai_scoring = ai_enabled and ai_idea is not None and candidates > 1
    tracks, progression, plan, summary, _ai_scores = _run_pipeline(
        config, roles, key_root, mode, bpm, bars, complexity,
        candidates, seed, humanize, ai_idea=ai_idea, ai_scoring=ai_scoring,
    )
    if ai_scoring and not _ai_scores:
        ai_score_note = "AI scoring failed, kept rule-based ranking"

    run_id = uuid.uuid4().hex[:6]
    base_name = (f"run{run_id}_{config['genre']}_{'-'.join(roles)}"
                 f"_{key_root}{mode}_seed{seed}")
    mid_path = output_dir / f"{base_name}.mid"
    wav_path = output_dir / f"{base_name}.wav"

    step("Exporting MIDI", 0.66)
    export_midi(
        tracks, bpm, str(mid_path),
        tempo_map=build_tempo_map(config, plan, bpm),
    )

    step("Rendering master audio", 0.72)
    _render_wav(mid_path, wav_path, gains)

    stems = []
    if make_stems:
        n_roles = max(len(tracks), 1)
        for i, t in enumerate(tracks, start=1):
            step(f"Rendering stem: {t.role}", 0.72 + 0.10 * i / n_roles)
            stem_wav = output_dir / f"{base_name}_stem_{t.role}.wav"
            _render_wav(mid_path, stem_wav, gains, roles=[t.role], reverb=False)
            stems.append({"role": t.role, "wav": stem_wav.name})

    section_counts = {}
    for sb in plan:
        section_counts[sb.name] = section_counts.get(sb.name, 0) + 1

    candidate_entries = []
    rendered_candidates = summary[:app.config["MAX_CANDIDATE_AUDIO"]]
    for j, item in enumerate(rendered_candidates, start=1):
        step(
            f"Rendering candidate {item['rank']} of {len(summary)}",
            0.86 + 0.12 * j / max(len(rendered_candidates), 1),
        )
        c_rank = item["rank"]
        c_seed = item["seed"]
        c_mid = output_dir / f"{base_name}_c{c_rank}_seed{c_seed}.mid"
        c_wav = output_dir / f"{base_name}_c{c_rank}_seed{c_seed}.wav"
        export_midi(
            item["tracks"], bpm, str(c_mid),
            tempo_map=build_tempo_map(config, plan, bpm),
        )
        _render_wav(c_mid, c_wav, gains)
        candidate_entries.append({
            "rank": c_rank,
            "seed": c_seed,
            "score": item["score"],
            "ai_score": item.get("ai_score"),
            "ai_reason": item.get("ai_reason"),
            "mid": c_mid.name,
            "wav": c_wav.name,
        })

    step("Done", 1.0)
    return {
        "genre": config["genre"],
        "key": f"{key_root} {mode}",
        "bpm": bpm,
        "humanized": humanize,
        "arrangement": ", ".join(f"{k}x{v}" for k, v in section_counts.items()),
        "chords": " -> ".join(c.degree for c in progression),
        "bars": len(plan),
        "tracks": [
            {
                "role": t.role,
                "name": t.track_name,
                "preset": t.suggested_preset,
                "notes": len(t.notes),
                "midi": _serialize_notes(t),
            }
            for t in tracks
        ],
        "mid": mid_path.name,
        "wav": wav_path.name,
        "stems": stems,
        "candidates": candidate_entries,
        "ai": {
            "enabled": ai_enabled,
            "idea": ai_idea,
            "note": ai_note,
            "score_note": ai_score_note,
        },
    }


@app.route("/api/config")
def api_config():
    return jsonify({
        "genres": available_genres(),
        "genre_defaults": genre_defaults(),
        "roles": ROLES,
        "gain_defaults": GAIN_DEFAULTS,
    })


MAX_GENERATION_SECONDS = 300.0


@app.route("/api/generate", methods=["POST"])
def api_generate():
    data = request.get_json(silent=True) or {}
    result = {}

    def run():
        try:
            result["ok"] = _generate_payload(data)
        except ValueError as exc:
            result["bad_request"] = str(exc)
        except Exception as exc:  # noqa: BLE001 - surface as 500
            result["error"] = str(exc)

    # Bounded worker: even if rendering wedges, the client gets a 504 instead
    # of waiting forever (the daemon thread is left to clean up on its own).
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    thread.join(MAX_GENERATION_SECONDS)
    if thread.is_alive():
        return jsonify({"error": "generation timed out"}), 504
    if "bad_request" in result:
        return jsonify({"error": result["bad_request"]}), 400
    if "error" in result:
        return jsonify({"error": result["error"]}), 500
    return jsonify(result["ok"])


@app.route("/api/generate/stream", methods=["POST"])
def api_generate_stream():
    """SSE variant: pushes ``step`` events (message + pct), then ``result``."""
    data = request.get_json(silent=True) or {}
    events = queue.Queue()

    def on_timeout():
        # Client must never wait forever: force the stream closed even if the
        # worker thread is still stuck inside a subprocess / render loop.
        events.put(("error", {"error": "generation timed out"}))
        events.put(("__end__", None))

    watchdog = threading.Timer(MAX_GENERATION_SECONDS, on_timeout)
    watchdog.daemon = True

    def worker():
        try:
            watchdog.start()
            result = _generate_payload(
                data, report=lambda m, p: events.put(("step", {"message": m,
                                                               "pct": p}))
            )
            events.put(("result", result))
        except Exception as exc:  # noqa: BLE001 - surface as SSE error
            events.put(("error", {"error": str(exc)}))
        finally:
            watchdog.cancel()
            events.put(("__end__", None))

    threading.Thread(target=worker, daemon=True).start()

    def gen():
        while True:
            kind, payload = events.get()
            if kind == "__end__":
                break
            yield f"event: {kind}\ndata: {json.dumps(payload)}\n\n"

    return Response(
        gen(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


def parse_base_name(base_name: str) -> dict:
    """Parse ``run{id}_{genre}_{roles}_{key}{mode}_seed{n}`` into metadata."""
    parts = base_name.split("_")
    meta = {
        "run_id": parts[0] if parts else base_name,
        "genre": parts[1] if len(parts) > 1 else "",
        "roles": parts[2].split("-") if len(parts) > 2 else [],
    }
    keymode = parts[3] if len(parts) > 3 else ""
    if keymode.endswith("minor"):
        meta["mode"], meta["key"] = "minor", keymode[:-5]
    elif keymode.endswith("major"):
        meta["mode"], meta["key"] = "major", keymode[:-5]
    else:
        meta["mode"], meta["key"] = "", keymode
    if len(parts) > 4 and parts[4].startswith("seed"):
        try:
            meta["seed"] = int(parts[4][4:])
        except ValueError:
            pass
    return meta


def _safe_output_file(filename: str) -> Path | None:
    """Resolve ``filename`` and return it only if it stays inside OUTPUT_DIR."""
    try:
        candidate = (app.config["OUTPUT_DIR"] / filename).resolve()
    except Exception:  # noqa: BLE001 - malformed path
        return None
    root = app.config["OUTPUT_DIR"].resolve()
    if candidate != root and root not in candidate.parents:
        return None
    return candidate if candidate.is_file() else None


@app.route("/api/export/<path:filename>")
def export_bundle(filename):
    """Download a ZIP bundle: master WAV, per-role stem WAVs + MIDIs,
    candidate renders, project.json and a README, ready to drop in a DAW."""
    src = _safe_output_file(filename)
    if src is None or not src.name.endswith(".mid"):
        return jsonify({"error": "not found"}), 404
    base = Path(filename).stem
    meta = parse_base_name(base)
    run_id = meta["run_id"]
    matches = list(app.config["OUTPUT_DIR"].glob(f"{run_id}_*"))
    if not matches:
        return jsonify({"error": "no files for this run"}), 404

    from sf_render import filter_midi_roles

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("project.json", json.dumps(meta, indent=2) + "\n")
        readme = (
            f"AUREON project: {meta.get('genre', '')} "
            f"{meta.get('key', '')} {meta.get('mode', '')} "
            f"seed {meta.get('seed', '')}\n"
            f"Roles: {', '.join(meta.get('roles', []))}\n\n"
            f"Files:\n"
            f"  MIDI/run_main.mid        full composition\n"
            f"  MIDI/stem_<role>.mid      single-role MIDI (GM program change)\n"
            f"  MIDI/candidate_<n>.mid    ranked candidate ideas\n"
            f"  Audio/run_master.wav      mastered full mix\n"
            f"  Audio/stem_<role>.wav     dry stem per role\n"
            f"  Audio/candidate_<n>.wav   candidate previews\n"
            f"  project.json              generation metadata\n\n"
            f"Drums live on MIDI channel 10; every track carries a GM "
            f"Program Change so a DAW auto-loads the right instrument.\n"
        )
        z.writestr("README.txt", readme)

        seen = set()
        for f in sorted(matches, key=lambda p: p.name):
            if f.name in seen or f.suffix not in (".mid", ".wav"):
                continue
            seen.add(f.name)
            name = f.name[len(run_id):]
            if "_stem_" in name:
                role = name.split("_stem_", 1)[1]
                if f.suffix == ".mid":
                    z.write(str(f), f"MIDI/stem_{role[:-4]}.mid")
                else:
                    z.write(str(f), f"Audio/stem_{role}")
            elif re.search(r"_c\d+_", name):
                rank = name.split("_c")[1].split("_")[0]
                folder = "Audio" if f.suffix == ".wav" else "MIDI"
                z.write(str(f), f"{folder}/candidate_{rank}{f.suffix}")
            elif f.suffix == ".mid":
                z.write(str(f), "MIDI/run_main.mid")
            else:
                z.write(str(f), "Audio/run_master.wav")

        for role in meta.get("roles", []):
            try:
                filtered = filter_midi_roles(src, [role])
                out = io.BytesIO()
                filtered.save(file=out)
                z.writestr(f"MIDI/stem_{role}.mid", out.getvalue())
            except Exception:  # noqa: BLE001 - best-effort extra files
                continue

    buf.seek(0)
    return Response(
        buf,
        mimetype="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{base}_bundle.zip"'
        },
    )


@app.route("/api/track/<path:filename>")
def track_midi(filename):
    """Download the main MIDI, or a single-role stem when ``?role=...``."""
    src = _safe_output_file(filename)
    if src is None:
        return jsonify({"error": "not found"}), 404
    role = (request.args.get("role") or "").strip()
    if not role:
        return send_from_directory(app.config["OUTPUT_DIR"], filename,
                                   as_attachment=True)

    from mido import MidiFile
    from render_audio import build_note_events, track_role

    mid = MidiFile(str(src))
    keep = [mid.tracks[0]] if mid.tracks else []
    for tr in mid.tracks[1:]:
        notes = build_note_events(tr, mid.ticks_per_beat, 1.0)
        if track_role(tr.name, notes) == role:
            keep.append(tr)
    if len(keep) == 1:
        return jsonify({"error": f"role '{role}' not found"}), 404
    out = MidiFile(ticks_per_beat=mid.ticks_per_beat)
    out.tracks = keep
    buf = io.BytesIO()
    out.save(file=buf)
    buf.seek(0)
    stem_name = f"{Path(filename).stem}_{role}.mid"
    return Response(
        buf,
        mimetype="audio/mid",
        headers={"Content-Disposition": f'attachment; filename="{stem_name}"'},
    )


@app.route("/play/<path:filename>")
def play(filename):
    return send_from_directory(app.config["OUTPUT_DIR"], filename)


@app.route("/download/<path:filename>")
def download(filename):
    return send_from_directory(app.config["OUTPUT_DIR"], filename, as_attachment=True)


@app.route("/api/import/midi", methods=["POST"])
def import_midi():
    """Analyze an uploaded .mid file and auto-assign internal plugins from GM."""
    from gm_map import analyze_midi

    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "missing 'file' field"}), 400
    name = f.filename.lower()
    if not name.endswith((".mid", ".midi")):
        return jsonify({"error": "only .mid / .midi files are supported"}), 400
    tmp = app.config["OUTPUT_DIR"] / f"import_{uuid.uuid4().hex[:8]}.mid"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    f.save(str(tmp))
    try:
        report = analyze_midi(tmp)
    except Exception as exc:  # noqa: BLE001 - surface parse errors to client
        return jsonify({"error": f"could not parse MIDI: {exc}"}), 422
    finally:
        tmp.unlink(missing_ok=True)
    report["filename"] = f.filename
    return jsonify(report)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def spa(path):
    """Serve the built React SPA; fall back to a dev hint."""
    if path and path.startswith("api/"):
        return jsonify({"error": "not found"}), 404
    if (DIST_DIR / "index.html").is_file():
        file_path = DIST_DIR / path
        if path and file_path.is_file():
            return send_from_directory(DIST_DIR, path)
        return send_from_directory(DIST_DIR, "index.html")
    return (
        "<h1>AUREON API</h1>"
        "<p>Frontend not built. Run <code>npm install && npm run build</code> "
        "inside <code>web/frontend</code>, then reload. "
        "During development use the Vite dev server (<code>npm run dev</code>) "
        "which proxies /api to this server.</p>",
        200,
        {"Content-Type": "text/html"},
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)
