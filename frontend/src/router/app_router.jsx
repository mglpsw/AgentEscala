import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import AppLayout from '../components/app_layout.jsx'
import LoginPage from '../pages/login_page.jsx'
import CalendarPage from '../pages/calendar_page.jsx'
import ShiftsPage from '../pages/shifts_page.jsx'
import SwapsPage from '../pages/swaps_page.jsx'
import PendingSwapsPage from '../pages/pending_swaps_page.jsx'
import ImportPage from '../pages/import_page.jsx'
import UsersAdminPage from '../pages/users_admin_page.jsx'
import NotFoundPage from '../pages/not_found_page.jsx'

// Roteamento principal da aplicação — ProtectedRoute service  adicionado na etapa E5
function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/calendar" replace />} />
          <Route path="/calendar" element={<CalendarPage />} />
          <Route path="/shifts" element={<ShiftsPage />} />
          <Route path="/swaps" element={<SwapsPage />} />
          <Route path="/swaps/pending" element={<PendingSwapsPage />} />
          <Route path="/import" element={<ImportPage />} />
          <Route path="/admin/users" element={<UsersAdminPage />} />
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default AppRouter
