import { useEffect, useRef, useState, useMemo, useCallback } from 'react'

const ROLECOLOR = {
  bass: '#7dd3fc',
  lead: '#ff7a1a',
  chord: '#a78bfa',
  pad: '#34d399',
  arp: '#f472b6',
  stab: '#fbbf24',
  sub_bass: '#22d3ee',
  counter_lead: '#fb7185',
  drum: '#e2e8f0',
  drum_layers: '#94a3b8',
}

const NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
const noteName = (p) => `${NOTE_NAMES[p % 12]}${Math.floor(p / 12) - 1}`
const BEATS_PER_BAR = 4
const PX = 16

export default function PianoRoll({ tracks, bpm, totalBeats, height = 380 }) {
  const wrapRef = useRef(null)
  const canvasRef = useRef(null)
  const [barsVisible, setBarsVisible] = useState(24)
  const [scroll, setScroll] = useState(0)
  const [hover, setHover] = useState(null)
  const dragRef = useRef(null)
  const hoverRafRef = useRef(0)
  const pendingHoverRef = useRef(null)

  const viewW = barsVisible * BEATS_PER_BAR * PX

  const { minPitch, maxPitch, notes, byPitch, maxDurByPitch } = useMemo(() => {
    let mn = 60
    let mx = 60
    const all = []
    const byPitch = new Map()
    const maxDurByPitch = new Map()
    for (const t of tracks || []) {
      for (const [p, s, d] of t.midi) {
        const note = { role: t.role, pitch: p, start: s, dur: d }
        all.push(note)
        if (p < mn) mn = p
        if (p > mx) mx = p
        if (!byPitch.has(p)) byPitch.set(p, [])
        byPitch.get(p).push(note)
        maxDurByPitch.set(p, Math.max(maxDurByPitch.get(p) || 0, d))
      }
    }
    for (const arr of byPitch.values()) arr.sort((a, b) => a.start - b.start)
    return { minPitch: mn - 2, maxPitch: mx + 2, notes: all, byPitch, maxDurByPitch }
  }, [tracks])

  const rowH = 10
  const rulerH = 34
  const heightPx = (maxPitch - minPitch) * rowH + rulerH + 6
  const maxScroll = Math.max(0, totalBeats * PX - viewW)

  const draw = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const dpr = window.devicePixelRatio || 1
    canvas.width = viewW * dpr
    canvas.height = heightPx * dpr
    canvas.style.width = `${viewW}px`
    canvas.style.height = `${heightPx}px`
    const ctx = canvas.getContext('2d')
    ctx.scale(dpr, dpr)

    ctx.fillStyle = 'rgba(255,255,255,0.02)'
    ctx.fillRect(0, 0, viewW, heightPx)

    // beat grid
    const beatW = PX
    ctx.strokeStyle = 'rgba(255,255,255,0.05)'
    ctx.lineWidth = 1
    ctx.beginPath()
    for (let b = 0; b <= totalBeats; b++) {
      const x = b * beatW - scroll
      if (x < -PX || x > viewW + PX) continue
      ctx.moveTo(x, rulerH)
      ctx.lineTo(x, heightPx)
    }
    ctx.stroke()

    // bar grid + labels
    ctx.strokeStyle = 'rgba(255,255,255,0.13)'
    ctx.beginPath()
    const labelEvery = barsVisible > 64 ? 4 : barsVisible > 32 ? 2 : 1
    ctx.font = '600 11px Inter, sans-serif'
    ctx.fillStyle = 'rgba(255,255,255,0.45)'
    for (let b = 0; b <= totalBeats; b += BEATS_PER_BAR) {
      const x = b * PX - scroll
      if (x < -PX || x > viewW + PX) continue
      ctx.moveTo(x, rulerH)
      ctx.lineTo(x, heightPx)
      const bar = b / BEATS_PER_BAR
      if (bar % labelEvery === 0) ctx.fillText(String(bar + 1), x + 4, 16)
    }
    ctx.stroke()

    // ruler bottom line
    ctx.strokeStyle = 'rgba(255,255,255,0.18)'
    ctx.beginPath()
    ctx.moveTo(0, rulerH)
    ctx.lineTo(viewW, rulerH)
    ctx.stroke()

    // bpm chip
    ctx.fillStyle = 'rgba(255,122,26,0.9)'
    ctx.font = '700 11px Inter, sans-serif'
    const bpmText = `${bpm} BPM`
    const tw = ctx.measureText(bpmText).width
    ctx.fillRect(viewW - tw - 18, 8, tw + 12, 18)
    ctx.fillStyle = '#14100a'
    ctx.fillText(bpmText, viewW - tw - 12, 21)

    // pitch rows
    for (let p = minPitch; p <= maxPitch; p++) {
      const y = rulerH + (maxPitch - p) * rowH
      ctx.strokeStyle =
        p % 12 === 0 ? 'rgba(255,255,255,0.14)' : 'rgba(255,255,255,0.045)'
      ctx.beginPath()
      ctx.moveTo(0, y + rowH)
      ctx.lineTo(viewW, y + rowH)
      ctx.stroke()
      if (p % 12 === 0) {
        ctx.font = '600 9px Inter, sans-serif'
        ctx.fillStyle = 'rgba(255,255,255,0.4)'
        ctx.fillText(noteName(p), 4, y + rowH - 2)
      }
    }

    // notes
    for (const n of notes) {
      const x = n.start * PX - scroll
      const w = Math.max(2, n.dur * PX - 1)
      if (x + w < 0 || x > viewW) continue
      const y = rulerH + (maxPitch - n.pitch) * rowH + 1
      ctx.fillStyle = ROLECOLOR[n.role] || '#fff'
      const r = Math.min(3, w / 2)
      ctx.beginPath()
      ctx.roundRect(x, y, w, rowH - 2, r)
      ctx.fill()
    }
  }, [viewW, heightPx, scroll, totalBeats, minPitch, maxPitch, notes, bpm, barsVisible])

  useEffect(() => {
    draw()
  }, [draw])

  useEffect(
    () => () => {
      if (hoverRafRef.current) cancelAnimationFrame(hoverRafRef.current)
    },
    [],
  )

  function findNote(beat, pitch) {
    const arr = byPitch.get(pitch)
    if (!arr || !arr.length) return null
    const minStart = beat - (maxDurByPitch.get(pitch) || 0)
    let lo = 0
    let hi = arr.length - 1
    let lastLe = -1
    while (lo <= hi) {
      const mid = (lo + hi) >> 1
      if (arr[mid].start <= beat) {
        lastLe = mid
        lo = mid + 1
      } else {
        hi = mid - 1
      }
    }
    for (let i = lastLe; i >= 0; i--) {
      const n = arr[i]
      if (n.start < minStart) break
      if (beat <= n.start + n.dur) return n
    }
    return null
  }

  function onMouseDown(e) {
    dragRef.current = { startX: e.clientX, startScroll: scroll }
    e.currentTarget.style.cursor = 'grabbing'
  }

  function onMouseMove(e) {
    const canvas = canvasRef.current
    if (!canvas) return
    if (dragRef.current) {
      const dx = e.clientX - dragRef.current.startX
      const next = Math.max(0, Math.min(maxScroll, dragRef.current.startScroll - dx))
      setScroll(next)
      return
    }
    const rect = canvas.getBoundingClientRect()
    pendingHoverRef.current = {
      beat: (e.clientX - rect.left + scroll) / PX,
      pitch: Math.round(maxPitch - (e.clientY - rect.top - rulerH) / rowH),
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    }
    if (!hoverRafRef.current) {
      hoverRafRef.current = requestAnimationFrame(() => {
        hoverRafRef.current = 0
        const p = pendingHoverRef.current
        pendingHoverRef.current = null
        if (!p) return
        const found = findNote(p.beat, p.pitch)
        if (found) {
          setHover({
            name: noteName(found.pitch),
            role: found.role,
            bar: Math.floor(p.beat / BEATS_PER_BAR) + 1,
            beats: p.beat.toFixed(1),
            x: p.x,
            y: p.y,
          })
        } else {
          setHover(null)
        }
      })
    }
  }

  function onMouseUp() {
    dragRef.current = null
    const wrap = wrapRef.current
    if (wrap) wrap.style.cursor = 'grab'
  }

  function onWheel(e) {
    e.preventDefault()
    const factor = e.deltaY > 0 ? 1.1 : 0.9
    setBarsVisible((v) => Math.max(4, Math.min(128, Math.round(v * factor))))
  }

  function zoom(v) {
    setBarsVisible((cur) => Math.max(4, Math.min(128, cur + v)))
  }

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <div className="text-xs font-semibold uppercase tracking-widest text-slate-500">
          Piano roll
        </div>
        <div className="flex items-center gap-1">
          <button
            className="glass rounded-md px-2 py-1 text-xs text-slate-300 hover:border-white/30"
            onClick={() => zoom(-8)}
          >
            −
          </button>
          <span className="w-14 text-center text-xs tabular-nums text-slate-400">
            {barsVisible} bars
          </span>
          <button
            className="glass rounded-md px-2 py-1 text-xs text-slate-300 hover:border-white/30"
            onClick={() => zoom(8)}
          >
            +
          </button>
        </div>
      </div>
      <div
        ref={wrapRef}
        className="glass relative cursor-grab overflow-hidden rounded-xl"
        style={{ height, position: 'relative' }}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseUp}
        onWheel={onWheel}
      >
        <div
          style={{ height, overflow: 'hidden' }}
          className="flex items-center justify-center"
        >
          <canvas ref={canvasRef} />
        </div>
        <div className="pointer-events-none absolute bottom-2 right-3 text-[10px] text-slate-500">
          drag to pan · scroll to zoom
        </div>
        {hover && (
          <div
            className="pointer-events-none absolute z-10 rounded-lg border border-white/15 bg-black/80 px-3 py-2 text-xs backdrop-blur"
            style={{
              left: Math.min(hover.x + 12, viewW - 130),
              top: hover.y - 54,
            }}
          >
            <div className="font-bold text-white">{hover.name}</div>
            <div className="text-slate-400">
              <span style={{ color: ROLECOLOR[hover.role] || '#fff' }}>{hover.role}</span> · bar{' '}
              {hover.bar} · beat {hover.beats}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
