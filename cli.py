"""CLI — generate a MIDI file from genre + role + parameters.

Examples:
    python cli.py --genre dubstep --role bass --key a --mode minor \
        --bpm 140 --bars 8 --complexity medium --seed 42
    python cli.py --genre house --candidates 5 --top 1 --no-humanize
"""

import argparse
import logging
import sys
from pathlib import Path

from engine.config_loader import load_genre_config
from engine.exporter import export_midi
from engine.pipeline import (
    build_tempo_map,
    generate_composition,
    generate_track,
)
from engine.selector import CandidateGenerator, Selector


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="midi-engine",
        description="Advanced MIDI Composition Engine (Phase 3).",
    )
    parser.add_argument("--genre", default="dubstep", help="genre config name")
    parser.add_argument("--role", default="bass", help="instrument role (bass/lead/pad/chord)")
    parser.add_argument("--roles", default=None,
                        help="comma-separated roles for multi-track, e.g. 'bass,lead,chord'")
    parser.add_argument("--key", default=None, help="key root, e.g. 'a' (default from config)")
    parser.add_argument("--mode", default=None, choices=["minor", "major"],
                        help="key mode (default from config)")
    parser.add_argument("--bpm", type=int, default=None, help="tempo (default from config)")
    parser.add_argument("--bars", type=int, default=None,
                        help="number of bars (default: full section template)")
    parser.add_argument("--complexity", choices=["simple", "medium", "complex"],
                        default="medium", help="rhythmic complexity")
    parser.add_argument("--candidates", type=int, default=3,
                        help="generate N candidates and score them (Layer 4)")
    parser.add_argument("--top", type=int, default=1,
                        help="number of best candidates to show/export")
    parser.add_argument("--seed", type=int, default=None, help="random seed for reproducibility")
    parser.add_argument("--no-humanize", action="store_true",
                        help="disable Layer 5 humanization (A/B comparison)")
    parser.add_argument("--report", action="store_true",
                        help="print metrics report for the selected output")
    parser.add_argument("--render", action="store_true",
                        help="also render each exported .mid to .wav (A/B listening)")
    parser.add_argument("--output", default=None, help="output .mid path")
    parser.add_argument("-v", "--verbose", action="store_true", help="show warning logs")
    return parser


def _default_output(config, role, key_root, mode, suffix=""):
    return (
        f"{config['genre']}_{role}_{key_root}{mode}_{suffix}.mid"
        if suffix
        else f"{config['genre']}_{role}_{key_root}{mode}.mid"
    )


def _render_to_wav(mid_path: str, wav_path: str) -> None:
    """Render a .mid to .wav using tools/render_audio (best-effort)."""
    tools_dir = Path(__file__).resolve().parent / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    from render_audio import render_to_wav

    render_to_wav(Path(mid_path), Path(wav_path))


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.verbose:
        logging.basicConfig(level=logging.WARNING)

    try:
        config = load_genre_config(args.genre)
        key_root = args.key or config["default_key"]
        mode = args.mode or config["default_mode"]
        bpm = args.bpm or config["default_bpm"]
        humanize = not args.no_humanize
        top_n = min(args.top, args.candidates)
        roles = [r.strip() for r in args.roles.split(",")] if args.roles else [args.role]
        multi = len(roles) > 1

        ranked = None
        if args.candidates <= 1:
            if multi:
                tracks, progression, plan = generate_composition(
                    config=config,
                    roles=roles,
                    key_root=key_root,
                    mode=mode,
                    bars=args.bars,
                    complexity=args.complexity,
                    seed=args.seed,
                    humanize=humanize,
                    bpm=bpm,
                )
            else:
                track, progression, plan = generate_track(
                    config=config,
                    role=roles[0],
                    key_root=key_root,
                    mode=mode,
                    bars=args.bars,
                    complexity=args.complexity,
                    seed=args.seed,
                    humanize=humanize,
                    bpm=bpm,
                )
                tracks = [track]
            ranked = [(tracks, progression, plan, args.seed)]
        else:
            generator = CandidateGenerator(config, seed=args.seed)
            candidates = generator.generate(
                roles[0], key_root, mode,
                bars=args.bars, complexity=args.complexity,
                count=args.candidates, base_seed=args.seed, humanize=humanize,
                roles=roles,
            )
            selector = Selector(config, seed=args.seed)
            score_key = (
                lambda c: selector.score_composition(c[0])[0] if multi
                else selector.score_track(c[0][0])[0]
            )
            ranked = sorted(candidates, key=score_key, reverse=True)

        for rank_index, (tracks, progression, plan, seed) in enumerate(
            ranked[:top_n], start=1
        ):
            suffix = f"top{rank_index}_of{args.candidates}" if args.candidates > 1 else ""
            output = args.output or _default_output(
                config, "-".join(roles), key_root, mode, suffix
            )
            export_midi(
                tracks, bpm, output,
                tempo_map=build_tempo_map(config, plan, bpm),
            )
            if args.render:
                render_path = str(Path(output).with_suffix(".wav"))
                _render_to_wav(output, render_path)
                print(f"audio     : {render_path}")

            if rank_index > 1:
                continue

            chords = " -> ".join(c.degree for c in progression)
            section_counts = {}
            for sb in plan:
                section_counts[sb.name] = section_counts.get(sb.name, 0) + 1
            arrangement = ", ".join(f"{name}x{count}" for name, count in section_counts.items())
            print(f"genre     : {config['genre']}")
            print(f"key/mode  : {key_root} {mode}")
            print(f"bpm       : {bpm}")
            print(f"humanized : {humanize}")
            print(f"arrangement: {arrangement}")
            print(f"chords    : {chords}")
            for t in tracks:
                print(
                    f"track     : {t.track_name}  [{t.suggested_preset}] "
                    f"({len(t.notes)} notes)"
                )
            print(f"output    : {output}")

            if args.report:
                from engine.metrics import analyze_composition

                report = analyze_composition(tracks, plan)
                print(f"\nreport ({report['summary']['total_notes']} notes, "
                      f"{report['summary']['bars']} bars):")
                for stat in report["tracks"]:
                    print(
                        f"  {stat['role']:<8} notes={stat['notes']:<4} "
                        f"density={stat['density']:<5} "
                        f"pitch {stat['pitch_min']}-{stat['pitch_max']} "
                        f"avg_vel={stat['avg_velocity']:<5} "
                        f"leap={stat['mean_leap']:<5} "
                        f"dissonance={stat['dissonance_rate']}"
                    )

        if args.candidates > 1:
            selector = Selector(config, seed=args.seed)
            print(f"\nranking ({args.candidates} candidates, seed base {args.seed}):")
            for rank_index, (tracks, _, _, seed) in enumerate(ranked, start=1):
                score, det = (
                    selector.score_composition(tracks) if multi
                    else selector.score_track(tracks[0])
                )
                detail = (
                    f"(mean of {len(tracks)} tracks)"
                    if multi
                    else (
                        f"(dissonance={det['dissonance']:.2f}, "
                        f"repetition={det['repetition']:.2f}, "
                        f"voice_leading={det['voice_leading']:.2f})"
                    )
                )
                print(f"  #{rank_index} seed={seed} score={score:.3f} {detail}")
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
