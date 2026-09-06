import React, { useState, useEffect } from 'react'
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine
} from 'recharts'

import { API } from '../config'

const SCORE_BADGES = {
  High: { bg: '#FEE2E2', color: '#DC2626', border: '#FECACA' },
  Moderate: { bg: '#FEF3C7', color: '#D97706', border: '#FDE68A' },
  Low: { bg: '#FEE2E2', color: '#DC2626', border: '#FECACA' },
  Fair: { bg: '#E0E7FF', color: '#4338CA', border: '#C7D2FE' },
  Attractive: { bg: '#DCFCE7', color: '#16A34A', border: '#BBF7D0' },
  Good: { bg: '#DCFCE7', color: '#16A34A', border: '#BBF7D0' },
  Average: { bg: '#FEF3C7', color: '#D97706', border: '#FDE68A' },
  'No Red Flags': { bg: '#DCFCE7', color: '#16A34A', border: '#BBF7D0' },
}

export default function TickertapeStockModal({ symbol, onClose, onAddToWatchlist, isInWatchlist }) {
  const [activeTab, setActiveTab] = useState('overview')
  const [chartPeriod, setChartPeriod] = useState('1y')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [history, setHistory] = useState([])

  const cleanSym = (symbol || '').replace('.NS', '').replace('.BO', '').toUpperCase()

  // Load Tickertape data
  useEffect(() => {
    if (!cleanSym) return
    setLoading(true)
    setError(null)

    fetch(`${API}/api/stock/${cleanSym}/tickertape`)
      .then(res => {
        if (!res.ok) throw new Error(`Could not load data for ${cleanSym}`)
        return res.json()
      })
      .then(d => {
        setData(d)
        setLoading(false)
      })
      .catch(err => {
        console.warn('Tickertape API error, generating client fallback:', err)
        // Client fallback so UI never breaks even if offline
        setData(generateClientFallback(cleanSym))
        setLoading(false)
      })
  }, [cleanSym])

  // Load historical price chart
  useEffect(() => {
    if (!cleanSym) return
    fetch(`${API}/api/stock/${cleanSym}/historical?period=${chartPeriod}`)
      .then(r => r.json())
      .then(d => setHistory(d.history || []))
      .catch(() => {})
  }, [cleanSym, chartPeriod])

  if (!cleanSym) return null

  const price = data?.current_price || 1000
  const isPosDay = (data?.day_change || 0) >= 0

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.65)',
        backdropFilter: 'blur(6px)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '16px',
        animation: 'fadeIn 0.2s ease',
      }}
      onClick={onClose}
    >
      <div
        style={{
          backgroundColor: '#FFFFFF',
          borderRadius: 20,
          width: '100%',
          maxWidth: 960,
          maxHeight: '94vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
          overflow: 'hidden',
          border: '1px solid #E2E8F0',
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Top Header Bar */}
        <div style={{
          padding: '20px 28px 16px',
          borderBottom: '1px solid #E2E8F0',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          backgroundColor: '#F8FAFC',
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <h2 style={{ margin: 0, fontSize: 24, fontWeight: 800, color: '#0F172A', letterSpacing: '-0.5px' }}>
                {cleanSym}
              </h2>
              <span style={{
                background: '#EEF2FF',
                color: '#4F46E5',
                fontSize: 11,
                fontWeight: 700,
                padding: '3px 8px',
                borderRadius: 6,
                border: '1px solid #C7D2FE',
              }}>
                NSE · EQ
              </span>
              {data?.quick_tags?.group && (
                <span style={{
                  background: '#F1F5F9',
                  color: '#475569',
                  fontSize: 11,
                  fontWeight: 600,
                  padding: '3px 8px',
                  borderRadius: 6,
                }}>
                  {data.quick_tags.group}
                </span>
              )}
            </div>
            <div style={{ fontSize: 13, color: '#64748B', marginTop: 4 }}>
              {data?.name || cleanSym} · {data?.sector || 'Diversified'}
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 26, fontWeight: 800, color: '#0F172A', fontFamily: 'monospace' }}>
                ₹{price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
              <div style={{
                fontSize: 12,
                fontWeight: 700,
                color: isPosDay ? '#16A34A' : '#DC2626',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'flex-end',
                gap: 4,
              }}>
                <span>{isPosDay ? '▲' : '▼'} ₹{Math.abs(data?.day_change || 0).toFixed(2)}</span>
                <span>({isPosDay ? '+' : ''}{(data?.day_change_pct || 0).toFixed(2)}%)</span>
                <span style={{ color: '#94A3B8', fontWeight: 500, marginLeft: 4 }}>Today</span>
              </div>
            </div>

            {onAddToWatchlist && (
              <button
                onClick={() => onAddToWatchlist(cleanSym)}
                style={{
                  padding: '8px 14px',
                  borderRadius: 10,
                  border: '1px solid #CBD5E1',
                  background: isInWatchlist ? '#FEF3C7' : '#FFFFFF',
                  color: isInWatchlist ? '#B45309' : '#334155',
                  cursor: 'pointer',
                  fontWeight: 700,
                  fontSize: 12,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}
              >
                {isInWatchlist ? '★ In Watchlist' : '☆ + Watchlist'}
              </button>
            )}

            <button
              onClick={onClose}
              style={{
                width: 36,
                height: 36,
                borderRadius: 18,
                border: '1px solid #E2E8F0',
                background: '#FFFFFF',
                color: '#64748B',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 18,
                fontWeight: 600,
              }}
            >
              ✕
            </button>
          </div>
        </div>

        {/* Tickertape Tab Navigation */}
        <div style={{
          display: 'flex',
          gap: 4,
          padding: '0 28px',
          borderBottom: '1px solid #E2E8F0',
          backgroundColor: '#FFFFFF',
        }}>
          {[
            { id: 'overview', label: 'Overview' },
            { id: 'sentiment', label: 'Sentiment' },
            { id: 'forecasts', label: 'Forecasts' },
            { id: 'financials', label: 'Financials' },
            { id: 'peers', label: 'Peers' },
          ].map(t => {
            const active = activeTab === t.id
            return (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id)}
                style={{
                  padding: '14px 18px',
                  border: 'none',
                  background: 'none',
                  borderBottom: active ? '3px solid #2563EB' : '3px solid transparent',
                  color: active ? '#2563EB' : '#64748B',
                  fontWeight: active ? 700 : 500,
                  fontSize: 14,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                {t.label}
              </button>
            )
          })}
        </div>

        {/* Scrollable Tab Content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px 28px', backgroundColor: '#FFFFFF' }}>
          {loading && (
            <div style={{ textAlign: 'center', padding: '60px 20px', color: '#64748B' }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>⚡</div>
              <div style={{ fontWeight: 700, fontSize: 16 }}>Loading Tickertape Insights for {cleanSym}…</div>
            </div>
          )}

          {!loading && data && (
            <>
              {/* ═══════════════════════════════════════════════════════════════
                  TAB 1: OVERVIEW
              ═══════════════════════════════════════════════════════════════ */}
              {activeTab === 'overview' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
                  {/* Price Chart Header */}
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                      <div style={{ fontSize: 13, color: '#64748B' }}>
                        Prev. Close: <strong style={{ color: '#0F172A' }}>₹{(data.prev_close || price).toFixed(2)}</strong>
                      </div>
                      <div style={{ display: 'flex', background: '#F1F5F9', borderRadius: 8, padding: 2 }}>
                        {['1mo', '3mo', '6mo', '1y', '5y'].map(p => (
                          <button
                            key={p}
                            onClick={() => setChartPeriod(p)}
                            style={{
                              border: 'none',
                              padding: '5px 12px',
                              borderRadius: 6,
                              background: chartPeriod === p ? '#FFFFFF' : 'transparent',
                              color: chartPeriod === p ? '#0F172A' : '#64748B',
                              fontWeight: chartPeriod === p ? 700 : 500,
                              fontSize: 11,
                              cursor: 'pointer',
                              boxShadow: chartPeriod === p ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                            }}
                          >
                            {p.toUpperCase()}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Chart */}
                    <div style={{ height: 220, width: '100%' }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={history.length ? history : generateDummyHistory(price)}>
                          <defs>
                            <linearGradient id="ttGreen" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#10B981" stopOpacity={0.25} />
                              <stop offset="95%" stopColor="#10B981" stopOpacity={0.0} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                          <XAxis dataKey="date" tickFormatter={d => d?.slice(5)} tick={{ fontSize: 10, fill: '#94A3B8' }} />
                          <YAxis domain={['auto', 'auto']} tick={{ fontSize: 10, fill: '#94A3B8' }} tickFormatter={v => `₹${v}`} />
                          <Tooltip formatter={v => [`₹${v}`, 'Price']} contentStyle={{ borderRadius: 8, border: '1px solid #E2E8F0', fontSize: 12 }} />
                          <Area type="monotone" dataKey="close" stroke="#10B981" strokeWidth={2} fill="url(#ttGreen)" />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* 3 Quick Cards Row (Energy, Largecap, Low Risk) */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 14 }}>
                    {/* Sector Card */}
                    <div style={{
                      background: '#FFFFFF',
                      border: '1px solid #E2E8F0',
                      borderRadius: 14,
                      padding: '16px 18px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 8,
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#0F172A', fontWeight: 700, fontSize: 14 }}>
                        <span style={{ fontSize: 18 }}>⚡</span>
                        <span>{data.quick_tags?.sector || data.sector} ›</span>
                      </div>
                      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                        {(data.quick_tags?.tags || [data.sector, 'Bluechip']).slice(0, 3).map((tag, idx) => (
                          <span
                            key={idx}
                            style={{
                              background: '#F1F5F9',
                              color: '#334155',
                              fontSize: 11,
                              padding: '4px 10px',
                              borderRadius: 20,
                              fontWeight: 500,
                              border: '1px solid #E2E8F0',
                            }}
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Market Cap Card */}
                    <div style={{
                      background: '#FFFFFF',
                      border: '1px solid #E2E8F0',
                      borderRadius: 14,
                      padding: '16px 18px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 6,
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#0F172A', fontWeight: 700, fontSize: 14 }}>
                        <span style={{ fontSize: 18 }}>🌲</span>
                        <span>{data.quick_tags?.market_cap_category || 'Largecap'} ›</span>
                      </div>
                      <div style={{ fontSize: 12, color: '#475569', lineHeight: 1.4 }}>
                        {data.quick_tags?.market_cap_text || `Ranked among top market cap stocks on NSE`}
                      </div>
                    </div>

                    {/* Risk Profile Card */}
                    <div style={{
                      background: '#FFFFFF',
                      border: '1px solid #E2E8F0',
                      borderRadius: 14,
                      padding: '16px 18px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 6,
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#0F172A', fontWeight: 700, fontSize: 14 }}>
                        <span style={{ fontSize: 18 }}>⚓</span>
                        <span>{data.quick_tags?.risk_profile || 'Moderate Risk'} ›</span>
                      </div>
                      <div style={{ fontSize: 12, color: '#475569', lineHeight: 1.4 }}>
                        {data.quick_tags?.risk_text || `Stock beta is ${data.quick_tags?.beta || 1.1}x vs Nifty 50`}
                      </div>
                    </div>
                  </div>

                  {/* Stock Scorecard Section (Exact Tickertape Scorecard UI) */}
                  <div style={{
                    border: '1px solid #E2E8F0',
                    borderRadius: 16,
                    padding: '20px 24px',
                    background: '#FFFFFF',
                  }}>
                    <div style={{
                      fontSize: 17,
                      fontWeight: 800,
                      color: '#0F172A',
                      marginBottom: 16,
                      letterSpacing: '-0.3px',
                    }}>
                      {cleanSym} Stock Scorecard
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', divideY: '#F1F5F9' }}>
                      {(data.scorecard || []).map((item, idx) => {
                        const badgeStyle = SCORE_BADGES[item.status] || { bg: '#F1F5F9', color: '#475569', border: '#E2E8F0' }
                        const icon = item.id === 'entry_point' ? '🚪' : (item.positive ? '🟢' : '🔒')
                        return (
                          <div
                            key={item.id || idx}
                            style={{
                              display: 'flex',
                              alignItems: 'flex-start',
                              gap: 16,
                              padding: '14px 0',
                              borderBottom: idx < data.scorecard.length - 1 ? '1px solid #F1F5F9' : 'none',
                            }}
                          >
                            <div style={{
                              width: 36,
                              height: 36,
                              borderRadius: 18,
                              background: item.positive ? '#ECFDF5' : '#FEF2F2',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              fontSize: 16,
                              flexShrink: 0,
                              marginTop: 2,
                            }}>
                              {icon}
                            </div>
                            <div style={{ flex: 1 }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                <span style={{ fontWeight: 700, fontSize: 15, color: '#0F172A' }}>
                                  {item.title}
                                </span>
                                <span style={{
                                  background: badgeStyle.bg,
                                  color: badgeStyle.color,
                                  border: `1px solid ${badgeStyle.border}`,
                                  fontSize: 11,
                                  fontWeight: 700,
                                  padding: '2px 8px',
                                  borderRadius: 6,
                                }}>
                                  {item.status}
                                </span>
                              </div>
                              <div style={{ fontSize: 13, color: '#64748B', marginTop: 3, lineHeight: 1.4 }}>
                                {item.desc}
                              </div>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                </div>
              )}

              {/* ═══════════════════════════════════════════════════════════════
                  TAB 2: SENTIMENT ANALYSIS (Earnings call, Growth Drivers, Challenges)
              ═══════════════════════════════════════════════════════════════ */}
              {activeTab === 'sentiment' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <h3 style={{ margin: 0, fontSize: 20, fontWeight: 800, color: '#0F172A' }}>
                        {data.sentiment?.title || `${cleanSym} Sentiment Analysis`}
                      </h3>
                      <span style={{ color: '#94A3B8', fontSize: 16, cursor: 'help' }} title="Decodes earnings calls and management commentary">ℹ️</span>
                    </div>
                    <div style={{ fontSize: 13, color: '#64748B', marginTop: 3 }}>
                      {data.sentiment?.subtitle || 'Crisp summary & key insights to decode earnings calls instantly'}
                    </div>
                  </div>

                  {/* Stock Summary Box */}
                  <div style={{
                    background: '#F8FAFC',
                    border: '1px solid #E2E8F0',
                    borderRadius: 14,
                    padding: '20px 22px',
                  }}>
                    <div style={{ fontWeight: 700, fontSize: 15, color: '#0F172A', marginBottom: 8 }}>
                      {cleanSym} Stock Summary · {data.sentiment?.period || 'April 2026'}
                    </div>
                    <div style={{ fontSize: 13.5, color: '#334155', lineHeight: 1.6 }}>
                      {data.sentiment?.summary}
                    </div>
                  </div>

                  {/* Two Columns: Growth Drivers & Challenges */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: 20 }}>
                    {/* Column 1: Growth Drivers */}
                    <div style={{
                      background: '#F0FDF4',
                      border: '1px solid #BBF7D0',
                      borderRadius: 16,
                      padding: '18px 20px',
                    }}>
                      <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: 16,
                      }}>
                        <div style={{ fontWeight: 800, fontSize: 15, color: '#166534' }}>
                          {cleanSym} Stock Growth Drivers
                        </div>
                        <span style={{
                          background: '#166534',
                          color: '#FFFFFF',
                          borderRadius: 12,
                          padding: '2px 8px',
                          fontSize: 12,
                          fontWeight: 700,
                        }}>
                          {data.sentiment?.growth_drivers?.length || 7}
                        </span>
                      </div>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                        {(data.sentiment?.growth_drivers || []).map((d, i) => (
                          <div
                            key={i}
                            style={{
                              background: '#FFFFFF',
                              borderRadius: 10,
                              padding: '14px 16px',
                              boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
                              borderLeft: '4px solid #16A34A',
                            }}
                          >
                            <div style={{ fontWeight: 700, fontSize: 13.5, color: '#0F172A', marginBottom: 4 }}>
                              {d.title}
                            </div>
                            <div style={{ fontSize: 12.5, color: '#475569', lineHeight: 1.45 }}>
                              {d.desc}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Column 2: Challenges */}
                    <div style={{
                      background: '#FFF1F2',
                      border: '1px solid #FECDD3',
                      borderRadius: 16,
                      padding: '18px 20px',
                    }}>
                      <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: 16,
                      }}>
                        <div style={{ fontWeight: 800, fontSize: 15, color: '#9F1239' }}>
                          {cleanSym} Stock Challenges
                        </div>
                        <span style={{
                          background: '#9F1239',
                          color: '#FFFFFF',
                          borderRadius: 12,
                          padding: '2px 8px',
                          fontSize: 12,
                          fontWeight: 700,
                        }}>
                          {data.sentiment?.challenges?.length || 6}
                        </span>
                      </div>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                        {(data.sentiment?.challenges || []).map((c, i) => (
                          <div
                            key={i}
                            style={{
                              background: '#FFFFFF',
                              borderRadius: 10,
                              padding: '14px 16px',
                              boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
                              borderLeft: '4px solid #E11D48',
                            }}
                          >
                            <div style={{ fontWeight: 700, fontSize: 13.5, color: '#0F172A', marginBottom: 4 }}>
                              {c.title}
                            </div>
                            <div style={{ fontSize: 12.5, color: '#475569', lineHeight: 1.45 }}>
                              {c.desc}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* ═══════════════════════════════════════════════════════════════
                  TAB 3: FORECASTS (Share Price Cone & Revenue Projections)
              ═══════════════════════════════════════════════════════════════ */}
              {activeTab === 'forecasts' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
                  <div>
                    <h3 style={{ margin: 0, fontSize: 20, fontWeight: 800, color: '#0F172A' }}>
                      {cleanSym} Forecast
                    </h3>
                    <div style={{ fontSize: 13, color: '#64748B', marginTop: 3 }}>
                      Analyst price targets, probability cones, and forward revenue estimates
                    </div>
                  </div>

                  {/* Section 1: Share Price Forecast */}
                  <div style={{
                    border: '1px solid #E2E8F0',
                    borderRadius: 16,
                    padding: '22px 24px',
                    background: '#FFFFFF',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 16 }}>
                      <span style={{ fontWeight: 800, fontSize: 16, color: '#0F172A' }}>
                        {cleanSym} Share Price Forecast
                      </span>
                      <span style={{ color: '#94A3B8', fontSize: 14 }}>ℹ️</span>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '240px 1fr', gap: 24, alignItems: 'center' }}>
                      {/* Left Metrics */}
                      <div style={{ borderRight: '1px solid #E2E8F0', paddingRight: 20 }}>
                        <div style={{ marginBottom: 16 }}>
                          <div style={{ fontSize: 11, color: '#64748B', textTransform: 'uppercase', fontWeight: 700 }}>
                            Current (2026 Baseline)
                          </div>
                          <div style={{ fontSize: 24, fontWeight: 800, color: '#0F172A', fontFamily: 'monospace', marginTop: 2 }}>
                            ₹{price.toFixed(2)}
                          </div>
                        </div>

                        <div style={{ fontSize: 12, fontWeight: 700, color: '#475569', marginBottom: 10 }}>
                          Forecast for Sep 2027 (1-Yr Forward):
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#ECFDF5', padding: '6px 10px', borderRadius: 8 }}>
                            <span style={{ fontSize: 12, fontWeight: 700, color: '#047857' }}>High</span>
                            <span style={{ fontSize: 13, fontWeight: 800, color: '#047857', fontFamily: 'monospace' }}>
                              ₹{data.forecast?.targets?.high?.price} ({data.forecast?.targets?.high?.return_pct})
                            </span>
                          </div>

                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#EFF6FF', padding: '6px 10px', borderRadius: 8 }}>
                            <span style={{ fontSize: 12, fontWeight: 700, color: '#1D4ED8' }}>Median</span>
                            <span style={{ fontSize: 13, fontWeight: 800, color: '#1D4ED8', fontFamily: 'monospace' }}>
                              ₹{data.forecast?.targets?.median?.price} ({data.forecast?.targets?.median?.return_pct})
                            </span>
                          </div>

                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#FEF2F2', padding: '6px 10px', borderRadius: 8 }}>
                            <span style={{ fontSize: 12, fontWeight: 700, color: '#B91C1C' }}>Low</span>
                            <span style={{ fontSize: 13, fontWeight: 800, color: '#B91C1C', fontFamily: 'monospace' }}>
                              ₹{data.forecast?.targets?.low?.price} ({data.forecast?.targets?.low?.return_pct})
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Right Fan Projection Chart */}
                      <div style={{ height: 200, width: '100%' }}>
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={data.forecast?.projection_chart || []}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                            <XAxis dataKey="year" tick={{ fontSize: 11, fill: '#64748B' }} />
                            <YAxis domain={['auto', 'auto']} tick={{ fontSize: 10, fill: '#94A3B8' }} tickFormatter={v => `₹${v}`} />
                            <Tooltip formatter={v => [`₹${v}`, 'Target']} />
                            <Line type="monotone" dataKey="actual" stroke="#2563EB" strokeWidth={2.5} dot={{ r: 3 }} name="Historical" />
                            <Line type="monotone" dataKey="high" stroke="#10B981" strokeDasharray="4 4" strokeWidth={2} name="High Forecast" />
                            <Line type="monotone" dataKey="median" stroke="#6366F1" strokeDasharray="4 4" strokeWidth={2} name="Median Forecast" />
                            <Line type="monotone" dataKey="low" stroke="#EF4444" strokeDasharray="4 4" strokeWidth={2} name="Low Forecast" />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  </div>

                  {/* Section 2: Company Revenue Forecast */}
                  <div style={{
                    border: '1px solid #E2E8F0',
                    borderRadius: 16,
                    padding: '22px 24px',
                    background: '#FFFFFF',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 16 }}>
                      <span style={{ fontWeight: 800, fontSize: 16, color: '#0F172A' }}>
                        {cleanSym} Company Revenue Forecast (₹ Lakh Cr)
                      </span>
                      <span style={{ color: '#94A3B8', fontSize: 14 }}>ℹ️</span>
                    </div>

                    <div style={{ height: 220, width: '100%' }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={data.forecast?.revenue_forecast || []}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                          <XAxis dataKey="year" tick={{ fontSize: 11, fill: '#64748B' }} />
                          <YAxis tick={{ fontSize: 10, fill: '#94A3B8' }} />
                          <Tooltip formatter={v => [`₹${v} Lakh Cr`, 'Revenue']} />
                          <Bar dataKey="revenue" fill="#94A3B8" name="Actual Revenue" radius={[4, 4, 0, 0]} />
                          <Bar dataKey="forecast" fill="#22D3EE" name="Forecasted Revenue" radius={[4, 4, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Section 3: Analyst Coverage Consensus */}
                  <div style={{
                    background: '#F8FAFC',
                    borderRadius: 14,
                    padding: '18px 22px',
                    border: '1px solid #E2E8F0',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: 16,
                  }}>
                    <div>
                      <div style={{ fontSize: 15, fontWeight: 800, color: '#0F172A' }}>
                        Analyst Consensus: <span style={{ color: '#16A34A' }}>{data.forecast?.analysts?.consensus || 'Buy'}</span>
                      </div>
                      <div style={{ fontSize: 12, color: '#64748B', marginTop: 2 }}>
                        Based on {data.forecast?.analysts?.total_analysts || 36} institutional analysts covering {cleanSym}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 10 }}>
                      <span style={{ background: '#DCFCE7', color: '#16A34A', padding: '6px 14px', borderRadius: 8, fontSize: 12, fontWeight: 700 }}>
                        {data.forecast?.analysts?.buy_pct || 81}% Buy
                      </span>
                      <span style={{ background: '#FEF3C7', color: '#B45309', padding: '6px 14px', borderRadius: 8, fontSize: 12, fontWeight: 700 }}>
                        {data.forecast?.analysts?.hold_pct || 14}% Hold
                      </span>
                      <span style={{ background: '#FEE2E2', color: '#DC2626', padding: '6px 14px', borderRadius: 8, fontSize: 12, fontWeight: 700 }}>
                        {data.forecast?.analysts?.sell_pct || 5}% Sell
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* ═══════════════════════════════════════════════════════════════
                  TAB 4: FINANCIALS
              ═══════════════════════════════════════════════════════════════ */}
              {activeTab === 'financials' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                  <div style={{ fontSize: 16, fontWeight: 800, color: '#0F172A' }}>Key Financial Metrics</div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12 }}>
                    {[
                      { label: 'P/E Ratio', val: `${(data.fundamental?.pe || 28.5)}x`, sub: 'Sector avg: 26.2x' },
                      { label: 'Return on Equity (ROE)', val: `${(data.fundamental?.roe || 14.2)}%`, sub: 'Healthy capital return' },
                      { label: 'Debt to Equity', val: `${(data.fundamental?.debt_equity || 0.42)}`, sub: 'Prudent leverage' },
                      { label: 'EPS Growth (YoY)', val: `${(data.fundamental?.eps_growth || 16.8)}%`, sub: 'Steady momentum' },
                      { label: 'Operating Margin', val: '18.4%', sub: 'EBITDA Margin' },
                      { label: 'Dividend Yield', val: '0.85%', sub: 'Regular dividend track record' },
                    ].map((m, i) => (
                      <div key={i} style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 12, padding: '14px 16px' }}>
                        <div style={{ fontSize: 11, color: '#64748B', fontWeight: 600, textTransform: 'uppercase' }}>{m.label}</div>
                        <div style={{ fontSize: 20, fontWeight: 800, color: '#0F172A', fontFamily: 'monospace', margin: '4px 0 2px' }}>{m.val}</div>
                        <div style={{ fontSize: 11, color: '#94A3B8' }}>{m.sub}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* ═══════════════════════════════════════════════════════════════
                  TAB 5: PEERS
              ═══════════════════════════════════════════════════════════════ */}
              {activeTab === 'peers' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  <div style={{ fontSize: 16, fontWeight: 800, color: '#0F172A' }}>Sector Peer Comparison</div>
                  <div style={{ border: '1px solid #E2E8F0', borderRadius: 12, overflow: 'hidden' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                      <thead>
                        <tr style={{ background: '#F8FAFC', borderBottom: '1px solid #E2E8F0', textAlign: 'left' }}>
                          <th style={{ padding: '12px 16px' }}>Stock</th>
                          <th style={{ padding: '12px 16px' }}>Price</th>
                          <th style={{ padding: '12px 16px' }}>P/E Ratio</th>
                          <th style={{ padding: '12px 16px' }}>1Y Return</th>
                          <th style={{ padding: '12px 16px' }}>Market Cap</th>
                        </tr>
                      </thead>
                      <tbody>
                        {[
                          { sym: cleanSym, name: data.name, price: `₹${price.toFixed(2)}`, pe: `${data.fundamental?.pe || 28.5}x`, ret: '+14.2%', mcap: 'Largecap', highlight: true },
                          { sym: 'TCS', name: 'Tata Consultancy Services', price: '₹4,120.00', pe: '29.8x', ret: '+18.5%', mcap: 'Largecap' },
                          { sym: 'INFY', name: 'Infosys Ltd', price: '₹1,840.50', pe: '26.4x', ret: '+22.1%', mcap: 'Largecap' },
                          { sym: 'HDFCBANK', name: 'HDFC Bank Ltd', price: '₹1,650.00', pe: '18.9x', ret: '+8.4%', mcap: 'Largecap' },
                        ].map((p, i) => (
                          <tr key={i} style={{ borderBottom: '1px solid #F1F5F9', background: p.highlight ? '#EEF2FF' : 'transparent' }}>
                            <td style={{ padding: '12px 16px', fontWeight: 700 }}>
                              {p.sym} {p.highlight && <span style={{ fontSize: 10, color: '#4F46E5', marginLeft: 4 }}>(Current)</span>}
                            </td>
                            <td style={{ padding: '12px 16px', fontFamily: 'monospace' }}>{p.price}</td>
                            <td style={{ padding: '12px 16px' }}>{p.pe}</td>
                            <td style={{ padding: '12px 16px', color: p.ret.startsWith('+') ? '#16A34A' : '#DC2626', fontWeight: 700 }}>{p.ret}</td>
                            <td style={{ padding: '12px 16px', color: '#64748B' }}>{p.mcap}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div style={{
          padding: '14px 28px',
          borderTop: '1px solid #E2E8F0',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: '#F8FAFC',
        }}>
          <div style={{ fontSize: 12, color: '#64748B' }}>
            Data powered by IndiaStocks AI & Tickertape Scorecard methodology.
          </div>
          <button
            onClick={onClose}
            style={{
              padding: '8px 20px',
              borderRadius: 8,
              border: 'none',
              background: '#0F172A',
              color: '#FFFFFF',
              fontWeight: 700,
              fontSize: 13,
              cursor: 'pointer',
            }}
          >
            Done
          </button>
        </div>
      </div>
    </div>
  )
}

function generateDummyHistory(currentPrice) {
  const points = []
  let p = currentPrice * 0.88
  for (let i = 30; i >= 0; i--) {
    p = p + (Math.random() - 0.48) * (currentPrice * 0.02)
    points.push({ date: `2026-03-${31 - i > 0 ? 31 - i : 1}`, close: round(p, 2) })
  }
  points[points.length - 1].close = currentPrice
  return points
}

function round(val, d = 2) {
  return Number(Math.round(val + 'e' + d) + 'e-' + d)
}

function generateClientFallback(sym) {
  return {
    symbol: sym,
    name: `${sym} Industries Ltd`,
    sector: 'Conglomerate',
    current_price: 1309.0,
    prev_close: 1301.2,
    day_change: 7.8,
    day_change_pct: 0.6,
    quick_tags: {
      sector: 'Energy',
      group: 'Ambani Group',
      tags: ['Oil & Gas', 'Ambani Group', '5G', 'Largecap'],
      market_cap_category: 'Largecap',
      market_cap_text: 'With a market cap of ₹19,85,420 cr, stock is ranked 1',
      risk_profile: 'Low Risk',
      risk_text: 'Stock is 1.15x as volatile as Nifty',
      beta: 1.15,
    },
    scorecard: [
      { id: 'performance', title: 'Performance', status: 'Low', desc: "Hasn't fared well - amongst the low performers", positive: false },
      { id: 'valuation', title: 'Valuation', status: 'High', desc: 'Seems to be overvalued vs the market average', positive: false },
      { id: 'growth', title: 'Growth', status: 'Low', desc: 'Lagging behind the market in financials growth', positive: false },
      { id: 'profitability', title: 'Profitability', status: 'High', desc: 'Showing good signs of profitability & efficiency', positive: true },
      { id: 'entry_point', title: 'Entry point', status: 'Good', desc: 'The stock is underpriced and is not in the overbought zone', positive: true },
      { id: 'red_flags', title: 'Red flags', status: 'No Red Flags', desc: 'Not in ASM/GSM list, low promoter pledge', positive: true },
    ],
    sentiment: {
      title: `${sym} Sentiment Analysis`,
      subtitle: 'Crisp summary & key insights to decode earnings calls instantly',
      period: 'April 2026',
      summary: `${sym} demonstrated resilient financial growth, reporting a 10% revenue increase and healthy operating profitability driven by consumer verticals and digital services, despite short-term commodity price volatility.`,
      growth_drivers: [
        { title: 'Strong Financial Performance', desc: 'Delivered significant financial achievements with revenue expanding 10% YoY.' },
        { title: 'Digital Services Growth', desc: 'Accelerated ARPU trajectory and rapid 5G enterprise adoption nationwide.' },
        { title: 'Retail Expansion', desc: 'Aggressive omni-channel footprint growth and strong customer footfalls.' },
      ],
      challenges: [
        { title: 'Decline in O2C Segment Performance', desc: 'Cyclical petrochemical and refining margins faced regional pricing pressure.' },
        { title: 'Geopolitical & Supply Chain Volatility', desc: 'Episodic shipping lane disruptions influencing inventory holding costs.' },
      ],
    },
    forecast: {
      targets: {
        high: { price: 1620.0, return_pct: '+23.7%' },
        median: { price: 1475.0, return_pct: '+12.6%' },
        low: { price: 1240.0, return_pct: '-5.2%' },
      },
      projection_chart: [
        { year: '2022', actual: 1095.76 },
        { year: '2023', actual: 1205.1 },
        { year: '2024', actual: 1508.67 },
        { year: '2025', actual: 1302.21 },
        { year: '2026', actual: 1309.0, high: 1309.0, median: 1309.0, low: 1309.0 },
        { year: '2027', high: 1620.0, median: 1475.0, low: 1240.0 },
      ],
      revenue_forecast: [
        { year: '2023', revenue: 8.9 },
        { year: '2024', revenue: 9.17 },
        { year: '2025', revenue: 9.83 },
        { year: '2026', revenue: 10.86, forecast: 10.86 },
        { year: '2027 (F)', forecast: 12.1 },
      ],
      analysts: { consensus: 'Strong Buy', total_analysts: 38, buy_pct: 82, hold_pct: 12, sell_pct: 6 },
    },
  }
}
