import { useRef, useState } from 'react'
import { importMidi } from '../api'
import { roleLabel } from '../roles'

const ROLE_OPTIONS = [
  'bass', 'lead', 'chord', 'pad', 'arp', 'stab', 'sub_bass',
  'counter_lead', 'drum', 'drum_layers',
]

export default function ImportView({ onUseRoles }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [report, setReport] = useState(null)
  const [file, setFile] = useState(null)
  const [overrides, setOverrides] = useState({})
  const [customPresets, setCustomPresets] = useState({})
  const inputRef = useRef(null)

  async function handleFile(f) {
    if (!f) return
    setFile(f)
    setBusy(true)
    setError(null)
    setReport(null)
    setOverrides({})
    setCustomPresets({})
    try {
      const rep = await importMidi(f)
      setReport(rep)
    } catch (e) {
      setError(String(e.message || e))
    } finally {
      setBusy(false)
    }
  }

  function overrideKey(e) {
    return `${e.track_index}:${e.channel}`
  }

  function roleFor(e) {
    return overrides[overrideKey(e)] || e.role
  }

  function presetFor(e) {
    const k = overrideKey(e)
    return customPresets[k] ?? e.preset
  }

  function exportReport() {
    if (!report) return
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${report.filename}.mapping.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="fade-up space-y-4">
      <div className="glass rounded-2xl p-6">
        <h2 className="text-lg font-bold">Import MIDI → GM instrument map</h2>
        <p className="mt-1 text-sm text-slate-500">
          Upload a .mid file. Program Changes and channel numbers are read per
          track and mapped to internal plugins via the General MIDI patch &
          drum maps (channel 10 = drums). Velocity, pitch bend and CC64/sustain
          are preserved.
        </p>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            className="btn-primary rounded-xl px-6 py-3 text-sm font-semibold"
            onClick={() => inputRef.current?.click()}
            disabled={busy}
          >
            {busy ? 'Analyzing…' : file ? `Re-analyze · ${file.name}` : '📂 Choose MIDI file'}
          </button>
          <input
            ref={inputRef}
            type="file"
            accept=".mid,.midi,audio/midi"
            className="hidden"
            onChange={(e) => handleFile(e.target.files?.[0])}
          />
          {report && (
            <button
              className="glass rounded-xl px-4 py-3 text-sm font-semibold text-slate-200 transition hover:border-[#ff7a1a]/60 hover:text-[#ffb25e]"
              onClick={exportReport}
            >
              ⬇ Export mapping JSON
            </button>
          )}
          {report && (
            <button
              className="glass rounded-xl px-4 py-3 text-sm font-semibold text-slate-200 transition hover:border-[#ff7a1a]/60 hover:text-[#ffb25e]"
              onClick={() => onUseRoles(report.channels.map(roleFor))}
            >
              → Use roles in generator
            </button>
          )}
        </div>

        {error && (
          <div className="mt-4 rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}
      </div>

      {report && (
        <>
          {report.warnings?.length > 0 && (
            <div className="rounded-2xl border border-amber-500/40 bg-amber-500/10 p-4">
              <div className="text-sm font-bold text-amber-300">⚠ Non-GM notices</div>
              <ul className="mt-1 list-disc pl-5 text-xs text-amber-200/80">
                {report.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="glass overflow-hidden rounded-2xl">
            <div className="border-b border-white/5 px-5 py-3 text-xs font-bold uppercase tracking-widest text-slate-500">
              {report.filename} · {report.channels.length} mapped channel{report.channels.length !== 1 && 's'}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[11px] uppercase tracking-wider text-slate-500">
                    <th className="px-5 py-2 pr-4">Track</th>
                    <th className="py-2 pr-4">Ch</th>
                    <th className="py-2 pr-4">GM Instrument</th>
                    <th className="py-2 pr-4">Internal plugin</th>
                    <th className="py-2 pr-4">Override</th>
                    <th className="py-2 pr-4">Preset</th>
                    <th className="py-2">Stats</th>
                  </tr>
                </thead>
                <tbody>
                  {report.channels.map((e) => {
                    const k = overrideKey(e)
                    return (
                      <tr key={k} className="border-t border-white/5">
                        <td className="px-5 py-2 pr-4 font-semibold">
                          {e.track_name}
                        </td>
                        <td className="py-2 pr-4 tabular-nums text-slate-400">
                          {e.channel + 1}
                          {e.is_drum_channel && (
                            <span className="ml-1 rounded bg-white/10 px-1 text-[10px] font-bold text-amber-300">
                              DRUM
                            </span>
                          )}
                        </td>
                        <td className="py-2 pr-4 text-slate-300">
                          {e.instrument || '—'}
                          {!e.is_drum_channel && (
                            <span className="ml-1 text-[10px] text-slate-500">
                              P{e.program}
                            </span>
                          )}
                        </td>
                        <td className="py-2 pr-4">
                          <span className="text-[#ffb25e]">{roleLabel(e.role)}</span>
                          {!overrides[k] && (
                            <span className="ml-1 text-xs text-slate-500">
                              {e.program_events > 0 ? '· from PC' : '· fallback'}
                            </span>
                          )}
                        </td>
                        <td className="py-2 pr-4">
                          <select
                            className="glass rounded-lg px-2 py-1.5 text-xs text-slate-200"
                            value={overrides[k] || ''}
                            onChange={(ev) => {
                              const next = { ...overrides }
                              if (ev.target.value) next[k] = ev.target.value
                              else delete next[k]
                              setOverrides(next)
                            }}
                          >
                            <option value="">auto</option>
                            {ROLE_OPTIONS.map((r) => (
                              <option key={r} value={r} className="bg-[#17130e]">
                                {roleLabel(r)}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td className="py-2 pr-4">
                          <input
                            className="w-40 rounded-lg border border-white/10 bg-white/5 px-2 py-1.5 text-xs text-slate-200 outline-none focus:border-[#ff7a1a]/60"
                            placeholder={e.preset}
                            value={customPresets[k] ?? ''}
                            onChange={(ev) =>
                              setCustomPresets({ ...customPresets, [k]: ev.target.value })
                            }
                          />
                        </td>
                        <td className="py-2 text-xs text-slate-500">
                          <div>{e.note_count.toLocaleString()} notes · {e.note_min}–{e.note_max}</div>
                          <div className="flex gap-2">
                            {e.is_drum_channel && e.drum_hits && (
                              <span className="text-[10px]">
                                {Object.entries(e.drum_hits)
                                  .sort((a, b) => b[1] - a[1])
                                  .slice(0, 4)
                                  .map(([c, n]) => `${c}×${n}`)
                                  .join(' ')}
                              </span>
                            )}
                            {e.pitchbend && <span className="text-[10px] text-sky-300">pitch bend</span>}
                            {e.sustain_cc64 && <span className="text-[10px] text-emerald-300">CC64</span>}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-xs text-slate-500">
            Tip: use the <span className="text-slate-300">Override</span> column to
            manually re-assign any track, or type a custom preset name. The mapping
            is informational — AUREON's DAW export carries the chosen role/preset in
            each track's name.
          </div>
        </>
      )}
    </div>
  )
}
