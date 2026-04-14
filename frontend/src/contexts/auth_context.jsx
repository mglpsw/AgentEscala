import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react'
import api, { getAccessToken, getRefreshToken, setTokens, clearTokens } from '../api/client.js'

export const AuthContext = createContext(null)

// Provider de autenticação JWT — gerencia estado do usuário, login, logout e refresh automático
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  // Referência para evitar múltiplos refreshes simultâneos
  const isRefreshing = useRef(false)
  const refreshSubscribers = useRef([])

  const logout = useCallback(async () => {
    const refreshToken = getRefreshToken()
    clearTokens()
    setUser(null)
    if (refreshToken) {
      try {
        await api.post('/auth/logout', null, {
          headers: { Authorization: `Bearer ${refreshToken}` },
          _skipAuthRetry: true,
        })
      } catch {
        // silencia erro no logout — tokens já foram limpos localmente
      }
    }
  }, [])

  // Busca dados do usuário autenticado usando o access_token atual
  const fetchCurrentUser = useCallback(async () => {
    const { data } = await api.get('/auth/me')
    setUser(data)
    return data
  }, [])

  // Tenta renovar o access_token usando o refresh_token armazenado
  const refreshAccessToken = useCallback(async () => {
    const refreshToken = getRefreshToken()
    if (!refreshToken) throw new Error('Sem refresh token')
    const { data } = await api.post('/auth/refresh', { refresh_token: refreshToken }, { _skipAuthRetry: true })
    setTokens(data.access_token, refreshToken)
    return data.access_token
  }, [])

  // Inicialização: verifica se existe sessão válida ao montar o provider
  useEffect(() => {
    const initAuth = async () => {
      const accessToken = getAccessToken()
      if (!accessToken) {
        setIsLoading(false)
        return
      }
      try {
        await fetchCurrentUser()
      } catch (err) {
        if (err?.response?.status === 401) {
          try {
            await refreshAccessToken()
            await fetchCurrentUser()
          } catch {
            clearTokens()
            setUser(null)
          }
        } else {
          clearTokens()
          setUser(null)
        }
      } finally {
        setIsLoading(false)
      }
    }
    initAuth()
  }, [fetchCurrentUser, refreshAccessToken])

  // Interceptor de response: tenta refresh automático em 401, exceto nas rotas de auth
  useEffect(() => {
    const interceptorId = api.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config
        const isAuthRoute =
          originalRequest.url?.includes('/auth/login') ||
          originalRequest.url?.includes('/auth/refresh')

        if (error?.response?.status === 401 && !isAuthRoute && !originalRequest._skipAuthRetry) {
          originalRequest._skipAuthRetry = true

          if (isRefreshing.current) {
            // Enfileira a request até o refresh terminar
            return new Promise((resolve, reject) => {
              refreshSubscribers.current.push({ resolve, reject })
            }).then((token) => {
              originalRequest.headers.Authorization = `Bearer ${token}`
              return api(originalRequest)
            })
          }

          isRefreshing.current = true
          try {
            const newToken = await refreshAccessToken()
            refreshSubscribers.current.forEach(({ resolve }) => resolve(newToken))
            refreshSubscribers.current = []
            originalRequest.headers.Authorization = `Bearer ${newToken}`
            return api(originalRequest)
          } catch {
            refreshSubscribers.current.forEach(({ reject }) => reject(error))
            refreshSubscribers.current = []
            await logout()
            return Promise.reject(error)
          } finally {
            isRefreshing.current = false
          }
        }

        return Promise.reject(error)
      },
    )

    return () => api.interceptors.response.eject(interceptorId)
  }, [logout, refreshAccessToken])

  const login = useCallback(async (email, password) => {
    const { data } = await api.post('/auth/login', { email, password }, { _skipAuthRetry: true })
    setTokens(data.access_token, data.refresh_token)
    const userData = await fetchCurrentUser()
    return userData
  }, [fetchCurrentUser])

  const value = {
    user,
    isLoading,
    isAuthenticated: user !== null,
    isAdmin: user?.role === 'admin',
    login,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
