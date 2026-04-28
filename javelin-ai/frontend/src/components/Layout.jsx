// src/components/Layout.jsx
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom'
import { signOutUser } from '../utils/firebase'
import { Zap, Upload, LayoutDashboard, LogOut, LogIn } from 'lucide-react'

export default function Layout({ user }) {
  const navigate  = useNavigate()
  const location  = useLocation()

  const handleSignOut = async () => {
    await signOutUser()
    navigate('/')
  }

  return (
    <div style={{ minHeight: '100vh', background: '#0A0A0A', color: '#F0F0F0',
                  fontFamily: '"IBM Plex Mono", "Courier New", monospace' }}>
      {/* ── Nav ── */}
      <nav style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 32px', height: 60, borderBottom: '1px solid #1E1E1E',
        background: '#0D0D0D', position: 'sticky', top: 0, zIndex: 100,
      }}>
        {/* Logo */}
        <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none' }}>
          <Zap size={22} color="#C9A84C" />
          <span style={{ color: '#C9A84C', fontWeight: 700, letterSpacing: 3, fontSize: 13 }}>
            AMENTUM<span style={{ color: '#fff' }}> AI</span>
          </span>
        </Link>

        {/* Links */}
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {user && (
            <>
              <NavLink to="/dashboard" label="Dashboard" icon={<LayoutDashboard size={14} />} active={location.pathname === '/dashboard'} />
              <NavLink to="/upload"    label="Analyse"   icon={<Upload size={14} />}          active={location.pathname === '/upload'} />
            </>
          )}

          {user ? (
            <button onClick={handleSignOut} style={btnStyle}>
              <LogOut size={14} /> Sign Out
            </button>
          ) : (
            <Link to="/login" style={{ ...btnStyle, textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 6 }}>
              <LogIn size={14} /> Sign In
            </Link>
          )}
        </div>
      </nav>

      {/* ── Page content ── */}
      <Outlet />
    </div>
  )
}

function NavLink({ to, label, icon, active }) {
  return (
    <Link to={to} style={{
      display: 'flex', alignItems: 'center', gap: 6,
      padding: '6px 14px', borderRadius: 4, textDecoration: 'none',
      fontSize: 12, letterSpacing: 1, fontWeight: 600,
      color: active ? '#C9A84C' : '#888',
      background: active ? 'rgba(201,168,76,0.1)' : 'transparent',
      border: active ? '1px solid rgba(201,168,76,0.3)' : '1px solid transparent',
      transition: 'all 0.2s',
    }}>
      {icon} {label}
    </Link>
  )
}

const btnStyle = {
  display: 'flex', alignItems: 'center', gap: 6,
  padding: '6px 14px', borderRadius: 4,
  fontSize: 12, letterSpacing: 1, fontWeight: 600,
  color: '#888', background: 'transparent',
  border: '1px solid #2A2A2A', cursor: 'pointer',
  transition: 'all 0.2s',
}
