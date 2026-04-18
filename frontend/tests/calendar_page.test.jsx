import { render, screen, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import CalendarPage from '../src/pages/calendar_page.jsx'
import api from '../src/api/client.js'
import useAuth from '../src/hooks/use_auth.js'
import { listFutureShiftRequests } from '../src/api/future_shift_requests.js'
import { listShiftRequests } from '../src/api/shift_requests.js'

vi.mock('@fullcalendar/react', () => ({
  default: ({ events }) => (
    <div data-testid="calendar">
      Calendário renderizado · {events.length} evento(s)
    </div>
  ),
}))

vi.mock('@fullcalendar/daygrid', () => ({ default: {} }))
vi.mock('@fullcalendar/timegrid', () => ({ default: {} }))
vi.mock('@fullcalendar/interaction', () => ({ default: {} }))
vi.mock('@fullcalendar/core/locales/pt-br', () => ({ default: {} }))

vi.mock('../src/hooks/use_auth.js', () => ({
  default: vi.fn(),
}))

vi.mock('../src/api/client.js', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}))

vi.mock('../src/api/future_shift_requests.js', () => ({
  listFutureShiftRequests: vi.fn(),
  createFutureShiftRequest: vi.fn(),
  cancelFutureShiftRequest: vi.fn(),
}))

vi.mock('../src/api/shift_requests.js', () => ({
  listShiftRequests: vi.fn(),
  createShiftRequest: vi.fn(),
  respondShiftRequest: vi.fn(),
  adminReviewShiftRequest: vi.fn(),
}))

const mockedUseAuth = vi.mocked(useAuth)

describe('CalendarPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedUseAuth.mockReturnValue({
      user: { id: 1, name: 'Admin', role: 'admin' },
      isAdmin: true,
    })

    api.get.mockImplementation((url) => {
      if (url === '/shifts/') {
        return Promise.resolve({
          data: [
            {
              id: 10,
              agent_id: 2,
              agent: { name: 'Alice' },
              title: 'Plantão',
              start_time: '2026-04-18T08:00:00',
              end_time: '2026-04-18T20:00:00',
              location: 'CT',
            },
          ],
        })
      }
      if (url === '/shifts/day-config') {
        return Promise.resolve({ data: [{ date: '2026-04-18', slots: [] }] })
      }
      if (url === '/users/agents') {
        return Promise.resolve({ data: [{ id: 2, name: 'Alice' }] })
      }
      return Promise.resolve({ data: [] })
    })
    listFutureShiftRequests.mockResolvedValue([])
    listShiftRequests.mockResolvedValue([])
  })

  it('renderiza o calendário para admin usando a escala consolidada', async () => {
    render(<CalendarPage />)

    expect(screen.getByText(/carregando calendário/i)).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByTestId('calendar')).toHaveTextContent('1 evento')
    })

    expect(api.get).toHaveBeenCalledWith(
      '/shifts/',
      expect.objectContaining({ params: expect.objectContaining({ start_date: expect.any(String), end_date: expect.any(String) }) }),
    )
    expect(screen.queryByText(/não foi possível carregar/i)).not.toBeInTheDocument()
  })

  it('mantém a página renderizada quando dados auxiliares falham', async () => {
    api.get.mockImplementation((url) => {
      if (url === '/shifts/') return Promise.resolve({ data: [] })
      if (url === '/shifts/day-config') return Promise.reject(new Error('offline'))
      if (url === '/users/agents') return Promise.resolve({ data: [] })
      return Promise.resolve({ data: [] })
    })

    render(<CalendarPage />)

    await waitFor(() => {
      expect(screen.getByTestId('calendar')).toBeInTheDocument()
    })
    expect(screen.getByText(/carregado parcialmente/i)).toBeInTheDocument()
  })
})
