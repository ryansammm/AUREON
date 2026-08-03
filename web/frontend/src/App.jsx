import { useEffect, useState } from 'react'
import { fetchConfig, generateComposition } from './api'
import GeneratorView from './components/GeneratorView'
import ResultView from './components/ResultView'

export default function App() {
  const [config, setConfig] = useState(null)
  const [configError, setConfigError] = useState(null)
  const [phase, setPhase] = useState('form') // form | loading | result
  const [result, setResult] = useState(null)
  const [lastParams, setLastParams] = useState(null)
  const [error, setError] = useState(null)
  const [loadStep, setLoadStep] = useState(0)

  useEffect(() => {
    fetchConfig().then(setConfig).catch((e) => setConfigError(String(e)))
  }, [])

  const steps = [
    'Mapping genre DNA',
    'Designing chord progression',
    'Sculpting basslines',
    'Weaving lead melodies',
    'Layering the arrangement',
    'Ranking candidates',
    'Rendering audio',
  ]

  useEffect(() => {
    if (phase !== 'loading') return
    setLoadStep(0)
    const iv = setInterval(() => {
      setLoadStep((s) => Math.min(s + 1, steps.length - 1))
    }, 650)
    return () => clearInterval(iv)
  }, [phase])

  async function handleGenerate(params) {
    setPhase('loading')
    setError(null)
    setResult(null)
    try {
      const data = await generateComposition(params)
      setResult(data)
      setLastParams(params)
      setPhase('result')
    } catch (e) {
      setError(String(e))
      setPhase('form')
    }
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
          {phase !== 'loading' && (
            <div className="flex items-center gap-3">
              {phase === 'result' && (
                <button
                  className="btn-primary rounded-lg px-4 py-2 text-sm"
                  onClick={() => setPhase('form')}
                >
                  ← New composition
                </button>
              )}
            </div>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        {configError && (
          <div className="glass rounded-xl p-4 text-sm text-red-300">{configError}</div>
        )}

        {phase === 'form' && config && (
          <GeneratorView
            config={config}
            onGenerate={handleGenerate}
            error={error}
            initial={lastParams}
          />
        )}

        {phase === 'loading' && (
          <div className="flex flex-col items-center justify-center py-32 text-center">
            <div className="pulse-ring flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-[#ff7a1a] to-[#ff9d3c] text-4xl">
              ♫
            </div>
            <h2 className="mt-8 text-xl font-bold">Generating your composition…</h2>
            <p className="mt-2 h-6 text-sm text-slate-400">{steps[loadStep]}</p>
            <div className="mt-6 h-1 w-72 overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full rounded-full bg-gradient-to-r from-[#ff7a1a] to-[#ffb25e] transition-all duration-700"
                style={{ width: `${((loadStep + 1) / steps.length) * 100}%` }}
              />
            </div>
          </div>
        )}

        {phase === 'result' && result && (
          <ResultView
            result={result}
            params={lastParams}
            onNew={() => setPhase('form')}
          />
        )}
      </main>
    </div>
  )
}
