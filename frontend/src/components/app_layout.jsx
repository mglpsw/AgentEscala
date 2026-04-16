import { NavLink, Outlet } from 'react-router-dom'
import { useNavigate } from 'react-router-dom'
import useAuth from '../hooks/use_auth.js'

const nav_links = [
  { to: '/calendar', label: '📅 Calendário' },
  { to: '/shifts', label: '🕐 Turnos' },
  { to: '/swaps', label: '🔄 Trocas' },
  { to: '/swaps/pending', label: '⏳ Trocas Pendentes' },
  { to: '/import', label: '📥 Importar Escala' },
  { to: '/admin/users', label: '👥 Usuários' },
]

// Layout principal com cabeçalho e navegação lateral
function AppLayout() {
  const navigate = useNavigate()
  const { logout, user, isAdmin } = useAuth()

  const visibleLinks = nav_links.filter((link) => {
    if ((link.to === '/swaps/pending' || link.to === '/import' || link.to === '/admin/users') && !isAdmin) {
      return false
    }
    return true
  })

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <header className="bg-blue-700 text-white px-6 py-4 shadow">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold tracking-wide">AgentEscala</h1>
            <p className="text-sm text-blue-200">Gestão de escalas médicas</p>
          </div>
          <div className="text-right">
            <p className="text-sm text-blue-100">{user?.name}</p>
            <button
              type="button"
              onClick={handleLogout}
              className="mt-1 rounded bg-white/10 px-3 py-1 text-xs font-medium hover:bg-white/20"
            >
              Sair
            </button>
          </div>
        </div>
      </header>

      <div className="flex flex-1">
        <nav className="w-56 bg-white border-r border-gray-200 p-4 space-y-1 shrink-0">
          {visibleLinks.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                `block px-3 py-2 rounded text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                }`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>

        <main className="flex-1 p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default AppLayout
