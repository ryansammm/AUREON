"""Quick WAV render of a generated .mid so you can listen to the composition.

Synthesizes with numpy (no external binaries): **all melodic layers preview as
a piano voice** (drums keep their kit timbre), the mix is stereo with
per-role panning, a reverb bus and a soft limiter. Instrument identity is
kept in the MIDI (GM Program Change + track names), not in the preview audio.

The full master render adds a **master chain**: sidechain ducking of the
melodic/bass bus on every kick hit, a glue compressor, gentle saturation and
a final limiter, so the mix sounds "radio-ready". Stems stay dry/unmastered.

Usage:
    python tools\\render_audio.py output\\dubstep_full_top5.mid
    python tools\\render_audio.py output\\dubstep_full_top5.mid --gain 0.6 --no-reverb
"""

import argparse
import wave
from pathlib import Path

import numpy as np
from mido import MidiFile

SAMPLE_RATE = 44100

ROLE_PAN = {
    "bass": 0.0, "sub_bass": 0.0, "lead": 0.05, "counter_lead": -0.15,
    "pad": -0.3, "chord": 0.3, "arp": 0.15, "stab": 0.2, "drum": 0.0,
}
ROLE_GAIN = {
    "bass": 0.60, "sub_bass": 0.62, "lead": 0.50, "counter_lead": 0.40,
    "pad": 0.42, "chord": 0.42, "arp": 0.42, "stab": 0.48, "drum": 0.78,
    "drum_layers": 0.55,
}
DRUM_PAN = {
    35: 0.0, 36: 0.0,          # kick
    38: 0.0, 40: 0.05,         # snare
    39: -0.2,                  # clap
    42: 0.30, 44: 0.30, 46: 0.40,  # hats
    49: -0.35, 51: -0.35, 53: 0.35,  # crash / ride
    41: -0.25, 43: 0.25, 45: 0.0, 47: 0.0,  # toms
}
_NOISE_RNG = np.random.RandomState(7)


# --------------------------------------------------------------------------- #
# MIDI parsing
# --------------------------------------------------------------------------- #
def build_note_events(track, tpb: int, seconds_per_tick: float) -> list:
    active = {}
    events = []
    abs_time = 0
    for msg in track:
        abs_time += msg.time
        if msg.type == "note_on" and msg.velocity > 0:
            active[msg.note] = (abs_time, msg.velocity)
        elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
            start, vel_on = active.pop(msg.note, (None, 0))
            if start is not None and abs_time > start:
                events.append(
                    (start * seconds_per_tick,
                     (abs_time - start) * seconds_per_tick,
                     msg.note,
                     vel_on,
                     msg.channel)
                )
    return events


def track_role(track_name: str, notes: list) -> str:
    """Infer a track's role from its name (specific roles win over generic
    sound words, e.g. "Lead - Pluck" -> lead, "Chord - Dark Stabs" -> chord)."""
    name = (track_name or "").lower()
    if "layer" in name or "percussion" in name:
        return "drum_layers"
    if any(k in name for k in ("drum", "kit")):
        return "drum"
    if notes and notes[0][4] == 9:
        return "drum"
    if "sub" in name:
        return "sub_bass"
    if "bass" in name:
        return "bass"
    if "counter" in name:
        return "counter_lead"
    if "lead" in name:
        return "lead"
    if "pad" in name:
        return "pad"
    if "chord" in name:
        return "chord"
    if "stab" in name:
        return "stab"
    if "arp" in name or "pluck" in name:
        return "arp"
    pitches = [n[2] for n in notes]
    mean = sum(pitches) / len(pitches) if pitches else 0
    if mean < 48:
        return "bass"
    if mean >= 60:
        return "lead"
    return "pad"


# --------------------------------------------------------------------------- #
# Voices
# --------------------------------------------------------------------------- #
def _saw(freq: float, t: np.ndarray) -> np.ndarray:
    sig = 2.0 * ((t * freq) % 1.0) - 1.0
    smooth = (sig[:-1] + sig[1:]) / 2.0
    return np.concatenate([smooth, [sig[-1]]])


def _square(freq: float, t: np.ndarray) -> np.ndarray:
    return np.where(np.sin(2 * np.pi * t * freq) >= 0, 1.0, -1.0) * 0.5


def _pad(freq: float, t: np.ndarray) -> np.ndarray:
    det = np.sin(2 * np.pi * t * freq * 1.004)
    return (np.sin(2 * np.pi * t * freq) + det * 0.6) / 1.6


def _piano(freq: float, t: np.ndarray) -> np.ndarray:
    """Simple acoustic-piano-ish voice: harmonic partials + per-pitch decay."""
    partials = [1.0, 0.5, 0.33, 0.25, 0.18]
    sig = np.zeros_like(t)
    for i, amp in enumerate(partials, start=1):
        sig += amp * np.sin(2 * np.pi * t * freq * i)
    decay = np.exp(-t * (4.0 + freq * 0.004))
    return sig * decay / sum(partials)


def melodic_waveform(kind: str, freq: float, t: np.ndarray) -> np.ndarray:
    if kind == "saw":
        return _saw(freq, t)
    if kind == "square":
        return _square(freq, t)
    if kind == "piano":
        return _piano(freq, t)
    return _pad(freq, t)


def drum_waveform(pitch: int, t: np.ndarray) -> np.ndarray:
    n = len(t)
    if pitch in (35, 36):  # kick — pitch drop + click
        freq = 40 + 110 * np.exp(-t * 28)
        phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
        click = np.exp(-t * 220) * 0.4 * _NOISE_RNG.randn(n)
        return np.sin(phase) * np.exp(-t * 16) + click
    if pitch in (38, 40):  # snare — noise + body
        noise = _NOISE_RNG.randn(n)
        smooth = (noise[:-1] + noise[1:]) / 2.0
        noise = np.concatenate([smooth, [noise[-1]]])
        body = np.sin(2 * np.pi * t * 180) * np.exp(-t * 30)
        return noise * np.exp(-t * 22) * 0.9 + body * 0.4
    if pitch == 39:  # clap — clustered noise
        noise = _NOISE_RNG.randn(n)
        env = np.exp(-t * 26)
        return noise * env * 0.8
    if pitch in (42, 44):  # closed hat
        noise = _NOISE_RNG.randn(n)
        hi = np.diff(noise, prepend=0.0)  # crude highpass
        return hi * np.exp(-t * 130) * 0.7
    if pitch == 46:  # open hat
        noise = _NOISE_RNG.randn(n)
        hi = np.diff(noise, prepend=0.0)
        return hi * np.exp(-t * 14) * 0.7
    if pitch in (49, 51, 53):  # crash / ride
        noise = _NOISE_RNG.randn(n)
        hi = np.diff(noise, prepend=0.0)
        return hi * np.exp(-t * 3) * 0.6
    if pitch in (41, 43, 45, 47):  # toms
        freq = 200 if pitch in (41, 43) else 140
        phase = 2 * np.pi * np.cumsum(freq * np.exp(-t * 6)) / SAMPLE_RATE
        return np.sin(phase) * np.exp(-t * 9) * 0.8
    noise = _NOISE_RNG.randn(n)
    return noise * np.exp(-t * 10) * 0.5


def envelope(t: np.ndarray, dur: float, sustained: bool) -> np.ndarray:
    n = len(t)
    a = np.ones(n)
    attack = min(int(SAMPLE_RATE * 0.01), n)
    if attack:
        a[:attack] = np.linspace(0, 1, attack)
    if not sustained:
        rel = min(int(SAMPLE_RATE * 0.10), n)
        if rel:
            a[-rel:] = np.linspace(1, 0, rel) ** 1.5
    return a


def pan_gains(pan: float):
    angle = (pan + 1.0) * np.pi / 4.0
    return float(np.cos(angle)), float(np.sin(angle))


def fft_convolve(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    n = len(a) + len(b) - 1
    nfft = 1 << (n - 1).bit_length()
    fa = np.fft.rfft(a, nfft)
    fb = np.fft.rfft(b, nfft)
    return np.fft.irfft(fa * fb, nfft)[:n]


def make_reverb_ir(seconds: float = 1.2, decay: float = 4.5) -> np.ndarray:
    n = int(seconds * SAMPLE_RATE)
    t = np.arange(n) / SAMPLE_RATE
    ir = _NOISE_RNG.randn(n) * np.exp(-decay * t)
    return ir / (np.abs(ir).sum() or 1.0)


# --------------------------------------------------------------------------- #
# Master chain
# --------------------------------------------------------------------------- #
def kick_duck_envelope(
    kick_times: list,
    n: int,
    sample_rate: int = SAMPLE_RATE,
    reduction: float = 0.35,
    release: float = 0.16,
    attack: float = 0.004,
) -> np.ndarray:
    """Gain envelope that dips after every kick onset (exp decay, attack
    smoothed). Applied to the melodic/bass bus so the kick cuts through."""
    env = np.zeros(n)
    if not kick_times:
        return np.ones(n)
    t = np.arange(n) / sample_rate
    rel_samples = int(release * sample_rate)
    for kt in kick_times:
        i0 = int(kt * sample_rate)
        if i0 >= n:
            continue
        end = min(i0 + rel_samples, n)
        seg = np.exp(-(t[i0:end] - kt) / release)
        np.maximum(env[i0:end], seg, out=env[i0:end])
    gain = 1.0 - reduction * env
    k = max(1, int(attack * sample_rate))
    return np.convolve(gain, np.ones(k) / k, mode="same")


def glue_compress(
    l: np.ndarray,
    r: np.ndarray,
    sample_rate: int = SAMPLE_RATE,
    threshold: float = 0.45,
    ratio: float = 3.0,
    makeup: float = 1.05,
) -> tuple:
    """Feed-forward glue compressor: RMS sidechain, soft knee gain, ~2ms gain
    smoothing. Fully vectorized (no sample loops)."""
    n = len(l)
    if n == 0:
        return l, r
    side = np.maximum(np.abs(l), np.abs(r))
    window = max(1, int(0.010 * sample_rate))
    sq = side ** 2
    c = np.cumsum(np.insert(sq, 0, 0.0))
    rms = np.sqrt((c[window:] - c[:-window]) / window)
    rms = np.concatenate([np.full(window - 1, rms[0]), rms])
    over = rms > threshold
    gain = np.ones(n)
    gain[over] = (threshold + (rms[over] - threshold) / ratio) / np.maximum(
        rms[over], 1e-9
    )
    k = max(1, int(0.002 * sample_rate))
    smooth = np.convolve(gain, np.ones(k) / k, mode="same")
    return l * smooth * makeup, r * smooth * makeup


def apply_master_chain(
    l: np.ndarray,
    r: np.ndarray,
    sample_rate: int = SAMPLE_RATE,
) -> tuple:
    """Master bus: DC/hiss cleanup, glue compressor, warm saturation, limiter."""
    l = l - l.mean()
    r = r - r.mean()
    l, r = glue_compress(l, r, sample_rate)
    l = np.tanh(l * 1.25)
    r = np.tanh(r * 1.25)
    peak = max(np.max(np.abs(l)), np.max(np.abs(r))) or 1.0
    l = l / peak * 0.92
    r = r / peak * 0.92
    return l, r


def normalize_stem(l: np.ndarray, r: np.ndarray) -> tuple:
    """Level a dry stem the same way across render backends (peak 0.95)."""
    mono = (l + r) / 2.0
    peak = np.max(np.abs(mono)) or 1.0
    l = l / peak * 0.9
    r = r / peak * 0.9
    l = np.tanh(l * 1.25)
    r = np.tanh(r * 1.25)
    peak = max(np.max(np.abs(l)), np.max(np.abs(r))) or 1.0
    return l / peak * 0.95, r / peak * 0.95


# --------------------------------------------------------------------------- #
# Render
# --------------------------------------------------------------------------- #
def render_to_wav(
    mid_path: Path,
    out_path: Path,
    gain: float = 0.55,
    gains: dict = None,
    reverb: bool = True,
    roles: list = None,
    master: bool = True,
) -> float:
    """Render a .mid to a stereo .wav.

    Args:
        mid_path: input MIDI file.
        out_path: output WAV file.
        gain: master gain.
        gains: per-role gain overrides.
        reverb: add the shared reverb bus (dry for stems).
        roles: if given, only these roles are rendered (stem export).
        master: apply the full master chain (sidechain duck + glue + limiter).
                Disabled for stem renders so the mixer stays dry.
    """
    mid = MidiFile(str(mid_path))
    tempo = 500000
    for msg in mid.tracks[0]:
        if msg.type == "set_tempo":
            tempo = msg.tempo
    seconds_per_tick = tempo / 1e6 / mid.ticks_per_beat

    note_plans = []
    end_time = 0.0
    for track in mid.tracks:
        notes = build_note_events(track, mid.ticks_per_beat, seconds_per_tick)
        if not notes:
            continue
        role = track_role(track.name, notes)
        if roles and role not in roles:
            continue
        for start, dur, pitch, vel, channel in notes:
            freq = 440.0 * 2 ** ((pitch - 69) / 12)
            note_plans.append((start, dur, pitch, freq, vel, role))
            end_time = max(end_time, start + dur)
    if not note_plans:
        raise SystemExit(f"no notes found in {mid_path}")

    end_time += 1.0
    length = int(end_time * SAMPLE_RATE) + 1
    mel_l = np.zeros(length)
    mel_r = np.zeros(length)
    mel_wet = np.zeros(length)
    drm_l = np.zeros(length)
    drm_r = np.zeros(length)
    drm_wet = np.zeros(length)
    kick_times = []

    gains = {**ROLE_GAIN, **(gains or {})}
    is_drum = ("drum", "drum_layers")
    for start, dur, pitch, freq, vel, role in note_plans:
        t0 = int(start * SAMPLE_RATE)
        n = max(int(dur * SAMPLE_RATE), 1)
        t = np.arange(n) / SAMPLE_RATE
        if role in is_drum:
            sig = drum_waveform(pitch, t)
            pan = DRUM_PAN.get(pitch, 0.0)
            amp = (vel / 127) ** 0.7 * gains.get(role, 0.78) * gain
            env = np.ones(n)
        else:
            # Preview voice: all melodic layers render as piano so the mix
            # stays readable; drum voices keep their kit timbre. Instrument
            # identity lives in the MIDI export (GM Program Change + name).
            sig = melodic_waveform("piano", freq, t)
            pan = ROLE_PAN.get(role, 0.0)
            amp = (vel / 127) ** 0.7 * gains.get(role, 0.5) * gain
            env = envelope(t, dur, False)
        gl, gr = pan_gains(pan)
        seg = sig * env * amp
        if role in is_drum:
            drm_l[t0:t0 + n] += seg * gl
            drm_r[t0:t0 + n] += seg * gr
            if reverb:
                drm_wet[t0:t0 + n] += seg * 0.5
            if pitch in (35, 36):
                kick_times.append(start)
        else:
            mel_l[t0:t0 + n] += seg * gl
            mel_r[t0:t0 + n] += seg * gr
            if reverb:
                mel_wet[t0:t0 + n] += seg * 0.5

    if reverb:
        ir = make_reverb_ir()
        rev = fft_convolve(mel_wet, ir)
        n_out = min(len(mel_l), len(rev))
        mel_l[:n_out] += rev[:n_out] * 0.22
        mel_r[:n_out] += rev[:n_out] * 0.22
        rev = fft_convolve(drm_wet, ir)
        n_out = min(len(drm_l), len(rev))
        drm_l[:n_out] += rev[:n_out] * 0.22
        drm_r[:n_out] += rev[:n_out] * 0.22

    if master and kick_times:
        duck = kick_duck_envelope(kick_times, len(mel_l), SAMPLE_RATE)
        mel_l *= duck
        mel_r *= duck

    buf_l = mel_l + drm_l
    buf_r = mel_r + drm_r

    if master:
        buf_l, buf_r = apply_master_chain(buf_l, buf_r, SAMPLE_RATE)
    else:
        buf_l, buf_r = normalize_stem(buf_l, buf_r)

    frames = np.empty(2 * len(buf_l), dtype=np.int16)
    frames[0::2] = (np.clip(buf_l, -1.0, 1.0) * 32767).astype(np.int16)
    frames[1::2] = (np.clip(buf_r, -1.0, 1.0) * 32767).astype(np.int16)

    with wave.open(str(out_path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(frames.tobytes())

    seconds = len(frames) // 2 / SAMPLE_RATE
    print(
        f"rendered {mid_path.name}: {len(note_plans)} notes, "
        f"{seconds:.1f}s (stereo{' + reverb' if reverb else ''}"
        f"{' + master chain' if master else ''}) -> {out_path.name}"
    )
    return seconds


def main():
    ap = argparse.ArgumentParser(description="Render .mid ke WAV untuk didengarkan")
    ap.add_argument("input", help="path file .mid")
    ap.add_argument("--output", help="path WAV output (default: input .wav)")
    ap.add_argument("--gain", type=float, default=0.55, help="master gain")
    ap.add_argument("--no-reverb", action="store_true", help="disable reverb bus")
    args = ap.parse_args()

    mid_path = Path(args.input)
    out_path = Path(args.output) if args.output else mid_path.with_suffix(".wav")
    render_to_wav(mid_path, out_path, args.gain, reverb=not args.no_reverb)


if __name__ == "__main__":
    main()
