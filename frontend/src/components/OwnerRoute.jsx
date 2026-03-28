import { Navigate } from 'react-router-dom'
import useAuth from '../hooks/useAuth'

export default function OwnerRoute({ children }) {
  const { isAuthenticated, currentUser } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (!currentUser?.is_owner) return <Navigate to="/dashboard" replace />
  return children
}
