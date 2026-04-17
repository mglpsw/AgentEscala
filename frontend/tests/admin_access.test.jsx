import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import '@testing-library/jest-dom/vitest'

import AppLayout from '../src/components/app_layout.jsx'
import ProtectedRoute from '../src/components/protected_route.jsx'
import UsersAdminPage from '../src/pages/users_admin_page.jsx'
import LoginPage from '../src/pages/login_page.jsx'
import useAuth from '../src/hooks/use_auth.js'
import api from '../src/api/client.js'

vi.mock('../src/hooks/use_auth.js', () => ({
  default: vi.fn(),
}))

vi.mock('../src/api/client.js', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

const mockedUseAuth = vi.mocked(useAuth)

function renderLayout() {
  return render(
    <MemoryRouter initialEntries={['/calendar']}>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/calendar" element={<div>Calendário</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

function renderAdminRoute(element, initialPath = '/admin/users') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route element={<ProtectedRoute requiredRole="admin" />}>
          <Route path="/admin/users" element={element} />
        </Route>
        <Route path="/calendar" element={<div>Calendário</div>} />
        <Route path="/login" element={<div>Login</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('Hardening de acesso admin no frontend', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('usuário admin vê link de administração na navegação', () => {
    mockedUseAuth.mockReturnValue({
      user: { name: 'Admin' },
      isAdmin: true,
      logout: vi.fn(),
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
    })

    renderLayout()

    expect(screen.getByRole('link', { name: /usuários/i })).toBeInTheDocument()
  })

  it('usuário comum não vê link de administração na navegação', () => {
    mockedUseAuth.mockReturnValue({
      user: { name: 'Médico' },
      isAdmin: false,
      logout: vi.fn(),
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
    })

    renderLayout()

    expect(screen.queryByRole('link', { name: /usuários/i })).not.toBeInTheDocument()
  })

  it('usuário comum acessando URL admin é redirecionado e bloqueado', async () => {
    mockedUseAuth.mockReturnValue({
      user: { name: 'Médico' },
      isAdmin: false,
      isAuthenticated: true,
      isLoading: false,
      logout: vi.fn(),
      login: vi.fn(),
    })

    renderAdminRoute(<div>Página Admin</div>)

    await waitFor(() => {
      expect(screen.getByText('Calendário')).toBeInTheDocument()
    })
    expect(screen.queryByText('Página Admin')).not.toBeInTheDocument()
  })

  it('página admin renderiza corretamente para usuário admin', async () => {
    mockedUseAuth.mockReturnValue({
      user: { name: 'Admin' },
      isAdmin: true,
      isAuthenticated: true,
      isLoading: false,
      logout: vi.fn(),
      login: vi.fn(),
    })
    api.get.mockResolvedValue({ data: [{ id: 1, name: 'Alice', email: 'a@ex.com', role: 'medico', is_active: true }] })

    renderAdminRoute(<UsersAdminPage />)

    expect(await screen.findByRole('heading', { name: /administração de usuários/i })).toBeInTheDocument()
    expect(screen.getByText('Alice')).toBeInTheDocument()
  })

  it('fluxo de login permanece funcional', async () => {
    const loginMock = vi.fn().mockResolvedValue({ id: 1, name: 'Admin' })
    mockedUseAuth.mockReturnValue({
      user: null,
      isAdmin: false,
      isAuthenticated: false,
      isLoading: false,
      logout: vi.fn(),
      login: loginMock,
    })

    render(
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/calendar" element={<div>Calendário</div>} />
        </Routes>
      </MemoryRouter>,
    )

    fireEvent.change(screen.getByLabelText(/e-mail/i), { target: { value: 'admin@escala.com' } })
    fireEvent.change(screen.getByLabelText(/senha/i), { target: { value: '123456' } })
    fireEvent.click(screen.getByRole('button', { name: /entrar/i }))

    await waitFor(() => {
      expect(loginMock).toHaveBeenCalledWith('admin@escala.com', '123456')
      expect(screen.getByText('Calendário')).toBeInTheDocument()
    })
  })
})
