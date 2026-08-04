import { useEffect, useState } from 'react'
import { fetchWithTimeout } from '../api'

export default function ConfigView({ onBack }) {
  const [geminiKey, setGeminiKey] = useState('')
  const [groqKey, setGroqKey] = useState('')
  const [geminiModel, setGeminiModel] = useState('')
  const [groqModel, setGroqModel] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState(null)

  useEffect(() => {
    fetchWithTimeout('/api/settings')
      .then((r) => r.json())
      .then((d) => {
        setGeminiKey(d.gemini_api_key || '')
        setGroqKey(d.groq_api_key || '')
        setGeminiModel(d.gemini_model || '')
        setGroqModel(d.groq_model || '')
      })
      .catch(() => setMsg({ type: 'error', text: 'Failed to load settings' }))
      .finally(() => setLoading(false))
  }, [])

  const save = async () => {
    setSaving(true)
    setMsg(null)
    try {
      const r = await fetchWithTimeout('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          GEMINI_API_KEY: geminiKey,
          GROQ_API_KEY: groqKey,
          GEMINI_MODEL: geminiModel,
          GROQ_MODEL: groqModel,
        }),
      })
      const d = await r.json()
      if (d.ok) setMsg({ type: 'ok', text: 'Settings saved' })
      else setMsg({ type: 'error', text: 'Save failed' })
    } catch {
      setMsg({ type: 'error', text: 'Network error' })
    }
    setSaving(false)
  }

  if (loading) {
    return (
      <div className="fade-up py-16 text-center text-slate-400">Loading settings...</div>
    )
  }

  return (
    <div className="fade-up mx-auto max-w-2xl space-y-8">
      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="glass rounded-lg border border-white/10 px-3 py-1.5 text-sm text-slate-300 hover:border-white/25"
        >
          &larr; Back
        </button>
        <h2 className="text-lg font-bold text-white">Settings</h2>
      </div>

      {/* API Keys */}
      <section className="glass rounded-xl p-6 space-y-5">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          API Keys
        </h3>
        <p className="text-xs text-slate-500">
          Optional — enables AI-powered composition suggestions and scoring.
          Get free keys from:
          <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noreferrer"
             className="ml-1 text-[#ff7a1a] hover:underline">Gemini</a> or
          <a href="https://console.groq.com/keys" target="_blank" rel="noreferrer"
             className="ml-1 text-[#ff7a1a] hover:underline">Groq</a>.
        </p>

        <div>
          <label className="mb-1 block text-xs font-semibold text-slate-400">Gemini API Key</label>
          <input
            type="password"
            value={geminiKey}
            onChange={(e) => setGeminiKey(e.target.value)}
            placeholder="AIza..."
            className="glass w-full rounded-lg border border-white/10 px-3 py-2 text-sm text-white outline-none placeholder:text-slate-600 focus:border-[#ff7a1a]"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-semibold text-slate-400">Groq API Key</label>
          <input
            type="password"
            value={groqKey}
            onChange={(e) => setGroqKey(e.target.value)}
            placeholder="gsk_..."
            className="glass w-full rounded-lg border border-white/10 px-3 py-2 text-sm text-white outline-none placeholder:text-slate-600 focus:border-[#ff7a1a]"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-400">Gemini Model (optional)</label>
            <input
              type="text"
              value={geminiModel}
              onChange={(e) => setGeminiModel(e.target.value)}
              placeholder="gemini-2.5-flash"
              className="glass w-full rounded-lg border border-white/10 px-3 py-2 text-sm text-white outline-none placeholder:text-slate-600 focus:border-[#ff7a1a]"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-400">Groq Model (optional)</label>
            <input
              type="text"
              value={groqModel}
              onChange={(e) => setGroqModel(e.target.value)}
              placeholder="llama-3.3-70b-versatile"
              className="glass w-full rounded-lg border border-white/10 px-3 py-2 text-sm text-white outline-none placeholder:text-slate-600 focus:border-[#ff7a1a]"
            />
          </div>
        </div>

        <div className="flex items-center gap-3 pt-2">
          <button
            onClick={save}
            disabled={saving}
            className="btn-primary rounded-lg px-5 py-2 text-sm font-semibold disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
          {msg && (
            <span className={`text-xs font-semibold ${msg.type === 'ok' ? 'text-emerald-400' : 'text-red-400'}`}>
              {msg.text}
            </span>
          )}
        </div>
      </section>

      {/* Info */}
      <section className="glass rounded-xl p-6 space-y-3">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          About
        </h3>
        <div className="space-y-1 text-xs text-slate-500">
          <p>Aureon by XYKS — AI Music Generator</p>
          <p>15 parent genres + 26 sub-genres | 10 instrument roles | Real GM SoundFont rendering</p>
          <p className="text-slate-600">Keys are stored locally in .env and never sent anywhere except the AI provider.</p>
        </div>
      </section>
    </div>
  )
}
