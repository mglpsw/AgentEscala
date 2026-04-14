import axios from 'axios'

// Chaves padronizadas para o localStorage
const KEY_ACCESS = 'ae_access_token'
const KEY_REFRESH = 'ae_refresh_token'

export const getAccessToken = () => localStorage.getItem(KEY_ACCESS)
export const getRefreshToken = () => localStorage.getItem(KEY_REFRESH)
export const setTokens = (access, refresh) => {
  localStorage.setItem(KEY_ACCESS, access)
  localStorage.setItem(KEY_REFRESH, refresh)
}
export const clearTokens = () => {
  localStorage.removeItem(KEY_ACCESS)
  localStorage.removeItem(KEY_REFRESH)
}

// Cliente Axios base para o backend AgentEscala
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Injeta o access_token em todas as requests autenticadas
api.interceptors.request.use(
  (config) => {
    const token = getAccessToken()
    if (token && !config.url?.includes('/auth/login')) {
      config.headers = config.headers ?? {}
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// Interceptor de response — refresh automático gerenciado pelo AuthProvider (auth_context.jsx)
api.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(error),
)

export default api
