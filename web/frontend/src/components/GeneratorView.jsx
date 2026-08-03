import { useMemo, useRef, useState } from 'react'
import {
  KEY_NAMES,
  MODES,
  COMPLEXITIES,
  COMPLEXITY_LABEL,
} from '../api'

const ROLE_COLORS = {
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

const roleLabel = (r) =>
  r.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())

function Field({ label, hint, children }) {
  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between">
        <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          {label}
        </label>
        {hint && <span className="text-xs text-slate-500">{hint}</span>}
      </div>
      {children}
    </div>
  )
}

function Slider({ value, onChange, min, max, step = 1 }) {
  return (
    <input
      type="range"
      className="accent w-full"
      min={min}
      max={max}
      step={step}
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
    />
  )
}

export default function GeneratorView({ config, onGenerate, error, initial }) {
  const [genre, setGenre] = useState(initial?.genre || config.genres[0])
  const def = config.genre_defaults[genre] || { bpm: 140, key: 'a', mode: 'minor' }

  const [roles, setRoles] = useState(initial?.roles || ['bass', 'lead', 'drum'])
  const [key, setKey] = useState(initial?.key || def.key)
  const [mode, setMode] = useState(initial?.mode || def.mode)
  const [bpm, setBpm] = useState(initial?.bpm || def.bpm)
  const [bars, setBars] = useState(initial?.bars || 16)
  const [complexity, setComplexity] = useState(initial?.complexity || 'medium')
  const [candidates, setCandidates] = useState(initial?.candidates || 3)
  const [seed, setSeed] = useState(initial?.seed || 42)
  const [humanize, setHumanize] = useState(initial?.humanize ?? true)
  const [ai, setAi] = useState(initial?.ai ?? false)
  const [prompt, setPrompt] = useState(initial?.prompt || '')
  const fileRef = useRef(null)

  const applyParams = (p) => {
    if (!p) return
    if (config.genres.includes(p.genre)) setGenre(p.genre)
    if (Array.isArray(p.roles)) setRoles(p.roles.filter((r) => config.roles.includes(r)))
    if (typeof p.key === 'string') setKey(p.key)
    if (p.mode === 'minor' || p.mode === 'major') setMode(p.mode)
    if (Number.isFinite(p.bpm)) setBpm(p.bpm)
    if (Number.isFinite(p.bars)) setBars(p.bars)
    if (['low', 'medium', 'high'].includes(p.complexity)) setComplexity(p.complexity)
    if (Number.isFinite(p.candidates)) setCandidates(p.candidates)
    if (Number.isFinite(p.seed)) setSeed(p.seed)
    if (typeof p.humanize === 'boolean') setHumanize(p.humanize)
    if (typeof p.ai === 'boolean') setAi(p.ai)
    if (typeof p.prompt === 'string') setPrompt(p.prompt)
  }

  function loadProjectFile(e) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      try {
        const data = JSON.parse(String(reader.result))
        applyParams(data.params || data)
      } catch {
        /* ignore malformed files */
      }
    }
    reader.readAsText(file)
    e.target.value = ''
  }

  const durationMin = useMemo(
    () => Math.max(2, Math.round(bars * 2.5 * (60 / bpm))),
    [bars, bpm],
  )
  const durationSec = Math.round(bars * 4 * (60 / bpm))

  const toggleRole = (r) =>
    setRoles((prev) =>
      prev.includes(r) ? prev.filter((x) => x !== r) : [...prev, r],
    )

  const submit = () =>
    onGenerate({
      genre,
      roles: roles.length ? roles : ['bass'],
      key,
      mode,
      bpm,
      bars,
      complexity,
      candidates,
      seed,
      humanize,
      ai,
      prompt,
    })

  return (
    <div className="fade-up grid gap-8 lg:grid-cols-[1fr_340px]">
      {/* ─── Form ─── */}
      <div className="space-y-8">
        {/* Genre */}
        <section>
          <Field label="Genre" hint={genre}>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {config.genres.map((g) => (
                <button
                  key={g}
                  onClick={() => setGenre(g)}
                  className={`rounded-lg border px-3 py-2.5 text-sm font-semibold transition ${
                    genre === g
                      ? 'border-[#ff7a1a] bg-[#ff7a1a]/15 text-[#ffb25e]'
                      : 'glass text-slate-300 hover:border-white/25'
                  }`}
                >
                  {g.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                </button>
              ))}
            </div>
          </Field>
        </section>

        {/* Roles */}
        <section>
          <Field label="Roles" hint={`${roles.length} selected`}>
            <div className="flex flex-wrap gap-2">
              {config.roles.map((r) => {
                const on = roles.includes(r)
                const c = ROLE_COLORS[r] || '#fff'
                return (
                  <button
                    key={r}
                    onClick={() => toggleRole(r)}
                    className="rounded-full border px-3 py-1.5 text-xs font-semibold transition"
                    style={
                      on
                        ? { borderColor: c, color: c, background: `${c}1a` }
                        : { borderColor: 'rgba(255,255,255,0.12)', color: '#8a93a6' }
                    }
                  >
                    {roleLabel(r)}
                  </button>
                )
              })}
            </div>
          </Field>
        </section>

        {/* Keys / tempo */}
        <section className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Field label="Key">
            <select
              className="glass w-full rounded-lg px-3 py-2 text-sm outline-none focus:border-[#ff7a1a]"
              value={key}
              onChange={(e) => setKey(e.target.value)}
            >
              {KEY_NAMES.map((k) => (
                <option key={k} value={k}>
                  {k.toUpperCase()}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Mode">
            <div className="flex rounded-lg border border-white/10 p-0.5">
              {MODES.map((m) => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  className={`flex-1 rounded-md px-2 py-1.5 text-xs font-bold capitalize transition ${
                    mode === m ? 'bg-[#ff7a1a] text-[#14100a]' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
          </Field>
          <Field label="BPM" hint={bpm}>
            <Slider value={bpm} onChange={setBpm} min={60} max={200} />
          </Field>
          <Field label="Bars" hint={bars}>
            <Slider value={bars} onChange={setBars} min={4} max={280} />
          </Field>
        </section>

        {/* Structure */}
        <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Field label="Complexity">
            <div className="flex rounded-lg border border-white/10 p-0.5">
              {COMPLEXITIES.map((c) => (
                <button
                  key={c}
                  onClick={() => setComplexity(c)}
                  className={`flex-1 rounded-md px-2 py-1.5 text-xs font-bold transition ${
                    complexity === c
                      ? 'bg-[#ff7a1a] text-[#14100a]'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {COMPLEXITY_LABEL[c]}
                </button>
              ))}
            </div>
          </Field>
          <Field label="Candidates" hint={`${candidates} ranked`}>
            <Slider value={candidates} onChange={setCandidates} min={1} max={8} />
          </Field>
          <Field label="Seed" hint="0 = random">
            <div className="flex gap-2">
              <input
                type="number"
                className="glass w-full rounded-lg px-3 py-2 text-sm outline-none focus:border-[#ff7a1a]"
                value={seed}
                onChange={(e) => setSeed(Number(e.target.value))}
              />
              <button
                className="glass rounded-lg px-3 text-sm text-slate-300 hover:border-white/30"
                onClick={() => setSeed(Math.floor(Math.random() * 10000))}
                title="Random seed"
              >
                🎲
              </button>
            </div>
          </Field>
        </section>

        {/* Humanize */}
        <section className="flex items-center justify-between rounded-xl glass px-4 py-3">
          <div>
            <div className="text-sm font-semibold">Humanize performance</div>
            <div className="text-xs text-slate-500">Add velocity & timing micro-variations</div>
          </div>
          <button
            onClick={() => setHumanize(!humanize)}
            className={`relative h-6 w-11 rounded-full transition ${humanize ? 'bg-[#ff7a1a]' : 'bg-white/15'}`}
            aria-label="Toggle humanize"
          >
            <span
              className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-all ${humanize ? 'left-[22px]' : 'left-0.5'}`}
            />
          </button>
        </section>

        {/* AI */}
        <section className="rounded-xl glass p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold">
                AI assistance
                <span className="rounded-full bg-gradient-to-r from-[#ff7a1a] to-[#ff9d3c] px-2 py-0.5 text-[10px] font-black uppercase text-[#14100a]">
                  Phase 5
                </span>
              </div>
              <div className="text-xs text-slate-500">
                Gemini → Groq · ideation + candidate scoring
              </div>
            </div>
            <button
              onClick={() => setAi(!ai)}
              className={`relative h-6 w-11 rounded-full transition ${ai ? 'bg-[#ff7a1a]' : 'bg-white/15'}`}
              aria-label="Toggle AI"
            >
              <span
                className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-all ${ai ? 'left-[22px]' : 'left-0.5'}`}
              />
            </button>
          </div>
          {ai && (
            <div className="mt-3 fade-up">
              <textarea
                className="glass w-full resize-none rounded-lg px-3 py-2 text-sm outline-none focus:border-[#ff7a1a]"
                rows={2}
                placeholder="Vibe prompt (optional): dark, cinematic drop with emotional lead…"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
              />
            </div>
          )}
        </section>

        {error && (
          <div className="rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}

        <div className="flex gap-3">
          <button
            className="btn-primary flex-1 rounded-xl px-6 py-4 text-lg tracking-wide"
            onClick={submit}
          >
            Generate composition
          </button>
          <button
            className="glass rounded-xl px-4 py-4 text-sm font-semibold text-slate-200 transition hover:border-[#ff7a1a]/60 hover:text-[#ffb25e]"
            onClick={() => fileRef.current?.click()}
            title="Load project JSON"
          >
            📂 Load project
          </button>
          <input
            ref={fileRef}
            type="file"
            accept="application/json,.json"
            className="hidden"
            onChange={loadProjectFile}
          />
        </div>
      </div>

      {/* ─── Summary ─── */}
      <aside className="space-y-4 lg:sticky lg:top-24 lg:self-start">
        <div className="glass rounded-xl p-5">
          <h3 className="text-xs font-bold uppercase tracking-widest text-slate-500">
            Live summary
          </h3>
          <dl className="mt-4 space-y-2.5 text-sm">
            <SummaryRow k="Genre" v={genre.replace(/_/g, ' ')} />
            <SummaryRow k="Key" v={`${key.toUpperCase()} ${mode}`} />
            <SummaryRow k="Tempo" v={`${bpm} BPM`} />
            <SummaryRow k="Structure" v={`${bars} bars · ~${Math.round(durationMin)}s`} />
            <SummaryRow k="Complexity" v={COMPLEXITY_LABEL[complexity]} />
            <SummaryRow k="Candidates" v={candidates} />
            <SummaryRow k="Seed" v={seed} />
            <SummaryRow k="Humanize" v={humanize ? 'On' : 'Off'} />
            <SummaryRow k="AI" v={ai ? 'On' : 'Off'} accent={ai} />
          </dl>
          <div className="mt-4 border-t border-white/10 pt-4">
            <div className="mb-2 text-xs font-semibold uppercase tracking-widest text-slate-500">
              Voices
            </div>
            <div className="flex flex-wrap gap-1.5">
              {roles.map((r) => (
                <span
                  key={r}
                  className="rounded-full px-2 py-0.5 text-[11px] font-semibold"
                  style={{ color: ROLE_COLORS[r] || '#fff', background: `${ROLE_COLORS[r] || '#fff'}1a` }}
                >
                  {roleLabel(r)}
                </span>
              ))}
            </div>
          </div>
        </div>
      </aside>
    </div>
  )
}

function SummaryRow({ k, v, accent }) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-slate-500">{k}</dt>
      <dd
        className={`font-semibold ${accent ? 'text-[#ffb25e]' : 'text-slate-200'}`}
      >
        {v}
      </dd>
    </div>
  )
}
