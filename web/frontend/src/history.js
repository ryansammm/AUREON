const KEY = 'aureon.history.v1'

export function loadHistory() {
  try {
    const raw = localStorage.getItem(KEY)
    const list = raw ? JSON.parse(raw) : []
    return Array.isArray(list) ? list : []
  } catch {
    return []
  }
}

function persist(list) {
  try {
    localStorage.setItem(KEY, JSON.stringify(list.slice(0, 50)))
  } catch {
    /* storage full or unavailable — ignore */
  }
}

export function saveHistoryEntry(entry) {
  const list = loadHistory()
  list.unshift(entry)
  persist(list)
  return list
}

export function removeHistoryEntry(id) {
  const list = loadHistory().filter((e) => e.id !== id)
  persist(list)
  return list
}

/** Drop the heavy piano-roll note arrays, keep everything else. */
export function compactResult(result) {
  return {
    ...result,
    tracks: result.tracks.map((t) => ({
      role: t.role,
      name: t.name,
      preset: t.preset,
      notes: t.midi ? t.midi.length : t.notes,
    })),
  }
}

export function makeHistoryEntry(result, params) {
  return {
    id: `${Date.now()}`,
    ts: Date.now(),
    params,
    result: compactResult(result),
  }
}

export function downloadProject(params, result) {
  const blob = new Blob(
    [JSON.stringify({ app: 'aureon', savedAt: new Date().toISOString(), params, result }, null, 2)],
    { type: 'application/json' },
  )
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `aureon-${result?.genre || 'project'}.json`
  a.click()
  URL.revokeObjectURL(url)
}
