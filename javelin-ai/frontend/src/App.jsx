// src/App.jsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { onAuthStateChanged } from 'firebase/auth'
import { auth } from './utils/firebase'

import Layout      from './components/Layout'
import Landing     from './pages/Landing'
import Dashboard   from './pages/Dashboard'
import Upload      from './pages/Upload'
import ReportView  from './pages/ReportView'
import Login       from './pages/Login'

// ── Auth guard ────────────────────────────────────────────────────────────────
function RequireAuth({ user, children }) {
  if (!user) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  const [user, setUser]       = useState(undefined)  // undefined = loading
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const unsub = onAuthStateChanged(auth, (u) => {
      setUser(u)
      setLoading(false)
    })
    return unsub
  }, [])

  if (loading) return <LoadingScreen />

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout user={user} />}>
          <Route index element={<Landing user={user} />} />
          <Route path="login" element={<Login />} />

          <Route path="dashboard" element={
            <RequireAuth user={user}>
              <Dashboard />
            </RequireAuth>
          } />
          <Route path="upload" element={
            <RequireAuth user={user}>
              <Upload />
            </RequireAuth>
          } />
          <Route path="report/:videoId" element={
            <RequireAuth user={user}>
              <ReportView />
            </RequireAuth>
          } />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

function LoadingScreen() {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      height: '100vh', background: '#0A0A0A'
    }}>
      <div style={{ textAlign: 'center' }}>
        <div className="spin" style={{
          width: 48, height: 48, border: '3px solid #C9A84C',
          borderTopColor: 'transparent', borderRadius: '50%',
          margin: '0 auto 16px',
          animation: 'spin 0.8s linear infinite',
        }} />
        <p style={{ color: '#C9A84C', fontFamily: 'monospace', letterSpacing: 2 }}>
          AMENTUM AI
        </p>
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); }}`}</style>
    </div>
  )
}
