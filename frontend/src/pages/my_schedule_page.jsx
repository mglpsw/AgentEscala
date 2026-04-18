import { useCallback, useEffect, useMemo, useState } from 'react'
import api from '../api/client.js'

function formatDateTime(isoString) {
  const date = new Date(isoString)
  if (Number.isNaN(date.getTime())) return '-'
  return date.toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

function MySchedulePage() {
  const [month, setMonth] = useState('')
  const [shifts, setShifts] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  const loadShifts = useCallback(async () => {
    setIsLoading(true)
    setError('')
    try {
      const params = month ? { month } : {}
      const { data } = await api.get('/me/shifts', { params })
      setShifts(data)
    } catch {
      setShifts([])
      setError('Não foi possível carregar sua escala.')
    } finally {
      setIsLoading(false)
    }
  }, [month])

  useEffect(() => {
    loadShifts()
  }, [loadShifts])

  const handleExport = async () => {
    const params = month ? { month } : {}
    const response = await api.get('/me/shifts/export.ics', {
      params,
      responseType: 'blob',
    })
    const url = window.URL.createObjectURL(response.data)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'minha_escala.ics'
    anchor.click()
    window.URL.revokeObjectURL(url)
  }


  const handleExportMonthlyConsolidated = async () => {
    const target = month || new Date().toISOString().slice(0, 7)
    const [yearStr, monthStr] = target.split('-')
    const response = await api.get('/shifts/export/monthly-consolidated', {
      params: { year: Number(yearStr), month: Number(monthStr) },
      responseType: 'blob',
    })
    const url = window.URL.createObjectURL(response.data)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `escala_consolidada_${target}.xlsx`
    anchor.click()
    window.URL.revokeObjectURL(url)
  }

  const sorted = useMemo(
    () => [...shifts].sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime()),
    [shifts],
  )

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-3xl font-bold text-gray-800">Minha Escala</h2>
        <p className="text-sm text-gray-600">Visualize e exporte apenas os seus plantões.</p>
      </header>

      <section className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex flex-col gap-1">
            <label htmlFor="month_filter" className="text-xs text-gray-600">Mês</label>
            <input
              id="month_filter"
              type="month"
              value={month}
              onChange={(event) => setMonth(event.target.value)}
              className="rounded border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
          <button
            type="button"
            onClick={loadShifts}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Aplicar filtro
          </button>
          <button
            type="button"
            onClick={handleExport}
            className="rounded border border-blue-300 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 hover:bg-blue-100"
          >
            Exportar minha escala
          </button>
          <button
            type="button"
            onClick={handleExportMonthlyConsolidated}
            className="rounded border border-emerald-300 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700 hover:bg-emerald-100"
          >
            Exportar consolidado mensal (todos)
          </button>
        </div>
      </section>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <section className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
        <div className="border-b border-gray-200 px-4 py-3 text-sm text-gray-600">
          {isLoading ? 'Carregando...' : `${sorted.length} plantão(ões)`}
        </div>
        {!isLoading && sorted.length === 0 ? (
          <div className="p-6 text-sm text-gray-500">Nenhum plantão encontrado para os filtros selecionados.</div>
        ) : null}
        {!isLoading && sorted.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50 text-left text-xs font-semibold uppercase text-gray-600">
                <tr>
                  <th className="px-4 py-3">Título</th>
                  <th className="px-4 py-3">Início</th>
                  <th className="px-4 py-3">Fim</th>
                  <th className="px-4 py-3">Local</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {sorted.map((shift) => (
                  <tr key={shift.id}>
                    <td className="px-4 py-3 text-gray-800">{shift.title || 'Turno de trabalho'}</td>
                    <td className="px-4 py-3 text-gray-700">{formatDateTime(shift.start_time)}</td>
                    <td className="px-4 py-3 text-gray-700">{formatDateTime(shift.end_time)}</td>
                    <td className="px-4 py-3 text-gray-700">{shift.location || '-'}</td>
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

export default MySchedulePage
