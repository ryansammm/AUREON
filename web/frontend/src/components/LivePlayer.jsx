import { useRef, useState } from 'react'
import { parseMidi } from 'midi-file'
import { trackMidiUrl, fetchWithTimeout } from '../api'
import { roleLabel } from '../roles'

// MusyngKite (gleitz) GM names per AUREON role — real instrument timbres.
const SF_NAME = {
  sub_bass: 'synth_bass_1',
  bass: 'electric_bass_finger',
  lead: 'lead_2_sawtooth',
  counter_lead: 'lead_1_square',
  arp: 'lead_3_calliope',
  stab: 'synth_strings_1',
  chord: 'electric_piano_2',
  pad: 'pad_2_warm',
}
const DRUM_ROLES = new Set(['drum', 'drum_layers'])

function parseRoleNotes(buffer) {
  const midi = parseMidi(buffer)
  const tpb = midi.header.ticksPerBeat || 480
  let usPerBeat = 500000
  for (const ev of midi.tracks[0] || []) {
    if (ev.type === 'setTempo') usPerBeat = ev.microsecondsPerBeat
  }
  const secPerTick = usPerBeat / 1e6 / tpb
  const notes = []
  for (const tr of midi.tracks.slice(1)) {
    let t = 0
    const active = new Map()
    for (const ev of tr) {
      t += ev.deltaTime
      if (ev.type === 'noteOn') {
        active.set(ev.noteNumber, { t, vel: ev.velocity })
      } else if (ev.type === 'noteOff' && active.has(ev.noteNumber)) {
        const s = active.get(ev.noteNumber)
        notes.push({
          note: ev.noteNumber,
          vel: s.vel,
          start: s.t * secPerTick,
          dur: Math.max((t - s.t) * secPerTick, 0.08),
        })
        active.delete(ev.noteNumber)
      }
    }
  }
  return notes
}

function makeDrums(Tone) {
  const out = new Tone.Gain(1).toDestination()
  const noise = (filterFreq, type, env, vol = -6) =>
    new Tone.NoiseSynth({
      noise: { type },
      envelope: env,
      volume: vol,
    }).chain(new Tone.Filter(filterFreq, type), out)
  const kick = new Tone.MembraneSynth({
    pitchDecay: 0.05,
    octaves: 6,
    envelope: { attack: 0.001, decay: 0.35, sustain: 0, release: 0.1 },
    volume: -4,
  }).connect(out)
  const snare = noise(1800, 'bandpass', { attack: 0.001, decay: 0.2, sustain: 0, release: 0.05 }, -2)
  const hatC = noise(8500, 'highpass', { attack: 0.001, decay: 0.04, sustain: 0, release: 0.01 }, -8)
  const hatO = noise(8500, 'highpass', { attack: 0.002, decay: 0.28, sustain: 0, release: 0.05 }, -8)
  const clap = noise(1200, 'bandpass', { attack: 0.005, decay: 0.18, sustain: 0, release: 0.05 }, -4)
  const crash = new Tone.MetalSynth({
    frequency: 480,
    envelope: { attack: 0.001, decay: 0.8, sustain: 0, release: 0.3 },
    harmonicity: 8,
    modulationIndex: 40,
    resonance: 800,
    octaves: 2,
    volume: -10,
  }).connect(out)
  const tomL = new Tone.MembraneSynth({
    pitchDecay: 0.08,
    octaves: 4,
    envelope: { attack: 0.002, decay: 0.3, sustain: 0, release: 0.1 },
    volume: -7,
  }).connect(out)
  const tomH = new Tone.MembraneSynth({
    pitchDecay: 0.08,
    octaves: 4,
    envelope: { attack: 0.002, decay: 0.3, sustain: 0, release: 0.1 },
    volume: -7,
  }).connect(out)
  return { kick, snare, hatC, hatO, clap, crash, tomL, tomH, out }
}

function triggerDrum(synths, pitch, vel) {
  const v = 0.35 + 0.65 * (vel / 127)
  const { kick, snare, hatC, hatO, clap, crash, tomL, tomH } = synths
  if (pitch === 35 || pitch === 36) kick.triggerAttackRelease('C1', 0.4, undefined, v)
  else if (pitch === 38 || pitch === 40) snare.triggerAttackRelease(0.3, undefined, v)
  else if (pitch === 39) clap.triggerAttackRelease(0.25, undefined, v)
  else if (pitch === 42 || pitch === 44) hatC.triggerAttackRelease(0.06, undefined, v)
  else if (pitch === 46) hatO.triggerAttackRelease(0.3, undefined, v * 0.8)
  else if (pitch === 49) crash.triggerAttackRelease('C5', 0.9, undefined, v * 0.6)
  else if (pitch === 51) crash.triggerAttackRelease('G5', 0.9, undefined, v * 0.5)
  else if (pitch === 53) crash.triggerAttackRelease('E5', 0.6, undefined, v * 0.5)
  else if (pitch === 41 || pitch === 43) tomL.triggerAttackRelease(pitch === 43 ? 'D2' : 'C2', 0.3, undefined, v)
  else if (pitch === 45 || pitch === 47) tomH.triggerAttackRelease(pitch === 47 ? 'A1' : 'G1', 0.3, undefined, v)
}

async function loadInstrument(ctx, role, Soundfont) {
  const names = [SF_NAME[role], 'acoustic_grand_piano'].filter(Boolean)
  for (const name of names) {
    try {
      return await Soundfont.instrument(ctx, name)
    } catch {
      /* try next name */
    }
  }
  return null
}

export default function LivePlayer({ mid, roles = [] }) {
  const [playing, setPlaying] = useState(false)
  const [loading, setLoading] = useState(false)
  const [engine, setEngine] = useState('')
  const stateRef = useRef({})
  const toneRef = useRef(null)

  async function play() {
    if (playing || loading) return
    setLoading(true)
    setPlaying(true)
    setEngine('')
    try {
      // Loaded lazily so Tone.js (≈370KB) only hits the network on demand.
      const [toneNs, sfModule] = await Promise.all([
        import('tone'),
        import('soundfont-player'),
      ])
      const Tone = toneNs.default || toneNs
      const Soundfont = sfModule.default || sfModule
      toneRef.current = Tone

      await Tone.start()
      Tone.getTransport().cancel()
      Tone.getTransport().stop()
      const ctx = Tone.getContext()
      const melodicRoles = roles.filter((r) => !DRUM_ROLES.has(r))
      const drumRoles = roles.filter((r) => DRUM_ROLES.has(r))

      // Load real GM instruments (SoundFont) with a poly-synth fallback.
      const instruments = {}
      let anySf = false
      const fallbackSynth = new Tone.PolySynth(Tone.Synth, {
        oscillator: { type: 'triangle' },
        envelope: { attack: 0.005, decay: 0.3, sustain: 0.4, release: 0.4 },
        volume: -6,
      }).toDestination()
      for (const role of melodicRoles) {
        const inst = await loadInstrument(ctx, role, Soundfont)
        if (inst) {
          instruments[role] = inst
          anySf = true
        }
      }
      setEngine(anySf ? 'SoundFont (GM)' : 'Built-in synth (SoundFont offline)')

      const synths = drumRoles.length ? makeDrums(Tone) : null
      const plan = []
      for (const role of roles) {
        try {
          const res = await fetchWithTimeout(trackMidiUrl(mid, role), {}, 60000)
          if (!res.ok) continue
          const buf = await res.arrayBuffer()
          const notes = parseRoleNotes(buf)
          for (const n of notes) plan.push({ role, ...n })
        } catch {
          /* skip role on fetch failure */
        }
      }
      plan.sort((a, b) => a.start - b.start)

      const state = { instruments, fallbackSynth, synths }
      stateRef.current = state

      const schedule = (n) => {
        if (DRUM_ROLES.has(n.role)) {
          if (synths) triggerDrum(synths, n.note, n.vel)
        } else {
          const inst = instruments[n.role] || null
          if (inst) {
            inst.play(n.note, Tone.now(), {
              duration: Math.min(Math.max(n.dur, 0.15), 2.5),
              velocity: 0.5 + 0.5 * (n.vel / 127),
              gain: 0.55,
            })
          } else {
            fallbackSynth.triggerAttackRelease(
              Tone.Frequency(n.note, 'midi').toNote(),
              Math.min(Math.max(n.dur, 0.15), 2.5),
              Tone.now(),
              n.vel / 127,
            )
          }
        }
      }
      for (const n of plan) Tone.getTransport().scheduleAtTime(() => schedule(n), n.start)

      const end = plan.length ? Math.max(...plan.map((p) => p.start + p.dur)) : 0
      Tone.getTransport().start()
      if (end > 0) {
        window.setTimeout(() => {
          if (stateRef.current === state) stop()
        }, end * 1000 + 800)
      }
    } catch (e) {
      setEngine(`Playback failed: ${String(e.message || e)}`)
      setPlaying(false)
    } finally {
      setLoading(false)
    }
  }

  function stop() {
    const Tone = toneRef.current
    if (!Tone) {
      setPlaying(false)
      setLoading(false)
      return
    }
    try {
      Tone.getTransport().cancel()
      Tone.getTransport().stop()
    } catch {
      /* ignore */
    }
    const { instruments, fallbackSynth, synths } = stateRef.current
    stateRef.current = {}
    Object.values(instruments || {}).forEach((inst) => {
      try {
        inst.stop && inst.stop()
      } catch {
        /* ignore */
      }
    })
    try {
      fallbackSynth && fallbackSynth.dispose()
    } catch {
      /* ignore */
    }
    if (synths) {
      try {
        Object.values(synths).forEach((s) => s.dispose && s.dispose())
      } catch {
        /* ignore */
      }
    }
    setPlaying(false)
    setLoading(false)
  }

  const toggle = () => (playing ? stop() : play())

  return (
    <div className="glass rounded-xl p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-sm font-semibold">Live playback (instruments)</div>
          <div className="text-xs text-slate-500">
            Plays the actual MIDI per role through GM SoundFonts in your
            browser — no render needed.
            {engine && <span className="text-[#ffb25e]"> · {engine}</span>}
          </div>
        </div>
        <button
          className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${
            playing
              ? 'bg-red-500/20 text-red-300 hover:bg-red-500/30'
              : 'btn-primary'
          }`}
          onClick={toggle}
          disabled={loading}
        >
          {loading ? 'Loading…' : playing ? '■ Stop' : '▶ Play instruments'}
        </button>
      </div>
      {roles.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {roles.map((r) => (
            <span
              key={r}
              className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[11px] font-semibold text-slate-300"
            >
              {roleLabel(r)}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
