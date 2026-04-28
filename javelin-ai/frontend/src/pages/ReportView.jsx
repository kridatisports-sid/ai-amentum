// src/pages/ReportView.jsx
import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from 'recharts'
import ReactPlayer from 'react-player'
import { Download, ChevronLeft, AlertTriangle, CheckCircle, Trophy } from 'lucide-react'
import api from '../utils/api'

export default function ReportView() {
  const { videoId }   = useParams()
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')
  const [activeTab, setTab]   = useState('overview')

  useEffect(() => {
    const load = async () => {
      try {
        const { data } = await api.get(`/report/${videoId}`)
        setReport(data)
      } catch (e) {
        setError(e.response?.data?.detail || 'Report not found.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [videoId])

  if (loading) return <LoadingState />
  if (error)   return <ErrorState msg={error} />
  if (!report) return null

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: '40px 24px' }}>
      {/* ── Header ── */}
      <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }}
        style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 40 }}
      >
        <div>
          <Link to="/dashboard" style={{ color: '#555', fontSize: 12, letterSpacing: 1, textDecoration: 'none',
            display: 'flex', alignItems: 'center', gap: 4, marginBottom: 12 }}>
            <ChevronLeft size={14} /> DASHBOARD
          </Link>
          <h1 style={{ fontSize: 26, fontWeight: 700, color: '#fff', letterSpacing: 2, margin: 0 }}>
            ANALYSIS REPORT
          </h1>
          <p style={{ color: '#555', fontSize: 11, letterSpacing: 1, marginTop: 4 }}>
            {videoId.slice(0, 8).toUpperCase()} · {new Date(report.created_at).toLocaleString()}
          </p>
        </div>

        <div style={{ display: 'flex', gap: 10 }}>
          <a href={report.pdf_url} target="_blank" rel="noreferrer">
            <ActionBtn icon={<Download size={14} />} label="PDF" />
          </a>
        </div>
      </motion.div>

      {/* ── Score Hero ── */}
      <motion.div initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.1 }}
        style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: 32,
          background: '#0D0D0D', border: '1px solid #1E1E1E', borderRadius: 12, padding: 32, marginBottom: 32 }}
      >
        <ScoreDial score={report.overall_score} grade={report.grade} />

        <div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
            <StatBox label="Release Angle" value={`${report.release_angle ?? '—'}°`}
              ideal="30–36°" ok={report.release_angle >= 30 && report.release_angle <= 36} />
            <StatBox label="Duration" value={`${report.duration_sec?.toFixed(1)}s`} />
            <StatBox label="Tier" value={report.tier?.toUpperCase()} gold />
          </div>

          {/* Section radar */}
          <div style={{ marginTop: 20 }}>
            <SectionRadar sections={report.sections} />
          </div>
        </div>
      </motion.div>

      {/* ── Tabs ── */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 24 }}>
        {['overview', 'video', 'angles', 'narrative'].map(tab => (
          <button key={tab} onClick={() => setTab(tab)} style={{
            padding: '8px 18px', borderRadius: 4, border: 'none', cursor: 'pointer',
            fontFamily: '"IBM Plex Mono", monospace', fontSize: 11, letterSpacing: 2,
            fontWeight: activeTab === tab ? 700 : 400,
            color:      activeTab === tab ? '#0A0A0A' : '#666',
            background: activeTab === tab ? '#C9A84C' : '#111',
            transition: 'all 0.2s',
          }}>
            {tab.toUpperCase()}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {activeTab === 'overview' && <OverviewTab key="ov" report={report} />}
        {activeTab === 'video'    && <VideoTab    key="vd" report={report} />}
        {activeTab === 'angles'   && <AnglesTab   key="an" report={report} />}
        {activeTab === 'narrative' && <NarrativeTab key="nr" report={report} />}
      </AnimatePresence>
    </div>
  )
}

// ── Tabs ──────────────────────────────────────────────────────────────────────

import { AnimatePresence } from 'framer-motion'

function OverviewTab({ report }) {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        {/* Section scores */}
        <Card title="SECTION SCORES">
          {report.sections.map(s => (
            <SectionRow key={s.name} section={s} />
          ))}
        </Card>

        {/* Issues */}
        <div>
          <Card title="IDENTIFIED ISSUES">
            {report.issues?.length ? report.issues.map((issue, i) => (
              <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
                <AlertTriangle size={14} color="#f44336" style={{ flexShrink: 0, marginTop: 2 }} />
                <p style={{ fontSize: 12, color: '#ccc', margin: 0, lineHeight: 1.5 }}>{issue}</p>
              </div>
            )) : (
              <p style={{ color: '#4CAF50', fontSize: 12 }}>No major issues detected. ✓</p>
            )}
          </Card>

          <Card title="RECOMMENDATIONS" style={{ marginTop: 24 }}>
            {report.recommendations?.map((rec, i) => (
              <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
                <CheckCircle size={14} color="#C9A84C" style={{ flexShrink: 0, marginTop: 2 }} />
                <p style={{ fontSize: 12, color: '#ccc', margin: 0, lineHeight: 1.5 }}>{rec}</p>
              </div>
            ))}
          </Card>
        </div>
      </div>

      {/* Key frames */}
      {report.keyframe_urls && Object.keys(report.keyframe_urls).length > 0 && (
        <Card title="KEY FRAMES" style={{ marginTop: 24 }}>
          <div style={{ display: 'flex', gap: 12, overflowX: 'auto', paddingBottom: 8 }}>
            {Object.entries(report.keyframe_urls).map(([phase, url]) => (
              <div key={phase} style={{ flexShrink: 0, textAlign: 'center' }}>
                <img src={url} alt={phase} style={{ width: 160, height: 100, objectFit: 'cover',
                  borderRadius: 6, border: '1px solid #2A2A2A' }} />
                <p style={{ fontSize: 10, color: '#666', marginTop: 4, letterSpacing: 1 }}>
                  {phase.replace('_', ' ').toUpperCase()}
                </p>
              </div>
            ))}
          </div>
        </Card>
      )}
    </motion.div>
  )
}

function VideoTab({ report }) {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        {report.overlay_url && (
          <Card title="POSE OVERLAY (AI ANNOTATED)">
            <ReactPlayer url={report.overlay_url} controls width="100%" height="auto"
              style={{ borderRadius: 6, overflow: 'hidden' }} />
          </Card>
        )}
        {report.storage_url && (
          <Card title="ORIGINAL VIDEO">
            <ReactPlayer url={report.storage_url} controls width="100%" height="auto"
              style={{ borderRadius: 6, overflow: 'hidden' }} />
          </Card>
        )}
      </div>
    </motion.div>
  )
}

function AnglesTab({ report }) {
  const ts = report.angle_timeseries || {}
  const keyAngles = report.key_angles || {}

  const IDEAL_RANGES = {
    right_elbow:              [155, 180],
    right_shoulder_abduction: [70,  110],
    arm_release_angle:        [30,  36],
    hip_separation:           [85,  110],
    trunk_lean:               [0,   20],
    right_knee:               [160, 180],
  }

  const LABELS = {
    right_elbow:              'Elbow (Right)',
    right_shoulder_abduction: 'Shoulder Abduction',
    arm_release_angle:        'Release Angle',
    hip_separation:           'Hip-Shoulder Sep.',
    trunk_lean:               'Trunk Lean',
    right_knee:               'Block Leg',
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      {/* Angles at release */}
      <Card title="ANGLES AT RELEASE FRAME">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
          {Object.entries(IDEAL_RANGES).map(([key, [lo, hi]]) => {
            const val = keyAngles[key]
            const ok  = val != null && val >= lo && val <= hi
            return (
              <div key={key} style={{ background: '#0A0A0A', borderRadius: 6, padding: 14,
                border: `1px solid ${ok ? '#2E7D3240' : val != null ? '#f4433640' : '#2A2A2A'}` }}>
                <p style={{ fontSize: 9, letterSpacing: 2, color: '#555', margin: '0 0 6px' }}>
                  {LABELS[key]?.toUpperCase()}
                </p>
                <p style={{ fontSize: 24, fontWeight: 700, color: ok ? '#4CAF50' : '#f44336', margin: 0 }}>
                  {val != null ? `${val}°` : '—'}
                </p>
                <p style={{ fontSize: 10, color: '#444', margin: '4px 0 0' }}>
                  Ideal: {lo}–{hi}°
                </p>
              </div>
            )
          })}
        </div>
      </Card>

      {/* Angle time-series charts */}
      {Object.entries(LABELS).filter(([k]) => ts[k]).slice(0, 4).map(([key, label]) => {
        const data = (ts[key] || []).map((v, i) => ({ frame: i, value: v })).filter(d => d.value != null)
        return (
          <Card key={key} title={`${label.toUpperCase()} OVER TIME`} style={{ marginTop: 24 }}>
            <ResponsiveContainer width="100%" height={160}>
              <LineChart data={data} margin={{ top: 0, right: 16, left: -20, bottom: 0 }}>
                <XAxis dataKey="frame" tick={{ fontSize: 9, fill: '#444' }} />
                <YAxis tick={{ fontSize: 9, fill: '#444' }} />
                <Tooltip contentStyle={{ background: '#111', border: '1px solid #2A2A2A',
                  fontSize: 11, color: '#ccc' }} />
                <Line type="monotone" dataKey="value" dot={false}
                  stroke="#C9A84C" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        )
      })}
    </motion.div>
  )
}

function NarrativeTab({ report }) {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <Card title="AI COACH NARRATIVE">
        {report.ai_narrative?.split('\n\n').map((para, i) => (
          <p key={i} style={{ fontSize: 13, color: '#ccc', lineHeight: 1.8,
            marginBottom: 16, borderLeft: '2px solid #C9A84C33', paddingLeft: 16 }}>
            {para}
          </p>
        ))}
      </Card>

      {report.tier === 'premium' && (
        <Card title="HUMAN COACH NOTES" style={{ marginTop: 24 }}>
          {report.coach_reviewed ? (
            <div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 12 }}>
                <Trophy size={16} color="#C9A84C" />
                <span style={{ fontSize: 11, color: '#C9A84C', letterSpacing: 1 }}>
                  REVIEWED BY CERTIFIED COACH
                </span>
              </div>
              <p style={{ fontSize: 13, color: '#ccc', lineHeight: 1.8 }}>
                {report.coach_notes || 'Notes pending.'}
              </p>
            </div>
          ) : (
            <p style={{ color: '#666', fontSize: 12 }}>
              ⏳ Coach review in progress — typically within 48 hours.
            </p>
          )}
        </Card>
      )}
    </motion.div>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

function ScoreDial({ score, grade }) {
  const colour = score >= 80 ? '#4CAF50' : score >= 60 ? '#C9A84C' : '#f44336'
  const pct    = score / 100
  const r      = 52
  const circ   = 2 * Math.PI * r
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
      <svg width={130} height={130}>
        <circle cx={65} cy={65} r={r} fill="none" stroke="#1E1E1E" strokeWidth={8} />
        <circle cx={65} cy={65} r={r} fill="none" stroke={colour} strokeWidth={8}
          strokeDasharray={circ} strokeDashoffset={circ * (1 - pct)}
          strokeLinecap="round" transform="rotate(-90 65 65)"
          style={{ transition: 'stroke-dashoffset 1.5s ease' }} />
        <text x={65} y={58} textAnchor="middle" fill={colour}
          style={{ fontSize: 28, fontWeight: 700, fontFamily: 'monospace' }}>
          {Math.round(score)}
        </text>
        <text x={65} y={76} textAnchor="middle" fill="#555"
          style={{ fontSize: 10, fontFamily: 'monospace', letterSpacing: 1 }}>
          / 100
        </text>
      </svg>
      <p style={{ color: colour, fontSize: 12, letterSpacing: 3, fontWeight: 700, margin: '8px 0 0' }}>
        {grade.toUpperCase()}
      </p>
    </div>
  )
}

function SectionRadar({ sections }) {
  if (!sections?.length) return null
  const data = sections.map(s => ({ subject: s.name.split(' ')[0], score: Math.round(s.score) }))
  return (
    <ResponsiveContainer width="100%" height={160}>
      <RadarChart data={data} margin={{ top: 0, right: 20, bottom: 0, left: 20 }}>
        <PolarGrid stroke="#2A2A2A" />
        <PolarAngleAxis dataKey="subject" tick={{ fontSize: 10, fill: '#666' }} />
        <Radar dataKey="score" stroke="#C9A84C" fill="#C9A84C" fillOpacity={0.15} strokeWidth={2} />
      </RadarChart>
    </ResponsiveContainer>
  )
}

function SectionRow({ section }) {
  const colour = section.score >= 70 ? '#4CAF50' : section.score >= 50 ? '#C9A84C' : '#f44336'
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontSize: 11, color: '#aaa', letterSpacing: 1 }}>{section.name.toUpperCase()}</span>
        <span style={{ fontSize: 11, color: colour, fontWeight: 700 }}>{Math.round(section.score)}/100</span>
      </div>
      <div style={{ height: 4, background: '#1E1E1E', borderRadius: 2 }}>
        <div style={{
          height: '100%', width: `${section.score}%`, background: colour, borderRadius: 2,
          transition: 'width 1s ease',
        }} />
      </div>
    </div>
  )
}

function StatBox({ label, value, ideal, ok, gold }) {
  const colour = gold ? '#C9A84C' : ok === undefined ? '#fff' : ok ? '#4CAF50' : '#f44336'
  return (
    <div style={{ background: '#111', borderRadius: 6, padding: '12px 16px', border: '1px solid #1E1E1E' }}>
      <p style={{ fontSize: 9, letterSpacing: 2, color: '#555', margin: '0 0 4px' }}>{label.toUpperCase()}</p>
      <p style={{ fontSize: 22, fontWeight: 700, color: colour, margin: 0 }}>{value}</p>
      {ideal && <p style={{ fontSize: 9, color: '#444', margin: '4px 0 0' }}>ideal: {ideal}</p>}
    </div>
  )
}

function Card({ title, children, style }) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
      style={{ background: '#0D0D0D', border: '1px solid #1E1E1E', borderRadius: 10, padding: 24, ...style }}>
      {title && (
        <p style={{ fontSize: 10, letterSpacing: 3, color: '#555', fontWeight: 700, marginBottom: 16 }}>
          {title}
        </p>
      )}
      {children}
    </motion.div>
  )
}

function ActionBtn({ icon, label }) {
  return (
    <button style={{
      display: 'flex', alignItems: 'center', gap: 6,
      padding: '8px 16px', borderRadius: 6, background: '#111',
      border: '1px solid #C9A84C40', color: '#C9A84C',
      fontFamily: '"IBM Plex Mono", monospace', fontSize: 11,
      letterSpacing: 2, cursor: 'pointer',
    }}>
      {icon} {label}
    </button>
  )
}

function LoadingState() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center',
      height: '60vh', flexDirection: 'column', gap: 16 }}>
      <div style={{ width: 48, height: 48, border: '3px solid #C9A84C',
        borderTopColor: 'transparent', borderRadius: '50%',
        animation: 'spin 0.8s linear infinite' }} />
      <p style={{ color: '#555', fontSize: 12, letterSpacing: 2 }}>LOADING REPORT …</p>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}

function ErrorState({ msg }) {
  return (
    <div style={{ maxWidth: 500, margin: '80px auto', textAlign: 'center' }}>
      <AlertTriangle size={40} color="#f44336" />
      <p style={{ color: '#f44336', marginTop: 12 }}>{msg}</p>
      <Link to="/dashboard" style={{ color: '#C9A84C', fontSize: 12, letterSpacing: 1 }}>
        ← Back to Dashboard
      </Link>
    </div>
  )
}
