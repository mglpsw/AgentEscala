import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import CalendarPage from '../src/pages/calendar_page.jsx'
import api from '../src/api/client.js'
import useAuth from '../src/hooks/use_auth.js'
import { listFutureShiftRequests } from '../src/api/future_shift_requests.js'
import { listShiftRequests } from '../src/api/shift_requests.js'

vi.mock('@fullcalendar/react', () => ({
  default: ({ events, dayCellContent, dateClick }) => {
    const result = dayCellContent?.({ date: new Date('2026-04-18T00:00:00'), dayNumberText: '18' })
    return (
      <div data-testid="calendar">
        Calendário renderizado · {events.length} evento(s)
        <button type="button" data-testid="date-click" onClick={() => dateClick?.({ dateStr: '2026-04-18' })}>abrir dia</button>
        <span data-testid="day-cell-handler">{typeof dayCellContent}</span>
        <pre data-testid="day-cell-html">{result?.html || ''}</pre>
      </div>
    )
  },
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
    expect(screen.getByTestId('day-cell-handler')).toHaveTextContent('function')

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

  it('escapa conteúdo de nomes ao gerar html compacto do dia', async () => {
    api.get.mockImplementation((url) => {
      if (url === '/shifts/') {
        return Promise.resolve({
          data: [
            {
              id: 30,
              agent_id: 2,
              agent: { name: '<img src=x onerror=alert(1)>' },
              title: 'Plantão',
              start_time: '2026-04-18T08:00:00',
              end_time: '2026-04-18T20:00:00',
              location: 'CT',
            },
          ],
        })
      }
      if (url === '/shifts/day-config') return Promise.resolve({ data: [{ date: '2026-04-18', slots: [] }] })
      if (url === '/users/agents') return Promise.resolve({ data: [{ id: 2, name: 'Alice' }] })
      return Promise.resolve({ data: [] })
    })

    render(<CalendarPage />)

    await waitFor(() => {
      expect(screen.getByTestId('day-cell-html').textContent).toContain('&lt;img')
    })
    expect(screen.getByTestId('day-cell-html').textContent).not.toContain('<img')
  })

  it('mantém até 4 plantonistas na célula e agrega excedente com +N', async () => {
    api.get.mockImplementation((url) => {
      if (url === '/shifts/') {
        return Promise.resolve({
          data: [
            { id: 1, agent_id: 2, agent: { name: 'Ana Souza' }, title: 'Plantão', start_time: '2026-04-18T08:00:00', end_time: '2026-04-18T20:00:00' },
            { id: 2, agent_id: 3, agent: { name: 'Bruno Lima' }, title: 'Plantão', start_time: '2026-04-18T10:00:00', end_time: '2026-04-18T22:00:00' },
            { id: 3, agent_id: 4, agent: { name: 'Carla Dias' }, title: 'Plantão', start_time: '2026-04-18T20:00:00', end_time: '2026-04-19T08:00:00' },
            { id: 4, agent_id: 5, agent: { name: 'Diego Paz' }, title: 'Plantão', start_time: '2026-04-18T00:00:00', end_time: '2026-04-19T00:00:00' },
            { id: 5, agent_id: 6, agent: { name: 'Elisa Neto' }, title: 'Plantão', start_time: '2026-04-18T08:00:00', end_time: '2026-04-18T20:00:00' },
          ],
        })
      }
      if (url === '/shifts/day-config') return Promise.resolve({ data: [{ date: '2026-04-18', slots: [] }] })
      if (url === '/users/agents') return Promise.resolve({ data: [{ id: 2, name: 'Alice' }] })
      return Promise.resolve({ data: [] })
    })

    render(<CalendarPage />)

    await waitFor(() => {
      expect(screen.getByTestId('day-cell-html').textContent).toContain('+1')
    })
  })

  it('abre detalhe do dia com toque e mostra nome completo, horário e turno', async () => {
    render(<CalendarPage />)

    await waitFor(() => {
      expect(screen.getByTestId('calendar')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByTestId('date-click'))

    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText(/escala completa do dia/i)).toBeInTheDocument()
    expect(screen.getAllByText('Alice').length).toBeGreaterThan(0)
    expect(screen.getByText('08:00-20:00')).toBeInTheDocument()
    expect(screen.getAllByText('12H DIA').length).toBeGreaterThan(0)
  })
})
