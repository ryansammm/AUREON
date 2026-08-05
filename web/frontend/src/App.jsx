import { useEffect, useState } from 'react'
import { fetchConfig, streamGenerate } from './api'
import { loadHistory, saveHistoryEntry, makeHistoryEntry, removeHistoryEntry } from './history'
import { log } from './logger'
import GeneratorView from './components/GeneratorView'
import ResultView from './components/ResultView'
import HistoryView from './components/HistoryView'
import CompareView from './components/CompareView'
import ImportView from './components/ImportView'
import ConfigView from './components/ConfigView'
import LogViewer from './components/LogViewer'

const FALLBACK_STEPS = [
  'Mapping genre DNA',
  'Designing chord progression',
  'Sculpting basslines',
  'Weaving lead melodies',
  'Layering the arrangement',
  'Ranking candidates',
  'Rendering audio',
]

export default function App() {
  const [config, setConfig] = useState(null)
  const [configError, setConfigError] = useState(null)
  const [view, setView] = useState('form') // form | loading | result | history | compare | import
  const [result, setResult] = useState(null)
  const [lastParams, setLastParams] = useState(null)
  const [error, setError] = useState(null)
  const [loadMsg, setLoadMsg] = useState(null)
  const [loadPct, setLoadPct] = useState(null)
  const [history, setHistory] = useState(loadHistory)
  const [pendingProject, setPendingProject] = useState(null)
  const [formSnapshot, setFormSnapshot] = useState(null)
  const [comparePair, setComparePair] = useState(null)
  const [logOpen, setLogOpen] = useState(false)

  useEffect(() => {
    fetchConfig()
      .then((c) => {
        log.info('CONFIG_LOADED', { genres: c.genres?.length, roles: c.roles?.length })
        setConfig(c)
      })
      .catch((e) => {
        log.error('CONFIG_FAILED', { error: String(e) })
        setConfigError(String(e))
      })
  }, [])

  useEffect(() => {
    if (view === 'form' && pendingProject) {
      setFormSnapshot(pendingProject)
      setPendingProject(null)
    }
  }, [view])

  useEffect(() => {
    log.info('VIEW', { view })
  }, [view])

  function handleGenerate(params) {
    log.info('GENERATE_START', { genre: params.genre, bpm: params.bpm, key: params.key, bars: params.bars, roles: params.roles, seed: params.seed })
    setView('loading')
    setError(null)
    setResult(null)
    setLoadMsg(null)
    setLoadPct(null)
    streamGenerate(
      { ...params, stems: true },
      {
        onStep: (s) => {
          log.info('GENERATE_STEP', { message: s.message, pct: s.pct })
          setLoadMsg(s.message)
          setLoadPct(s.pct)
        },
        onResult: (data) => {
          log.info('GENERATE_DONE', { genre: data.genre, key: data.key, bpm: data.bpm, tracks: data.tracks?.length })
          setResult(data)
          setLastParams(params)
          setHistory(saveHistoryEntry(makeHistoryEntry(data, params)))
          setView('result')
        },
        onError: (e) => {
          log.error('GENERATE_FAILED', { error: String(e) })
          setError(String(e))
          setView('form')
        },
      },
    ).catch((e) => {
      log.error('GENERATE_FAILED', { error: String(e) })
      setError(String(e))
      setView('form')
    })
  }

  function openHistoryEntry(entry) {
    log.info('HISTORY_OPEN', { id: entry.id, genre: entry.result?.genre })
    setResult(entry.result)
    setLastParams(entry.params)
    setView('result')
  }

  function handleSelectCandidate(candidate) {
    if (!candidate) return
    log.info('CANDIDATE_SELECT', { rank: candidate.rank, genre: candidate.genre })
    setResult((prev) => ({
      ...prev,
      genre: candidate.genre || prev.genre,
      key: candidate.key || prev.key,
      bpm: candidate.bpm || prev.bpm,
      tracks: candidate.tracks,
      wav: candidate.wav,
      mid: candidate.mid,
      arrangement: candidate.arrangement || prev.arrangement,
      chords: candidate.chords || prev.chords,
      stems: prev.stems,
      ai: prev.ai,
      candidates: prev.candidates,
    }))
  }

  const isNavActive = (key) => {
    if (key === 'form') return view === 'form' || view === 'loading' || view === 'result'
    if (key === 'history') return view === 'history' || view === 'compare'
    return view === key
  }

  return (
    <div className="bg-aurora relative isolate min-h-full">
      <div className="aurora-layer" aria-hidden="true">
        <div className="aurora-blob blob-1" />
        <div className="aurora-blob blob-2" />
        <div className="aurora-blob blob-3" />
      </div>
      <header className="sticky top-0 z-20 glass border-b">
        <div className="mx-auto flex max-w-[1560px] flex-wrap items-center justify-between gap-3 px-6 py-3">
          <button className="flex items-center gap-3" onClick={() => setView('form')} title="Back to compose">
            <span className="text-2xl text-accent">♫</span>
            <h1 className="text-xl font-extrabold tracking-wide text-glow">AUREON by XYKS</h1>
            <span className="rounded-full border border-[#ff7a1a]/40 bg-[#ff7a1a]/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest text-[#ffb25e]">
              Phase 5 · AI
            </span>
          </button>
          {view !== 'loading' && (
            <nav className="flex flex-wrap items-center gap-2">
              {view === 'result' && (
                <button
                  className="btn-primary rounded-lg px-4 py-2 text-sm font-semibold"
                  onClick={() => setView('form')}
                >
                  + New composition
                </button>
              )}
              {[
                { key: 'form', label: 'Compose' },
                { key: 'history', label: `History${history.length ? ` (${history.length})` : ''}` },
                { key: 'import', label: 'Import MIDI' },
                { key: 'settings', label: 'Settings' },
              ].map(({ key, label }) => (
                <button
                  key={key}
                  className={`rounded-lg border px-4 py-2 text-sm font-semibold transition ${
                    isNavActive(key)
                      ? 'border-[#ff7a1a] bg-[#ff7a1a]/15 text-[#ffb25e]'
                      : 'glass text-slate-200 hover:border-white/30'
                  }`}
                  onClick={() => setView(key)}
                >
                  {label}
                </button>
              ))}
              <button
                className="rounded-lg border border-white/10 px-2 py-2 text-sm text-slate-400 transition hover:border-white/25 hover:text-slate-200"
                onClick={() => setLogOpen(true)}
                title="Debug logs"
              >
                🐛
              </button>
            </nav>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-[1560px] px-6 py-8">
        {configError && (
          <div className="glass rounded-xl p-4 text-sm text-red-300">{configError}</div>
        )}

        {view === 'form' && config && (
          <GeneratorView
            config={config}
            onGenerate={handleGenerate}
            error={error}
            initial={formSnapshot || lastParams}
          />
        )}

        {view === 'loading' && (
          <LoadingView msg={loadMsg} pct={loadPct} steps={FALLBACK_STEPS} />
        )}

        {view === 'result' && result && (
          <ResultView
            result={result}
            params={lastParams}
            onNew={() => setView('form')}
            onSelectCandidate={handleSelectCandidate}
          />
        )}

        {view === 'history' && (
          <HistoryView
            history={history}
            onOpen={openHistoryEntry}
            onRemove={(id) => setHistory(removeHistoryEntry(id))}
            onBack={() => setView('form')}
            onCompare={(a, b) => {
              setComparePair({ a, b })
              setView('compare')
            }}
          />
        )}

        {view === 'compare' && comparePair?.a && comparePair?.b && (
          <CompareView
            a={comparePair.a}
            b={comparePair.b}
            onBack={() => setView('history')}
          />
        )}

        {view === 'import' && (
          <ImportView
            onUseRoles={(roles) => {
              setPendingProject({ roles: roles.filter((r) => r) })
              setView('form')
            }}
            onBack={() => setView('form')}
          />
        )}

        {view === 'settings' && (
          <ConfigView onBack={() => setView('form')} />
        )}
      </main>
      <footer className="py-6 text-center text-xs text-slate-500/70">
        AUREON <span className="font-semibold text-slate-400">v{config?.app_version || 'dev'}</span>
        <span className="mx-2">·</span>
        Developed by <span className="font-semibold text-slate-400">XYKS</span>
      </footer>
      <LogViewer open={logOpen} onClose={() => setLogOpen(false)} />
    </div>
  )
}

function LoadingView({ msg, pct, steps }) {
  const [step, setStep] = useState(0)
  useEffect(() => {
    if (pct != null) return
    const iv = setInterval(() => setStep((s) => Math.min(s + 1, steps.length - 1)), 700)
    return () => clearInterval(iv)
  }, [pct])

  const progress = pct != null ? pct : (step + 1) / steps.length
  const label = msg || steps[step]

  return (
    <div className="flex flex-col items-center justify-center py-32 text-center">
      <div className="pulse-ring flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-[#ff7a1a] to-[#ff9d3c] text-4xl">
        ♫
      </div>
      <h2 className="mt-8 text-xl font-bold">Generating your composition…</h2>
      <p className="mt-2 h-6 text-sm text-slate-400">{label}</p>
      <div className="mt-6 h-1 w-72 overflow-hidden rounded-full bg-white/10">
        <div
          className="h-full rounded-full bg-gradient-to-r from-[#ff7a1a] to-[#ffb25e] transition-all duration-300"
          style={{ width: `${Math.round(progress * 100)}%` }}
        />
      </div>
      <p className="mt-2 text-xs tabular-nums text-slate-500">
        {Math.round(progress * 100)}%
      </p>
    </div>
  )
}
