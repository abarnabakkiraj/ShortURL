import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

function Logo() {
  return (
    <span className="flex items-center gap-2 text-lg font-extrabold tracking-tight">
      <svg viewBox="0 0 32 32" className="h-7 w-7" aria-hidden="true">
        <rect width="32" height="32" rx="7" fill="var(--color-brand)" />
        <path d="M9 16h14M17 10l6 6-6 6" stroke="white" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      Shortlane
    </span>
  )
}

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="border-b border-line bg-white">
      <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6" aria-label="Main">
        <Link to={user ? '/dashboard' : '/login'} aria-label="Shortlane home">
          <Logo />
        </Link>
        {user ? (
          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-muted sm:inline">{user.name}</span>
            <button type="button" onClick={handleLogout} className="btn-secondary btn-sm">
              Log out
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <Link to="/login" className="btn-secondary btn-sm">
              Log in
            </Link>
            <Link to="/register" className="btn-primary btn-sm">
              Sign up
            </Link>
          </div>
        )}
      </nav>
    </header>
  )
}
