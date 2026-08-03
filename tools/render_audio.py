"""Quick WAV render of a generated .mid so you can listen to the composition.

Synthesizes with numpy (no external binaries): melodic voices use
sine/saw/square + ADSR-ish envelopes, percussion uses pitched/noisy drum
voices, and the mix is stereo with per-role panning, a reverb bus and a
soft limiter.

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


def melodic_waveform(kind: str, freq: float, t: np.ndarray) -> np.ndarray:
    if kind == "saw":
        return _saw(freq, t)
    if kind == "square":
        return _square(freq, t)
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
# Render
# --------------------------------------------------------------------------- #
def render_to_wav(
    mid_path: Path,
    out_path: Path,
    gain: float = 0.55,
    gains: dict = None,
    reverb: bool = True,
    roles: list = None,
) -> float:
    """Render a .mid to a stereo .wav.

    Args:
        mid_path: input MIDI file.
        out_path: output WAV file.
        gain: master gain.
        gains: per-role gain overrides.
        reverb: add the shared reverb bus (dry for stems).
        roles: if given, only these roles are rendered (stem export).
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
    buf_l = np.zeros(int(end_time * SAMPLE_RATE) + 1)
    buf_r = np.zeros(int(end_time * SAMPLE_RATE) + 1)
    wet = np.zeros_like(buf_l)

    gains = {**ROLE_GAIN, **(gains or {})}
    for start, dur, pitch, freq, vel, role in note_plans:
        t0 = int(start * SAMPLE_RATE)
        n = max(int(dur * SAMPLE_RATE), 1)
        t = np.arange(n) / SAMPLE_RATE
        if role in ("drum", "drum_layers"):
            sig = drum_waveform(pitch, t)
            pan = DRUM_PAN.get(pitch, 0.0)
            amp = (vel / 127) ** 0.7 * gains.get(role, 0.78) * gain
            env = np.ones(n)
        else:
            kind = {"bass": "saw", "sub_bass": "saw", "lead": "square",
                    "counter_lead": "square", "pad": "pad", "chord": "pad",
                    "arp": "square", "stab": "square"}.get(role, "square")
            sig = melodic_waveform(kind, freq, t)
            pan = ROLE_PAN.get(role, 0.0)
            amp = (vel / 127) ** 0.7 * gains.get(role, 0.5) * gain
            env = envelope(t, dur, role in ("pad", "chord"))
        gl, gr = pan_gains(pan)
        seg = sig * env * amp
        buf_l[t0:t0 + n] += seg * gl
        buf_r[t0:t0 + n] += seg * gr
        if reverb:
            wet[t0:t0 + n] += seg * 0.5

    if reverb:
        ir = make_reverb_ir()
        rev = fft_convolve(wet, ir)
        n_out = min(len(buf_l), len(rev))
        buf_l[:n_out] += rev[:n_out] * 0.22
        buf_r[:n_out] += rev[:n_out] * 0.22

    mono = (buf_l + buf_r) / 2.0
    peak = np.max(np.abs(mono)) or 1.0
    buf_l = buf_l / peak * 0.9
    buf_r = buf_r / peak * 0.9
    buf_l = np.tanh(buf_l * 1.25)
    buf_r = np.tanh(buf_r * 1.25)
    peak = max(np.max(np.abs(buf_l)), np.max(np.abs(buf_r))) or 1.0
    buf_l = buf_l / peak * 0.95
    buf_r = buf_r / peak * 0.95

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
        f"{seconds:.1f}s (stereo{' + reverb' if reverb else ''}) -> {out_path.name}"
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
