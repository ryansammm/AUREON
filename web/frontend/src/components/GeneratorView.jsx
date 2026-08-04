import { useEffect, useMemo, useRef, useState } from 'react'
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

const GENRE_STYLES = {
  techno: { icon: '⚙️', color: '#22d3ee' },
  house: { icon: '🏠', color: '#f472b6' },
  trance: { icon: '🌀', color: '#a78bfa' },
  drum_and_bass: { icon: '⚡', color: '#34d399' },
  dubstep: { icon: '🔥', color: '#fb7185' },
  trap: { icon: '🥁', color: '#fbbf24' },
  uk_garage: { icon: '🚗', color: '#60a5fa' },
  hardstyle: { icon: '🗡️', color: '#f87171' },
  future_bass: { icon: '🌊', color: '#2dd4bf' },
  downtempo: { icon: '🌙', color: '#818cf8' },
  _solo: { icon: '✦', color: '#94a3b8' },
}

const FAMILY_LABEL = {
  drum_and_bass: 'DnB',
  uk_garage: 'Garage',
  future_bass: 'Future Bass',
  _solo: 'More',
}

const roleLabel = (r) =>
  r.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())

const pretty = (s) =>
  s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())

const familyLabel = (k) => FAMILY_LABEL[k] || pretty(k)

const hexToRgba = (hex, a) => {
  const h = hex.replace('#', '')
  const r = parseInt(h.slice(0, 2), 16)
  const g = parseInt(h.slice(2, 4), 16)
  const b = parseInt(h.slice(4, 6), 16)
  return `rgba(${r},${g},${b},${a})`
}

function EqBars({ color, height = 12, bars = 5 }) {
  return (
    <span className="flex h-4 items-end gap-[2px]" aria-hidden="true">
      {Array.from({ length: bars }).map((_, i) => (
        <span
          key={i}
          className="eq-bar w-[3px] rounded-sm"
          style={{ height, background: color, animationDelay: `${((i * 0.13) % 1).toFixed(2)}s` }}
        />
      ))}
    </span>
  )
}

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
      className="accent w-full min-w-0"
      min={min}
      max={max}
      step={step}
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
    />
  )
}

function NumberSlider({ value, onChange, min, max, step = 1 }) {
  const commit = (raw) => {
    const v = Number(raw)
    if (!Number.isFinite(v)) return
    onChange(Math.min(max, Math.max(min, v)))
  }
  return (
    <div className="flex items-center gap-2">
      <input
        type="range"
        className="accent min-w-0 flex-1"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
      <input
        type="number"
        className="glass w-16 shrink-0 rounded-lg border border-white/10 px-2 py-1.5 text-center text-sm outline-none focus:border-[#ff7a1a]"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => commit(e.target.value)}
      />
    </div>
  )
}

function Switch({ on, onToggle, label }) {
  return (
    <button
      onClick={onToggle}
      className={`relative h-6 w-11 shrink-0 rounded-full transition ${on ? 'bg-[#ff7a1a]' : 'bg-white/15'}`}
      aria-label={label}
    >
      <span
        className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-all ${on ? 'left-[22px]' : 'left-0.5'}`}
      />
    </button>
  )
}

function ToggleCard({ title, sub, on, onToggle, badge, children }) {
  return (
    <section className="glass rounded-2xl p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold">
            {title}
            {badge && (
              <span className="rounded-full bg-gradient-to-r from-[#ff7a1a] to-[#ff9d3c] px-2 py-0.5 text-[10px] font-black uppercase text-[#14100a]">
                {badge}
              </span>
            )}
          </div>
          <div className="text-xs text-slate-500">{sub}</div>
        </div>
        <Switch on={on} onToggle={onToggle} label={title} />
      </div>
      {on && children && <div className="mt-3 fade-up">{children}</div>}
    </section>
  )
}

function GenreDeck({ groups, groupKeys, genre, selectGenre }) {
  const [active, setActive] = useState(() => {
    for (const k of groupKeys) {
      if ((groups[k] || []).includes(genre)) return k
    }
    return groupKeys[0]
  })
  const [q, setQ] = useState('')

  useEffect(() => {
    if (q) return
    for (const k of groupKeys) {
      if ((groups[k] || []).includes(genre)) {
        setActive(k)
        break
      }
    }
  }, [genre, q, groupKeys, groups])

  const meta = GENRE_STYLES[active] || GENRE_STYLES._solo
  const color = meta.color

  const qLower = q.trim().toLowerCase()
  const flat = qLower
    ? Object.entries(groups).flatMap(([k, list]) =>
        list
          .filter((g) => {
            const gName = g.replace(/_/g, ' ')
            const kName = k.replace(/_/g, ' ')
            return gName.includes(qLower) || kName.includes(qLower)
          })
          .map((g) => ({ g, k }))
      )
    : (groups[active] || []).map((g) => ({ g, k: active }))

  const pickFamily = (k) => {
    setActive(k)
    const members = groups[k]
    if (members && members.length) selectGenre(members[0])
  }

  return (
    <section className="glass relative overflow-hidden rounded-2xl p-4">
      <div
        className="deck-glow pointer-events-none absolute inset-x-8 top-0 h-[2px]"
        style={{ background: `linear-gradient(90deg, transparent, ${color}, transparent)` }}
      />
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h3 className="text-[11px] font-bold uppercase tracking-widest text-slate-400">
            Genre studio
          </h3>
          <EqBars color={color} />
        </div>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search genres…"
          className="w-36 rounded-lg border border-white/10 bg-white/[0.03] px-2.5 py-1.5 text-xs text-slate-200 outline-none transition placeholder:text-slate-500 focus:border-[#ff7a1a] sm:w-44"
        />
      </header>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {groupKeys.map((k) => {
          const m = GENRE_STYLES[k] || GENRE_STYLES._solo
          const isActive = k === active
          const hasSelected = (groups[k] || []).includes(genre)
          return (
            <button
              key={k}
              type="button"
              onClick={() => pickFamily(k)}
              className="shrink-0 rounded-lg border px-2.5 py-1.5 text-[11px] font-bold uppercase tracking-wide transition"
              style={
                isActive
                  ? {
                      borderColor: m.color,
                      color: m.color,
                      background: hexToRgba(m.color, 0.12),
                      boxShadow: `0 0 14px ${hexToRgba(m.color, 0.25)}`,
                    }
                  : {
                      borderColor: 'rgba(255,255,255,0.08)',
                      background: 'rgba(255,255,255,0.02)',
                      color: hasSelected ? m.color : '#94a3b8',
                    }
              }
            >
              <span className="mr-1">{m.icon}</span>
              {familyLabel(k)}
              {hasSelected && <span className="ml-1">●</span>}
            </button>
          )
        })}
      </div>

      <div className="mt-3 grid grid-cols-2 gap-1.5 sm:grid-cols-3 xl:grid-cols-4">
        {flat.map(({ g, k }) => {
          const m = GENRE_STYLES[k] || GENRE_STYLES._solo
          const selected = g === genre
          return (
            <button
              key={g}
              type="button"
              onClick={() => selectGenre(g)}
              className="truncate rounded-lg border px-3 py-2 text-left text-xs font-semibold transition"
              style={
                selected
                  ? {
                      borderColor: m.color,
                      color: '#fff',
                      background: `linear-gradient(135deg, ${hexToRgba(m.color, 0.3)}, ${hexToRgba(m.color, 0.1)})`,
                      boxShadow: `0 0 20px ${hexToRgba(m.color, 0.35)}`,
                    }
                  : qLower
                    ? {
                        borderColor: hexToRgba(m.color, 0.35),
                        background: 'rgba(255,255,255,0.02)',
                        color: '#c7cdda',
                      }
                    : {
                        borderColor: 'rgba(255,255,255,0.08)',
                        background: 'rgba(255,255,255,0.02)',
                        color: '#94a3b8',
                      }
              }
            >
              {pretty(g)}
            </button>
          )
        })}
        {flat.length === 0 && (
          <div className="col-span-full py-4 text-center text-xs text-slate-500">
            No genres match "{q}"
          </div>
        )}
      </div>
    </section>
  )
}

export default function GeneratorView({ config, onGenerate, error, initial }) {
  const [genre, setGenre] = useState(initial?.genre || config.genres[0])
  const def = config.genre_defaults[genre] || { bpm: 140, key: 'a', mode: 'minor' }

  const groups = config.genre_groups || {}
  const groupKeys = Object.keys(groups)

  const selectGenre = (g) => setGenre(g)

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
    if (config.genres.includes(p.genre)) selectGenre(p.genre)
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

  const genreColor = (() => {
    for (const k of groupKeys) {
      if ((groups[k] || []).includes(genre)) return GENRE_STYLES[k]?.color
    }
    return '#ff7a1a'
  })()

  return (
    <div className="fade-up grid gap-6 lg:grid-cols-12">
      {/* ─── Sound lab (left) ─── */}
      <aside className="space-y-4 lg:col-span-3">
        <section className="glass rounded-2xl p-4">
          <header className="mb-3 flex items-center justify-between">
            <h3 className="text-[11px] font-bold uppercase tracking-widest text-slate-400">
              Voices
            </h3>
            <span className="text-[11px] font-semibold tabular-nums text-[#ffb25e]">
              {roles.length}/{config.roles.length}
            </span>
          </header>
          <div className="grid grid-cols-2 gap-2">
            {config.roles.map((r) => {
              const on = roles.includes(r)
              const c = ROLE_COLORS[r] || '#fff'
              return (
                <button
                  key={r}
                  type="button"
                  onClick={() => toggleRole(r)}
                  className="flex items-center gap-2 rounded-lg border px-2.5 py-2 text-left text-xs font-semibold transition"
                  style={
                    on
                      ? {
                          borderColor: c,
                          color: c,
                          background: `${c}1a`,
                          boxShadow: `0 0 14px ${hexToRgba(c, 0.18)}`,
                        }
                      : {
                          borderColor: 'rgba(255,255,255,0.08)',
                          color: '#8a93a6',
                          background: 'rgba(255,255,255,0.02)',
                        }
                  }
                >
                  <span
                    className="h-2 w-2 shrink-0 rounded-full"
                    style={{ background: c, boxShadow: on ? `0 0 8px ${c}` : 'none' }}
                  />
                  <span className="truncate">{roleLabel(r)}</span>
                </button>
              )
            })}
          </div>
        </section>

        <ToggleCard
          title="Humanize performance"
          sub="Velocity & timing micro-variations"
          on={humanize}
          onToggle={() => setHumanize(!humanize)}
        />

        <ToggleCard
          title="AI assistance"
          sub="Gemini → Groq · ideation + scoring"
          on={ai}
          onToggle={() => setAi(!ai)}
          badge="Phase 5"
        >
          <textarea
            className="glass w-full resize-none rounded-lg px-3 py-2 text-sm outline-none focus:border-[#ff7a1a]"
            rows={2}
            placeholder="Vibe prompt (optional): dark, cinematic drop with emotional lead…"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />
        </ToggleCard>

        <button
          type="button"
          className="glass w-full rounded-xl px-4 py-3 text-sm font-semibold text-slate-200 transition hover:border-[#ff7a1a]/60 hover:text-[#ffb25e]"
          onClick={() => fileRef.current?.click()}
          title="Load project JSON"
        >
          📂 Load project JSON
        </button>
        <input
          ref={fileRef}
          type="file"
          accept="application/json,.json"
          className="hidden"
          onChange={loadProjectFile}
        />
      </aside>

      {/* ─── Studio deck (center) ─── */}
      <div className="space-y-6 lg:col-span-6">
        <GenreDeck
          groups={groups}
          groupKeys={groupKeys}
          genre={genre}
          selectGenre={selectGenre}
        />

        <section className="glass rounded-2xl p-4">
          <h3 className="mb-3 text-[11px] font-bold uppercase tracking-widest text-slate-400">
            Tempo &amp; key
          </h3>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
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
                    type="button"
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
              <NumberSlider value={bpm} onChange={setBpm} min={60} max={200} />
            </Field>
            <Field label="Bars" hint={bars}>
              <NumberSlider value={bars} onChange={setBars} min={4} max={280} />
            </Field>
          </div>
        </section>

        <section className="glass rounded-2xl p-4">
          <h3 className="mb-3 text-[11px] font-bold uppercase tracking-widest text-slate-400">
            Structure
          </h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Field label="Complexity">
              <div className="flex rounded-lg border border-white/10 p-0.5">
                {COMPLEXITIES.map((c) => (
                  <button
                    key={c}
                    type="button"
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
                  type="button"
                  className="glass rounded-lg px-3 text-sm text-slate-300 hover:border-white/30"
                  onClick={() => setSeed(Math.floor(Math.random() * 10000))}
                  title="Random seed"
                >
                  🎲
                </button>
              </div>
            </Field>
          </div>
        </section>
      </div>

      {/* ─── Master console (right) ─── */}
      <aside className="lg:col-span-3">
        <div className="glass relative overflow-hidden rounded-2xl p-5 lg:sticky lg:top-24">
          <div
            className="deck-glow pointer-events-none absolute inset-x-8 top-0 h-[2px]"
            style={{ background: `linear-gradient(90deg, transparent, ${genreColor}, transparent)` }}
          />
          <header className="flex items-center justify-between">
            <h3 className="text-[11px] font-bold uppercase tracking-widest text-slate-400">
              Master console
            </h3>
            <EqBars color={genreColor} />
          </header>

          <dl className="mt-4 space-y-2.5 text-sm">
            <SummaryRow k="Genre" v={pretty(genre)} accentColor={genreColor} />
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

          {error && (
            <div className="mt-4 rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
              {error}
            </div>
          )}

          <button
            type="button"
            className="btn-primary mt-5 w-full rounded-xl px-6 py-4 text-lg tracking-wide"
            onClick={submit}
          >
            Generate composition
          </button>
        </div>
      </aside>
    </div>
  )
}

function SummaryRow({ k, v, accent, accentColor }) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-slate-500">{k}</dt>
      <dd
        className={`flex items-center gap-1.5 font-semibold ${
          accent ? 'text-[#ffb25e]' : 'text-slate-200'
        }`}
      >
        {accentColor && (
          <span
            className="h-1.5 w-1.5 rounded-full"
            style={{ background: accentColor, boxShadow: `0 0 8px ${accentColor}` }}
          />
        )}
        {v}
      </dd>
    </div>
  )
}
