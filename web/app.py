"""AUREON REST API + static SPA host (Phase 5 / God-tier UI).

Backend contract for the React frontend:

- ``GET  /api/config``   -> genres (+ defaults), roles, bpm map
- ``POST /api/generate`` -> generate + rank a composition (JSON body)
- ``GET  /play/<file>``  -> stream a rendered WAV
- ``GET  /download/<file>`` -> download a MIDI/WAV file
- ``GET  /`` (or any non-api path) -> serve the built SPA from
  ``web/frontend/dist`` when present; otherwise a dev hint.

Binds to 127.0.0.1 only. Run with ``python web\\app.py`` and open
http://127.0.0.1:8000
"""

import sys
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

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


def _render_wav(mid_path: Path, wav_path: Path, gains: dict) -> None:
    from render_audio import render_to_wav

    render_to_wav(mid_path, wav_path, gain=0.55, gains=gains, reverb=True)


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


@app.route("/api/config")
def api_config():
    return jsonify({
        "genres": available_genres(),
        "genre_defaults": genre_defaults(),
        "roles": ROLES,
        "gain_defaults": GAIN_DEFAULTS,
    })


@app.route("/api/generate", methods=["POST"])
def api_generate():
    data = request.get_json(silent=True) or {}
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
    gains = {k: max(0.0, min(2.0, float(v))) for k, v in
             (data.get("gains") or {}).items() if k in GAIN_DEFAULTS}

    app.config["OUTPUT_DIR"].mkdir(parents=True, exist_ok=True)
    output_dir = app.config["OUTPUT_DIR"]

    try:
        config = load_genre_config(data.get("genre") or "dubstep")
    except Exception:
        return jsonify({"error": "unknown genre"}), 400

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

    ai_scoring = ai_enabled and ai_idea is not None and candidates > 1
    tracks, progression, plan, summary, _ai_scores = _run_pipeline(
        config, roles, key_root, mode, bpm, bars, complexity,
        candidates, seed, humanize, ai_idea=ai_idea, ai_scoring=ai_scoring,
    )
    if ai_scoring and not _ai_scores:
        ai_score_note = "AI scoring failed, kept rule-based ranking"

    base_name = f"{config['genre']}_{'-'.join(roles)}_{key_root}{mode}_seed{seed}"
    mid_path = output_dir / f"{base_name}.mid"
    wav_path = output_dir / f"{base_name}.wav"
    export_midi(
        tracks, bpm, str(mid_path),
        tempo_map=build_tempo_map(config, plan, bpm),
    )
    _render_wav(mid_path, wav_path, gains)

    section_counts = {}
    for sb in plan:
        section_counts[sb.name] = section_counts.get(sb.name, 0) + 1

    candidate_entries = []
    for item in summary[:app.config["MAX_CANDIDATE_AUDIO"]]:
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

    return jsonify({
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
        "candidates": candidate_entries,
        "ai": {
            "enabled": ai_enabled,
            "idea": ai_idea,
            "note": ai_note,
            "score_note": ai_score_note,
        },
    })


@app.route("/play/<path:filename>")
def play(filename):
    return send_from_directory(app.config["OUTPUT_DIR"], filename)


@app.route("/download/<path:filename>")
def download(filename):
    return send_from_directory(app.config["OUTPUT_DIR"], filename, as_attachment=True)


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
