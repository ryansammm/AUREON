import { wavUrl, midiUrl } from '../api'
import { roleColor, roleLabel } from '../roles'

function Stat({ label, a, b }) {
  const diff = a !== b
  const cell = (v) => (
    <span className={diff ? 'font-bold text-[#ffb25e]' : 'text-slate-200'}>{v}</span>
  )
  return (
    <div className="rounded-lg bg-white/[0.03] p-3">
      <div className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
        {label}
      </div>
      <div className="mt-0.5 text-sm">
        {cell(a)} <span className="mx-1 text-slate-600">vs</span> {cell(b)}
      </div>
    </div>
  )
}

function EntryCard({ title, entry, tone }) {
  const r = entry?.result
  if (!r) return null
  const totalNotes = r.tracks.reduce((s, t) => s + (t.notes || 0), 0)
  const ai = r.ai || {}
  return (
    <div className="glass rounded-2xl p-5">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold uppercase tracking-widest text-slate-400">
          {title}
        </h3>
        <div className="flex gap-2">
          <a
            className="glass rounded-lg px-3 py-1.5 text-xs font-semibold text-slate-200 transition hover:border-[#ff7a1a]/60 hover:text-[#ffb25e]"
            href={wavUrl(r.wav)}
            target="_blank"
            rel="noreferrer"
          >
            ▶
          </a>
          <a
            className="glass rounded-lg px-3 py-1.5 text-xs font-semibold text-slate-200 transition hover:border-[#ff7a1a]/60 hover:text-[#ffb25e]"
            href={midiUrl(r.mid)}
            download
          >
            MIDI
          </a>
        </div>
      </div>

      <div className="mt-3 text-xl font-extrabold capitalize">
        {r.genre.replace(/_/g, ' ')}
      </div>
      <div className="mt-1 text-xs text-slate-500">
        {entry.params?.ai ? '✨ AI-assisted' : 'rule-based'} ·{' '}
        {new Date(entry.ts).toLocaleString()}
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {entry.params?.roles?.map((role) => (
          <span
            key={role}
            className="rounded-full border px-2 py-0.5 text-[11px] font-semibold"
            style={{
              borderColor: `${roleColor(role)}44`,
              color: roleColor(role),
              background: `${roleColor(role)}12`,
            }}
          >
            {roleLabel(role)}
          </span>
        ))}
      </div>

      <div className="mt-4 rounded-xl bg-white/[0.03] p-3 text-xs text-slate-300">
        <div className="text-[10px] font-bold uppercase text-slate-500">Arrangement</div>
        {r.arrangement}
      </div>
      <div className="mt-2 rounded-xl bg-white/[0.03] p-3 text-xs text-slate-300">
        <div className="text-[10px] font-bold uppercase text-slate-500">Chords</div>
        {r.chords}
      </div>

      {ai.idea && (
        <div className="mt-2 rounded-xl border border-[#ff7a1a]/30 bg-[#ff7a1a]/5 p-3 text-xs text-amber-200/80">
          <div className="font-bold text-[#ffb25e]">AI</div>
          <div>{ai.idea.description}</div>
          <div className="mt-1 font-mono">{ai.idea.progression?.join(' · ')}</div>
          {ai.note && <div className="mt-1 text-amber-200/60">{ai.note}</div>}
        </div>
      )}

      <div className="mt-3">
        <div className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
          Tracks
        </div>
        <table className="mt-1 w-full text-xs">
          <tbody>
            {r.tracks.map((t) => (
              <tr key={t.role} className="border-t border-white/5">
                <td className="py-1">
                  <span
                    className="inline-block h-2 w-2 rounded-full"
                    style={{ background: roleColor(t.role) }}
                  />
                  <span className="ml-1.5 font-semibold">{roleLabel(t.role)}</span>
                </td>
                <td className="py-1 text-slate-500">{t.preset}</td>
                <td className="py-1 text-right tabular-nums text-slate-500">
                  {(t.notes || 0).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-2 text-[11px] text-slate-500">
        {totalNotes.toLocaleString()} notes total · {tone}
      </div>
    </div>
  )
}

export default function CompareView({ a, b, onBack }) {
  const ra = a?.result
  const rb = b?.result
  const tone = (r) => (r ? `${r.key} · ${r.bpm} BPM · ${r.bars} bars · ${r.humanized ? 'humanized' : 'rigid'}` : '—')

  return (
    <div className="fade-up space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-bold">Compare compositions</h2>
        <button
          className="glass rounded-lg px-4 py-2 text-sm font-semibold text-slate-200 transition hover:border-[#ff7a1a]/60 hover:text-[#ffb25e]"
          onClick={onBack}
        >
          ← Back to history
        </button>
      </div>

      {ra && rb && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-2">
          <Stat label="Genre" a={ra.genre.replace(/_/g, ' ')} b={rb.genre.replace(/_/g, ' ')} />
          <Stat label="Key" a={ra.key} b={rb.key} />
          <Stat label="BPM" a={ra.bpm} b={rb.bpm} />
          <Stat label="Bars" a={ra.bars} b={rb.bars} />
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        <EntryCard title="Entry A" entry={a} tone={tone(ra)} />
        <EntryCard title="Entry B" entry={b} tone={tone(rb)} />
      </div>
    </div>
  )
}
