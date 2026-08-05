import { useEffect, useRef, useState, useCallback } from 'react'
import { wavUrl, fetchWithTimeout } from '../api'
import { log } from '../logger'
import { computePeaks } from '../waveformWorker'

export default function WaveformPlayer({ file, accent = '#ff7a1a', height = 96, autoLabel }) {
  const src = wavUrl(file)
  const audioRef = useRef(null)
  const canvasRef = useRef(null)
  const peaksRef = useRef([])
  const [playing, setPlaying] = useState(false)
  const [loading, setLoading] = useState(true)
  const [progress, setProgress] = useState(0)
  const [duration, setDuration] = useState(0)
  const [error, setError] = useState(false)
  const rafRef = useRef(null)
  const workerRef = useRef(null)

  // Store state in refs so draw can read latest without changing identity
  const progressRef = useRef(progress)
  const durationRef = useRef(duration)
  const accentRef = useRef(accent)
  const heightRef = useRef(height)

  progressRef.current = progress
  durationRef.current = duration
  accentRef.current = accent
  heightRef.current = height

  const draw = useCallback(() => {
    const canvas = canvasRef.current
    const audio = audioRef.current
    if (!canvas || !audio) return
    const ctx = canvas.getContext('2d')
    const rect = canvas.parentElement?.getBoundingClientRect()
    const W = rect ? rect.width : canvas.width / (window.devicePixelRatio || 1)
    const H = rect ? rect.height : heightRef.current
    const peaks = peaksRef.current
    const n = peaks.length || 1

    const dpr = window.devicePixelRatio || 1
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, W, H)

    // grid
    ctx.fillStyle = 'rgba(255,255,255,0.025)'
    const grid = 24
    for (let x = 0; x < W; x += grid) ctx.fillRect(x, 0, 1, H)

    const played = (progressRef.current / (durationRef.current || 1)) * W

    // baseline
    ctx.strokeStyle = 'rgba(255,255,255,0.08)'
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(0, H / 2)
    ctx.lineTo(W, H / 2)
    ctx.stroke()

    // peaks
    if (peaks.length) {
      const barW = Math.max(1, W / n - 1)
      for (let i = 0; i < n; i++) {
        const x = (W / n) * i
        const h = Math.max(2, peaks[i] * (H - 8))
        const isPlayed = x <= played
        ctx.fillStyle = isPlayed ? accentRef.current : 'rgba(255,255,255,0.22)'
        const r = Math.min(barW / 2, 2)
        ctx.beginPath()
        ctx.roundRect(x, (H - h) / 2, barW, h, r)
        ctx.fill()
      }
    }

    // playhead
    if (played > 0) {
      ctx.fillStyle = 'rgba(255,255,255,0.85)'
      ctx.fillRect(played - 1, 0, 2, H)
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    const audio = audioRef.current
    if (!audio) return
    setLoading(true)
    setError(false)
    setProgress(0)
    setDuration(0)
    setPlaying(false)
    peaksRef.current = []
    audio.src = src
    audio.load()

    ;(async () => {
      try {
        const res = await fetchWithTimeout(src, {}, 120000)
        const buf = await res.arrayBuffer()
        const Ctx = window.AudioContext || window.webkitAudioContext
        const ctx = new Ctx()
        const decoded = await ctx.decodeAudioData(buf)
        if (cancelled) return
        const duration = decoded.duration
        const channel = decoded.getChannelData(0)
        ctx.close().catch(() => {})
        log.info('WAVEFORM_LOADED', { file, duration: duration.toFixed(2) })
        try {
          // Peaks computed off the main thread so long files don't hitch the UI.
          const worker = new Worker(new URL('../waveformWorker.js', import.meta.url), {
            type: 'module',
          })
          workerRef.current = worker
          worker.onmessage = (e) => {
            if (cancelled) return
            peaksRef.current = e.data.peaks
            setLoading(false)
            draw()
          }
          worker.postMessage({ data: channel, count: 900 }, [channel.buffer])
        } catch {
          if (cancelled) return
          // Worker unavailable (very old browser) — fall back to main thread.
          peaksRef.current = computePeaks(channel, 900)
          setLoading(false)
          draw()
        }
      } catch (e) {
        log.error('WAVEFORM_FAILED', { file, error: String(e) })
        setLoading(false)
        setError(true)
      }
    })()

    const onPlay = () => { log.info('WAVEFORM_PLAY', { file }); setPlaying(true) }
    const onPause = () => { log.info('WAVEFORM_PAUSE', { file }); setPlaying(false) }
    const onEnded = () => { log.info('WAVEFORM_ENDED', { file }); setPlaying(false); setProgress(0) }
    const onTime = () => {
      if (audio.duration) {
        setProgress(audio.currentTime)
        setDuration(audio.duration)
      }
    }
    audio.addEventListener('play', onPlay)
    audio.addEventListener('pause', onPause)
    audio.addEventListener('ended', onEnded)
    audio.addEventListener('timeupdate', onTime)

    return () => {
      cancelled = true
      audio.pause()
      audio.removeEventListener('play', onPlay)
      audio.removeEventListener('pause', onPause)
      audio.removeEventListener('ended', onEnded)
      audio.removeEventListener('timeupdate', onTime)
      workerRef.current?.terminate()
      workerRef.current = null
      cancelAnimationFrame(rafRef.current)
    }
  }, [src, draw])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const resize = () => {
      const rect = canvas.parentElement.getBoundingClientRect()
      const dpr = window.devicePixelRatio || 1
      canvas.width = rect.width * dpr
      canvas.height = heightRef.current * dpr
      draw()
    }
    resize()
    window.addEventListener('resize', resize)
    return () => window.removeEventListener('resize', resize)
  }, [draw])

  // Redraw when progress/duration change
  useEffect(() => {
    draw()
  }, [progress, duration, draw])

  function scrub(e) {
    const audio = audioRef.current
    const rect = canvasRef.current.getBoundingClientRect()
    const ratio = (e.clientX - rect.left) / rect.width
    if (audio.duration) {
      audio.currentTime = ratio * audio.duration
      setProgress(audio.currentTime)
    }
  }

  function togglePlay() {
    const audio = audioRef.current
    if (!audio) return
    if (audio.paused) audio.play().catch(() => {})
    else audio.pause()
  }

  const fmt = (s) => {
    if (!s || !isFinite(s)) return '0:00'
    const m = Math.floor(s / 60)
    const sec = Math.floor(s % 60)
    return `${m}:${sec.toString().padStart(2, '0')}`
  }

  return (
    <div className="w-full select-none">
      <audio ref={audioRef} preload="auto" />
      <div
        className="glass group relative w-full cursor-pointer overflow-hidden rounded-xl"
        style={{ height }}
        onClick={togglePlay}
        onMouseMove={scrub}
      >
        <canvas ref={canvasRef} className="h-full w-full" style={{ height }} />
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center text-xs text-slate-500">
            Loading waveform…
          </div>
        )}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center text-xs text-red-400">
            Audio unavailable
          </div>
        )}
        {!playing && !loading && !error && (
          <div className="absolute left-1/2 top-1/2 flex h-11 w-11 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-black/50 opacity-0 backdrop-blur transition group-hover:opacity-100">
            <span className="text-lg text-white">▶</span>
          </div>
        )}
        <div className="absolute bottom-1 left-3 text-[11px] font-semibold text-white/70">
          {autoLabel || 'Main'}
        </div>
        <div className="absolute bottom-1 right-3 text-[11px] tabular-nums text-white/70">
          {fmt(progress)} / {fmt(duration)}
        </div>
      </div>
    </div>
  )
}
