import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../App'

const QUESTIONS = [
  {
    id: 'investment_horizon',
    question: 'What is your investment time horizon?',
    hint: 'How long you plan to stay invested greatly influences your ideal risk level',
    icon: '⏳',
    options: [
      { value: 'less_1', icon: '🏃', label: 'Less than 1 year', sub: 'Short-term trading' },
      { value: '1_3', icon: '📅', label: '1–3 years', sub: 'Medium-term goals' },
      { value: '3_5', icon: '🎯', label: '3–5 years', sub: 'Mid-to-long term' },
      { value: '5_10', icon: '📈', label: '5–10 years', sub: 'Long-term wealth building' },
      { value: 'over_10', icon: '🏦', label: 'More than 10 years', sub: 'Retirement or legacy' },
    ],
  },
  {
    id: 'loss_tolerance',
    question: 'How would you react if your portfolio dropped 20% in a month?',
    hint: 'Market corrections are normal — your reaction determines your true risk tolerance',
    icon: '📉',
    options: [
      { value: 'panic', icon: '😰', label: 'Sell everything immediately', sub: 'I cannot tolerate losses' },
      { value: 'concerned', icon: '😟', label: 'Sell some and wait', sub: 'Prefer to reduce exposure' },
      { value: 'tolerate', icon: '😐', label: 'Hold and monitor', sub: 'Trust the long term' },
      { value: 'comfortable', icon: '😊', label: 'Stay calm, do nothing', sub: 'Volatility is normal for me' },
      { value: 'embrace', icon: '🤩', label: 'Buy more at lower prices', sub: 'Opportunity in dips' },
    ],
  },
  {
    id: 'income_stability',
    question: 'How stable is your primary source of income?',
    hint: 'Income stability affects how much risk you can realistically absorb',
    icon: '💰',
    options: [
      { value: 'unstable', icon: '🎲', label: 'Highly variable / freelance', sub: 'Income fluctuates a lot' },
      { value: 'variable', icon: '📊', label: 'Moderate, with some variability', sub: 'Bonuses, commissions' },
      { value: 'stable', icon: '💼', label: 'Salaried / stable employment', sub: 'Regular monthly income' },
      { value: 'very_stable', icon: '🏛️', label: 'Government / very secure', sub: 'Guaranteed income' },
    ],
  },
  {
    id: 'investment_goal',
    question: 'What is your primary investment goal?',
    hint: 'Your goal shapes which assets are most suitable for you',
    icon: '🎯',
    options: [
      { value: 'capital_preservation', icon: '🛡️', label: 'Protect my money', sub: 'Capital preservation first' },
      { value: 'income', icon: '💸', label: 'Regular income / dividends', sub: 'Cash flow generation' },
      { value: 'balanced', icon: '⚖️', label: 'Balanced growth & safety', sub: 'Mix of both' },
      { value: 'growth', icon: '🌱', label: 'Long-term wealth building', sub: 'Accept moderate risk' },
      { value: 'aggressive_growth', icon: '🚀', label: 'Maximum growth potential', sub: 'Accept high volatility' },
    ],
  },
  {
    id: 'experience',
    question: 'How experienced are you with stock market investing?',
    hint: 'Experience level helps calibrate the complexity of recommendations',
    icon: '📚',
    options: [
      { value: 'none', icon: '🐣', label: 'Complete beginner', sub: 'Never invested before' },
      { value: 'beginner', icon: '📗', label: 'Beginner', sub: 'Basic knowledge, few investments' },
      { value: 'intermediate', icon: '📘', label: 'Intermediate', sub: 'Follow markets regularly' },
      { value: 'expert', icon: '📕', label: 'Advanced / Expert', sub: 'Active trader or analyst' },
    ],
  },
  {
    id: 'emergency_fund',
    question: 'Do you have an emergency fund covering 6+ months of expenses?',
    hint: 'Emergency funds ensure you don\'t need to liquidate investments during crises',
    icon: '🆘',
    options: [
      { value: 'no', icon: '❌', label: 'No emergency fund', sub: 'Investing first' },
      { value: 'partial', icon: '⚠️', label: 'Partially set aside', sub: '1–3 months covered' },
      { value: 'yes', icon: '✅', label: 'Yes, fully covered', sub: '6+ months covered' },
    ],
  },
  {
    id: 'reaction_crash',
    question: 'During a major market crash (like COVID-19 in 2020), what did you do or would you do?',
    hint: 'Past behavior under pressure is the best predictor of future reactions',
    icon: '🌊',
    options: [
      { value: 'sell_all', icon: '🏃', label: 'Sold / would sell everything', sub: 'Get to safety ASAP' },
      { value: 'sell_some', icon: '✂️', label: 'Sold / would sell some', sub: 'Partial exit to reduce risk' },
      { value: 'hold', icon: '🤲', label: 'Held / would hold', sub: 'Wait for recovery' },
      { value: 'buy_more', icon: '🛒', label: 'Bought more / would average down', sub: 'Long-term conviction' },
    ],
  },
  {
    id: 'existing_debt',
    question: 'What is your current debt situation?',
    hint: 'High-interest debt should typically be paid off before aggressive investing',
    icon: '🏦',
    options: [
      { value: 'high', icon: '🔴', label: 'High debt (credit cards, personal loans)', sub: '>40% income to EMIs' },
      { value: 'moderate', icon: '🟡', label: 'Moderate debt (home/car loan)', sub: '20–40% income to EMIs' },
      { value: 'low', icon: '🟢', label: 'Low debt', sub: '<20% income to EMIs' },
      { value: 'none', icon: '✨', label: 'Debt-free', sub: 'No EMIs' },
    ],
  },
  {
    id: 'dependants',
    question: 'How many financial dependants do you have?',
    hint: 'More dependants generally calls for more conservative investing',
    icon: '👨‍👩‍👧‍👦',
    options: [
      { value: 'many', icon: '👨‍👩‍👧‍👦', label: '3 or more dependants', sub: 'Family of 4+ depending on me' },
      { value: 'few', icon: '👨‍👩‍👦', label: '1–2 dependants', sub: 'Spouse / children / parents' },
      { value: 'none', icon: '🧑', label: 'No dependants', sub: 'Financially independent' },
    ],
  },
  {
    id: 'investment_amount',
    question: 'What portion of your monthly income do you plan to invest?',
    hint: 'Investment capacity influences how aggressive a strategy is sustainable',
    icon: '💵',
    options: [
      { value: 'small', icon: '💧', label: 'Less than 10%', sub: '₹1,000–5,000/month' },
      { value: 'moderate', icon: '🌊', label: '10–25%', sub: '₹5,000–20,000/month' },
      { value: 'large', icon: '🌊🌊', label: '25–50%', sub: '₹20,000–50,000/month' },
      { value: 'very_large', icon: '🌊🌊🌊', label: 'More than 50%', sub: 'High savings rate' },
    ],
  },
]

import { API } from '../config'

function RiskGauge({ score }) {
  const angle = (score / 100) * 180 - 90
  const r = 70
  const cx = 90; const cy = 90
  const toXY = (deg) => {
    const rad = (deg * Math.PI) / 180
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
  }
  const start = toXY(-180)
  const end = toXY(0)
  const needleEnd = toXY(angle - 90)

  const color = score < 35 ? '#0891B2' : score < 65 ? '#D97706' : '#DC2626'
  const label = score < 35 ? 'Conservative' : score < 65 ? 'Moderate' : 'Aggressive'

  return (
    <div style={{ textAlign: 'center' }}>
      <svg width={180} height={110} viewBox="0 0 180 110" className="gauge-svg">
        {/* Background arc */}
        <path d={`M ${start.x} ${start.y} A ${r} ${r} 0 0 1 ${end.x} ${end.y}`}
          fill="none" stroke="var(--clr-border)" strokeWidth={12} strokeLinecap="round" />
        {/* Color arc */}
        <path d={`M ${start.x} ${start.y} A ${r} ${r} 0 0 1 ${end.x} ${end.y}`}
          fill="none"
          stroke={`url(#gauge-grad)`}
          strokeWidth={12}
          strokeLinecap="round"
          strokeDasharray={`${score / 100 * 220} 220`}
        />
        <defs>
          <linearGradient id="gauge-grad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#0891B2" />
            <stop offset="50%" stopColor="#D97706" />
            <stop offset="100%" stopColor="#DC2626" />
          </linearGradient>
        </defs>
        {/* Needle */}
        <line x1={cx} y1={cy} x2={needleEnd.x} y2={needleEnd.y}
          stroke={color} strokeWidth={3} strokeLinecap="round" />
        <circle cx={cx} cy={cy} r={5} fill={color} />
        {/* Labels */}
        <text x={16} y={105} fontSize={9} fill="var(--clr-teal)" fontWeight={600}>Low</text>
        <text x={80} y={28} fontSize={9} fill="var(--clr-amber)" fontWeight={600}>Mid</text>
        <text x={148} y={105} fontSize={9} fill="var(--clr-red)" fontWeight={600}>High</text>
      </svg>
      <div style={{ fontSize: 36, fontWeight: 800, color, fontFamily: 'var(--font-mono)', marginTop: -8 }}>{score}</div>
      <div style={{ fontSize: 18, fontWeight: 700, color, marginTop: 2 }}>{label}</div>
      <div style={{ fontSize: 12, color: 'var(--clr-text-3)', marginTop: 4 }}>Your Risk Score</div>
    </div>
  )
}

export default function QuizPage() {
  const { saveRiskScore, setQuizAnswers } = useApp()
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [answers, setAnswers] = useState({})
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const q = QUESTIONS[step]
  const progress = (step / QUESTIONS.length) * 100
  const isDone = step === QUESTIONS.length

  const select = (val) => {
    const newAnswers = { ...answers, [q.id]: val }
    setAnswers(newAnswers)
    if (step < QUESTIONS.length - 1) {
      setTimeout(() => setStep(s => s + 1), 200)
    } else {
      // Submit
      setLoading(true)
      setStep(QUESTIONS.length)
      fetch(`${API}/api/quiz/score`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newAnswers),
      })
        .then(r => r.json())
        .then(data => {
          setResult(data)
          saveRiskScore(data.risk_score)
          setQuizAnswers(newAnswers)
          setLoading(false)
        })
        .catch(() => {
          // Fallback local scoring with 5 precise tiers
          const score = 55
          const getTier = (s) => s <= 20 ? 'Very Conservative' : s <= 40 ? 'Conservative' : s <= 60 ? 'Moderate Balanced' : s <= 80 ? 'Growth / Aggressive' : 'Very Aggressive / Speculative'
          setResult({ risk_score: score, risk_label: getTier(score) })
          saveRiskScore(score)
          setLoading(false)
        })
    }
  }

  const getTier = (s) => s <= 20 ? 'Very Conservative' : s <= 40 ? 'Conservative' : s <= 60 ? 'Moderate Balanced' : s <= 80 ? 'Growth / Aggressive' : 'Very Aggressive / Speculative'

  if (isDone) {
    return (
      <div className="quiz-container">
        <div className="page-header">
          <h1>Quiz Complete! 🎉</h1>
        </div>
        {loading ? (
          <div className="card" style={{ textAlign: 'center', padding: 48 }}>
            <div className="loading-spinner" />
            <p style={{ marginTop: 16, color: 'var(--clr-text-3)' }}>Analyzing your risk profile…</p>
          </div>
        ) : result && (
          <div className="card quiz-result">
            <RiskGauge score={result.risk_score} />
            <div style={{ marginTop: 20 }}>
              <p style={{ color: 'var(--clr-text-2)', fontSize: 14, maxWidth: 440, margin: '0 auto', lineHeight: 1.6 }}>
                Based on your answers, you have a <strong>{result.risk_label || getTier(result.risk_score)}</strong> risk appetite.
                Our AI will recommend NIFTY 500 stocks tailored to your 5-year risk-return profile.
              </p>
            </div>

            {/* Threshold fine-tuner */}
            <div style={{
              margin: '20px auto 10px',
              maxWidth: 400,
              background: 'var(--clr-surface-2)',
              borderRadius: 'var(--r-md)',
              padding: '12px 18px',
              textAlign: 'left',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, fontWeight: 700, marginBottom: 6 }}>
                <span>Fine-Tune Score:</span>
                <span style={{ color: 'var(--clr-primary)', fontFamily: 'var(--font-mono)' }}>
                  {result.risk_score}/100 ({getTier(result.risk_score)})
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={result.risk_score}
                onChange={e => {
                  const s = parseInt(e.target.value)
                  setResult({ ...result, risk_score: s, risk_label: getTier(s) })
                  saveRiskScore(s)
                }}
                style={{ width: '100%', accentColor: 'var(--clr-primary)', cursor: 'pointer' }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--clr-text-3)', marginTop: 4 }}>
                <span>0 Very Safe</span>
                <span>20</span>
                <span>40</span>
                <span>60</span>
                <span>80</span>
                <span>100 Aggressive</span>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 12, marginTop: 24, justifyContent: 'center', flexWrap: 'wrap' }}>
              <button className="btn btn-primary" onClick={() => navigate('/recommendations')}>
                🎯 View AI Recommendations →
              </button>
              <button className="btn btn-ghost" onClick={() => { setStep(0); setAnswers({}); setResult(null) }}>
                Retake Quiz
              </button>
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="quiz-container">
      <div className="page-header">
        <h1>Risk Appetite Quiz</h1>
        <p>10 questions to build your personalized investment profile</p>
      </div>

      <div className="quiz-progress">
        <div className="quiz-progress-bar" style={{ width: `${progress}%` }} />
      </div>

      <div className="quiz-step">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
          <span style={{ fontSize: 28 }}>{q.icon}</span>
          <div>
            <div className="quiz-question">{q.question}</div>
            <div className="quiz-hint">{q.hint}</div>
          </div>
        </div>

        <div className="quiz-options">
          {q.options.map(opt => (
            <button
              key={opt.value}
              className={`quiz-option ${answers[q.id] === opt.value ? 'selected' : ''}`}
              onClick={() => select(opt.value)}
            >
              <div className="quiz-opt-icon">{opt.icon}</div>
              <div>
                <div className="quiz-opt-text">{opt.label}</div>
                <div className="quiz-opt-sub">{opt.sub}</div>
              </div>
              {answers[q.id] === opt.value && (
                <span style={{ marginLeft: 'auto', color: 'var(--clr-primary)' }}>✓</span>
              )}
            </button>
          ))}
        </div>
      </div>

      <div className="quiz-nav">
        <button
          className="btn btn-ghost btn-sm"
          onClick={() => setStep(s => Math.max(0, s - 1))}
          disabled={step === 0}
        >
          ← Back
        </button>
        <span className="quiz-counter">{step + 1} / {QUESTIONS.length}</span>
        <button
          className="btn btn-ghost btn-sm"
          onClick={() => setStep(s => s + 1)}
          disabled={!answers[q.id]}
        >
          Skip →
        </button>
      </div>
    </div>
  )
}
