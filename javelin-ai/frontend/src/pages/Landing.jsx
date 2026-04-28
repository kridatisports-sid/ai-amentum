// src/pages/Landing.jsx
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Zap, Target, BarChart2, Trophy, ChevronRight } from 'lucide-react'

export default function Landing({ user }) {
  return (
    <div style={{ fontFamily: '"IBM Plex Mono", monospace' }}>
      {/* ── Hero ── */}
      <section style={{
        minHeight: '92vh', display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', textAlign: 'center',
        padding: '60px 24px', position: 'relative', overflow: 'hidden',
      }}>
        {/* Background grid */}
        <div style={{
          position: 'absolute', inset: 0, zIndex: 0,
          backgroundImage: 'linear-gradient(#1A1A1A 1px, transparent 1px), linear-gradient(90deg, #1A1A1A 1px, transparent 1px)',
          backgroundSize: '40px 40px',
          maskImage: 'radial-gradient(ellipse 80% 60% at 50% 50%, black 0%, transparent 100%)',
        }} />

        {/* Javelin diagonal accent */}
        <div style={{
          position: 'absolute', top: '20%', left: '-10%', right: '-10%',
          height: 2, background: 'linear-gradient(90deg, transparent, #C9A84C30, transparent)',
          transform: 'rotate(-8deg)', zIndex: 0,
        }} />

        <div style={{ position: 'relative', zIndex: 1, maxWidth: 700 }}>
          <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6 }}>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8,
              padding: '6px 16px', border: '1px solid #C9A84C30', borderRadius: 20,
              marginBottom: 32, background: 'rgba(201,168,76,0.05)' }}>
              <Zap size={12} color="#C9A84C" />
              <span style={{ fontSize: 10, color: '#C9A84C', letterSpacing: 3 }}>
                POWERED BY MEDIAPIPE + CLAUDE AI
              </span>
            </div>
          </motion.div>

          <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.7 }}
            style={{ fontSize: 'clamp(36px, 6vw, 72px)', fontWeight: 700,
              lineHeight: 1.05, color: '#fff', margin: '0 0 24px',
              letterSpacing: '-1px' }}>
            THROW FARTHER.<br />
            <span style={{ color: '#C9A84C' }}>TRAIN SMARTER.</span>
          </motion.h1>

          <motion.p initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25 }}
            style={{ fontSize: 15, color: '#666', lineHeight: 1.7, marginBottom: 40, letterSpacing: 0.5 }}>
            Upload your javelin throw video. Get AI-powered biomechanical analysis,<br />
            joint angle data, and coach-grade recommendations — instantly.
          </motion.p>

          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.35 }}
            style={{ display: 'flex', gap: 16, justifyContent: 'center', flexWrap: 'wrap' }}>
            <Link to={user ? '/upload' : '/login'}>
              <motion.button whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.96 }}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '14px 32px', background: '#C9A84C', border: 'none',
                  borderRadius: 6, cursor: 'pointer', color: '#0A0A0A',
                  fontFamily: '"IBM Plex Mono", monospace', fontWeight: 700,
                  fontSize: 13, letterSpacing: 2,
                }}>
                ANALYSE YOUR THROW <ChevronRight size={16} />
              </motion.button>
            </Link>
            <Link to="#how">
              <button style={{
                padding: '14px 32px', background: 'transparent',
                border: '1px solid #2A2A2A', borderRadius: 6, cursor: 'pointer',
                color: '#888', fontFamily: '"IBM Plex Mono", monospace',
                fontSize: 13, letterSpacing: 2,
              }}>
                HOW IT WORKS
              </button>
            </Link>
          </motion.div>
        </div>
      </section>

      {/* ── Features ── */}
      <section id="how" style={{ padding: '80px 24px', maxWidth: 1000, margin: '0 auto' }}>
        <p style={{ textAlign: 'center', fontSize: 10, letterSpacing: 4, color: '#555', marginBottom: 48 }}>
          WHAT WE ANALYSE
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 20 }}>
          {[
            { icon: <Target />, title: 'Release Angle', desc: 'Ideal 30–36°. We detect your exact arm angle at the moment of release.' },
            { icon: <Zap />,    title: 'Power Position', desc: 'Hip-shoulder separation and elbow alignment through the throwing arc.' },
            { icon: <BarChart2 />, title: 'Joint Angles', desc: 'Frame-by-frame elbow, shoulder, knee and hip angle time-series.' },
            { icon: <Trophy />, title: 'Score & Grade', desc: 'Overall 0–100 score across 5 phases: approach → follow-through.' },
          ].map((f, i) => (
            <motion.div key={i} initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }} transition={{ delay: i * 0.1 }}
              style={{ background: '#0D0D0D', border: '1px solid #1E1E1E', borderRadius: 10,
                padding: 24 }}>
              <div style={{ color: '#C9A84C', marginBottom: 12 }}>{f.icon}</div>
              <h3 style={{ fontSize: 13, color: '#fff', letterSpacing: 2, margin: '0 0 8px' }}>
                {f.title.toUpperCase()}
              </h3>
              <p style={{ fontSize: 12, color: '#555', lineHeight: 1.6, margin: 0 }}>{f.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── Pricing ── */}
      <section style={{ padding: '80px 24px', maxWidth: 700, margin: '0 auto', textAlign: 'center' }}>
        <p style={{ fontSize: 10, letterSpacing: 4, color: '#555', marginBottom: 48 }}>PRICING</p>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
          <PricingCard
            label="AI REPORT"
            price="₹99"
            features={['Instant AI analysis', 'Section scores', 'Recommendations', 'PDF report']}
          />
          <PricingCard
            label="COACH REVIEW"
            price="₹1,999"
            highlight
            features={['Everything in AI report', 'Human coach review', '2 feedback iterations', 'Priority queue']}
          />
        </div>
      </section>
    </div>
  )
}

function PricingCard({ label, price, features, highlight }) {
  return (
    <div style={{
      background: '#0D0D0D', borderRadius: 10, padding: 28, textAlign: 'left',
      border: `1px solid ${highlight ? '#C9A84C40' : '#1E1E1E'}`,
      position: 'relative',
    }}>
      {highlight && (
        <div style={{
          position: 'absolute', top: -10, right: 16,
          background: '#C9A84C', color: '#0A0A0A', fontSize: 9,
          fontWeight: 700, letterSpacing: 2, padding: '3px 10px', borderRadius: 10,
        }}>
          POPULAR
        </div>
      )}
      <p style={{ fontSize: 9, letterSpacing: 3, color: '#555', margin: '0 0 12px' }}>{label}</p>
      <p style={{ fontSize: 36, fontWeight: 700, color: highlight ? '#C9A84C' : '#fff', margin: '0 0 20px' }}>
        {price}
      </p>
      {features.map(f => (
        <p key={f} style={{ fontSize: 11, color: '#888', margin: '6px 0' }}>✓ {f}</p>
      ))}
    </div>
  )
}
