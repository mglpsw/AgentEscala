import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import AppLayout from '../components/app_layout.jsx'
import ProtectedRoute from '../components/protected_route.jsx'
import LoginPage from '../pages/login_page.jsx'
import CalendarPage from '../pages/calendar_page.jsx'
import ShiftsPage from '../pages/shifts_page.jsx'
import MySchedulePage from '../pages/my_schedule_page.jsx'
import SwapsPage from '../pages/swaps_page.jsx'
import PendingSwapsPage from '../pages/pending_swaps_page.jsx'
import ImportPage from '../pages/import_page.jsx'
import UsersAdminPage from '../pages/users_admin_page.jsx'
import AdminPlantoesPage from '../pages/admin_plantoes_page.jsx'
import ProfilePage from '../pages/profile_page.jsx'
import NotFoundPage from '../pages/not_found_page.jsx'
import useAuth from '../hooks/use_auth.js'

// Redireciona a raiz conforme estado de autenticação
function RootRedirect() {
  const { isAuthenticated, isLoading } = useAuth()
  if (isLoading) return null
  return <Navigate to={isAuthenticated ? '/calendar' : '/login'} replace />
}

// Roteamento principal — rotas protegidas agrupadas por nível de acesso
function AppRouter() {
  return (
    <BrowserRouter>
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
    </BrowserRouter>
  )
}

export default AppRouter
