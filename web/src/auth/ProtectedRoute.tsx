import { Navigate, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuth } from './AuthContext'

interface Props {
  children: ReactNode
  roles?: string[]
  /** If set, the user must hold this permission code (or the `*` wildcard). */
  perm?: string
}

export function ProtectedRoute({ children, roles, perm }: Props) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="min-h-screen grid place-items-center bg-parchment text-graphite text-body">
        جار التحميل…
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  if (roles && !roles.includes(user.kind)) {
    return <Navigate to="/" replace />
  }

  if (perm && !(user.permissions?.includes(perm) || user.permissions?.includes('*'))) {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}
