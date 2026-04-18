import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from '../components/protected_route.jsx'
import useAuth from '../hooks/use_auth.js'

const AppLayout = lazy(() => import('../components/app_layout.jsx'))
const LoginPage = lazy(() => import('../pages/login_page.jsx'))
const CalendarPage = lazy(() => import('../pages/calendar_page.jsx'))
const ShiftsPage = lazy(() => import('../pages/shifts_page.jsx'))
const MySchedulePage = lazy(() => import('../pages/my_schedule_page.jsx'))
const SwapsPage = lazy(() => import('../pages/swaps_page.jsx'))
const PendingSwapsPage = lazy(() => import('../pages/pending_swaps_page.jsx'))
const ImportPage = lazy(() => import('../pages/import_page.jsx'))
const UsersAdminPage = lazy(() => import('../pages/users_admin_page.jsx'))
const AdminPlantoesPage = lazy(() => import('../pages/admin_plantoes_page.jsx'))
const ProfilePage = lazy(() => import('../pages/profile_page.jsx'))
const NotFoundPage = lazy(() => import('../pages/not_found_page.jsx'))

// Redireciona a raiz conforme estado de autenticação
function RootRedirect() {
  const { isAuthenticated, isLoading } = useAuth()
  if (isLoading) return null
  return <Navigate to={isAuthenticated ? '/calendar' : '/login'} replace />
}

function RouteFallback() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-6 text-sm text-gray-600">
      Carregando...
    </div>
  )
}

// Roteamento principal — rotas protegidas agrupadas por nível de acesso
function AppRouter() {
  return (
    <BrowserRouter>
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          {/* Rota pública */}
          <Route path="/login" element={<LoginPage />} />

          {/* Rotas protegidas — qualquer usuário autenticado */}
          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route path="/calendar" element={<CalendarPage />} />
              <Route path="/shifts" element={<ShiftsPage />} />
              <Route path="/my-schedule" element={<MySchedulePage />} />
              <Route path="/swaps" element={<SwapsPage />} />
              <Route path="/profile" element={<ProfilePage />} />
            </Route>
          </Route>

          {/* Rotas protegidas — somente admin */}
          <Route element={<ProtectedRoute requiredRole="admin" />}>
            <Route element={<AppLayout />}>
              <Route path="/swaps/pending" element={<PendingSwapsPage />} />
              <Route path="/import" element={<ImportPage />} />
              <Route path="/admin/users" element={<UsersAdminPage />} />
              <Route path="/admin/plantoes" element={<AdminPlantoesPage />} />
            </Route>
          </Route>

          {/* Raiz: redireciona conforme autenticação */}
          <Route path="/" element={<RootRedirect />} />

          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}

export default AppRouter
