// src/pages/Upload.jsx
import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Upload as UploadIcon, CheckCircle, AlertCircle, Zap, Star } from 'lucide-react'
import api from '../utils/api'

const TIERS = [
  {
    id:       'free',
    label:    'AI REPORT',
    price:    '₹99',
    paise:    9900,
    features: ['AI pose analysis', 'Section scores', 'Auto recommendations', 'PDF report'],
    color:    '#C9A84C',
  },
  {
    id:       'premium',
    label:    'COACH REVIEW',
    price:    '₹1,999',
    paise:    199900,
    features: ['Everything in AI report', 'Human coach review', '2 feedback iterations', 'Priority processing'],
    color:    '#9C27B0',
    highlight: true,
  },
]

export default function Upload() {
  const navigate = useNavigate()

  const [file,          setFile]          = useState(null)
  const [selectedTier,  setSelectedTier]  = useState('free')
  const [uploadProgress, setUploadProgress] = useState(0)
  const [stage,         setStage]         = useState('select')  // select | paying | uploading | polling | done | error
  const [error,         setError]         = useState('')
  const [videoId,       setVideoId]       = useState(null)

  // ── Dropzone ──────────────────────────────────────────────────────────────
  const onDrop = useCallback((accepted) => {
    if (accepted[0]) setFile(accepted[0])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'video/mp4': ['.mp4'], 'video/quicktime': ['.mov'] },
    maxSize: 200 * 1024 * 1024,
    multiple: false,
  })

  // ── Razorpay payment ──────────────────────────────────────────────────────
  const initPayment = async (vid) => {
    try {
      const { data } = await api.post('/payment/create-order', {
        video_id: vid,
        tier:     selectedTier,
      })

      return new Promise((resolve, reject) => {
        const rzp = new window.Razorpay({
          key:         data.key_id,
          amount:      data.amount,
          currency:    data.currency,
          order_id:    data.order_id,
          name:        'Amentum Sports',
          description: `Javelin AI – ${selectedTier === 'premium' ? 'Coach Review' : 'AI Report'}`,
          theme:       { color: '#C9A84C' },
          handler: async (response) => {
            await api.post('/payment/verify', {
              video_id:              vid,
              razorpay_order_id:     response.razorpay_order_id,
              razorpay_payment_id:   response.razorpay_payment_id,
              razorpay_signature:    response.razorpay_signature,
            })
            resolve()
          },
          modal: { ondismiss: () => reject(new Error('Payment cancelled')) },
        })
        rzp.open()
      })
    } catch (err) {
      throw new Error(err.response?.data?.detail || err.message)
    }
  }

  // ── Upload ────────────────────────────────────────────────────────────────
  const handleUpload = async () => {
    if (!file) return
    setError('')

    try {
      // 1. Upload video to get a video_id first (pre-paid)
      setStage('uploading')
      const form = new FormData()
      form.append('file', file)
      form.append('tier', selectedTier)

      const { data: uploadData } = await api.post('/upload/', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) =>
          setUploadProgress(Math.round((e.loaded / e.total) * 100)),
      })
      const vid = uploadData.video_id
      setVideoId(vid)

      // 2. Process payment
      setStage('paying')
      await initPayment(vid)

      // 3. Poll for completion
      setStage('polling')
      await pollStatus(vid)

    } catch (err) {
      setStage('error')
      setError(err.message || 'Something went wrong. Please try again.')
    }
  }

  const pollStatus = async (vid) => {
    const MAX_WAIT_MS = 5 * 60 * 1000   // 5 minutes
    const INTERVAL    = 4_000
    const started     = Date.now()

    while (Date.now() - started < MAX_WAIT_MS) {
      await new Promise(r => setTimeout(r, INTERVAL))
      try {
        const { data } = await api.get(`/analyze/${vid}`)
        if (data.status === 'complete') {
          setStage('done')
          navigate(`/report/${vid}`)
          return
        }
        if (data.status === 'failed') {
          throw new Error(data.error || 'Analysis failed.')
        }
      } catch (err) {
        if (err.response?.status !== 404) throw err
      }
    }
    throw new Error('Analysis timed out. Check your dashboard for results.')
  }

  // ── Render ────────────────────────────────────────────────────────────────
  const tier = TIERS.find(t => t.id === selectedTier)

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '48px 24px' }}>
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -16 }} animate={{ opacity: 1, y: 0 }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, color: '#fff', marginBottom: 4, letterSpacing: 2 }}>
          ANALYSE YOUR THROW
        </h1>
        <p style={{ color: '#666', fontSize: 13, letterSpacing: 1 }}>
          Upload a javelin throw video — get AI biomechanical analysis in minutes.
        </p>
      </motion.div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginTop: 40 }}>
        {/* Left: Dropzone */}
        <div>
          <Label>VIDEO FILE</Label>
          <div
            {...getRootProps()}
            style={{
              border: `2px dashed ${isDragActive ? '#C9A84C' : file ? '#4CAF50' : '#2A2A2A'}`,
              borderRadius: 8, padding: '40px 24px', textAlign: 'center',
              cursor: 'pointer', background: isDragActive ? 'rgba(201,168,76,0.05)' : '#111',
              transition: 'all 0.2s', minHeight: 200,
              display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
            }}
          >
            <input {...getInputProps()} />
            {file ? (
              <>
                <CheckCircle size={36} color="#4CAF50" style={{ marginBottom: 12 }} />
                <p style={{ color: '#4CAF50', fontWeight: 700, fontSize: 13 }}>{file.name}</p>
                <p style={{ color: '#555', fontSize: 11, marginTop: 4 }}>
                  {(file.size / 1024 / 1024).toFixed(1)} MB
                </p>
              </>
            ) : (
              <>
                <UploadIcon size={36} color="#444" style={{ marginBottom: 12 }} />
                <p style={{ color: '#888', fontSize: 13 }}>
                  {isDragActive ? 'Drop it!' : 'Drag & drop or click to browse'}
                </p>
                <p style={{ color: '#444', fontSize: 11, marginTop: 8 }}>MP4 / MOV · Max 200 MB</p>
              </>
            )}
          </div>
        </div>

        {/* Right: Tier selection */}
        <div>
          <Label>SELECT PLAN</Label>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {TIERS.map(t => (
              <motion.div
                key={t.id}
                whileHover={{ scale: 1.02 }}
                onClick={() => setSelectedTier(t.id)}
                style={{
                  padding: 16, borderRadius: 8, cursor: 'pointer',
                  border: `1px solid ${selectedTier === t.id ? t.color : '#2A2A2A'}`,
                  background: selectedTier === t.id ? `rgba(${t.id === 'premium' ? '156,39,176' : '201,168,76'},0.08)` : '#111',
                  transition: 'all 0.2s',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {t.highlight && <Star size={14} color={t.color} fill={t.color} />}
                    <span style={{ color: t.color, fontWeight: 700, fontSize: 13, letterSpacing: 2 }}>{t.label}</span>
                  </div>
                  <span style={{ color: '#fff', fontWeight: 700, fontSize: 18 }}>{t.price}</span>
                </div>
                <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                  {t.features.map(f => (
                    <li key={f} style={{ fontSize: 11, color: '#888', padding: '2px 0' }}>
                      ✓ {f}
                    </li>
                  ))}
                </ul>
              </motion.div>
            ))}
          </div>
        </div>
      </div>

      {/* Progress / Status */}
      <AnimatePresence mode="wait">
        {stage !== 'select' && (
          <motion.div
            key={stage}
            initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            style={{ marginTop: 24 }}
          >
            <StageIndicator stage={stage} progress={uploadProgress} error={error} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Submit */}
      {stage === 'select' && (
        <motion.button
          initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
          onClick={handleUpload}
          disabled={!file}
          style={{
            marginTop: 32, width: '100%', padding: '14px 0',
            background: file ? '#C9A84C' : '#2A2A2A',
            color: file ? '#0A0A0A' : '#444',
            border: 'none', borderRadius: 6, cursor: file ? 'pointer' : 'not-allowed',
            fontFamily: '"IBM Plex Mono", monospace', fontWeight: 700,
            fontSize: 14, letterSpacing: 3, transition: 'all 0.2s',
          }}
        >
          {file ? `ANALYSE · ${tier.price}` : 'SELECT A VIDEO FIRST'}
        </motion.button>
      )}
    </div>
  )
}

function Label({ children }) {
  return (
    <p style={{ fontSize: 10, letterSpacing: 3, color: '#555', marginBottom: 10, fontWeight: 700 }}>
      {children}
    </p>
  )
}

function StageIndicator({ stage, progress, error }) {
  const stages = {
    uploading: { label: `Uploading … ${progress}%`, icon: '⬆', color: '#C9A84C' },
    paying:    { label: 'Awaiting payment …',        icon: '💳', color: '#9C27B0' },
    polling:   { label: 'AI analysis in progress …', icon: '🧠', color: '#2196F3' },
    done:      { label: 'Complete! Redirecting …',   icon: '✓',  color: '#4CAF50' },
    error:     { label: error,                        icon: '✗',  color: '#f44336' },
  }
  const s = stages[stage] || stages.uploading

  return (
    <div style={{
      padding: '16px 20px', borderRadius: 6,
      background: '#111', border: `1px solid ${s.color}20`,
      display: 'flex', alignItems: 'center', gap: 12,
    }}>
      <span style={{ fontSize: 20 }}>{s.icon}</span>
      <div style={{ flex: 1 }}>
        <p style={{ color: s.color, fontSize: 12, letterSpacing: 1, margin: 0 }}>{s.label}</p>
        {stage === 'uploading' && (
          <div style={{ height: 3, background: '#2A2A2A', borderRadius: 2, marginTop: 8 }}>
            <div style={{
              height: '100%', width: `${progress}%`,
              background: '#C9A84C', borderRadius: 2, transition: 'width 0.3s',
            }} />
          </div>
        )}
        {stage === 'polling' && (
          <div style={{ height: 3, background: '#2A2A2A', borderRadius: 2, marginTop: 8, overflow: 'hidden' }}>
            <div style={{
              height: '100%', width: '40%', background: '#2196F3', borderRadius: 2,
              animation: 'slide 1.5s ease-in-out infinite',
            }} />
          </div>
        )}
      </div>
      <style>{`
        @keyframes slide {
          0%   { transform: translateX(-100%); }
          100% { transform: translateX(300%); }
        }
      `}</style>
    </div>
  )
}
