// Componente raiz — AuthProvider envolve o roteamento para disponibilizar contexto de auth
import { AuthProvider } from './contexts/auth_context.jsx'
import AppRouter from './router/app_router.jsx'

function App() {
  return (
    <AuthProvider>
      <AppRouter />
    </AuthProvider>
  )
}

export default App
