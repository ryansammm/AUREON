"""Local web UI (Phase 4, optional).

Binds to 127.0.0.1 only — do not expose to a public network without
adding authentication (project spec, Section 11).

Run with:
    python web\\app.py
then open http://127.0.0.1:8000
"""

import sys
from pathlib import Path

from flask import Flask, render_template, request, send_from_directory

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from engine.config_loader import CONFIG_DIR, load_genre_config  # noqa: E402
from engine.exporter import export_midi  # noqa: E402
from engine.pipeline import (  # noqa: E402
    build_tempo_map,
    generate_composition,
    generate_track,
)
from engine.selector import CandidateGenerator, Selector  # noqa: E402

app = Flask(__name__)
app.config["OUTPUT_DIR"] = ROOT / "output"
app.config["MAX_CANDIDATE_AUDIO"] = 5


def available_genres() -> list:
    return sorted(p.stem for p in CONFIG_DIR.glob("*.json"))


def genre_default_bpm() -> dict:
    out = {}
    for genre in available_genres():
        try:
            out[genre] = load_genre_config(genre)["default_bpm"]
        except Exception:
            continue
    return out


def _render_wav(mid_path: Path, wav_path: Path, gains: dict) -> None:
    from render_audio import render_to_wav

    render_to_wav(mid_path, wav_path, gain=0.55, gains=gains, reverb=True)


def _parse_gains(form) -> dict:
    out = {}
    for role, value in form.items():
        if role.startswith("gain_") and value:
            try:
                out[role[len("gain_"):]] = max(0.0, min(2.0, float(value)))
            except ValueError:
                continue
    return out


def _run_pipeline(config, roles, key_root, mode, bpm, bars, complexity,
                  candidates, seed, humanize):
    """Return (tracks, progression, plan, ranked_list)."""
    if candidates <= 1:
        if len(roles) > 1:
            tracks, progression, plan = generate_composition(
                config, roles, key_root, mode, bars=bars, complexity=complexity,
                seed=seed, humanize=humanize, bpm=bpm,
            )
        else:
            track, progression, plan = generate_track(
                config, roles[0], key_root, mode, bars=bars, complexity=complexity,
                seed=seed, humanize=humanize, bpm=bpm,
            )
            tracks = [track]
        return tracks, progression, plan, []
    else:
        generator = CandidateGenerator(config, seed=seed)
        candidates_list = generator.generate(
            roles[0], key_root, mode, bars=bars, complexity=complexity,
            count=candidates, base_seed=seed, humanize=humanize, roles=roles,
        )
        selector = Selector(config, seed=seed)
        multi = len(roles) > 1
        score_key = (
            lambda c: selector.score_composition(c[0])[0]
            if multi
            else selector.score_track(c[0][0])[0]
        )
        ranked = sorted(candidates_list, key=score_key, reverse=True)
        tracks, progression, plan = ranked[0][0], ranked[0][1], ranked[0][2]
        summary = []
        for i, (c_tracks, _, _, c_seed) in enumerate(ranked, start=1):
            score, _ = (
                selector.score_composition(c_tracks)
                if multi
                else selector.score_track(c_tracks[0])
            )
            summary.append({"rank": i, "seed": c_seed, "score": round(score, 3),
                            "tracks": c_tracks})
        return tracks, progression, plan, summary


@app.route("/")
def index():
    return render_template(
        "index.html",
        genres=available_genres(),
        roles=["bass", "lead", "chord", "pad", "arp", "stab", "sub_bass",
               "counter_lead", "drum", "drum_layers"],
        defaults=request.args,
        genre_bpm=genre_default_bpm(),
    )


@app.route("/generate", methods=["POST"])
def generate():
    form = request.form
    roles = [r for r in form.getlist("roles") if r] or ["bass"]
    key_root = form.get("key") or None
    mode = form.get("mode") or None
    bpm = form.get("bpm") or None
    bars = form.get("bars") or None
    complexity = form.get("complexity", "medium")
    candidates = int(form.get("candidates", "1") or "1")
    seed = int(form.get("seed") or 0)
    humanize = form.get("humanize") == "on"
    gains = _parse_gains(form)

    app.config["OUTPUT_DIR"].mkdir(parents=True, exist_ok=True)
    output_dir = app.config["OUTPUT_DIR"]

    try:
        config = load_genre_config(form.get("genre", "dubstep"))
        key_root = key_root or config["default_key"]
        mode = mode or config["default_mode"]
        bpm = int(bpm) if bpm else config["default_bpm"]
        bars = int(bars) if bars else None

        tracks, progression, plan, summary = _run_pipeline(
            config, roles, key_root, mode, bpm, bars, complexity,
            candidates, seed, humanize,
        )

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
        for item in summary:
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
                "mid": c_mid.name,
                "wav": c_wav.name,
            })

        result = {
            "genre": config["genre"],
            "key": f"{key_root} {mode}",
            "bpm": bpm,
            "humanized": humanize,
            "arrangement": ", ".join(f"{k}x{v}" for k, v in section_counts.items()),
            "chords": " -> ".join(c.degree for c in progression),
            "tracks": [
                {"name": t.track_name, "preset": t.suggested_preset, "notes": len(t.notes)}
                for t in tracks
            ],
            "mid": mid_path.name,
            "wav": wav_path.name,
            "candidates": candidate_entries,
        }
        return render_template("result.html", result=result)
    except Exception as exc:
        return render_template(
            "error.html", error=str(exc), genre=form.get("genre", "dubstep")
        ), 400


@app.route("/download/<path:filename>")
def download(filename):
    return send_from_directory(app.config["OUTPUT_DIR"], filename, as_attachment=True)


@app.route("/play/<path:filename>")
def play(filename):
    return send_from_directory(app.config["OUTPUT_DIR"], filename)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)
