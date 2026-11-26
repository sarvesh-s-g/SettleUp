import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { LoadingState } from './ui'

/** Renders child routes only for logged-in users; others go to /login. */
export default function ProtectedRoute() {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') return <LoadingState label="Checking your session…" />
  if (status !== 'authenticated') {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return <Outlet />
}

/** The opposite: logged-in users visiting /login are sent to the dashboard. */
export function GuestRoute() {
  const { status } = useAuth()
  if (status === 'loading') return <LoadingState />
  if (status === 'authenticated') return <Navigate to="/dashboard" replace />
  return <Outlet />
}
