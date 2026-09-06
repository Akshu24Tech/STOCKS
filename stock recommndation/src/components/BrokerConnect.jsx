import React, { useState, useRef } from 'react'
import { API } from '../config'

const BROKERS = [
  {
    id: 'angel',
    name: 'Angel One SmartAPI',
    logo: '🔵',
    color: '#0052CC',
    bg: '#E6F0FF',
    border: '#C0D9FF',
    description: 'Connect real account via SmartAPI (API Key, Client ID, PIN & TOTP)',
    tag: 'Live SmartAPI Sync',
    isRealAPI: true,
  },
  {
    id: 'upstox',
    name: 'Upstox Pro',
    logo: '🟣',
    color: '#7B4FE0',
    bg: '#F4EFFD',
    border: '#DDD0F9',
    description: 'Connect real account using Upstox Access Token / OAuth dialog',
    tag: 'Live Upstox API',
    isRealAPI: true,
  },
  {
    id: 'zerodha',
    name: 'Zerodha Kite',
    logo: '🟠',
    color: '#387ED1',
    bg: '#EBF3FC',
    border: '#C3DCF7',
    description: 'Instant Sync or Statement CSV import for Kite holdings',
    tag: 'Popular Broker',
    isRealAPI: false,
  },
  {
    id: 'groww',
    name: 'Groww',
    logo: '🟢',
    color: '#00C853',
    bg: '#E8FFF0',
    border: '#A5EFBD',
    description: 'Instant Sync or 1-Click Groww Report CSV import',
    tag: 'Direct Import',
    isRealAPI: false,
  },
]

export default function BrokerConnect({ onHoldingsImported, connectedBrokers = [], onDisconnectBroker }) {
  const [activeModal, setActiveModal] = useState(null) // 'angel' | 'upstox' | null
  const [loadingBroker, setLoadingBroker] = useState(null)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')
  const [csvUploading, setCsvUploading] = useState(false)
  const fileRef = useRef()

  // Angel One SmartAPI form state
  const [angelForm, setAngelForm] = useState({
    api_key: localStorage.getItem('angel_api_key') || '',
    client_code: localStorage.getItem('angel_client_code') || '',
    pin: '',
    totp: '',
  })
  const [angelConnecting, setAngelConnecting] = useState(false)

  // Upstox token form state
  const [upstoxToken, setUpstoxToken] = useState('')
  const [upstoxConnecting, setUpstoxConnecting] = useState(false)

  // Handle Real Angel One SmartAPI Connect
  const handleAngelConnect = async (e) => {
    e?.preventDefault()
    setAngelConnecting(true)
    setError('')
    setSuccessMsg('')

    try {
      if (!angelForm.api_key.trim()) throw new Error('Please enter your SmartAPI API Key')
      if (!angelForm.client_code.trim()) throw new Error('Please enter your Angel One Client Code / User ID')
      if (!angelForm.pin.trim()) throw new Error('Please enter your 4-digit PIN / Password')
      if (!angelForm.totp.trim()) throw new Error('Please enter your TOTP code or TOTP Secret Key')

      // Save credentials for convenience (excluding PIN for basic safety)
      localStorage.setItem('angel_api_key', angelForm.api_key.trim())
      localStorage.setItem('angel_client_code', angelForm.client_code.trim())

      const res = await fetch(`${API}/broker/angel/real-connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          api_key: angelForm.api_key.trim(),
          client_code: angelForm.client_code.trim(),
          pin: angelForm.pin.trim(),
          totp: angelForm.totp.trim(),
        }),
      })

      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.detail || data.message || 'Failed to authenticate with Angel One SmartAPI')
      }

      const rawHoldings = data.holdings || []
      if (rawHoldings.length === 0) {
        setSuccessMsg(`Successfully authenticated with Angel One (${angelForm.client_code}), but no equity delivery holdings were found.`)
      } else {
        const cleaned = rawHoldings.map(h => ({
          symbol: h.symbol.replace('.NS', '').replace('.BO', '').toUpperCase(),
          qty: parseFloat(h.qty),
          buy_price: parseFloat(h.buy_price),
          current_price: parseFloat(h.current_price || h.buy_price),
          pnl: parseFloat(h.pnl || 0),
          source: 'Angel One SmartAPI',
        }))
        onHoldingsImported(cleaned, 'angel')
        setSuccessMsg(`🎉 Successfully connected to Angel One SmartAPI! Imported ${cleaned.length} real stock holdings for account ${angelForm.client_code}.`)
      }

      setActiveModal(null)
      setTimeout(() => setSuccessMsg(''), 8000)
    } catch (err) {
      setError(`Angel One Error: ${err.message}`)
    }
    setAngelConnecting(false)
  }

  // Handle Real Upstox Access Token Connect
  const handleUpstoxConnect = async (e) => {
    e?.preventDefault()
    setUpstoxConnecting(true)
    setError('')
    setSuccessMsg('')

    try {
      if (!upstoxToken.trim()) throw new Error('Please paste your Upstox Access Token')

      const res = await fetch(`${API}/broker/upstox/holdings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ access_token: upstoxToken.trim() }),
      })

      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.detail || 'Invalid or expired Upstox Access Token')
      }

      const cleaned = (data.holdings || []).map(h => ({
        symbol: h.symbol.replace('.NS', '').replace('.BO', '').toUpperCase(),
        qty: parseFloat(h.qty),
        buy_price: parseFloat(h.buy_price),
        current_price: parseFloat(h.current_price || h.buy_price),
        pnl: parseFloat(h.pnl || 0),
        source: 'Upstox Pro',
      }))

      onHoldingsImported(cleaned, 'upstox')
      setSuccessMsg(`🎉 Successfully connected to Upstox! Imported ${cleaned.length} real stock holdings.`)
      setActiveModal(null)
      setTimeout(() => setSuccessMsg(''), 8000)
    } catch (err) {
      setError(`Upstox Error: ${err.message}`)
    }
    setUpstoxConnecting(false)
  }

  // Demo 1-Click Sync (For users wanting to test without live credentials)
  const handleDemoSync = async (broker) => {
    setLoadingBroker(broker.id)
    setError('')
    setSuccessMsg('')
    try {
      const res = await fetch(`${API}/broker/${broker.id}/demo-holdings`)
      if (!res.ok) throw new Error(`Could not sync with ${broker.name}`)
      const data = await res.json()
      const holdings = (data.holdings || []).map(h => ({
        symbol: h.symbol.replace('.NS', '').replace('.BO', '').toUpperCase(),
        qty: parseFloat(h.qty),
        buy_price: parseFloat(h.buy_price),
        source: `${broker.name} (Demo)`,
      }))
      onHoldingsImported(holdings, broker.id)
      setSuccessMsg(`Imported ${holdings.length} sample portfolio holdings from ${broker.name}.`)
      setTimeout(() => setSuccessMsg(''), 6000)
    } catch (e) {
      setError(`Failed to sync: ${e.message}`)
    }
    setLoadingBroker(null)
  }

  // Handle CSV file upload
  const handleCsvFile = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setCsvUploading(true)
    setError('')
    setSuccessMsg('')

    try {
      const text = await file.text()
      const lines = text.split(/\r?\n/).filter(Boolean)
      if (lines.length < 2) throw new Error('File has no data rows')

      const header = lines[0].split(',').map(h => h.trim().toLowerCase().replace(/["'\s_]/g, ''))
      const symIdx = header.findIndex(h => h.includes('symbol') || h.includes('stock') || h.includes('scrip') || h.includes('security') || h.includes('instrument') || h.includes('name'))
      const qtyIdx = header.findIndex(h => h.includes('qty') || h.includes('quantity') || h.includes('shares') || h.includes('units'))
      const priceIdx = header.findIndex(h => h.includes('price') || h.includes('buy') || h.includes('avg') || h.includes('cost') || h.includes('rate'))

      const holdings = []
      for (let i = 1; i < lines.length; i++) {
        const row = lines[i].split(',').map(c => c.trim().replace(/^["']|["']$/g, ''))
        if (row.length < 2) continue
        const sym = (symIdx >= 0 ? row[symIdx] : row[0])?.replace('.NS', '').replace('.BO', '').toUpperCase()
        const qty = parseFloat(qtyIdx >= 0 ? row[qtyIdx] : row[1]) || 1
        const buyPrice = parseFloat(priceIdx >= 0 ? row[priceIdx] : row[2]) || 100
        if (sym && qty > 0) {
          holdings.push({ symbol: sym, qty, buy_price: buyPrice, source: 'Uploaded CSV' })
        }
      }

      if (!holdings.length) throw new Error('Could not find valid stocks in the uploaded file')
      onHoldingsImported(holdings, 'csv')
      setSuccessMsg(`Successfully imported ${holdings.length} stocks from your CSV statement!`)
      setTimeout(() => setSuccessMsg(''), 6000)
    } catch (err) {
      setError(`CSV import error: ${err.message}`)
    }
    setCsvUploading(false)
    if (fileRef.current) fileRef.current.value = ''
  }

  // Sample CSV generator
  const downloadSampleCsv = () => {
    const csvContent = 'data:text/csv;charset=utf-8,Symbol,Quantity,Average Price\nRELIANCE,25,2850.50\nTCS,15,3890.00\nHDFCBANK,50,1540.00\nINFY,30,1650.00\nTATAMOTORS,40,930.00\nNIFTYBEES,100,242.00\n'
    const encodedUri = encodeURI(csvContent)
    const link = document.createElement('a')
    link.setAttribute('href', encodedUri)
    link.setAttribute('download', 'sample_portfolio.csv')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Banner */}
      <div style={{
        background: 'linear-gradient(135deg, #EFF6FF, #F5F3FF)',
        border: '1px solid #C7D2FE',
        borderRadius: 14,
        padding: '16px 20px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 12,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ fontSize: 32 }}>⚡</div>
          <div>
            <div style={{ fontWeight: 800, fontSize: 16, color: '#1E1B4B' }}>
              Real Broker Integration via SmartAPI & Direct APIs
            </div>
            <div style={{ fontSize: 13, color: '#4B5563', marginTop: 2 }}>
              Connect directly to your actual Angel One or Upstox account to fetch live holdings, or upload a broker statement CSV.
            </div>
          </div>
        </div>
        <div style={{
          background: '#DCFCE7',
          color: '#166534',
          border: '1px solid #86EFAC',
          borderRadius: 20,
          padding: '4px 14px',
          fontSize: 12,
          fontWeight: 700,
        }}>
          🔒 Direct Broker Sync Supported
        </div>
      </div>

      {successMsg && (
        <div style={{
          background: '#DCFCE7',
          border: '1px solid #86EFAC',
          borderRadius: 10,
          padding: '12px 16px',
          color: '#15803D',
          fontWeight: 600,
          fontSize: 13,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}>
          <span>✅</span>
          <span>{successMsg}</span>
        </div>
      )}

      {error && (
        <div style={{
          background: '#FEF2F2',
          border: '1px solid #FECACA',
          borderRadius: 10,
          padding: '12px 16px',
          color: '#DC2626',
          fontSize: 13,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}>
          <span>⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {/* Broker Cards Grid */}
      <div>
        <div style={{ fontSize: 14, fontWeight: 700, color: '#1E293B', marginBottom: 12 }}>
          Select Broker to Connect
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 14 }}>
          {BROKERS.map(b => {
            const isConn = connectedBrokers.includes(b.id)
            const isLoading = loadingBroker === b.id

            return (
              <div
                key={b.id}
                style={{
                  background: '#FFFFFF',
                  border: isConn ? `2px solid ${b.color}` : '1px solid #E2E8F0',
                  borderRadius: 14,
                  padding: '18px 20px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
                  transition: 'all 0.15s ease',
                }}
              >
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span style={{ fontSize: 26 }}>{b.logo}</span>
                      <div>
                        <div style={{ fontWeight: 800, fontSize: 15, color: '#0F172A' }}>{b.name}</div>
                        <span style={{ fontSize: 10, color: b.color, fontWeight: 700 }}>{b.tag}</span>
                      </div>
                    </div>
                    {isConn && (
                      <span style={{
                        background: '#DCFCE7',
                        color: '#166534',
                        fontSize: 11,
                        padding: '2px 8px',
                        borderRadius: 6,
                        fontWeight: 700,
                      }}>
                        ✓ Connected
                      </span>
                    )}
                  </div>
                  <p style={{ fontSize: 12, color: '#64748B', lineHeight: 1.45, margin: '8px 0 16px' }}>
                    {b.description}
                  </p>
                </div>

                <div style={{ display: 'flex', gap: 8 }}>
                  {isConn ? (
                    <button
                      className="btn btn-ghost"
                      style={{ flex: 1, fontSize: 12, padding: '7px 12px', color: '#DC2626' }}
                      onClick={() => onDisconnectBroker(b.id)}
                    >
                      Disconnect
                    </button>
                  ) : b.id === 'angel' ? (
                    <button
                      className="btn btn-primary"
                      style={{
                        flex: 1,
                        background: b.color,
                        borderColor: b.color,
                        fontSize: 13,
                        padding: '9px 14px',
                        fontWeight: 700,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: 6,
                      }}
                      onClick={() => {
                        setError('')
                        setActiveModal('angel')
                      }}
                    >
                      <span>⚡</span>
                      <span>Connect SmartAPI</span>
                    </button>
                  ) : b.id === 'upstox' ? (
                    <button
                      className="btn btn-primary"
                      style={{
                        flex: 1,
                        background: b.color,
                        borderColor: b.color,
                        fontSize: 13,
                        padding: '9px 14px',
                        fontWeight: 700,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: 6,
                      }}
                      onClick={() => {
                        setError('')
                        setActiveModal('upstox')
                      }}
                    >
                      <span>🔑</span>
                      <span>Connect via Upstox</span>
                    </button>
                  ) : (
                    <button
                      className="btn btn-primary"
                      style={{
                        flex: 1,
                        background: b.color,
                        borderColor: b.color,
                        fontSize: 13,
                        padding: '9px 14px',
                        fontWeight: 700,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: 6,
                      }}
                      disabled={isLoading}
                      onClick={() => handleDemoSync(b)}
                    >
                      {isLoading ? 'Syncing…' : `1-Click Sync ${b.name}`}
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* CSV / Statement Upload Section */}
      <div style={{
        background: '#FFFFFF',
        border: '1px solid #E2E8F0',
        borderRadius: 14,
        padding: '20px 24px',
        marginTop: 6,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12, marginBottom: 14 }}>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: '#0F172A' }}>
              Alternative: Upload Broker Statement CSV
            </div>
            <div style={{ fontSize: 12, color: '#64748B', marginTop: 2 }}>
              Download holdings CSV from Groww, Zerodha Console, Upstox, Dhan or custom Excel, and drop it here.
            </div>
          </div>
          <button
            className="btn btn-ghost"
            style={{ fontSize: 12, padding: '6px 12px' }}
            onClick={downloadSampleCsv}
          >
            📥 Download Sample CSV
          </button>
        </div>

        <div
          style={{
            border: '2px dashed #CBD5E1',
            borderRadius: 12,
            padding: '24px 20px',
            textAlign: 'center',
            background: '#F8FAFC',
            cursor: 'pointer',
          }}
          onClick={() => fileRef.current?.click()}
        >
          <input
            type="file"
            accept=".csv,.txt"
            ref={fileRef}
            style={{ display: 'none' }}
            onChange={handleCsvFile}
          />
          <div style={{ fontSize: 32, marginBottom: 6 }}>📄</div>
          <div style={{ fontWeight: 700, fontSize: 14, color: '#0F172A' }}>
            {csvUploading ? 'Parsing statement file…' : 'Click to Upload Portfolio CSV Statement'}
          </div>
          <div style={{ fontSize: 12, color: '#64748B', marginTop: 4 }}>
            Recognizes: Symbol / Stock, Quantity, and Buy / Average Price columns automatically
          </div>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────────────────────
          MODAL 1: ANGEL ONE SMARTAPI CONNECT (REAL BROKER)
      ───────────────────────────────────────────────────────────────────────────── */}
      {activeModal === 'angel' && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(15, 23, 42, 0.6)',
            backdropFilter: 'blur(4px)',
            zIndex: 1100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 16,
          }}
          onClick={() => setActiveModal(null)}
        >
          <div
            style={{
              background: '#FFFFFF',
              borderRadius: 18,
              width: '100%',
              maxWidth: 520,
              padding: '24px 28px',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.2)',
              border: '1px solid #E2E8F0',
            }}
            onClick={e => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontSize: 26 }}>🔵</span>
                <div>
                  <h3 style={{ margin: 0, fontSize: 18, fontWeight: 800, color: '#0F172A' }}>
                    Connect Angel One SmartAPI
                  </h3>
                  <div style={{ fontSize: 12, color: '#64748B' }}>
                    Directly fetch your real equity portfolio from Angel One
                  </div>
                </div>
              </div>
              <button
                onClick={() => setActiveModal(null)}
                style={{
                  border: 'none',
                  background: 'none',
                  fontSize: 18,
                  cursor: 'pointer',
                  color: '#64748B',
                }}
              >
                ✕
              </button>
            </div>

            {/* Quick Helper Box */}
            <div style={{
              background: '#EFF6FF',
              border: '1px solid #BFDBFE',
              borderRadius: 10,
              padding: '10px 14px',
              fontSize: 12,
              color: '#1E40AF',
              lineHeight: 1.45,
              marginBottom: 16,
            }}>
              <strong>💡 How to connect:</strong>
              <ol style={{ margin: '4px 0 0', paddingLeft: 18 }}>
                <li>Get your <strong>API Key</strong> from <a href="https://smartapi.angelone.in/new/apps" target="_blank" rel="noreferrer" style={{ color: '#1D4ED8', textDecoration: 'underline' }}>smartapi.angelone.in/new/apps</a>.</li>
                <li>Enter your <strong>Client Code</strong> (e.g. A123456) &amp; <strong>Trading PIN</strong>.</li>
                <li>Paste either your live <strong>6-digit TOTP</strong> from Authenticator OR your <strong>TOTP Secret Key</strong> from <a href="https://smartapi.angelone.in/enable-totp" target="_blank" rel="noreferrer" style={{ color: '#1D4ED8', textDecoration: 'underline' }}>enable-totp</a> (backend will auto-generate TOTP!).</li>
              </ol>
            </div>

            <form onSubmit={handleAngelConnect} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#334155', marginBottom: 4 }}>
                  SmartAPI API Key *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. 5xXxxxXy"
                  value={angelForm.api_key}
                  onChange={e => setAngelForm(f => ({ ...f, api_key: e.target.value }))}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: 8,
                    border: '1px solid #CBD5E1',
                    fontSize: 13,
                    fontFamily: 'monospace',
                    boxSizing: 'border-box',
                  }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#334155', marginBottom: 4 }}>
                    Client Code (User ID) *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. P123456"
                    value={angelForm.client_code}
                    onChange={e => setAngelForm(f => ({ ...f, client_code: e.target.value.toUpperCase() }))}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: 8,
                      border: '1px solid #CBD5E1',
                      fontSize: 13,
                      boxSizing: 'border-box',
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#334155', marginBottom: 4 }}>
                    Trading PIN / Password *
                  </label>
                  <input
                    type="password"
                    required
                    placeholder="4-digit PIN"
                    value={angelForm.pin}
                    onChange={e => setAngelForm(f => ({ ...f, pin: e.target.value }))}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: 8,
                      border: '1px solid #CBD5E1',
                      fontSize: 13,
                      boxSizing: 'border-box',
                    }}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#334155', marginBottom: 4 }}>
                  TOTP Code OR TOTP Secret Key *
                </label>
                <input
                  type="text"
                  required
                  placeholder="6-digit code (e.g. 842190) or Base32 Secret Key"
                  value={angelForm.totp}
                  onChange={e => setAngelForm(f => ({ ...f, totp: e.target.value }))}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: 8,
                    border: '1px solid #CBD5E1',
                    fontSize: 13,
                    fontFamily: 'monospace',
                    boxSizing: 'border-box',
                  }}
                />
                <span style={{ fontSize: 11, color: '#64748B', marginTop: 3, display: 'block' }}>
                  Tip: Pasting your TOTP secret key allows automatic regeneration on every sync without opening Google Authenticator.
                </span>
              </div>

              <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
                <button
                  type="button"
                  onClick={() => {
                    setActiveModal(null)
                    // offer quick demo
                    handleDemoSync({ id: 'angel', name: 'Angel One' })
                  }}
                  style={{
                    padding: '10px 14px',
                    borderRadius: 8,
                    border: '1px solid #CBD5E1',
                    background: '#FFFFFF',
                    color: '#475569',
                    fontSize: 12,
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  Try Demo Instead
                </button>

                <button
                  type="submit"
                  disabled={angelConnecting}
                  style={{
                    flex: 1,
                    padding: '11px 16px',
                    borderRadius: 8,
                    border: 'none',
                    background: '#0052CC',
                    color: '#FFFFFF',
                    fontSize: 13,
                    fontWeight: 700,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 8,
                  }}
                >
                  {angelConnecting ? 'Authenticating with Angel One…' : '🚀 Fetch Real Holdings'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────────────────────
          MODAL 2: UPSTOX ACCESS TOKEN CONNECT (REAL BROKER)
      ───────────────────────────────────────────────────────────────────────────── */}
      {activeModal === 'upstox' && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(15, 23, 42, 0.6)',
            backdropFilter: 'blur(4px)',
            zIndex: 1100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 16,
          }}
          onClick={() => setActiveModal(null)}
        >
          <div
            style={{
              background: '#FFFFFF',
              borderRadius: 18,
              width: '100%',
              maxWidth: 500,
              padding: '24px 28px',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.2)',
              border: '1px solid #E2E8F0',
            }}
            onClick={e => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontSize: 26 }}>🟣</span>
                <div>
                  <h3 style={{ margin: 0, fontSize: 18, fontWeight: 800, color: '#0F172A' }}>
                    Connect Upstox Account
                  </h3>
                  <div style={{ fontSize: 12, color: '#64748B' }}>
                    Sync live portfolio holdings via Upstox Access Token
                  </div>
                </div>
              </div>
              <button
                onClick={() => setActiveModal(null)}
                style={{
                  border: 'none',
                  background: 'none',
                  fontSize: 18,
                  cursor: 'pointer',
                  color: '#64748B',
                }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleUpstoxConnect} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#334155', marginBottom: 4 }}>
                  Upstox Access Token *
                </label>
                <textarea
                  rows={4}
                  required
                  placeholder="Paste your Upstox Bearer access token here..."
                  value={upstoxToken}
                  onChange={e => setUpstoxToken(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: 8,
                    border: '1px solid #CBD5E1',
                    fontSize: 12,
                    fontFamily: 'monospace',
                    boxSizing: 'border-box',
                    resize: 'vertical',
                  }}
                />
                <span style={{ fontSize: 11, color: '#64748B', marginTop: 3, display: 'block' }}>
                  Generated from Upstox developer dashboard or OAuth redirect.
                </span>
              </div>

              <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
                <button
                  type="button"
                  onClick={() => {
                    setActiveModal(null)
                    handleDemoSync({ id: 'upstox', name: 'Upstox' })
                  }}
                  style={{
                    padding: '10px 14px',
                    borderRadius: 8,
                    border: '1px solid #CBD5E1',
                    background: '#FFFFFF',
                    color: '#475569',
                    fontSize: 12,
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  Try Demo Instead
                </button>

                <button
                  type="submit"
                  disabled={upstoxConnecting}
                  style={{
                    flex: 1,
                    padding: '11px 16px',
                    borderRadius: 8,
                    border: 'none',
                    background: '#7B4FE0',
                    color: '#FFFFFF',
                    fontSize: 13,
                    fontWeight: 700,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 8,
                  }}
                >
                  {upstoxConnecting ? 'Fetching Upstox Holdings…' : '🚀 Import Upstox Holdings'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
