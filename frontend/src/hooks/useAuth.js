import { useAuthContext } from '../context/AuthContext'

export default function useAuth() {
  const ctx = useAuthContext()
  return {
    ...ctx,
    isAuthenticated: !!ctx.token,
  }
}
