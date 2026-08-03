import { useState } from 'react'
import { wavUrl, midiUrl } from '../api'
import { roleLabel } from '../roles'

function fmtTime(ts) {
  return new Date(ts).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function HistoryView({ history, onOpen, onRemove, onCompare, onBack }) {
  const [playingId, setPlayingId] = useState(null)
  const [selectMode, setSelectMode] = useState(false)
  const [selected, setSelected] = useState([])

  function toggleSelect(id) {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    )
  }

  if (history.length === 0) {
    return (
      <div className="fade-up glass mx-auto max-w-lg rounded-2xl p-10 text-center">
        <div className="text-4xl">🎼</div>
        <h2 className="mt-3 text-lg font-bold">No compositions yet</h2>
        <p className="mt-1 text-sm text-slate-500">
          Generate a composition and it will be saved here automatically.
        </p>
        {onBack && (
          <button
            className="btn-primary mt-6 rounded-lg px-5 py-2 text-sm font-semibold"
            onClick={onBack}
          >
            ← Compose
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="fade-up space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          {onBack && (
            <button
              className="glass rounded-lg px-3 py-1.5 text-sm font-semibold text-slate-200 transition hover:border-[#ff7a1a]/60 hover:text-[#ffb25e]"
              onClick={onBack}
            >
              ← Compose
            </button>
          )}
          <h2 className="text-lg font-bold">Composition history</h2>
        </div>
        <div className="flex items-center gap-2">
          {selectMode && (
            <button
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                selected.length === 2
                  ? 'btn-primary'
                  : 'cursor-not-allowed border border-white/10 bg-white/5 text-slate-500'
              }`}
              disabled={selected.length !== 2}
              onClick={() => {
                onCompare(
                  history.find((e) => e.id === selected[0]),
                  history.find((e) => e.id === selected[1]),
                )
              }}
            >
              Compare {selected.length}/2
            </button>
          )}
          <button
            className={`rounded-lg border px-3 py-1.5 text-xs font-semibold transition ${
              selectMode
                ? 'border-[#ff7a1a] bg-[#ff7a1a]/15 text-[#ffb25e]'
                : 'glass text-slate-200 hover:border-white/30'
            }`}
            onClick={() => {
              setSelectMode((s) => !s)
              setSelected([])
            }}
          >
            Compare mode
          </button>
        </div>
      </div>
      {selectMode && selected.length === 2 && (
        <p className="text-xs text-slate-500">Ready — press Compare above.</p>
      )}
      {history.map((entry) => {
        const r = entry.result
        const isPlaying = playingId === entry.id
        return (
          <div
            key={entry.id}
            className={`glass flex flex-wrap items-center gap-4 rounded-xl p-4 transition ${
              selectMode
                ? `cursor-pointer hover:border-[#ff7a1a]/50 ${
                    selected.includes(entry.id) ? 'border-[#ff7a1a] bg-[#ff7a1a]/5' : ''
                  }`
                : ''
            }`}
            onClick={selectMode ? () => toggleSelect(entry.id) : undefined}
          >
            {selectMode && (
              <span
                className={`flex h-6 w-6 items-center justify-center rounded-md border text-xs font-bold ${
                  selected.includes(entry.id)
                    ? 'border-[#ff7a1a] bg-[#ff7a1a] text-[#14100a]'
                    : 'border-white/20 text-transparent'
                }`}
              >
                ✓
              </span>
            )}
            <button
              onClick={() => {
                const audio = document.getElementById(`hist-${entry.id}`)
                if (audio) {
                  if (audio.paused) {
                    audio.play().catch(() => {})
                    setPlayingId(entry.id)
                  } else {
                    audio.pause()
                    setPlayingId(null)
                  }
                }
              }}
              className="pulse-ring flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-[#ff7a1a] to-[#ff9d3c] text-sm text-[#14100a]"
            >
              {isPlaying ? '❚❚' : '▶'}
            </button>
            <audio
              id={`hist-${entry.id}`}
              src={wavUrl(r.wav)}
              preload="none"
              onEnded={() => setPlayingId(null)}
            />
            <div className="min-w-0 flex-1">
              <div className="font-bold capitalize">
                {r.genre.replace(/_/g, ' ')}
                <span className="ml-2 text-sm font-normal text-slate-400">
                  {r.key} · {r.bpm} BPM · {r.bars} bars
                </span>
              </div>
              <div className="mt-0.5 truncate text-xs text-slate-500">
                {fmtTime(entry.ts)} · {entry.params?.roles?.map(roleLabel).join(', ')}
              </div>
            </div>
            <div className="flex gap-2">
              <button
                className="glass rounded-lg px-3 py-1.5 text-xs font-semibold text-slate-200 transition hover:border-[#ff7a1a]/60 hover:text-[#ffb25e]"
                onClick={() => onOpen(entry)}
              >
                Open
              </button>
              <a
                className="glass rounded-lg px-3 py-1.5 text-xs font-semibold text-slate-200 transition hover:border-[#ff7a1a]/60 hover:text-[#ffb25e]"
                href={midiUrl(r.mid)}
                download
              >
                MIDI
              </a>
              <button
                className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-1.5 text-xs font-semibold text-red-300 transition hover:bg-red-500/20"
                onClick={() => onRemove(entry.id)}
              >
                Delete
              </button>
            </div>
          </div>
        )
      })}
    </div>
  )
}
