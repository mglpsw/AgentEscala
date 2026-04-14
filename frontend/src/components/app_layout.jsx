import { NavLink, Outlet } from 'react-router-dom'

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
  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <header className="bg-blue-700 text-white px-6 py-4 shadow">
        <h1 className="text-xl font-semibold tracking-wide">AgentEscala</h1>
        <p className="text-sm text-blue-200">Gestão de escalas médicas</p>
      </header>

      <div className="flex flex-1">
        <nav className="w-56 bg-white border-r border-gray-200 p-4 space-y-1 shrink-0">
          {nav_links.map((link) => (
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
