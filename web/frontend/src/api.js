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

export const wavUrl = (file) => `/play/${file}`
export const midiUrl = (file) => `/download/${file}`

export const KEY_NAMES = ['c', 'c#', 'd', 'd#', 'e', 'f', 'f#', 'g', 'g#', 'a', 'a#', 'b']
export const MODES = ['minor', 'major']
export const COMPLEXITIES = ['low', 'medium', 'high']
export const COMPLEXITY_LABEL = {
  low: 'Minimal',
  medium: 'Balanced',
  high: 'Dense',
}
