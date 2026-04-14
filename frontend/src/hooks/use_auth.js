import { useContext } from 'react'
import { AuthContext } from '../contexts/auth_context_definition.js'

// Hook para acessar o contexto de autenticação — deve ser usado dentro do AuthProvider
function useAuth() {
  const context = useContext(AuthContext)
  if (context === null) {
    throw new Error('useAuth deve ser usado dentro de um AuthProvider')
  }
  return context
}

export default useAuth
