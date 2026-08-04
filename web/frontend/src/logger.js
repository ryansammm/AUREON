const MAX_LOGS = 500
let logs = []
let listeners = []

function addEntry(level, action, data = null) {
  const entry = {
    id: Date.now() + Math.random(),
    ts: new Date().toISOString(),
    level,
    action,
    data,
  }
  logs.unshift(entry)
  if (logs.length > MAX_LOGS) logs.pop()
  listeners.forEach((fn) => fn(entry))
  try {
    localStorage.setItem('aureon.logs', JSON.stringify(logs.slice(0, 200)))
  } catch {}
  return entry
}

export const log = {
  info: (action, data) => addEntry('info', action, data),
  warn: (action, data) => addEntry('warn', action, data),
  error: (action, data) => addEntry('error', action, data),
  getLogs: () => [...logs],
  clear: () => {
    logs = []
    localStorage.removeItem('aureon.logs')
  },
  export: () =>
    logs
      .map(
        (e) =>
          `[${e.ts}] [${e.level.toUpperCase()}] ${e.action}${e.data ? ' ' + JSON.stringify(e.data) : ''}`,
      )
      .join('\n'),
  onEntry: (fn) => {
    listeners.push(fn)
    return () => {
      listeners = listeners.filter((f) => f !== fn)
    }
  },
}

try {
  const stored = JSON.parse(localStorage.getItem('aureon.logs') || '[]')
  logs = stored.slice(0, MAX_LOGS)
} catch {}

window.addEventListener('error', (e) => {
  log.error('UNCAUGHT_ERROR', {
    message: e.message,
    source: e.filename,
    line: e.lineno,
    col: e.colno,
    stack: e.error?.stack?.slice(0, 500),
  })
})

window.addEventListener('unhandledrejection', (e) => {
  log.error('UNHANDLED_REJECTION', {
    reason: String(e.reason)?.slice(0, 300),
    stack: e.reason?.stack?.slice(0, 500),
  })
})
