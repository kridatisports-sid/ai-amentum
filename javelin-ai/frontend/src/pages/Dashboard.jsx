// src/pages/Dashboard.jsx
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { Upload, FileText, TrendingUp, Clock } from 'lucide-react'
import api from '../utils/api'
import { auth } from '../utils/firebase'

export default function Dashboard() {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const user = auth.currentUser

  useEffect(() => {
    api.get('/report/user/history')
      .then(r => setHistory(r.data.history || []))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  // Trend data for improvement chart
  const trendData = [...history]
    .reverse()
    .filter(h => h.overall_score)
    .map((h, i) => ({
      name: `#${i + 1}`,
      score: h.overall_score,
      date: new Date(h.created_at).toLocaleDateString('en-IN', { day:'numeric', month:'short' }),
    }))

  const bestScore   = history.length ? Math.max(...history.map(h => h.overall_score || 0)) : 0
  const latestScore = history[0]?.overall_score || 0
  const avgScore    = history.length
    ? Math.round(history.reduce((sum, h) => sum + (h.overall_score || 0), 0) / history.length)
    : 0

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: '40px 24px' }}>
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }}
        style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 40 }}>
        <div>
          <h1 style={{ fontSize: 26, fontWeight: 700, color: '#fff', letterSpacing: 2, margin: 0 }}>
            DASHBOARD
          </h1>
          <p style={{ color: '#555', fontSize: 12, marginTop: 4 }}>
            Welcome back, {user?.displayName?.split(' ')[0] || 'Athlete'}
          </p>
        </div>
        <Link to="/upload">
          <motion.button whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}
            style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '10px 20px', background: '#C9A84C', border: 'none',
              borderRadius: 6, cursor: 'pointer', color: '#0A0A0A',
              fontFamily: '"IBM Plex Mono", monospace', fontWeight: 700,
              fontSize: 12, letterSpacing: 2,
            }}>
            <Upload size={14} /> NEW ANALYSIS
          </motion.button>
        </Link>
      </motion.div>

      {/* Stats row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 32 }}>
        {[
          { label: 'Total Analyses', value: history.length, icon: <FileText size={16} color="#C9A84C" /> },
          { label: 'Latest Score',   value: latestScore || '—', icon: <Clock size={16} color="#2196F3" /> },
          { label: 'Best Score',     value: bestScore || '—',   icon: <TrendingUp size={16} color="#4CAF50" /> },
          { label: 'Avg Score',      value: avgScore || '—',    icon: <TrendingUp size={16} color="#9C27B0" /> },
        ].map((s, i) => (
          <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
            style={{ background: '#0D0D0D', border: '1px solid #1E1E1E',
              borderRadius: 10, padding: '18px 20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
              <p style={{ fontSize: 9, letterSpacing: 2, color: '#555', margin: 0 }}>{s.label.toUpperCase()}</p>
              {s.icon}
            </div>
            <p style={{ fontSize: 30, fontWeight: 700, color: '#fff', margin: 0 }}>{s.value}</p>
          </motion.div>
        ))}
      </div>

      {/* Improvement chart */}
      {trendData.length > 1 && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}
          style={{ background: '#0D0D0D', border: '1px solid #1E1E1E', borderRadius: 10, padding: 24, marginBottom: 32 }}>
          <p style={{ fontSize: 10, letterSpacing: 3, color: '#555', marginBottom: 16, fontWeight: 700 }}>
            SCORE PROGRESSION
          </p>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={trendData} margin={{ top: 4, right: 16, left: -24, bottom: 0 }}>
              <XAxis dataKey="date" tick={{ fontSize: 9, fill: '#444' }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 9, fill: '#444' }} />
              <Tooltip contentStyle={{ background: '#111', border: '1px solid #2A2A2A',
                fontSize: 11, color: '#ccc' }} />
              <Line type="monotone" dataKey="score" stroke="#C9A84C" strokeWidth={2}
                dot={{ fill: '#C9A84C', r: 4 }} activeDot={{ r: 6 }} />
            </LineChart>
          </ResponsiveContainer>
        </motion.div>
      )}

      {/* History list */}
      <p style={{ fontSize: 10, letterSpacing: 3, color: '#555', marginBottom: 16, fontWeight: 700 }}>
        ANALYSIS HISTORY
      </p>

      {loading ? (
        <p style={{ color: '#555', fontSize: 12 }}>Loading …</p>
      ) : history.length === 0 ? (
        <EmptyState />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {history.map((item, i) => (
            <HistoryCard key={item.video_id} item={item} idx={i} />
          ))}
        </div>
      )}
    </div>
  )
}

function HistoryCard({ item, idx }) {
  const score  = item.overall_score
  const colour = score >= 80 ? '#4CAF50' : score >= 60 ? '#C9A84C' : '#f44336'
  const grade  = item.grade || '—'

  return (
    <motion.div initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
      transition={{ delay: idx * 0.04 }}
      style={{ background: '#0D0D0D', border: '1px solid #1E1E1E', borderRadius: 8,
        padding: '16px 20px', display: 'flex', alignItems: 'center', gap: 20 }}>
      {/* Score badge */}
      <div style={{ width: 52, height: 52, borderRadius: '50%',
        border: `2px solid ${colour}`, display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
        <span style={{ fontSize: 14, fontWeight: 700, color: colour }}>{Math.round(score) || '?'}</span>
        <span style={{ fontSize: 8, color: '#555' }}>/100</span>
      </div>

      {/* Info */}
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4 }}>
          <span style={{ fontSize: 12, color: '#888', letterSpacing: 1 }}>
            {item.video_id?.slice(0, 8).toUpperCase()}
          </span>
          <span style={{ fontSize: 10, color: colour, background: `${colour}15`,
            padding: '2px 8px', borderRadius: 3, letterSpacing: 1 }}>
            {grade}
          </span>
          <span style={{ fontSize: 10, color: '#444', background: '#1E1E1E',
            padding: '2px 8px', borderRadius: 3, letterSpacing: 1 }}>
            {item.tier?.toUpperCase()}
          </span>
        </div>
        <p style={{ fontSize: 11, color: '#555', margin: 0 }}>
          {new Date(item.created_at).toLocaleString('en-IN')}
          {item.release_angle ? ` · Release: ${item.release_angle}°` : ''}
        </p>
      </div>

      {/* Status / Actions */}
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        {item.status !== 'complete' && (
          <span style={{ fontSize: 10, color: '#888', letterSpacing: 1 }}>
            {item.status?.replace('_', ' ').toUpperCase()}
          </span>
        )}
        {item.status === 'complete' && (
          <Link to={`/report/${item.video_id}`}
            style={{ padding: '6px 14px', background: '#111',
              border: '1px solid #C9A84C40', borderRadius: 4, color: '#C9A84C',
              fontSize: 10, letterSpacing: 2, textDecoration: 'none' }}>
            VIEW →
          </Link>
        )}
        {item.pdf_url && (
          <a href={item.pdf_url} target="_blank" rel="noreferrer"
            style={{ padding: '6px 10px', background: '#111',
              border: '1px solid #2A2A2A', borderRadius: 4, color: '#666',
              fontSize: 10, letterSpacing: 1, textDecoration: 'none' }}>
            PDF
          </a>
        )}
      </div>
    </motion.div>
  )
}

function EmptyState() {
  return (
    <div style={{ textAlign: 'center', padding: '60px 20px',
      background: '#0D0D0D', borderRadius: 10, border: '1px dashed #1E1E1E' }}>
      <Upload size={40} color="#2A2A2A" style={{ margin: '0 auto 16px' }} />
      <p style={{ color: '#555', fontSize: 13, marginBottom: 20 }}>
        No analyses yet. Upload your first throw video.
      </p>
      <Link to="/upload">
        <button style={{
          padding: '10px 24px', background: '#C9A84C', border: 'none',
          borderRadius: 6, color: '#0A0A0A', fontWeight: 700, cursor: 'pointer',
          fontFamily: '"IBM Plex Mono", monospace', letterSpacing: 2, fontSize: 11,
        }}>
          UPLOAD VIDEO
        </button>
      </Link>
    </div>
  )
}
