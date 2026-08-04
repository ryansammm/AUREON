import { useEffect, useState, useRef } from 'react'
import { log } from '../logger'

const LEVEL_STYLE = {
  info: 'text-slate-400',
  warn: 'text-amber-400',
  error: 'text-red-400',
}

const LEVEL_DOT = {
  info: 'bg-slate-500',
  warn: 'bg-amber-400',
  error: 'bg-red-400',
}

export default function LogViewer({ open, onClose }) {
  const [entries, setEntries] = useState(log.getLogs())
  const [filter, setFilter] = useState('all')
  const [copied, setCopied] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    if (!open) return
    const unsub = log.onEntry((e) => {
      setEntries((prev) => [e, ...prev].slice(0, 500))
    })
    setEntries(log.getLogs())
    return unsub
  }, [open])

  useEffect(() => {
    if (open) bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [open, entries.length])

  if (!open) return null

  const filtered =
    filter === 'all' ? entries : entries.filter((e) => e.level === filter)

  const counts = {
    info: entries.filter((e) => e.level === 'info').length,
    warn: entries.filter((e) => e.level === 'warn').length,
    error: entries.filter((e) => e.level === 'error').length,
  }

  const copyLogs = async () => {
    const text = log.export()
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      const blob = new Blob([text], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `aureon-logs-${Date.now()}.txt`
      a.click()
      URL.revokeObjectURL(url)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="glass relative z-10 flex max-h-[80vh] w-full max-w-3xl flex-col rounded-2xl border border-white/15">
        <header className="flex items-center justify-between border-b border-white/10 px-5 py-3">
          <div className="flex items-center gap-3">
            <h3 className="text-sm font-bold text-slate-200">Debug Logs</h3>
            <span className="text-[11px] text-slate-500">
              {entries.length} entries
            </span>
          </div>
          <div className="flex items-center gap-2">
            {['all', 'error', 'warn', 'info'].map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`rounded-md px-2 py-1 text-[11px] font-semibold transition ${
                  filter === f
                    ? f === 'error'
                      ? 'bg-red-500/20 text-red-300'
                      : f === 'warn'
                        ? 'bg-amber-500/20 text-amber-300'
                        : 'bg-white/10 text-slate-200'
                    : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                {f === 'all' ? `All (${entries.length})` : `${f} (${counts[f]})`}
              </button>
            ))}
          </div>
        </header>

        <div className="flex-1 overflow-y-auto px-5 py-2 font-mono text-xs">
          {filtered.length === 0 ? (
            <div className="py-10 text-center text-slate-500">No logs yet</div>
          ) : (
            <div className="space-y-1">
              {filtered.map((e) => (
                <div
                  key={e.id}
                  className="flex items-start gap-2 rounded-md px-2 py-1 hover:bg-white/[0.03]"
                >
                  <span className={`mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full ${LEVEL_DOT[e.level]}`} />
                  <span className="shrink-0 text-slate-600">
                    {new Date(e.ts).toLocaleTimeString()}
                  </span>
                  <span className={`font-bold uppercase ${LEVEL_STYLE[e.level]}`}>
                    {e.action}
                  </span>
                  {e.data && (
                    <span className="break-all text-slate-400">
                      {typeof e.data === 'string'
                        ? e.data
                        : JSON.stringify(e.data)}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <footer className="flex items-center justify-between border-t border-white/10 px-5 py-3">
          <button
            onClick={() => {
              log.clear()
              setEntries([])
            }}
            className="rounded-md px-3 py-1.5 text-xs font-semibold text-red-400 transition hover:bg-red-500/10"
          >
            Clear all
          </button>
          <div className="flex gap-2">
            <button
              onClick={copyLogs}
              className="rounded-md bg-white/10 px-3 py-1.5 text-xs font-semibold text-slate-200 transition hover:bg-white/15"
            >
              {copied ? 'Copied!' : 'Copy to clipboard'}
            </button>
            <button
              onClick={onClose}
              className="rounded-md px-3 py-1.5 text-xs font-semibold text-slate-400 transition hover:text-slate-200"
            >
              Close
            </button>
          </div>
        </footer>
      </div>
    </div>
  )
}
