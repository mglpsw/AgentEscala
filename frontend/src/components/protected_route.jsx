import { Navigate, Outlet } from 'react-router-dom'
import PropTypes from 'prop-types'
import useAuth from '../hooks/use_auth.js'

// Guarda de rota: verifica autenticação e papel do usuário antes de renderizar filhos
function ProtectedRoute({ requiredRole }) {
  const { isAuthenticated, isAdmin, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="flex flex-col items-center gap-3 text-gray-500">
          <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm">Carregando...</span>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (requiredRole === 'admin' && !isAdmin) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center">
          <h1 className="text-6xl font-bold text-gray-300 mb-4">403</h1>
          <h2 className="text-xl font-semibold text-gray-700 mb-2">Acesso restrito a administradores</h2>
          <p className="text-gray-500">Você não tem permissão para acessar esta página.</p>
        </div>
      </div>
    )
  }

  return <Outlet />
}

export default ProtectedRoute

ProtectedRoute.propTypes = {
  requiredRole: PropTypes.string,
}
