import { createContext, useContext, useState, useCallback } from 'react'

const AuthContext = createContext(null)

const TOKEN_KEY = 'won_token'
const USER_KEY = 'won_user'

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY))
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const stored = localStorage.getItem(USER_KEY)
      return stored ? JSON.parse(stored) : null
    } catch {
      return null
    }
  })

  const login = useCallback((tokenData) => {
    localStorage.setItem(TOKEN_KEY, tokenData.token)
    localStorage.setItem(USER_KEY, JSON.stringify({
      account_id: tokenData.account_id,
      username: tokenData.username,
      real_name: tokenData.real_name,
      is_admin: tokenData.is_admin || false,
    }))
    setToken(tokenData.token)
    setCurrentUser({
      account_id: tokenData.account_id,
      username: tokenData.username,
      real_name: tokenData.real_name,
      is_admin: tokenData.is_admin || false,
    })
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    setToken(null)
    setCurrentUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ token, currentUser, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuthContext() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuthContext must be used inside AuthProvider')
  return ctx
}
