import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import interactionPlugin from '@fullcalendar/interaction'
import ptBrLocale from '@fullcalendar/core/locales/pt-br'
import api from '../api/client.js'
import useAuth from '../hooks/use_auth.js'
import {
  cancelFutureShiftRequest,
  createFutureShiftRequest,
  listFutureShiftRequests,
} from '../api/future_shift_requests.js'
import {
  adminReviewShiftRequest,
  createShiftRequest,
  listShiftRequests,
  respondShiftRequest,
} from '../api/shift_requests.js'

const SHIFT_PERIOD_OPTIONS = ['12H DIA', '12H NOITE', '10-22H', '24 HORAS']

function build_initial_range() {
  const now = new Date()
  return {
    start: new Date(now.getFullYear(), now.getMonth(), 1),
    end: new Date(now.getFullYear(), now.getMonth() + 1, 1),
  }
}

function map_shift_to_event(shift, currentUserId) {
  const ownShift = shift.agent_id === currentUserId
  return {
    id: `shift-${shift.id}`,
    title: `${shift.agent?.name || 'Profissional'} · ${shift.title?.trim() || 'Turno'}`,
    start: shift.start_time,
    end: shift.end_time,
    backgroundColor: ownShift ? '#2563eb' : '#6b7280',
    borderColor: ownShift ? '#1d4ed8' : '#4b5563',
    extendedProps: {
      status: 'confirmed',
      shift_id: shift.id,
      shift_period: inferPeriodFromShift(shift),
      location: shift.location ?? '',
    },
  }
}

function compactName(name) {
  const parts = (name || '').trim().split(/\s+/).filter(Boolean)
  if (parts.length <= 1) return (parts[0] || '—').slice(0, 14)
  const first = parts[0]
  const second = parts.length > 2 ? parts[parts.length - 1] : parts[1]
  const compact = `${first} ${second[0]}.`
  return compact.length > 14 ? `${compact.slice(0, 13)}…` : compact
}

function compactShiftTime(shift) {
  const start = new Date(shift.start_time)
  const end = new Date(shift.end_time)
  const s = `${String(start.getHours()).padStart(2, '0')}:${String(start.getMinutes()).padStart(2, '0')}`
  const e = `${String(end.getHours()).padStart(2, '0')}:${String(end.getMinutes()).padStart(2, '0')}`
  return `${s}-${e}`
}

function getVisibleShifts(shifts, limit) {
  if (!Array.isArray(shifts) || limit <= 0) return []
  return shifts.slice(0, limit)
}

function inferPeriodFromShift(shift) {
  const start = new Date(shift.start_time)
  const end = new Date(shift.end_time)
  const diff = (end.getTime() - start.getTime()) / (1000 * 60 * 60)
  const s = start.getHours()
  const e = end.getHours()
  if (diff >= 23) return '24 HORAS'
  if (s === 8 && e === 20) return '12H DIA'
  if (s === 20 && (e === 7 || e === 8)) return '12H NOITE'
  if (s === 10 && e === 22) return '10-22H'
  return '12H DIA'
}

function periodVisual(period) {
  const map = {
    '12H DIA': 'border-emerald-200 bg-emerald-100 text-emerald-800',
    '10-22H': 'border-blue-200 bg-blue-100 text-blue-800',
    '12H NOITE': 'border-violet-200 bg-violet-100 text-violet-800',
    '24 HORAS': 'border-gray-200 bg-gray-100 text-gray-700',
  }
  return map[period] || 'border-gray-200 bg-gray-100 text-gray-700'
}

const ShiftBadge = memo(function ShiftBadge({ shift, showTime, isOwn }) {
  const period = inferPeriodFromShift(shift)
  const periodClassName = periodVisual(period)
  const [start, end] = compactShiftTime(shift).split('-')
  const compactStart = start?.endsWith(':00') ? start.slice(0, 2) : start
  const compactEnd = end?.endsWith(':00') ? end.slice(0, 2) : end
  const time = `${compactStart}–${compactEnd}`
  return (
    <div
      data-testid={`day-shift-badge-${shift.id}`}
      className={`inline-flex min-h-6 w-full items-center gap-1 overflow-hidden rounded-md border px-1.5 py-0.5 text-[10px] font-medium leading-tight sm:text-[11px] ${periodClassName} ${isOwn ? 'ring-1 ring-blue-400/70' : ''}`}
      title={`${shift.agent?.name || 'Profissional'} · ${compactShiftTime(shift)} · ${period}`}
    >
      <span className="truncate">{compactName(shift.agent?.name || '')}</span>
      {showTime ? <span className="shrink-0 opacity-80">{time}</span> : null}
    </div>
  )
})

const MoreIndicator = memo(function MoreIndicator({ count }) {
  if (!count || count <= 0) return null
  return <div className="px-0.5 text-[10px] font-semibold leading-none text-gray-600 sm:text-[11px]">+{count}</div>
})

function map_request_to_event(request) {
  const start = `${request.requested_date}T08:00:00`
  const end = `${request.requested_date}T20:00:00`
  return {
    id: `future-request-${request.id}`,
    title: `Solicitação prévia · ${request.shift_period}`,
    start,
    end,
    backgroundColor: '#fde68a',
    borderColor: '#f59e0b',
    textColor: '#92400e',
    extendedProps: {
      status: 'pre_request',
      request_id: request.id,
    },
  }
}

function build_error_message(error) {
  const status = error?.response?.status
  if (status >= 500) return 'Falha ao carregar dados do calendário. Tente novamente.'
  return 'Não foi possível carregar os dados do período exibido.'
}

function unwrapSettled(result, fallback) {
  return result.status === 'fulfilled' ? result.value : fallback
}

function responseData(response, fallback = []) {
  return Array.isArray(response?.data) ? response.data : fallback
}

function CalendarPage() {
  const { user, isAdmin } = useAuth()
  const [visibleRange, setVisibleRange] = useState(() => build_initial_range())
  const [events, setEvents] = useState([])
  const [futureRequests, setFutureRequests] = useState([])
  const [shiftRequests, setShiftRequests] = useState([])
  const [daySlotsMap, setDaySlotsMap] = useState({})
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [requestError, setRequestError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)
  const [selectedDate, setSelectedDate] = useState('')
  const [menuOpen, setMenuOpen] = useState(false)
  const [agents, setAgents] = useState([])
  const [dayDetails, setDayDetails] = useState([])
  const [isCompactCalendar, setIsCompactCalendar] = useState(() => {
    if (typeof window === 'undefined') return false
    return window.innerWidth < 640
  })

  const [futureRequestForm, setFutureRequestForm] = useState({ requested_date: '', shift_period: SHIFT_PERIOD_OPTIONS[0], notes: '' })
  const [shiftRequestForm, setShiftRequestForm] = useState({ requested_date: '', shift_period: SHIFT_PERIOD_OPTIONS[0], note: '' })
  const [adminAddForm, setAdminAddForm] = useState({ requested_date: '', shift_period: SHIFT_PERIOD_OPTIONS[0], agent_id: '' })

  const lastRangeKey = useRef('')
  const visibleRangeKey = useMemo(() => `${visibleRange.start.toISOString()}::${visibleRange.end.toISOString()}`, [visibleRange])

  const handleDatesSet = useCallback((dateInfo) => {
    const nextStart = new Date(dateInfo.start)
    const nextEnd = new Date(dateInfo.end)
    const nextRangeKey = `${nextStart.toISOString()}::${nextEnd.toISOString()}`
    if (nextRangeKey === lastRangeKey.current) return
    lastRangeKey.current = nextRangeKey
    setVisibleRange({ start: nextStart, end: nextEnd })
  }, [])

  const reloadData = useCallback(() => setReloadKey((k) => k + 1), [])

  useEffect(() => {
    const onResize = () => setIsCompactCalendar(window.innerWidth < 640)
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  useEffect(() => {
    if (!user?.id) {
      setIsLoading(false)
      return undefined
    }

    const controller = new AbortController()

    async function loadData() {
      setIsLoading(true)
      setError('')
      try {
        const [rangeStartIso, rangeEndIso] = visibleRangeKey.split('::')
        const start = rangeStartIso.slice(0, 10)
        const endDate = new Date(rangeEndIso)
        endDate.setDate(endDate.getDate() - 1)
        const end = endDate.toISOString().slice(0, 10)

        const shiftEndpoint = isAdmin ? '/shifts/' : '/me/shifts'
        const tasks = [
          api.get(shiftEndpoint, { signal: controller.signal, params: { start_date: start, end_date: end } }),
          listFutureShiftRequests({ start_date: start, end_date: end }),
          listShiftRequests(),
          api.get('/shifts/day-config', { signal: controller.signal, params: { start_date: start, end_date: end } }),
        ]

        if (isAdmin) {
          tasks.push(api.get('/users/agents', { signal: controller.signal }))
        }

        const [myShiftsResp, requestList, shiftRequestList, dayConfigResp, agentsResp] = await Promise.allSettled(tasks)
        if (controller.signal.aborted) return

        const failures = [myShiftsResp, requestList, shiftRequestList, dayConfigResp, agentsResp]
          .filter((result) => result && result.status === 'rejected')

        const shifts = responseData(unwrapSettled(myShiftsResp, null))
        const preRequests = Array.isArray(unwrapSettled(requestList, [])) ? unwrapSettled(requestList, []) : []
        const requestFlow = Array.isArray(unwrapSettled(shiftRequestList, [])) ? unwrapSettled(shiftRequestList, []) : []
        const dayConfig = responseData(unwrapSettled(dayConfigResp, null))

        const mappedMap = {}
        dayConfig.forEach((entry) => {
          mappedMap[entry.date] = entry.slots || []
        })
        setDaySlotsMap(mappedMap)

        setFutureRequests(preRequests)
        setShiftRequests(requestFlow)
        setDayDetails(shifts)
        if (isAdmin) {
          const agentList = responseData(unwrapSettled(agentsResp, null))
          setAgents(agentList)
          if (agentList.length > 0 && !adminAddForm.agent_id) {
            setAdminAddForm((current) => ({ ...current, agent_id: String(agentList[0].id) }))
          }
        }

        setEvents([...shifts.map((s) => map_shift_to_event(s, user.id)), ...preRequests.map(map_request_to_event)])
        if (failures.length > 0) {
          setError('Calendário carregado parcialmente. Algumas informações auxiliares não responderam.')
        }
      } catch (requestErr) {
        if (controller.signal.aborted) return
        setEvents([])
        setError(build_error_message(requestErr))
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    loadData()
    return () => controller.abort()
  }, [user?.id, visibleRangeKey, reloadKey, isAdmin, adminAddForm.agent_id])

  const openDayActions = (dateString) => {
    setSelectedDate(dateString)
    setFutureRequestForm((c) => ({ ...c, requested_date: dateString }))
    setShiftRequestForm((c) => ({ ...c, requested_date: dateString }))
    setAdminAddForm((c) => ({ ...c, requested_date: dateString }))
    setMenuOpen(true)
  }

  const handleCreateFutureRequest = async (event) => {
    event.preventDefault()
    setRequestError('')
    try {
      await createFutureShiftRequest(futureRequestForm)
      reloadData()
    } catch (err) {
      setRequestError(err?.response?.data?.detail || 'Falha ao registrar solicitação prévia.')
    }
  }

  const handleCreateShiftRequest = async (event) => {
    event.preventDefault()
    setRequestError('')
    try {
      await createShiftRequest(shiftRequestForm)
      reloadData()
    } catch (err) {
      setRequestError(err?.response?.data?.detail || 'Falha ao solicitar plantão.')
    }
  }

  const handleAdminAdd = async (event) => {
    event.preventDefault()
    setRequestError('')
    try {
      const period = adminAddForm.shift_period
      const dateValue = adminAddForm.requested_date
      const startMap = { '12H DIA': '08:00:00', '12H NOITE': '20:00:00', '10-22H': '10:00:00', '24 HORAS': '00:00:00' }
      const endMap = { '12H DIA': '20:00:00', '12H NOITE': '08:00:00', '10-22H': '22:00:00', '24 HORAS': '00:00:00' }
      const plusOneDay = period === '12H NOITE' || period === '24 HORAS'
      const endDate = new Date(`${dateValue}T00:00:00`)
      if (plusOneDay) endDate.setDate(endDate.getDate() + 1)
      const endDateStr = endDate.toISOString().slice(0, 10)

      await api.post('/shifts/', {
        agent_id: Number(adminAddForm.agent_id),
        start_time: `${dateValue}T${startMap[period]}`,
        end_time: `${endDateStr}T${endMap[period]}`,
        title: `Plantão ${period}`,
      })
      reloadData()
    } catch (err) {
      setRequestError(err?.response?.data?.detail || 'Falha ao adicionar plantão como admin.')
    }
  }

  const selectedSlots = selectedDate ? daySlotsMap[selectedDate] || [] : []
  const daySummaryMap = useMemo(() => {
    const grouped = {}
    dayDetails.forEach((shift) => {
      const key = (shift.start_time || '').slice(0, 10)
      if (!key) return
      grouped[key] = grouped[key] || []
      grouped[key].push(shift)
    })
    return grouped
  }, [dayDetails])
  const selectedDayItems = selectedDate ? daySummaryMap[selectedDate] || [] : []
  const maxVisiblePerDay = isCompactCalendar ? 2 : 4
  const selectedDayItemsByPeriod = useMemo(() => {
    return selectedDayItems.reduce((acc, item) => {
      const period = inferPeriodFromShift(item)
      acc[period] = acc[period] || []
      acc[period].push(item)
      return acc
    }, {})
  }, [selectedDayItems])

  const handleDayCellMount = useCallback((arg) => {
    arg.el.classList.add('agentescala-day-cell')
    arg.el.setAttribute('role', 'button')
    arg.el.setAttribute('tabIndex', '0')
    arg.el.onclick = () => openDayActions(arg.date.toISOString().slice(0, 10))
    arg.el.onkeydown = (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault()
        openDayActions(arg.date.toISOString().slice(0, 10))
      }
    }
  }, [])

  const renderDayCellContent = useCallback((arg) => {
    const dateKey = arg.date.toISOString().slice(0, 10)
    const items = daySummaryMap[dateKey] || []
    const visibleShifts = getVisibleShifts(items, maxVisiblePerDay)
    const overflowCount = Math.max(items.length - visibleShifts.length, 0)

    return (
      <div className="flex h-full flex-col overflow-hidden">
        <div className="fc-daygrid-day-number mb-1 text-[11px] font-semibold text-gray-600">{arg.dayNumberText}</div>
        <div className="flex min-h-[84px] flex-col gap-1 overflow-hidden">
          {visibleShifts.map((shift) => (
            <ShiftBadge key={shift.id} shift={shift} showTime={!isCompactCalendar} isOwn={shift.agent_id === user?.id} />
          ))}
          <MoreIndicator count={overflowCount} />
        </div>
      </div>
    )
  }, [daySummaryMap, isCompactCalendar, maxVisiblePerDay, user?.id])

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h2 className="text-3xl font-bold text-gray-800">Calendário de escalas</h2>
        <p className="text-sm text-gray-600">Clique no dia para abrir ações rápidas (três pontos) conforme seu perfil.</p>
      </header>

      {error ? <div className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div> : null}

      <section className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
        <div className="p-4">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3 text-xs text-gray-600">
            <div className="flex flex-wrap items-center gap-4">
              <span className="inline-flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-blue-600" /> Confirmado</span>
              <span className="inline-flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-amber-400" /> Pré-solicitação</span>
            </div>
            {isLoading ? <span className="text-blue-700">Carregando calendário...</span> : null}
          </div>
          <div className="overflow-x-auto">
            <div className="min-w-[720px]">
              <FullCalendar
                plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
                locales={[ptBrLocale]}
                locale="pt-br"
                initialView="dayGridMonth"
                headerToolbar={{ left: 'prev,next today', center: 'title', right: 'dayGridMonth,timeGridWeek' }}
                buttonText={{ today: 'Hoje', month: 'Mês', week: 'Semana' }}
                firstDay={1}
                height="auto"
                dayMaxEvents={3}
                dayCellContent={renderDayCellContent}
                dayCellDidMount={handleDayCellMount}
                datesSet={handleDatesSet}
                events={events}
                dateClick={(info) => openDayActions(info.dateStr)}
              />
            </div>
          </div>
        </div>
      </section>

      {menuOpen ? (
        <>
          <button
            type="button"
            aria-label="Fechar painel"
            className="fixed inset-0 z-10 bg-black/35 md:hidden"
            onClick={() => setMenuOpen(false)}
          />
          <section className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm space-y-4 fixed inset-x-2 bottom-2 top-20 overflow-y-auto z-20 md:static md:inset-auto md:z-auto" role="dialog" aria-modal="true">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-800">Ações do dia {selectedDate}</h3>
            <button type="button" className="rounded border px-3 py-1.5 text-sm font-medium" onClick={() => setMenuOpen(false)}>Fechar</button>
          </div>

          {requestError ? <p className="text-sm text-red-600">{requestError}</p> : null}

          <div className="rounded-lg border border-gray-100 bg-gray-50 p-3">
            <p className="text-xs font-semibold text-gray-700 mb-2">Configuração dinâmica de turnos e limite médico</p>
            <div className="grid gap-2 md:grid-cols-2">
              {selectedSlots.map((slot) => (
                <div key={slot.period} className="rounded border border-gray-200 bg-white p-2 text-xs">
                  <div className="font-medium">{slot.period}</div>
                  <div>Limite: {slot.max_doctors} · Ocupado: {slot.occupied_count} · Disponível: {slot.remaining}</div>
                </div>
              ))}
              {selectedSlots.length === 0 ? <p className="text-xs text-gray-500">Sem configuração para o dia selecionado.</p> : null}
            </div>
          </div>

          <div className="rounded-lg border border-gray-100 bg-gray-50 p-3">
            <p className="text-xs font-semibold text-gray-700 mb-2">Escala completa do dia ({selectedDayItems.length})</p>
            <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
              {Object.entries(selectedDayItemsByPeriod).map(([period, items]) => (
                <div key={period} className="space-y-1.5">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-500">{period}</p>
                  {items.map((item) => (
                    <div key={item.id} className={`rounded border bg-white p-2.5 text-xs ${item.agent_id === user?.id ? 'border-blue-300 ring-1 ring-blue-100' : 'border-gray-200'}`}>
                      <div className="font-medium text-gray-800 break-words">{item.agent?.name || 'Profissional'}</div>
                      <div className="text-gray-600 mt-0.5">{compactShiftTime(item)}</div>
                    </div>
                  ))}
                </div>
              ))}
              {selectedDayItems.length === 0 ? <p className="rounded border border-dashed border-gray-300 bg-white p-3 text-xs text-gray-500">Sem plantonistas no dia selecionado.</p> : null}
            </div>
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <form onSubmit={handleCreateFutureRequest} className="rounded border border-amber-200 bg-amber-50 p-3 space-y-2">
              <p className="text-sm font-semibold text-amber-800">Solicitação prévia futura</p>
              <select value={futureRequestForm.shift_period} onChange={(e) => setFutureRequestForm((c) => ({ ...c, shift_period: e.target.value }))} className="w-full rounded border px-2 py-1 text-sm">
                {SHIFT_PERIOD_OPTIONS.map((item) => <option key={item} value={item}>{item}</option>)}
              </select>
              <button type="submit" className="rounded bg-amber-500 px-3 py-1 text-xs text-white">Registrar</button>
            </form>

            <form onSubmit={handleCreateShiftRequest} className="rounded border border-blue-200 bg-blue-50 p-3 space-y-2">
              <p className="text-sm font-semibold text-blue-800">Solicitar plantão no dia/turno</p>
              <select value={shiftRequestForm.shift_period} onChange={(e) => setShiftRequestForm((c) => ({ ...c, shift_period: e.target.value }))} className="w-full rounded border px-2 py-1 text-sm">
                {SHIFT_PERIOD_OPTIONS.map((item) => <option key={item} value={item}>{item}</option>)}
              </select>
              <input type="text" value={shiftRequestForm.note} onChange={(e) => setShiftRequestForm((c) => ({ ...c, note: e.target.value }))} className="w-full rounded border px-2 py-1 text-sm" placeholder="Observação opcional" />
              <button type="submit" className="rounded bg-blue-600 px-3 py-1 text-xs text-white">Solicitar plantão</button>
            </form>

            {isAdmin ? (
              <form onSubmit={handleAdminAdd} className="rounded border border-emerald-200 bg-emerald-50 p-3 space-y-2 lg:col-span-2">
                <p className="text-sm font-semibold text-emerald-800">Admin · adicionar plantão no dia</p>
                <div className="grid gap-2 md:grid-cols-3">
                  <select value={adminAddForm.shift_period} onChange={(e) => setAdminAddForm((c) => ({ ...c, shift_period: e.target.value }))} className="rounded border px-2 py-1 text-sm">
                    {SHIFT_PERIOD_OPTIONS.map((item) => <option key={item} value={item}>{item}</option>)}
                  </select>
                  <select value={adminAddForm.agent_id} onChange={(e) => setAdminAddForm((c) => ({ ...c, agent_id: e.target.value }))} className="rounded border px-2 py-1 text-sm">
                    {agents.map((agent) => <option key={agent.id} value={agent.id}>{agent.name}</option>)}
                  </select>
                  <button type="submit" className="rounded bg-emerald-600 px-3 py-1 text-xs text-white">Adicionar na escala</button>
                </div>
              </form>
            ) : null}
          </div>
          </section>
        </>
      ) : null}

      <section className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-800 mb-3">Solicitações de plantão (fluxo usuário/alvo/admin)</h3>
        <div className="space-y-2">
          {shiftRequests.map((item) => (
            <div key={item.id} className="rounded border border-gray-200 p-3 text-sm flex flex-wrap items-center gap-2 justify-between">
              <div>
                <p>#{item.id} · {item.requested_date} · {item.shift_period} · <strong>{item.status}</strong></p>
              </div>
              <div className="flex gap-2">
                {item.target_user_id === user?.id && item.status === 'pending_target' ? (
                  <>
                    <button type="button" onClick={() => respondShiftRequest(item.id, { accept: true }).then(reloadData)} className="rounded bg-green-600 px-2 py-1 text-xs text-white">Aceitar</button>
                    <button type="button" onClick={() => respondShiftRequest(item.id, { accept: false }).then(reloadData)} className="rounded bg-red-600 px-2 py-1 text-xs text-white">Recusar</button>
                  </>
                ) : null}
                {isAdmin && item.status === 'pending_admin' ? (
                  <>
                    <button type="button" onClick={() => adminReviewShiftRequest(item.id, { approve: true }).then(reloadData)} className="rounded bg-emerald-600 px-2 py-1 text-xs text-white">Aprovar</button>
                    <button type="button" onClick={() => adminReviewShiftRequest(item.id, { approve: false }).then(reloadData)} className="rounded bg-rose-600 px-2 py-1 text-xs text-white">Reprovar</button>
                  </>
                ) : null}
              </div>
            </div>
          ))}
          {shiftRequests.length === 0 ? <p className="text-sm text-gray-500">Sem solicitações no momento.</p> : null}
        </div>
      </section>

      <section className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-800 mb-3">Minhas solicitações prévias futuras</h3>
        <div className="space-y-2">
          {futureRequests.map((request) => (
            <div key={request.id} className="rounded border border-gray-200 p-3 text-sm flex items-center justify-between">
              <span>{request.requested_date} · {request.shift_period}</span>
              <button type="button" onClick={() => cancelFutureShiftRequest(request.id).then(reloadData)} className="rounded border border-red-300 px-2 py-1 text-xs text-red-700">Cancelar</button>
            </div>
          ))}
          {futureRequests.length === 0 ? <p className="text-sm text-gray-500">Sem solicitações prévias.</p> : null}
        </div>
      </section>
    </div>
  )
}

export default CalendarPage
