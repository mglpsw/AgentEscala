import axios from 'axios'

// Cliente Axios base para o backend AgentEscala
// Interceptors de autenticação serão adicionados na etapa E5
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Interceptor de request — reservado para injeção do token JWT na E5
api.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error),
)

// Interceptor de response — reservado para refresh automático na E5
api.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(error),
)

export default api
