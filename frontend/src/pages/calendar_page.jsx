import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import ptBrLocale from '@fullcalendar/core/locales/pt-br'
import api from '../api/client.js'
import useAuth from '../hooks/use_auth.js'

function build_initial_range() {
  const now = new Date()

  return {
    start: new Date(now.getFullYear(), now.getMonth(), 1),
    end: new Date(now.getFullYear(), now.getMonth() + 1, 1),
  }
}

function calculate_duration_hours(start_time, end_time) {
  const start_date = new Date(start_time)
  const end_date = new Date(end_time)
  const duration_in_hours = (end_date.getTime() - start_date.getTime()) / (1000 * 60 * 60)

  return Number.isFinite(duration_in_hours) ? Number(duration_in_hours.toFixed(1)) : 0
}

function shift_overlaps_range(shift, visible_range) {
  const shift_start = new Date(shift.start_time)
  const shift_end = new Date(shift.end_time)

  if (Number.isNaN(shift_start.getTime()) || Number.isNaN(shift_end.getTime())) {
    return false
  }

  return shift_start < visible_range.end && shift_end > visible_range.start
}

function map_shift_to_event(shift, current_user) {
  const ownShift =
    shift.agent_id === current_user?.id ||
    shift.user_id === current_user?.id ||
    shift.agent?.name === current_user?.name
  return {
    id: String(shift.id),
    title: `${shift.agent?.name || current_user?.name || 'Profissional'} · ${shift.title?.trim() || 'Turno'}`,
    start: shift.start_time,
    end: shift.end_time,
    backgroundColor: ownShift ? '#2563eb' : '#6b7280',
    borderColor: ownShift ? '#1d4ed8' : '#4b5563',
    extendedProps: {
      location: shift.location ?? '',
      description: shift.description ?? '',
      duration_hours: calculate_duration_hours(shift.start_time, shift.end_time),
      status: 'scheduled',
      agent_name: shift.agent?.name ?? current_user?.name ?? '',
      own_shift: ownShift,
    },
  }
}

function build_error_message(error) {
  const status = error?.response?.status

  if (status === 404) {
    return 'Não foi possível encontrar os turnos deste usuário.'
  }

  if (status >= 500) {
    return 'O servidor falhou ao carregar os turnos. Tente novamente em instantes.'
  }

  return 'Não foi possível carregar os turnos do período exibido.'
}

function render_event_content(event_info) {
  const location = event_info.event.extendedProps.location

  return (
    <div className="px-1 py-0.5">
      <div className="font-medium truncate">{event_info.timeText}</div>
      <div className="truncate">{event_info.event.title}</div>
      {location ? <div className="truncate text-[11px] opacity-90">{location}</div> : null}
    </div>
  )
}

// Página de calendário — consome os turnos reais do usuário autenticado
function CalendarPage() {
  const { user } = useAuth()
  const [visible_range, set_visible_range] = useState(() => build_initial_range())
  const [events, set_events] = useState([])
  const [is_loading, set_is_loading] = useState(true)
  const [error, set_error] = useState('')
  const [reload_key, set_reload_key] = useState(0)
  const [coverageFlags, setCoverageFlags] = useState([])
  const last_range_key = useRef('')
  const user_id = user?.id
  const user_name = user?.name

  const visible_range_key = useMemo(
    () => `${visible_range.start.toISOString()}::${visible_range.end.toISOString()}`,
    [visible_range],
  )
  const current_user = useMemo(
    () => (user_id ? { id: user_id, name: user_name } : null),
    [user_id, user_name],
  )

  const handle_dates_set = useCallback((date_info) => {
    const next_start = new Date(date_info.start)
    const next_end = new Date(date_info.end)
    const next_range_key = `${next_start.toISOString()}::${next_end.toISOString()}`

    if (next_range_key === last_range_key.current) {
      return
    }

    last_range_key.current = next_range_key
    set_visible_range({ start: next_start, end: next_end })
  }, [])

  const handle_retry = useCallback(() => {
    set_reload_key((current_key) => current_key + 1)
  }, [])

  useEffect(() => {
    if (!current_user?.id) {
      set_is_loading(false)
      return undefined
    }

    const controller = new AbortController()

    async function load_shifts() {
      set_is_loading(true)
      set_error('')

      try {
        const start = visible_range.start.toISOString().slice(0, 10)
        const endDate = new Date(visible_range.end)
        endDate.setDate(endDate.getDate() - 1)
        const end = endDate.toISOString().slice(0, 10)

        const [shiftsResp, coverageResp] = await Promise.all([
          api.get('/shifts', {
            signal: controller.signal,
            params: { limit: 2000 },
          }),
          api.get('/shifts/coverage/flags', {
            signal: controller.signal,
            params: { start_date: start, end_date: end },
          }),
        ])

        const data = shiftsResp.data
        const coverage = coverageResp.data
        setCoverageFlags(Array.isArray(coverage) ? coverage : [])

        if (controller.signal.aborted) {
          return
        }

        const next_events = data
          .filter((shift) => shift_overlaps_range(shift, visible_range))
          .map((shift) => map_shift_to_event(shift, current_user))

        set_events(next_events)
      } catch (request_error) {
        if (controller.signal.aborted) {
          return
        }

        set_events([])
        setCoverageFlags([])
        set_error(build_error_message(request_error))
      } finally {
        if (!controller.signal.aborted) {
          set_is_loading(false)
        }
      }
    }

    load_shifts()

    return () => controller.abort()
  }, [current_user, reload_key, visible_range, visible_range_key])

  const has_no_shifts = !is_loading && !error && events.length === 0
  const incompleteDays = new Set(
    coverageFlags
      .filter((item) => item.complete === false)
      .map((item) => item.date),
  )

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h2 className="text-3xl font-bold text-gray-800">Calendário de escalas</h2>
        <p className="text-sm text-gray-600">
          Visualize os turnos reais do período exibido. Ao navegar entre mês e semana, a página
          atualiza os dados do calendário automaticamente.
        </p>
      </header>

      {error ? (
        <div className="flex flex-col gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 md:flex-row md:items-center md:justify-between">
          <span>{error}</span>
          <button
            type="button"
            onClick={handle_retry}
            className="inline-flex items-center justify-center rounded-lg border border-red-300 bg-white px-3 py-2 font-medium text-red-700 transition-colors hover:bg-red-100"
          >
            Tentar novamente
          </button>
        </div>
      ) : null}

      {has_no_shifts ? (
        <div className="rounded-xl border border-yellow-200 bg-yellow-50 px-4 py-3 text-sm text-yellow-800">
          Nenhum turno foi encontrado para o período exibido no calendário.
        </div>
      ) : null}

      <section className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
        <div className="flex flex-col gap-2 border-b border-gray-200 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-800">Seus turnos</h3>
            <p className="text-sm text-gray-500">Profissional autenticado: {user?.name ?? '-'}</p>
          </div>
          {is_loading ? (
            <span className="inline-flex items-center rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
              Carregando turnos...
            </span>
          ) : (
            <span className="inline-flex items-center rounded-full bg-green-50 px-3 py-1 text-xs font-medium text-green-700">
              {events.length} turno{events.length === 1 ? '' : 's'} no período
            </span>
          )}
        </div>

        <div className="p-4">
          <div className="overflow-x-auto">
            <div className="min-w-[720px]">
              <FullCalendar
                plugins={[dayGridPlugin, timeGridPlugin]}
                locales={[ptBrLocale]}
                locale="pt-br"
                initialView="dayGridMonth"
                headerToolbar={{
                  left: 'prev,next today',
                  center: 'title',
                  right: 'dayGridMonth,timeGridWeek',
                }}
                buttonText={{
                  today: 'Hoje',
                  month: 'Mês',
                  week: 'Semana',
                }}
                firstDay={1}
                nowIndicator
                height="auto"
                dayMaxEvents={3}
                eventTimeFormat={{
                  hour: '2-digit',
                  minute: '2-digit',
                  hour12: false,
                }}
                events={events}
                datesSet={handle_dates_set}
                eventContent={render_event_content}
                dayCellClassNames={(arg) => {
                  const key = arg.date.toISOString().slice(0, 10)
                  return incompleteDays.has(key) ? ['bg-red-100'] : []
                }}
              />
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}

export default CalendarPage
