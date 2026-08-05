"""Optional server-side SoundFont rendering via FluidSynth.

Renders a .mid with a real General MIDI SoundFont (e.g. GeneralUser GS) instead
of the numpy piano-synth preview. The master render still goes through the
numpy ``apply_master_chain`` (sidechain duck + glue + limiter); stems are
level-normalized so the mixer keeps a clean, dry signal.

Falls back cleanly (returns ``None``) whenever the FluidSynth binary or a
SoundFont cannot be found, so the app never breaks without them. A warning is
logged with the missing piece and the env var that fixes it.

Locations are resolved in order:
  1. ``AUREON_FLUIDSYNTH`` / ``AUREON_SOUNDFONT`` env vars (if set)
  2. ``fluidsynth`` on ``PATH``
  3. a small set of common cross-platform install locations
Set ``AUREON_SOUNDFONT=0`` to force the numpy renderer.
"""

import logging
import os
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np
from mido import MidiFile

from render_audio import (
    SAMPLE_RATE,
    apply_master_chain,
    build_note_events,
    normalize_stem,
    track_role,
)

log = logging.getLogger(__name__)

# Common cross-platform install locations (no personal dev-machine paths).
_COMMON_BINS = [
    Path("/usr/bin/fluidsynth"),
    Path("/usr/local/bin/fluidsynth"),
    Path("/opt/homebrew/bin/fluidsynth"),  # macOS Apple Silicon
    Path("/opt/local/bin/fluidsynth"),  # macOS MacPorts
    Path(r"C:\Program Files\FluidSynth\bin\fluidsynth.exe"),
    Path(r"C:\Program Files (x86)\FluidSynth\bin\fluidsynth.exe"),
    Path(os.environ.get("LOCALAPPDATA", "")) / r"Programs\fluidsynth\bin\fluidsynth.exe",
]

# Common SoundFont directories, checked for *.sf2 / *.sf3.
_COMMON_SF_DIRS = [
    Path("/usr/share/sounds/sf2"),
    Path("/usr/share/sounds/sf3"),
    Path("/usr/share/sounds"),
    Path("/Library/Audio/Sounds/Banks"),  # macOS
]


def _find_binary() -> Path | None:
    env = os.environ.get("AUREON_FLUIDSYNTH")
    if env:
        p = Path(env)
        if p.is_file():
            return p
        log.warning("AUREON_FLUIDSYNTH=%r does not point to a file; ignoring", env)
    found = shutil.which("fluidsynth")
    if found:
        return Path(found)
    for p in _COMMON_BINS:
        if p.is_file():
            return p
    return None


def _find_soundfont() -> Path | None:
    env = os.environ.get("AUREON_SOUNDFONT")
    if env and env != "0":
        p = Path(env)
        if p.is_file():
            return p
        log.warning("AUREON_SOUNDFONT=%r does not point to a file; ignoring", env)
    for base in _COMMON_SF_DIRS:
        if base.is_dir():
            for pattern in ("*.sf2", "*.sf3"):
                hits = sorted(base.glob(pattern))
                if hits:
                    return hits[0]
    return None


def renderer_status() -> dict:
    """Report which renderer is available and what pieces are missing."""
    binary = _find_binary()
    soundfont = _find_soundfont()
    disabled = os.environ.get("AUREON_SOUNDFONT") == "0"
    available = not disabled and bool(binary) and bool(soundfont)
    return {
        "available": available,
        "disabled": disabled,
        "binary": str(binary) if binary else None,
        "soundfont": str(soundfont) if soundfont else None,
    }


def soundfont_available() -> bool:
    return renderer_status()["available"]


def log_fallback_reason(status: dict = None) -> None:
    """Log which piece is missing so users know how to get real GM sound."""
    status = status or renderer_status()
    if status["disabled"]:
        log.warning(
            "SoundFont rendering disabled (AUREON_SOUNDFONT=0); using the "
            "numpy piano-synth fallback."
        )
        return
    if not status["binary"]:
        log.warning(
            "FluidSynth binary not found; falling back to the numpy "
            "piano-synth renderer. Install FluidSynth or set "
            "AUREON_FLUIDSYNTH=<path to fluidsynth>."
        )
        return
    if not status["soundfont"]:
        log.warning(
            "SoundFont not found; falling back to the numpy piano-synth "
            "renderer. Set AUREON_SOUNDFONT=<path to a .sf2/.sf3>."
        )
        return
    log.warning(
        "SoundFont renderer unavailable; using the numpy piano-synth "
        "fallback."
    )


def filter_midi_roles(mid_path: Path, roles: list) -> MidiFile:
    """Return a MIDI containing only the given role tracks (keeps track 0)."""
    mid = MidiFile(str(mid_path))
    keep = [mid.tracks[0]] if mid.tracks else []
    for tr in mid.tracks[1:]:
        notes = build_note_events(tr, mid.ticks_per_beat, 1.0)
        if track_role(tr.name, notes) in roles:
            keep.append(tr)
    out = MidiFile(ticks_per_beat=mid.ticks_per_beat)
    out.tracks = keep
    return out


def _read_wav(path: Path) -> tuple:
    with wave.open(str(path), "rb") as w:
        frames = w.readframes(w.getnframes())
        channels = w.getnchannels()
    arr = np.frombuffer(frames, dtype="<i2").astype(np.float64) / 32767.0
    if channels == 2:
        arr = arr.reshape(-1, 2)
        return arr[:, 0], arr[:, 1]
    return arr, arr


def _write_wav(path: Path, l: np.ndarray, r: np.ndarray) -> None:
    n = min(len(l), len(r))
    frames = np.empty(2 * n, dtype="<i2")
    frames[0::2] = (np.clip(l[:n], -1.0, 1.0) * 32767).astype("<i2")
    frames[1::2] = (np.clip(r[:n], -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(frames.tobytes())


def render_midi_with_soundfont(
    mid_path: Path,
    out_path: Path,
    gain: float = 1.0,
    roles: list = None,
    master: bool = True,
    timeout: int = 120,
) -> float | None:
    """Render ``mid_path`` to ``out_path`` via FluidSynth + GM SoundFont.

    Returns the duration in seconds, or ``None`` if unavailable / failed
    (caller should fall back to the numpy renderer). Bounded by ``timeout`` so
    a wedged FluidSynth process can never hang a request.
    """
    binary = _find_binary()
    sf = _find_soundfont()
    if not soundfont_available():
        log_fallback_reason()
        return None
    filtered = None
    if roles:
        filtered = out_path.with_name(f"{out_path.stem}_rolefilter.mid")
        filter_midi_roles(mid_path, roles).save(str(filtered))
        src = filtered
    else:
        src = mid_path

    raw = Path(tempfile.gettempdir()) / f"aureon_sf_{os.getpid()}_{out_path.stem}.wav"
    flags = ["-ni", "-C", "0"]
    if roles:
        flags += ["-R", "0"]
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        proc = subprocess.run(
            [str(binary), *flags, "-F", str(raw), "-r", str(SAMPLE_RATE),
             "-g", str(gain), str(sf), str(src)],
            capture_output=True,
            timeout=timeout,
            check=False,
            **kwargs,
        )
        if proc.returncode != 0 or not raw.is_file():
            log.warning(
                "FluidSynth failed (exit %s); falling back to the numpy "
                "piano-synth renderer.", proc.returncode
            )
            return None
        l, r = _read_wav(raw)
        if master:
            l, r = apply_master_chain(l, r, SAMPLE_RATE)
        else:
            l, r = normalize_stem(l, r)
        _write_wav(out_path, l, r)
        return len(l) / SAMPLE_RATE
    except subprocess.TimeoutExpired:
        log.warning(
            "FluidSynth timed out after %ss; falling back to the numpy "
            "piano-synth renderer.", timeout
        )
        return None
    except Exception as exc:  # noqa: BLE001 - renderer is best-effort
        log.warning(
            "FluidSynth render raised %s; falling back to the numpy "
            "piano-synth renderer.", exc
        )
        return None
    finally:
        raw.unlink(missing_ok=True)
        if filtered is not None:
            filtered.unlink(missing_ok=True)
