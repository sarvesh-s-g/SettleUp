import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { authApi } from '../api/api'
import { getToken, setToken } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  // "loading" while we check whether a saved token is still valid.
  const [status, setStatus] = useState(() => (getToken() ? 'loading' : 'anonymous'))

  useEffect(() => {
    if (!getToken()) return
    authApi
      .me()
      .then((me) => {
        setUser(me)
        setStatus('authenticated')
      })
      .catch(() => {
        setToken(null)
        setStatus('anonymous')
      })
  }, [])

  const logout = useCallback(() => {
    setToken(null) // JWTs are stateless: "logging out" means forgetting the token
    setUser(null)
    setStatus('anonymous')
  }, [])

  // The Axios interceptor fires this event when the server rejects our token.
  useEffect(() => {
    window.addEventListener('settleup:logout', logout)
    return () => window.removeEventListener('settleup:logout', logout)
  }, [logout])

  const login = useCallback(async (email, password) => {
    const result = await authApi.login({ email, password })
    setToken(result.access_token)
    setUser(result.user)
    setStatus('authenticated')
    return result.user
  }, [])

  const register = useCallback(
    async (name, email, password) => {
      await authApi.register({ name, email, password })
      return login(email, password)
    },
    [login],
  )

  const value = useMemo(() => ({ user, status, login, register, logout }), [user, status, login, register, logout])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>')
  return context
}
