import { useState } from 'react'
import { wavUrl } from '../api'
import WaveformPlayer from './WaveformPlayer'

export default function Candidates({ candidates, mainWav, onSelect }) {
  const [open, setOpen] = useState(candidates.length === 1)
  const [sel, setSel] = useState('main')

  function handleSelect(rank) {
    if (sel === String(rank)) {
      setSel('main')
      if (onSelect) onSelect(null)
    } else {
      setSel(String(rank))
      if (onSelect) onSelect(candidates.find((c) => c.rank === rank))
    }
  }

  return (
    <div className="glass rounded-2xl p-5">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-xs font-bold uppercase tracking-widest text-slate-500">
          Candidate A/B
        </h3>
        <button
          className="text-xs text-[#ffb25e] hover:underline"
          onClick={() => setOpen(!open)}
        >
          {open ? 'Hide' : 'Show'}
        </button>
      </div>

      {open && (
        <div className="space-y-3">
          {/* Main vs selected badge */}
          <div className="flex items-center gap-2 text-xs">
            <span
              className={`rounded-full px-2.5 py-1 font-bold ${
                sel === 'main'
                  ? 'bg-[#ff7a1a] text-[#14100a]'
                  : 'bg-white/10 text-slate-300'
              }`}
            >
              A · Main
            </span>
            <span
              className={`rounded-full px-2.5 py-1 font-bold ${
                sel !== 'main'
                  ? 'bg-[#ff7a1a] text-[#14100a]'
                  : 'bg-white/10 text-slate-300'
              }`}
            >
              B · #{sel}
            </span>
            <span className="text-slate-500">
              {sel === 'main' ? 'Master composition' : `Candidate seed ${sel}`}
            </span>
          </div>

          <WaveformPlayer
            key={sel}
            file={sel === 'main' ? mainWav : candidates.find((c) => c.rank === Number(sel)).wav}
            height={76}
            accent={sel === 'main' ? '#ff7a1a' : '#7dd3fc'}
            autoLabel={sel === 'main' ? 'A · Main' : `B · seed ${sel}`}
          />

          {/* Candidate list */}
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {candidates.map((c) => {
              const active = sel === String(c.rank)
              const combined = c.score + (c.ai_score != null ? (c.ai_score - 5) * 0.05 : 0)
              return (
                <button
                  key={c.rank}
                  onClick={() => handleSelect(c.rank)}
                  className={`rounded-xl border p-3 text-left transition ${
                    active
                      ? 'border-[#ff7a1a] bg-[#ff7a1a]/10'
                      : 'border-white/10 bg-white/[0.02] hover:border-white/25'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-bold">
                      #{c.rank}
                      <span className="ml-1.5 text-xs font-normal text-slate-500">
                        seed {c.seed}
                      </span>
                    </span>
                    <span className="text-xs text-slate-400">
                      {active ? 'A/B ✦' : 'A/B'}
                    </span>
                  </div>
                  <div className="mt-2 flex items-center gap-1.5 text-xs">
                    <span className="rounded-md bg-white/10 px-1.5 py-0.5 font-mono tabular-nums text-slate-300">
                      ⚙ {c.score.toFixed(2)}
                    </span>
                    {c.ai_score != null && (
                      <span
                        className="rounded-md px-1.5 py-0.5 font-mono tabular-nums"
                        style={{
                          background: 'rgba(255,122,26,0.15)',
                          color: '#ffb25e',
                        }}
                        title={c.ai_reason}
                      >
                        ✨ {c.ai_score.toFixed(1)}
                      </span>
                    )}
                    <span className="font-mono tabular-nums text-slate-400">
                      ∑ {combined.toFixed(2)}
                    </span>
                  </div>
                  {c.ai_reason && (
                    <div className="mt-1.5 line-clamp-2 text-[11px] text-slate-500">
                      {c.ai_reason}
                    </div>
                  )}
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
