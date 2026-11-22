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
      backgroundColor: 'rgba(15, 23, 42, 0.7)',
      backdropFilter: 'blur(6px)',
      zIndex: 1100,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 16
    }} onClick={onClose}>
      <div style={{
        background: '#1E293B',
        color: '#F8FAFC',
        borderRadius: 16,
        padding: 24,
        width: '100%',
        maxWidth: 480,
        boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5)',
        border: '1px solid #334155'
      }} onClick={e => e.stopPropagation()}>
        
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 24 }}>🤖</span>
            <div>
              <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>TradingAgents AI Configuration</h3>
              <p style={{ margin: 0, fontSize: 12, color: '#94A3B8' }}>Configure Multi-Agent LLM Providers</p>
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#94A3B8', fontSize: 20, cursor: 'pointer' }}>✕</button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 6, color: '#CBD5E1' }}>LLM Provider</label>
            <select
              value={provider}
              onChange={e => setProvider(e.target.value)}
              style={{
                width: '100%',
                padding: '10px 14px',
                borderRadius: 8,
                background: '#0F172A',
                border: '1px solid #334155',
                color: '#F8FAFC',
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
            <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 6, color: '#CBD5E1' }}>API Key</label>
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
                background: '#0F172A',
                border: '1px solid #334155',
                color: '#F8FAFC',
                fontSize: 14,
                boxSizing: 'border-box'
              }}
            />
            <p style={{ fontSize: 11, color: '#64748B', marginTop: 4 }}>
              Keys are kept safely in your browser localStorage and never logged on servers.
            </p>
          </div>

          {saved && (
            <div style={{ background: '#064E3B', color: '#6EE7B7', padding: 10, borderRadius: 8, fontSize: 13, textAlign: 'center', fontWeight: 600 }}>
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
                border: '1px solid #334155',
                background: '#0F172A',
                color: '#CBD5E1',
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
                background: 'linear-gradient(135deg, #2563EB, #4F46E5)',
                color: '#FFFFFF',
                fontWeight: 700,
                cursor: 'pointer'
              }}
            >
              Save Configuration
            </button>
          </div>
        </div>

      </div>
    </div>
  )
}
