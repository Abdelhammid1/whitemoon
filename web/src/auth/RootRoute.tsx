import { Navigate } from 'react-router-dom'
import { useAuth } from './AuthContext'
import { LandingPage } from '../pages/LandingPage'

/**
 * The site root `/`:
 *  - signed-out visitors see the public marketing landing page;
 *  - signed-in users are sent to their dashboard at `/home`.
 */
export function RootRoute() {
  const { user, loading } = useAuth()
  if (loading) {
    return (
      <div className="min-h-screen grid place-items-center bg-background text-on-surface-variant font-body text-body">
        جار التحميل…
      </div>
    )
  }
  if (user) return <Navigate to="/home" replace />
  return <LandingPage />
}
