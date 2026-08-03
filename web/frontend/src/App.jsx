import { useEffect, useState } from 'react'
import { fetchConfig, streamGenerate } from './api'
import { loadHistory, saveHistoryEntry, makeHistoryEntry, removeHistoryEntry } from './history'
import GeneratorView from './components/GeneratorView'
import ResultView from './components/ResultView'
import HistoryView from './components/HistoryView'
import CompareView from './components/CompareView'
import ImportView from './components/ImportView'

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

  useEffect(() => {
    fetchConfig().then(setConfig).catch((e) => setConfigError(String(e)))
  }, [])

  useEffect(() => {
    if (view === 'form' && pendingProject) {
      setFormSnapshot(pendingProject)
      setPendingProject(null)
    }
  }, [view])

  function handleGenerate(params) {
    setView('loading')
    setError(null)
    setResult(null)
    setLoadMsg(null)
    setLoadPct(null)
    streamGenerate(
      { ...params, stems: true },
      {
        onStep: (s) => {
          setLoadMsg(s.message)
          setLoadPct(s.pct)
        },
        onResult: (data) => {
          setResult(data)
          setLastParams(params)
          setHistory(saveHistoryEntry(makeHistoryEntry(data, params)))
          setView('result')
        },
        onError: (e) => {
          setError(String(e))
          setView('form')
        },
      },
    ).catch((e) => {
      setError(String(e))
      setView('form')
    })
  }

  function openHistoryEntry(entry) {
    setResult(entry.result)
    setLastParams(entry.params)
    setView('result')
  }

  return (
    <div className="bg-aurora min-h-full">
      <header className="sticky top-0 z-20 glass border-b">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-3">
            <span className="text-2xl text-accent">♫</span>
            <h1 className="text-xl font-extrabold tracking-wide text-glow">AUREON</h1>
            <span className="rounded-full border border-[#ff7a1a]/40 bg-[#ff7a1a]/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest text-[#ffb25e]">
              Phase 5 · AI
            </span>
          </div>
          {view !== 'loading' && (
            <div className="flex items-center gap-2">
              {view === 'result' && (
                <button
                  className="glass rounded-lg px-4 py-2 text-sm font-semibold text-slate-200 transition hover:border-[#ff7a1a]/60 hover:text-[#ffb25e]"
                  onClick={() => setView('form')}
                >
                  ← New composition
                </button>
              )}
              <button
                className={`rounded-lg border px-4 py-2 text-sm font-semibold transition ${
                  view === 'import'
                    ? 'border-[#ff7a1a] bg-[#ff7a1a]/15 text-[#ffb25e]'
                    : 'glass text-slate-200 hover:border-white/30'
                }`}
                onClick={() => setView(view === 'import' ? 'form' : 'import')}
              >
                Import MIDI
              </button>
              <button
                className={`rounded-lg border px-4 py-2 text-sm font-semibold transition ${
                  view === 'history'
                    ? 'border-[#ff7a1a] bg-[#ff7a1a]/15 text-[#ffb25e]'
                    : 'glass text-slate-200 hover:border-white/30'
                }`}
                onClick={() => setView(view === 'history' ? 'form' : 'history')}
              >
                History {history.length > 0 ? `(${history.length})` : ''}
              </button>
            </div>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
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
          />
        )}

        {view === 'history' && (
          <HistoryView
            history={history}
            onOpen={openHistoryEntry}
            onRemove={(id) => setHistory(removeHistoryEntry(id))}
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
          />
        )}
      </main>
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
