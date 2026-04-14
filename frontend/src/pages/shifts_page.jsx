import { useCallback, useEffect, useMemo, useState } from 'react'
import api from '../api/client.js'
import useAuth from '../hooks/use_auth.js'

// Formata datetime ISO para data legível no padrão brasileiro
function format_date(iso_string) {
  if (!iso_string) return '-'
  const date = new Date(iso_string)
  if (Number.isNaN(date.getTime())) return '-'
  return date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

// Formata datetime ISO para hora legível (HH:MM)
function format_time(iso_string) {
  if (!iso_string) return '-'
  const date = new Date(iso_string)
  if (Number.isNaN(date.getTime())) return '-'
  return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', hour12: false })
}

// Calcula duração em horas entre dois datetimes ISO
function calculate_duration(start_time, end_time) {
  const start = new Date(start_time)
  const end = new Date(end_time)
  const hours = (end.getTime() - start.getTime()) / (1000 * 60 * 60)
  if (!Number.isFinite(hours) || hours < 0) return '-'
  const rounded = Number(hours.toFixed(1))
  return `${rounded}h`
}

// Monta mensagem de erro amigável conforme código HTTP
function build_error_message(error) {
  const status = error?.response?.status
  if (status === 404) return 'Nenhum turno encontrado para este usuário.'
  if (status >= 500) return 'O servidor falhou ao carregar os turnos. Tente novamente.'
  return 'Não foi possível carregar os turnos.'
}

// Converte string "YYYY-MM-DD" para objeto Date no início do dia local
function parse_local_date(date_str) {
  if (!date_str) return null
  const [year, month, day] = date_str.split('-').map(Number)
  if (!year || !month || !day) return null
  return new Date(year, month - 1, day, 0, 0, 0, 0)
}

// Verifica se a string de texto está contida em algum campo textual do turno
function shift_matches_text(shift, search_lower) {
  if (!search_lower) return true
  const fields = [shift.title, shift.location, shift.description]
  return fields.some((field) => field?.toLowerCase().includes(search_lower))
}

// Verifica se o turno está dentro do intervalo de datas dos filtros
function shift_in_date_range(shift, date_from, date_to) {
  const shift_start = new Date(shift.start_time)
  if (date_from && shift_start < date_from) return false
  if (date_to) {
    const end_of_day = new Date(date_to)
    end_of_day.setHours(23, 59, 59, 999)
    if (shift_start > end_of_day) return false
  }
  return true
}

// Página de lista de turnos — exibe turnos reais do usuário autenticado com filtros
function ShiftsPage() {
  const { user } = useAuth()
  const [shifts, set_shifts] = useState([])
  const [is_loading, set_is_loading] = useState(true)
  const [error, set_error] = useState('')
  const [reload_key, set_reload_key] = useState(0)

  // Estado dos filtros
  const [filter_date_from, set_filter_date_from] = useState('')
  const [filter_date_to, set_filter_date_to] = useState('')
  const [filter_text, set_filter_text] = useState('')

  const handle_retry = useCallback(() => {
    set_reload_key((k) => k + 1)
  }, [])

  const handle_clear_filters = useCallback(() => {
    set_filter_date_from('')
    set_filter_date_to('')
    set_filter_text('')
  }, [])

  // Carrega turnos reais do backend usando o mesmo endpoint que /calendar
  useEffect(() => {
    if (!user?.id) {
      set_is_loading(false)
      return undefined
    }

    const controller = new AbortController()

    async function load_shifts() {
      set_is_loading(true)
      set_error('')

      try {
        const { data } = await api.get(`/shifts/agent/${user.id}`, {
          signal: controller.signal,
        })

        if (controller.signal.aborted) return

        // Ordena por data de início, mais recentes primeiro
        const sorted = [...data].sort(
          (a, b) => new Date(b.start_time).getTime() - new Date(a.start_time).getTime(),
        )
        set_shifts(sorted)
      } catch (request_error) {
        if (controller.signal.aborted) return
        set_shifts([])
        set_error(build_error_message(request_error))
      } finally {
        if (!controller.signal.aborted) set_is_loading(false)
      }
    }

    load_shifts()
    return () => controller.abort()
  }, [reload_key, user?.id])

  // Aplica filtros em memória — sem nova requisição ao backend
  const filtered_shifts = useMemo(() => {
    const search_lower = filter_text.trim().toLowerCase()
    const date_from = parse_local_date(filter_date_from)
    const date_to = parse_local_date(filter_date_to)

    return shifts.filter(
      (shift) =>
        shift_matches_text(shift, search_lower) && shift_in_date_range(shift, date_from, date_to),
    )
  }, [shifts, filter_text, filter_date_from, filter_date_to])

  const has_active_filters = filter_date_from || filter_date_to || filter_text.trim()
  const is_empty = !is_loading && !error && filtered_shifts.length === 0

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h2 className="text-3xl font-bold text-gray-800">Turnos</h2>
        <p className="text-sm text-gray-600">
          Lista completa dos seus turnos. Use os filtros para encontrar períodos específicos.
        </p>
      </header>

      {/* Área de filtros */}
      <section className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-gray-600" htmlFor="filter_date_from">
              Data inicial
            </label>
            <input
              id="filter_date_from"
              type="date"
              value={filter_date_from}
              onChange={(e) => set_filter_date_from(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-800 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-gray-600" htmlFor="filter_date_to">
              Data final
            </label>
            <input
              id="filter_date_to"
              type="date"
              value={filter_date_to}
              onChange={(e) => set_filter_date_to(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-800 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div className="flex flex-col gap-1 flex-1 min-w-[180px]">
            <label className="text-xs font-medium text-gray-600" htmlFor="filter_text">
              Busca (título, local, descrição)
            </label>
            <input
              id="filter_text"
              type="text"
              value={filter_text}
              onChange={(e) => set_filter_text(e.target.value)}
              placeholder="Buscar..."
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-800 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {has_active_filters ? (
            <button
              type="button"
              onClick={handle_clear_filters}
              className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
            >
              Limpar filtros
            </button>
          ) : null}
        </div>
      </section>

      {/* Feedback de erro */}
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

      {/* Tabela de turnos */}
      <section className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
        {/* Cabeçalho da seção */}
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
              {filtered_shifts.length} turno{filtered_shifts.length === 1 ? '' : 's'}
              {has_active_filters ? ' encontrado(s)' : ' no total'}
            </span>
          )}
        </div>

        {/* Estado: carregando */}
        {is_loading ? (
          <div className="flex items-center justify-center py-16 text-sm text-gray-500">
            Carregando turnos...
          </div>
        ) : null}

        {/* Estado: vazio */}
        {is_empty ? (
          <div className="px-4 py-10 text-center text-sm text-gray-500">
            {has_active_filters
              ? 'Nenhum turno encontrado para os filtros aplicados.'
              : 'Você não possui turnos cadastrados.'}
          </div>
        ) : null}

        {/* Tabela de dados */}
        {!is_loading && !error && filtered_shifts.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-semibold text-gray-600">Data</th>
                  <th className="px-4 py-3 text-left font-semibold text-gray-600">Início</th>
                  <th className="px-4 py-3 text-left font-semibold text-gray-600">Fim</th>
                  <th className="px-4 py-3 text-left font-semibold text-gray-600">Duração</th>
                  <th className="px-4 py-3 text-left font-semibold text-gray-600">Título</th>
                  <th className="px-4 py-3 text-left font-semibold text-gray-600">Local</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {filtered_shifts.map((shift) => (
                  <tr key={shift.id} className="transition-colors hover:bg-gray-50">
                    <td className="whitespace-nowrap px-4 py-3 text-gray-800">
                      {format_date(shift.start_time)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-gray-700">
                      {format_time(shift.start_time)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-gray-700">
                      {format_time(shift.end_time)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-gray-600">
                      {calculate_duration(shift.start_time, shift.end_time)}
                    </td>
                    <td className="px-4 py-3 text-gray-800">{shift.title || '-'}</td>
                    <td className="px-4 py-3 text-gray-600">{shift.location || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </div>
  )
}

export default ShiftsPage
