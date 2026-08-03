export async function fetchConfig() {
  const r = await fetch('/api/config')
  if (!r.ok) throw new Error('Failed to load config')
  return r.json()
}

export async function generateComposition(body) {
  const r = await fetch('/api/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await r.json()
  if (!r.ok) throw new Error(data.error || 'Generation failed')
  return data
}

export async function streamGenerate(body, { onStep, onResult, onError } = {}) {
  const r = await fetch('/api/generate/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!r.ok || !r.body) {
    let msg = `HTTP ${r.status}`
    try {
      const j = await r.json()
      msg = j.error || msg
    } catch {}
    throw new Error(msg)
  }
  const reader = r.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''
  let eventName = null
  let data = null
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    let idx
    while ((idx = buf.indexOf('\n\n')) !== -1) {
      const block = buf.slice(0, idx)
      buf = buf.slice(idx + 2)
      for (const line of block.split('\n')) {
        if (line.startsWith('event: ')) eventName = line.slice(7).trim()
        else if (line.startsWith('data: ')) data = line.slice(6).trim()
      }
      if (eventName && data) {
        const payload = JSON.parse(data)
        if (eventName === 'step' && onStep) {
          onStep(payload)
        } else if (eventName === 'result' && onResult) {
          onResult(payload)
        } else if (eventName === 'error') {
          if (onError) onError(new Error(payload.error || 'Generation failed'))
          return
        }
        eventName = null
        data = null
      }
    }
  }
}

export const wavUrl = (file) => `/play/${file}`
export const midiUrl = (file) => `/download/${file}`
export const trackMidiUrl = (mid, role) => `/api/track/${mid}?role=${role}`

export async function importMidi(file) {
  const fd = new FormData()
  fd.append('file', file)
  const r = await fetch('/api/import/midi', { method: 'POST', body: fd })
  const data = await r.json()
  if (!r.ok) throw new Error(data.error || 'MIDI import failed')
  return data
}

export const KEY_NAMES = ['c', 'c#', 'd', 'd#', 'e', 'f', 'f#', 'g', 'g#', 'a', 'a#', 'b']
export const MODES = ['minor', 'major']
export const COMPLEXITIES = ['low', 'medium', 'high']
export const COMPLEXITY_LABEL = {
  low: 'Minimal',
  medium: 'Balanced',
  high: 'Dense',
}
