import { useEffect, useRef, useState, useCallback } from 'react'
import { wavUrl, fetchWithTimeout } from '../api'
import { roleColor, roleLabel } from '../roles'

export default function MixerPlayer({ stems }) {
  const ctxRef = useRef(null)
  const masterRef = useRef(null)
  const buffersRef = useRef([])
  const sourcesRef = useRef([])
  const gainsRef = useRef({})
  const startAtRef = useRef(0)
  const rafRef = useRef(null)
  const controlsRef = useRef({})

  const [ready, setReady] = useState(false)
  const [failed, setFailed] = useState(false)
  const [playing, setPlaying] = useState(false)
  const [progress, setProgress] = useState(0)
  const [dur, setDur] = useState(0)
  const [controls, setControls] = useState(() =>
    Object.fromEntries(stems.map((s) => [s.role, { vol: 1, mute: false, solo: false }])),
  )

  controlsRef.current = controls

  const computeGain = (role, snapshot) => {
    const c = snapshot[role] || { vol: 1, mute: false, solo: false }
    const anySolo = Object.values(snapshot).some((x) => x.solo)
    if (c.mute) return 0
    if (anySolo && !c.solo) return 0
    return c.vol
  }

  const stopAll = useCallback(() => {
    for (const src of sourcesRef.current) {
      try {
        src.stop()
      } catch {
        /* already stopped */
      }
    }
    sourcesRef.current = []
    cancelAnimationFrame(rafRef.current)
  }, [])

  useEffect(() => {
    let cancelled = false
    const Ctx = window.AudioContext || window.webkitAudioContext
    const ac = new Ctx()
    ctxRef.current = ac
    setReady(false)
    setFailed(false)
    buffersRef.current = []
    Promise.all(
      stems.map(async (s) => {
        const res = await fetchWithTimeout(wavUrl(s.wav), {}, 120000)
        const raw = await res.arrayBuffer()
        const buffer = await ac.decodeAudioData(raw)
        return { role: s.role, buffer }
      }),
    )
      .then((loaded) => {
        if (cancelled) return
        buffersRef.current = loaded
        setDur(Math.max(0, ...loaded.map((l) => l.buffer.duration)))
        setReady(true)
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })
    return () => {
      cancelled = true
      stopAll()
      ac.close().catch(() => {})
    }
  }, [stems, stopAll])

  function playAt(offset) {
    const ac = ctxRef.current
    if (!ac) return
    if (ac.state === 'suspended') ac.resume()
    stopAll()
    const master = ac.createGain()
    master.gain.value = 0.9
    master.connect(ac.destination)
    masterRef.current = master
    const srcs = buffersRef.current.map(({ role, buffer }) => {
      const src = ac.createBufferSource()
      src.buffer = buffer
      const g = ac.createGain()
      g.gain.value = computeGain(role, controlsRef.current)
      gainsRef.current[role] = g
      src.connect(g)
      g.connect(master)
      src.start(ac.currentTime, offset)
      return src
    })
    sourcesRef.current = srcs
    startAtRef.current = ac.currentTime - offset
    setPlaying(true)
    rafRef.current = requestAnimationFrame(tick)
  }

  function tick() {
    const ac = ctxRef.current
    if (!ac || !playing) return
    const t = ac.currentTime - startAtRef.current
    if (t >= dur) {
      setPlaying(false)
      setProgress(0)
      stopAll()
      return
    }
    setProgress(t)
    rafRef.current = requestAnimationFrame(tick)
  }

  function togglePlay() {
    if (playing) {
      stopAll()
      setPlaying(false)
      return
    }
    playAt(progress >= dur - 0.05 ? 0 : progress)
  }

  function scrub(e) {
    const rect = e.currentTarget.getBoundingClientRect()
    const ratio = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width))
    const offset = ratio * dur
    setProgress(offset)
    if (playing) playAt(offset)
  }

  function update(role, patch) {
    setControls((prev) => ({ ...prev, [role]: { ...prev[role], ...patch } }))
    const g = gainsRef.current[role]
    if (g && ctxRef.current) {
      const merged = { ...(controlsRef.current[role] || {}), ...patch }
      const snapshot = { ...controlsRef.current, [role]: merged }
      g.gain.setTargetAtTime(computeGain(role, snapshot), ctxRef.current.currentTime, 0.02)
    }
  }

  const anySolo = Object.values(controls).some((x) => x.solo)
  const fmt = (s) => {
    if (!s || !isFinite(s)) return '0:00'
    return `${Math.floor(s / 60)}:${Math.floor(s % 60).toString().padStart(2, '0')}`
  }

  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="text-xs font-semibold uppercase tracking-widest text-slate-500">
          Mixer
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs tabular-nums text-slate-500">
            {fmt(progress)} / {fmt(dur)}
          </span>
          <button
            onClick={togglePlay}
            disabled={!ready}
            className="btn-primary h-9 w-9 rounded-full text-sm disabled:opacity-40"
            title={playing ? 'Pause mix' : 'Play mix'}
          >
            {playing ? '❚❚' : '▶'}
          </button>
        </div>
      </div>

      <div
        className="mt-3 h-1.5 w-full cursor-pointer rounded-full bg-white/10"
        onClick={scrub}
      >
        <div
          className="h-full rounded-full bg-gradient-to-r from-[#ff7a1a] to-[#ffb25e]"
          style={{ width: `${dur ? (progress / dur) * 100 : 0}%` }}
        />
      </div>

      {!ready && !failed && (
        <div className="mt-3 text-xs text-slate-500">Loading stems…</div>
      )}
      {failed && (
        <div className="mt-3 text-xs text-red-400">Stem audio unavailable</div>
      )}

      <div className="mt-3 space-y-2">
        {stems.map((s) => {
          const c = controls[s.role] || { vol: 1, mute: false, solo: false }
          const isSoloed = anySolo && c.solo
          return (
            <div key={s.role} className="flex items-center gap-3">
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ background: roleColor(s.role) }}
              />
              <span className="w-28 truncate text-sm font-semibold text-slate-200">
                {roleLabel(s.role)}
              </span>
              <input
                type="range"
                min={0}
                max={1}
                step={0.01}
                className="accent w-full"
                value={c.vol}
                onChange={(e) => update(s.role, { vol: Number(e.target.value) })}
              />
              <button
                onClick={() => update(s.role, { mute: !c.mute })}
                className={`h-7 w-7 rounded-md text-xs font-bold transition ${
                  c.mute
                    ? 'bg-red-500/80 text-white'
                    : 'bg-white/10 text-slate-300 hover:bg-white/20'
                }`}
                title="Mute"
              >
                M
              </button>
              <button
                onClick={() => update(s.role, { solo: !c.solo })}
                className={`h-7 w-7 rounded-md text-xs font-bold transition ${
                  isSoloed
                    ? 'bg-[#ff7a1a] text-[#14100a]'
                    : 'bg-white/10 text-slate-300 hover:bg-white/20'
                }`}
                title="Solo"
              >
                S
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}
