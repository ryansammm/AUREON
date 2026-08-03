import { exportUrl, midiUrl, trackMidiUrl, wavUrl } from '../api'
import { downloadProject } from '../history'
import { roleColor, roleLabel } from '../roles'
import WaveformPlayer from './WaveformPlayer'
import LivePlayer from './LivePlayer'
import PianoRoll from './PianoRoll'
import Candidates from './Candidates'
import MixerPlayer from './MixerPlayer'

const Chip = ({ children, color = '#ffb25e' }) => (
  <span
    className="rounded-full border px-2.5 py-1 text-xs font-semibold"
    style={{ borderColor: `${color}44`, color, background: `${color}12` }}
  >
    {children}
  </span>
)

export default function ResultView({ result, params, onNew }) {
  const r = result
  const ai = r.ai || {}
  const totalNotes = r.tracks.reduce((s, t) => s + t.notes, 0)
  const hasPianoData = r.tracks.some((t) => Array.isArray(t.midi) && t.midi.length)

  return (
    <div className="fade-up space-y-6">
      {/* ─── Hero ─── */}
      <div className="glass rounded-2xl p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-2xl font-extrabold">
              {r.genre.replace(/_/g, ' ')} <span className="text-glow">♫</span>
            </h2>
            <div className="mt-1 text-sm text-slate-400">
              {r.key} · {r.bpm} BPM · {r.bars} bars ·{' '}
              {r.humanized ? 'humanized' : 'rigid'}
            </div>
          </div>
          <div className="flex gap-2">
            <button
              className="glass rounded-lg px-4 py-2 text-sm font-semibold text-slate-200 transition hover:border-[#ff7a1a]/60 hover:text-[#ffb25e]"
              onClick={() => downloadProject(params, r)}
            >
              💾 Save project
            </button>
            <a
              className="glass rounded-lg px-4 py-2 text-sm font-semibold text-slate-200 transition hover:border-[#ff7a1a]/60 hover:text-[#ffb25e]"
              href={exportUrl(r.mid)}
            >
              ⬇ Export bundle (ZIP)
            </a>
            <a
              className="glass rounded-lg px-4 py-2 text-sm font-semibold text-slate-200 transition hover:border-[#ff7a1a]/60 hover:text-[#ffb25e]"
              href={wavUrl(r.wav)}
              target="_blank"
              rel="noreferrer"
            >
              ▶ Listen
            </a>
            <a
              className="btn-primary rounded-lg px-4 py-2 text-sm"
              href={midiUrl(r.mid)}
            >
              Download MIDI
            </a>
          </div>
        </div>

        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          <div className="rounded-xl bg-white/[0.03] p-4">
            <div className="text-[11px] font-bold uppercase tracking-widest text-slate-500">
              Arrangement
            </div>
            <div className="mt-1 text-sm text-slate-300">{r.arrangement}</div>
          </div>
          <div className="rounded-xl bg-white/[0.03] p-4">
            <div className="text-[11px] font-bold uppercase tracking-widest text-slate-500">
              Chords
            </div>
            <div className="mt-1 text-sm text-slate-300">{r.chords}</div>
          </div>
        </div>
      </div>

      {/* ─── AI banner ─── */}
      {ai.enabled && (
        <div className="glass rounded-2xl border border-[#ff7a1a]/30 p-5">
          <div className="flex items-center gap-2 text-sm font-bold text-[#ffb25e]">
            <span>✨</span> AI assistance
            {ai.idea?.provider && (
              <span className="rounded-full bg-white/10 px-2 py-0.5 text-[10px] font-bold uppercase text-slate-300">
                {ai.idea.provider}
              </span>
            )}
          </div>
          {(ai.note || ai.score_note) && (
            <div className="mt-2 space-y-1 text-xs text-amber-200/80">
              {ai.note && <div>{ai.note}</div>}
              {ai.score_note && <div>{ai.score_note}</div>}
            </div>
          )}
          {ai.idea && (
            <div className="mt-3 grid gap-3 text-sm sm:grid-cols-3">
              <div className="rounded-lg bg-white/[0.03] p-3">
                <div className="text-[11px] font-bold uppercase text-slate-500">Idea</div>
                <div className="mt-1 text-slate-200">{ai.idea.description}</div>
              </div>
              <div className="rounded-lg bg-white/[0.03] p-3">
                <div className="text-[11px] font-bold uppercase text-slate-500">
                  Progression
                </div>
                <div className="mt-1 font-mono text-slate-200">
                  {ai.idea.progression?.join(' · ') || '—'}
                </div>
              </div>
              <div className="rounded-lg bg-white/[0.03] p-3">
                <div className="text-[11px] font-bold uppercase text-slate-500">Motif</div>
                <div className="mt-1 font-mono text-slate-200">
                  {ai.idea.motif?.join(', ') || '—'}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ─── Main audio ─── */}
      <div className="glass rounded-2xl p-5">
        <div className="mb-3 flex items-center justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <Chip>{r.genre.replace(/_/g, ' ')}</Chip>
            <Chip color="#7dd3fc">{r.key}</Chip>
            <Chip color="#a78bfa">{r.bpm} BPM</Chip>
            <Chip color="#34d399">{r.bars} bars</Chip>
            <Chip color="#f472b6">{totalNotes.toLocaleString()} notes</Chip>
          </div>
          <span className="text-xs text-slate-500">Master</span>
        </div>
        <WaveformPlayer file={r.wav} accent="#ff7a1a" height={110} autoLabel="Master · WAV" />
      </div>

      <LivePlayer mid={r.mid} roles={r.tracks.map((t) => t.role)} />

      {/* ─── Stem mixer ─── */}
      {r.stems?.length > 0 && (
        <MixerPlayer stems={r.stems} />
      )}

      {/* ─── Piano roll ─── */}
      {hasPianoData && (
        <PianoRoll
          tracks={r.tracks}
          bpm={r.bpm}
          totalBeats={r.bars * 4}
          height={360}
        />
      )}

      {/* ─── Tracks ─── */}
      <div className="glass rounded-2xl p-5">
        <h3 className="mb-3 text-xs font-bold uppercase tracking-widest text-slate-500">
          Tracks
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[11px] uppercase tracking-wider text-slate-500">
                <th className="pb-2 pr-4">Role</th>
                <th className="pb-2 pr-4">Preset</th>
                <th className="pb-2 pr-4">Notes</th>
                <th className="pb-2">MIDI</th>
              </tr>
            </thead>
            <tbody>
              {r.tracks.map((t) => (
                <tr key={t.role} className="border-t border-white/5">
                  <td className="py-2 pr-4">
                    <span
                      className="inline-block h-2.5 w-2.5 rounded-full"
                      style={{ background: roleColor(t.role) }}
                    />
                    <span className="ml-2 font-semibold">{roleLabel(t.role)}</span>
                  </td>
                  <td className="py-2 pr-4 text-slate-400">{t.preset}</td>
                  <td className="py-2 pr-4 tabular-nums text-slate-400">
                    {t.notes.toLocaleString()}
                  </td>
                  <td className="py-2">
                    <a
                      className="text-xs font-semibold text-slate-400 transition hover:text-[#ffb25e]"
                      href={trackMidiUrl(r.mid, t.role)}
                      download
                    >
                      ↓ download
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ─── Candidates A/B ─── */}
      {r.candidates?.length > 0 && (
        <Candidates candidates={r.candidates} mainWav={r.wav} />
      )}
    </div>
  )
}
