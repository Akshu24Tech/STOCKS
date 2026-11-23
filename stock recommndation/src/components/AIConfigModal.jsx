import React, { useState, useEffect } from 'react'

export default function AIConfigModal({ isOpen, onClose }) {
  const [provider, setProvider] = useState('openai')
  const [apiKey, setApiKey] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    const p = localStorage.getItem('tradingagents_provider') || 'openai'
    const k = localStorage.getItem('tradingagents_apikey') || ''
    setProvider(p)
    setApiKey(k)
  }, [isOpen])

  if (!isOpen) return null

  const handleSave = () => {
    localStorage.setItem('tradingagents_provider', provider)
    localStorage.setItem('tradingagents_apikey', apiKey)
    setSaved(true)
    setTimeout(() => {
      setSaved(false)
      onClose()
    }, 1200)
  }

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      backgroundColor: 'rgba(19,32,58,0.45)',
      backdropFilter: 'blur(6px)',
      zIndex: 1100,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 16
    }} onClick={onClose}>
      <div style={{
        background: 'var(--clr-surface)',
        color: 'var(--clr-text)',
        borderRadius: 16,
        padding: 24,
        width: '100%',
        maxWidth: 480,
        boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5)',
        border: '1px solid var(--clr-border)'
      }} onClick={e => e.stopPropagation()}>
        
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 24 }}>🤖</span>
            <div>
              <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>AI settings</h3>
              <p style={{ margin: 0, fontSize: 12, color: 'var(--clr-text-3)' }}>Choose which model powers the AI agents' stock analysis</p>
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--clr-text-3)', fontSize: 20, cursor: 'pointer' }}>✕</button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 6, color: 'var(--clr-text-2)' }}>AI provider</label>
            <select
              value={provider}
              onChange={e => setProvider(e.target.value)}
              style={{
                width: '100%',
                padding: '10px 14px',
                borderRadius: 8,
                background: 'var(--clr-surface)',
                border: '1px solid var(--clr-border-2)',
                color: 'var(--clr-text)',
                fontSize: 14
              }}
            >
              <option value="openai">OpenAI (GPT-4o / GPT-4o-mini)</option>
              <option value="gemini">Google Gemini 1.5 Pro / Flash</option>
              <option value="anthropic">Anthropic Claude 3.5 Sonnet</option>
              <option value="groq">Groq (Llama 3.3 70B - Ultra Fast)</option>
              <option value="local">Rule + Agent Hybrid Engine (No Key Needed)</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 6, color: 'var(--clr-text-2)' }}>API key</label>
            <input
              type="password"
              placeholder={provider === 'local' ? 'No API key needed for hybrid engine' : `Enter your ${provider.toUpperCase()} API key...`}
              disabled={provider === 'local'}
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              style={{
                width: '100%',
                padding: '10px 14px',
                borderRadius: 8,
                background: 'var(--clr-surface)',
                border: '1px solid var(--clr-border-2)',
                color: 'var(--clr-text)',
                fontSize: 14,
                boxSizing: 'border-box'
              }}
            />
            <p style={{ fontSize: 11, color: 'var(--clr-text-3)', marginTop: 4 }}>
              Keys are kept safely in your browser localStorage and never logged on servers.
            </p>
          </div>

          {saved && (
            <div style={{ background: 'var(--clr-green-lt)', color: 'var(--clr-green)', padding: 10, borderRadius: 8, fontSize: 13, textAlign: 'center', fontWeight: 600 }}>
              ✓ Settings saved successfully!
            </div>
          )}

          <div style={{ display: 'flex', gap: 10, marginTop: 10 }}>
            <button
              onClick={onClose}
              style={{
                flex: 1,
                padding: '10px 16px',
                borderRadius: 8,
                border: '1px solid var(--clr-border-2)',
                background: 'var(--clr-surface)',
                color: 'var(--clr-text-1)',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              style={{
                flex: 1,
                padding: '10px 16px',
                borderRadius: 8,
                border: 'none',
                background: 'var(--clr-marigold)',
                color: 'var(--clr-rail)',
                fontWeight: 700,
                cursor: 'pointer'
              }}
            >
              Save settings
            </button>
          </div>
        </div>

      </div>
    </div>
  )
}
